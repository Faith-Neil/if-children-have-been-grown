# 为什么有这个文件：单节正文落盘前/落盘后的后置自动化核验器（TV-M0-T26）。
# 它解决什么问题：本地模型分节写长标书容易把历史标书里的旧甲方名、旧型号抄进新正文（串标），或让工期/SLA/质保期
# 与全局事实表打架，以及高分评分点只喊口号没有实质落地举措；这里把四类风险扫成按节警示，汇入覆盖视图 confirm_reasons，
# 绝不静默把有问题的正文标成合规。

from __future__ import annotations

import json
import re
from typing import Any

from icg.domain.writing_knowledge_prompt import allowed_identity_names, foreign_entity_names

_COMMITMENT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(分钟|小时|个工作日|工作日|自然日|天|日|周|个月|月|年|人|名|次|台|套|%|％)"
)
_SLOGAN = re.compile(r"完全满足招标|全力配合|完全响应|保质保量|优质服务|一流水平")
_GAP_MARKER = re.compile(r"待确认|待人工补充|待补")

# 指标词 → 事实表字段。同一指标在正文不同小节取值不一致、或与事实表不一致，都算冲突。
_FACT_METRICS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("service_period", ("服务期限", "服务期", "维保期", "运维期", "工期"), "服务期限"),
    ("warranty_period", ("质保期", "免费维保期", "保修期"), "质保期"),
    ("sla_response", ("响应时限", "故障响应", "SLA"), "SLA响应"),
    ("on_site_staff", ("驻场人数", "驻场人员", "驻场"), "驻场人数"),
)

# 跨节数字冲突检查的指标词（事实表查不到时也横向互查）
_CROSS_METRICS: tuple[tuple[str, str], ...] = tuple(
    (kw, label) for _field, kws, label in _FACT_METRICS for kw in kws[:2]
)

# 指标词的兼容单位：真机验收发现窗口内无关数字（驻场句里的30分钟、服务期句里的7×24小时）被误抓为承诺值，
# 造成大量核验假阳性。服务期/质保只认日历单位，SLA 只认分钟/小时，驻场只认人/名。
_CALENDAR_UNITS = frozenset({"个月", "月", "年", "周", "天", "日", "自然日", "工作日", "个工作日"})
_METRIC_FIELD_UNITS: dict[str, frozenset[str]] = {
    "service_period": _CALENDAR_UNITS,
    "warranty_period": _CALENDAR_UNITS,
    "sla_response": frozenset({"分钟", "小时"}),
    "on_site_staff": frozenset({"人", "名"}),
}
_KEYWORD_FIELD: dict[str, str] = {kw: field for field, kws, _label in _FACT_METRICS for kw in kws}

# 国家部委、监管机构与标准制定组织白名单：正文引用其规范/标准属合规引用，不算外项目实体残留。
# 只放国家级标准引用常名；省市级委办局仍可能是旧甲方，不在此列。
_VERIFY_ORG_ALLOWLIST = (
    "国务院", "工业和信息化部", "财政部", "发展改革委", "中国人民银行", "银保监会", "金融监管总局",
    "证监会", "国家卫健委", "卫生健康委员会", "国家税务总局", "国家邮政局", "国家药监局",
    "国家医保局", "国家统计局", "国家能源局", "国家数据局", "国家档案局", "国家保密局",
    "国家密码管理局", "国家市场监督管理总局", "国家标准化管理委员会", "中国质量认证中心",
    "国家信息中心", "中国信息安全测评中心",
)

# 实体名只出现在“严禁出现XX/符合XX要求/经核查无冲突”这类自否定或合规引用句中时不报警
_NEGATED_CONTEXT = re.compile(
    r"不(?:得|应|需|允许|再|会)(?:出现|包含|引用|照抄|提及|使用)|严禁|禁止|"
    r"经核查|核查(?:一致|通过)|无冲突|未发现(?:冲突|问题|异常|残留)|符合(?:要求|标准|规范|招标)"
)
# 最终警示文本自否定兜底：含“经核查/无冲突”等表述的条目不得进入 verify_warnings
_SELF_NEGATED = re.compile(r"经核查|无冲突|未发现冲突")


def _shares_org_suffix(name: str, allowed: set[str]) -> bool:
    """匹配段与放行身份共享 ≥4 字后缀（如"大数据局"承接"星河市大数据局"）时视为同一机构的简称引用。"""
    for ident in allowed:
        ident = str(ident or "").strip()
        if len(ident) < 4:
            continue
        for cut in range(4, min(len(name), len(ident)) + 1):
            if name.endswith(ident[-cut:]) and ident.endswith(ident[-cut:]):
                return True
    return False


def _verify_org_allowed(name: str) -> bool:
    return any(token in name for token in _VERIFY_ORG_ALLOWLIST)


def _name_only_in_negated_context(body: str, name: str) -> bool:
    """该实体名在正文中的每次出现都落在自否定/合规引用句里时为 True，不报警。"""
    occurrences = list(re.finditer(re.escape(name), body))
    if not occurrences:
        return False
    for match in occurrences:
        seg_start = max(body.rfind(c, 0, match.start()) for c in "。；;\n") + 1
        tail_ends = [body.find(c, match.end()) for c in "。；;\n"]
        seg_end = min((e for e in tail_ends if e >= 0), default=len(body))
        if not _NEGATED_CONTEXT.search(body[seg_start:seg_end]):
            return False
    return True


def _metric_commitments(text: str, keyword: str, window: int = 24) -> set[str]:
    """指标词附近窗口内的数字承诺（如 服务期限3年 / 响应不超过30分钟）。
    按指标兼容单位过滤：驻场句旁的30分钟、服务期句旁的24小时不再误抓为承诺值。"""
    allowed_units = _METRIC_FIELD_UNITS.get(_KEYWORD_FIELD.get(keyword, ""), frozenset())
    found: set[str] = set()
    blob = str(text or "")
    for match in re.finditer(re.escape(keyword), blob):
        seg = blob[match.end():match.end() + window]
        for num, unit in _COMMITMENT.findall(seg):
            if not allowed_units or unit in allowed_units or _UNIT_SYNONYMS.get(unit, unit) in allowed_units:
                found.add(_norm_commitment(num, unit))
        seg_back = blob[max(0, match.start() - window):match.start()]
        for num, unit in _COMMITMENT.findall(seg_back):
            if not allowed_units or unit in allowed_units or _UNIT_SYNONYMS.get(unit, unit) in allowed_units:
                found.add(_norm_commitment(num, unit))
    return found


# 量词同义归一：驻场 2名/2人/2位 是同一承诺；分钟/分、小时/钟头同理。
# 真机验收假阳性：正文取2名与事实表驻场2人被误报冲突。
_UNIT_SYNONYMS = {"名": "人", "位": "人", "个": "人", "分": "分钟", "钟头": "小时", "％": "%"}


def _norm_commitment(num: str, unit: str) -> str:
    return f"{num}{_UNIT_SYNONYMS.get(unit, unit)}"


def _sheet_commitments(value: str, field: str = "") -> set[str]:
    allowed_units = _METRIC_FIELD_UNITS.get(field, frozenset())
    return {
        _norm_commitment(num, unit)
        for num, unit in _COMMITMENT.findall(str(value or ""))
        if not allowed_units or unit in allowed_units or _UNIT_SYNONYMS.get(unit, unit) in allowed_units
    }


def _fact_conflicts(body: str, sheet: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for field, keywords, label in _FACT_METRICS:
        fact_val = str(sheet.get(field) or "").strip()
        if not fact_val:
            continue
        fact_nums = _sheet_commitments(fact_val, field)
        if not fact_nums:
            continue
        for kw in keywords:
            body_nums = _metric_commitments(body, kw)
            clashing = sorted(n for n in body_nums if n not in fact_nums)
            if clashing:
                warnings.append(f"与全局事实表冲突：{label}正文取{'、'.join(clashing[:3])}，事实表为{fact_val[:40]}")
                break
    return warnings


def _minutes(num: str, unit: str) -> int:
    value = int(float(num))
    return value * 60 if unit == "小时" else value


def _sla_expectations(sheet: dict[str, Any]) -> dict[str, dict[str, int]]:
    """从当前项目 Global Fact Sheet 的 sla_response 动态解析分级 SLA，不写死任何项目数字。"""
    text = str(sheet.get("sla_response") or "")
    expected: dict[str, dict[str, int]] = {}
    for level in ("一级故障", "二级故障", "三级故障"):
        start = text.find(level)
        if start < 0:
            continue
        ends = [text.find(other, start + len(level)) for other in ("一级故障", "二级故障", "三级故障")]
        end = min((x for x in ends if x > start), default=len(text))
        segment = text[start:end]
        item: dict[str, int] = {}
        match = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:到达现场|到场)", segment)
        if match:
            item["onsite_minutes"] = _minutes(match.group(1), match.group(2))
        match = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:完成)?修复", segment)
        if match:
            item["repair_minutes"] = _minutes(match.group(1), match.group(2))
        match = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:电话)?响应", segment)
        if match:
            item["response_minutes"] = _minutes(match.group(1), match.group(2))
        if item:
            expected[level] = item
    return expected


def _sla_fact_conflicts(body: str, sheet: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    expected = _sla_expectations(sheet)
    for level, want in expected.items():
        onsite = want.get("onsite_minutes")
        if onsite:
            for match in re.finditer(level + r"[^。；\n]{0,36}?(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:到达现场|到场)", body):
                got = _minutes(match.group(1), match.group(2))
                if got != onsite:
                    warnings.append(f"与全局事实表冲突：{level}到场正文取{got}分钟，事实表为{onsite}分钟")
                    break
        repair = want.get("repair_minutes")
        if repair:
            for match in re.finditer(level + r"[^。；\n]{0,42}?(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:完成)?修复", body):
                got = _minutes(match.group(1), match.group(2))
                if got != repair:
                    warnings.append(f"与全局事实表冲突：{level}修复正文取{got}分钟，事实表为{repair}分钟")
                    break
        response = want.get("response_minutes")
        if response:
            for match in re.finditer(level + r"[^。；\n]{0,36}?(\d+(?:\.\d+)?)\s*(分钟|小时)\s*(?:内)?(?:电话)?响应", body):
                got = _minutes(match.group(1), match.group(2))
                if got != response:
                    warnings.append(f"与全局事实表冲突：{level}响应正文取{got}分钟，事实表为{response}分钟")
                    break
    return warnings


def _asset_total(sheet: dict[str, Any]) -> int | None:
    rows = sheet.get("asset_inventory") or []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and "合计" in str(row.get("category") or ""):
                match = re.search(r"(\d+)\s*套", str(row.get("subtotal") or ""))
                if match:
                    return int(match.group(1))
    profile = str((sheet.get("asset_profile") or {}).get("databases") or "")
    match = re.search(r"(\d+)\s*套", profile)
    return int(match.group(1)) if match else None


def _team_mentions(body: str) -> set[int]:
    """提取正文中明确陈述的团队总人数/角色人数，用于跨节一致性比对（不判断哪个数正确）。"""
    found: set[int] = set()
    for match in re.finditer(r"项目总监\s*[+＋]\s*(\d+)\s*[人名]", body):
        found.add(int(match.group(1)) + 1)
    for line in body.splitlines():
        if "DBA工程师" in line and "|" in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and re.fullmatch(r"\d+", cells[1]):
                found.add(int(cells[1]))
    for match in re.finditer(r"(?:共|合计|团队)\s*(\d+)\s*[人名]", body):
        found.add(int(match.group(1)))
    return found


def _team_capacity_conflicts(body: str, sheet: dict[str, Any]) -> list[str]:
    """按当前项目资产总量动态校验「人数×每人负责套数」是否覆盖资产，不写死人数或资产数。"""
    total = _asset_total(sheet)
    if not total:
        return []
    warnings: list[str] = []
    for match in re.finditer(r"每人负责\s*(\d+)\s*套", body):
        per = int(match.group(1))
        for staff in sorted(_team_mentions(body)):
            if staff and staff * per < total:
                warnings.append(f"团队配置容量冲突：{staff}人×每人{per}套仅覆盖{staff * per}套，低于资产总量{total}套")
                return warnings
    return warnings


def _case_year_conflicts(body: str, sheet: dict[str, Any]) -> list[str]:
    """从评分事实动态读取案例年限；正文出现不同年限时报警。"""
    blob = json.dumps({k: sheet.get(k) for k in ("scoring_rules", "scoring_decisions")}, ensure_ascii=False)
    expected = sorted(set(re.findall(r"近[一二三四五六七八九十两三四五]年", blob)))
    if not expected:
        return []
    want = expected[0]
    warnings: list[str] = []
    for match in re.finditer(r"近[一二三四五六七八九十两三四五]年[^。；\n]{0,24}(?:案例|证明材料|数据库问题)", body):
        if not match.group(0).startswith(want):
            warnings.append(f"与全局事实表冲突：案例年限正文取{match.group(0)[:12]}，事实表为{want}")
            break
    return warnings


def _scoring_gaps(body: str, rows: list[dict]) -> list[str]:
    """挂载评分点实质响应核验：要求原文的关键词在正文里完全缺席、或正文只剩口号时给警示。"""
    warnings: list[str] = []
    text = str(body or "")
    thin = len(re.sub(r"\s|待确认|待补", "", text)) < 60
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if row.get("section_kind") != "scoring" and not row.get("score_item"):
            continue
        source = str(row.get("extracted_summary") or row.get("text") or "").strip()
        if not source:
            continue
        tokens = [tok for tok in re.findall(r"[\u4e00-\u9fff]{4,}|[A-Za-z0-9\-]{3,}", source) if tok not in ("本项目",)]
        # 真机误报修正：长中文连续串（如"每月提交巡检报告"）正文里插一字即整串不中。
        # 切为 4 字片段，任一片段命中即视为有实质响应痕迹——本核验只抓"完全缺席/空喊口号"。
        phrases: list[str] = []
        for tok in tokens[:6]:
            if len(tok) > 4 and all("一" <= ch <= "鿿" for ch in tok):
                phrases.extend(tok[i:i + 4] for i in range(0, len(tok), 4) if len(tok[i:i + 4]) >= 2)
            else:
                phrases.append(tok)
        hit = any(ph in text for ph in phrases)
        if not hit or thin:
            clip = source[:30] + ("…" if len(source) > 30 else "")
            warnings.append(f"评分点疑似未实质响应：{clip}")
            break
    if _SLOGAN.search(text) and thin:
        warnings.append("疑似空泛承诺：有口号缺落地举措")
    return warnings


def verify_sections(workflow: dict | None, sections: list[dict]) -> dict[str, Any]:
    """对 sections=[{key,title,body,task,rows}] 做后置核验。

    返回 {"sections": {key: [warnings]}, "summary": {"checked": n, "warned": m, "warnings": total}}。
    警示不是阻断：覆盖视图按 confirm_reasons 提示人工复核，不把核验失败静默标合规。
    """
    from icg.domain.technical_fact_sheet import prompt_fact_sheet_json

    wf = workflow or {}
    sheet = prompt_fact_sheet_json(wf)
    allowed = allowed_identity_names(wf)
    per_section: dict[str, list[str]] = {}

    # 第一遍：节内检查（外实体串标、事实表冲突、评分点实质响应）
    for sec in sections:
        key = str(sec.get("key") or "")
        body = str(sec.get("body") or "")
        warnings: list[str] = []
        if not body.strip() or body.strip() in ("待补", "（待补）"):
            warnings.append("正文为空或仅有占位符")
            per_section[key] = warnings
            continue
        foreign = [
            name for name in foreign_entity_names([body], allowed)
            if not _verify_org_allowed(name) and not _name_only_in_negated_context(body, name)
            and not _shares_org_suffix(name, allowed)
        ]
        for name in foreign[:3]:
            warnings.append(f"疑似外项目实体残留：{name}")
        warnings.extend(_fact_conflicts(body, sheet))
        warnings.extend(_sla_fact_conflicts(body, sheet))
        warnings.extend(_team_capacity_conflicts(body, sheet))
        warnings.extend(_case_year_conflicts(body, sheet))
        warnings.extend(_scoring_gaps(body, sec.get("rows") or []))
        per_section[key] = [w for w in warnings if not _SELF_NEGATED.search(w)]

    # 第二遍：跨节同一指标数字口径互查（SLA、服务期、质保等前后矛盾）
    metric_map: dict[str, dict[str, set[str]]] = {}
    for sec in sections:
        key = str(sec.get("key") or "")
        body = str(sec.get("body") or "")
        for kw, label in _CROSS_METRICS:
            nums = _metric_commitments(body, kw)
            if nums:
                metric_map.setdefault(label, {})[key] = nums
    for label, by_key in metric_map.items():
        if len(by_key) < 2:
            continue
        all_nums: set[str] = set().union(*by_key.values())
        if len(all_nums) < 2:
            continue
        for key, nums in by_key.items():
            others = sorted(all_nums - nums)
            if others:
                per_section.setdefault(key, []).append(
                    f"跨节口径冲突：{label}本节取{'、'.join(sorted(nums)[:2])}，他节出现{'、'.join(others[:2])}"
                )

    # 跨节团队人数互查：不预设正确人数，只检出同一项目不同章节给出冲突人数。
    team_map: dict[str, set[int]] = {}
    for sec in sections:
        key = str(sec.get("key") or "")
        mentions = _team_mentions(str(sec.get("body") or ""))
        if mentions:
            team_map[key] = mentions
    all_team = set().union(*team_map.values()) if team_map else set()
    if len(all_team) > 1:
        for key, nums in team_map.items():
            others = sorted(all_team - nums)
            if others:
                per_section.setdefault(key, []).append(
                    f"跨节口径冲突：团队人数本节取{'、'.join(str(x) for x in sorted(nums)[:2])}，他节出现{'、'.join(str(x) for x in others[:2])}"
                )

    warned = sum(1 for warns in per_section.values() if warns)
    total = sum(len(warns) for warns in per_section.values())
    return {
        "sections": per_section,
        "summary": {"checked": len(sections), "warned": warned, "warnings": total},
    }
