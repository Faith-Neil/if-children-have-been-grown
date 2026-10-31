# 为什么有这个文件：PRD v1.8 §5.8.1 中依赖正文内容的一期规则 R36、R39、R40、R41、R42、R43、R44。
# 它解决什么问题：这些规则原先未实现，合标核对清单只能写“未运行”。这里按现有数据能核到的范围实现，
# 数据还没有的子项（结构化人员条件、盖章标记、安全事件记录、风格样例、产品字典）在结果里明确写“未核对”，不冒充通过。
# R21、R22 为 PRD 二期；R33 拟派人员条件与 R38 证明材料对应见 staff_proof_rules.py。

from __future__ import annotations

import re
from typing import Any

from .scope_rules import _bigrams, _system_chapter, paragraphs_of, tender_text

VOLUME_NAMES = {"technical": "技术分册", "business": "商务分册"}


def _result(rule_id: str, title: str, issues: list[dict], *, ok: str, fail: str, suggestion: str, details: dict | None = None):
    from .compliance_rules import ComplianceRuleResult
    worst = "blocker" if any(i["severity"] == "blocker" for i in issues) else (
        "warning" if any(i["severity"] == "warning" for i in issues) else "info")
    passed = not [i for i in issues if i["severity"] != "info"]
    return ComplianceRuleResult(rule_id=rule_id, title=title, severity="info" if passed else worst, passed=passed,
                                finding_summary=ok if not issues else fail.format(n=len(issues)),
                                suggestion="" if not issues else suggestion, issues=issues, details=details or {})


def _issue(rule_id: str, code: str, severity: str, message: str, **links) -> dict:
    from .compliance_rules import ComplianceRuleIssue
    from .domain import new_id
    details = links.pop("details", {})
    return ComplianceRuleIssue(id=new_id("issue"), rule_id=rule_id, code=code, severity=severity, message=message,
                               details=details, **links).to_dict()


def _chapters(state: Any, project: Any, volume: str = "all") -> list:
    positions = {cid: i for i, cid in enumerate((state.workflows.get(project.id) or {}).get("chapter_order", []))}
    rows = [c for c in state.chapters.values() if c.project_id == project.id and (volume == "all" or c.volume == volume)]
    return sorted(rows, key=lambda c: positions.get(c.id, len(positions)))


def _library(state: Any, project: Any, kind: str) -> list[dict]:
    return [i for i in state.library.values() if i.get("company_id") == project.company_id and i.get("type") == kind
            and i.get("status") != "rejected" and len(str(i.get("name") or "").strip()) >= 2]


def _rows(workflow: dict, volume: str = "all") -> list[dict]:
    return [r for r in (workflow.get("requirements") or {}).values()
            if r.get("status") != "rejected" and (volume == "all" or r.get("volume") == volume)]


# ---------------------------------------------------------------------------
# R36 跨分册一致性
# ---------------------------------------------------------------------------

def check_r36(state: Any, project: Any, workflow: dict, volume: str = "all"):
    from .project_access import project_volumes
    title = "跨分册一致性"
    if len(project_volumes(state, project.id)) < 2:
        return _result("R36", title, [], ok="只有一个分册在系统内编制：R36 未运行，须人工核对。", fail="", suggestion="",
                       details={"skipped": "single_volume"})
    if volume != "all":
        return _result("R36", title, [], ok="跨分册一致性只在全文检查与导出前运行。", fail="", suggestion="",
                       details={"skipped": "volume_check"})
    tech = "\n".join(c.content or "" for c in _chapters(state, project, "technical"))
    biz = "\n".join(c.content or "" for c in _chapters(state, project, "business"))
    biz_evidence = {eid for r in _rows(workflow, "business") for eid in r.get("evidence_ids") or []}
    issues = []
    for item in _library(state, project, "qualification"):
        if item["name"] in tech and item["id"] not in biz_evidence and item["name"] not in biz:
            issues.append(_issue("R36", "CROSS_VOLUME_QUALIFICATION_MISSING", "blocker",
                                 f"技术分册提到资质《{item['name']}》，商务分册没有对应的证明材料。",
                                 evidence_id=item["id"], details={"name": item["name"]}))
    for person in _library(state, project, "personnel"):
        if person["name"] in tech and person["name"] not in biz:
            issues.append(_issue("R36", "CROSS_VOLUME_PERSONNEL_MISMATCH", "blocker",
                                 f"技术分册的人员“{person['name']}”不在商务分册的人员一览中。", details={"name": person["name"]}))
    negative = [r for r in _rows(workflow) if str(r.get("deviation_type") or "").lower() in ("negative", "负偏离")]
    if negative:
        for name, text in (("技术分册", tech), ("商务分册", biz)):
            if re.search(r"无(任何)?偏离|完全响应全部|全部无偏离", text):
                issues.append(_issue("R36", "CROSS_VOLUME_DEVIATION_MISMATCH", "warning",
                                     f"矩阵登记了 {len(negative)} 条负偏离，但{name}写有“无偏离”，两册偏离口径不一致。"))
    return _result("R36", title, issues, ok="两册的资质、人员与偏离口径一致（按资料库名称比对）。",
                   fail="发现 {n} 处跨分册不一致。", suggestion="在另一分册补齐证明材料或统一人员表、偏离口径。",
                   details={"evidence_version_check": "未核对：章节引用不带资料版本号"})


# ---------------------------------------------------------------------------
# R39 披露类条款
# ---------------------------------------------------------------------------

_DISCLOSE_REQ = re.compile(r"安全隐患|行政处罚|责任事故|重大违法|违法违规记录|须披露|如实披露|披露")
_DISCLOSE_TEXT = re.compile(r"披露|未(发生|受到|有)[^。；]{0,12}(处罚|事故|违法|隐患)|无[^。；]{0,8}(处罚|事故|违法)记录|(处罚|事故)情况如下")


def check_r39(state: Any, project: Any, workflow: dict, volume: str = "all"):
    issues = []
    for row in _rows(workflow, volume):
        if not _DISCLOSE_REQ.search(str(row.get("text") or "")):
            continue
        chapter = state.chapters.get(row.get("chapter_id") or "")
        content = chapter.content if chapter else ""
        if not chapter or not _DISCLOSE_TEXT.search(content or ""):
            issues.append(_issue("R39", "DISCLOSURE_MISSING", "blocker",
                                 f"招标要求披露：{str(row['text'])[:50]}；对应章节没有披露段落。",
                                 requirement_id=row["id"], chapter_id=row.get("chapter_id")))
        else:
            # 资料库还没有“安全与合规事件记录”，无记录不等于没有发生：只能请负责人确认
            issues.append(_issue("R39", "DISCLOSURE_UNVERIFIED", "warning",
                                 f"《{chapter.title}》有披露段落，但资料库没有安全与合规事件记录可比对，须项目负责人确认已核实。",
                                 requirement_id=row["id"], chapter_id=chapter.id))
    return _result("R39", "披露类条款", issues, ok="招标未要求披露安全或处罚事项。", fail="{n} 条披露类条款须处理。",
                   suggestion="补写披露段落；核实后由项目负责人放行警告。")


# ---------------------------------------------------------------------------
# R40 评审索引表
# ---------------------------------------------------------------------------

_INDEX_REQUIRED = re.compile(r"评审索引表|评分索引表|评分对照表|评审因素索引|索引表")
_INDEX_TITLE = re.compile(r"评审索引|评分索引|索引表|评分对照")


def _factor(text: str) -> str:
    head = re.split(r"[（(:：|]", re.sub(r"^\s*[0-9.()（）]+\s*", "", str(text)), maxsplit=1)[0]
    return head.strip()[:20]


def check_r40(state: Any, project: Any, workflow: dict, volume: str = "all"):
    if not _INDEX_REQUIRED.search(tender_text(workflow)):
        return _result("R40", "评审索引表", [], ok="招标未要求评审索引表。", fail="", suggestion="")
    chapters = _chapters(state, project)
    index = next((c for c in chapters if _INDEX_TITLE.search(c.title)), None)
    if volume != "all" and index is not None and index.volume != volume:
        return _result("R40", "评审索引表", [], ok="索引表不在本分册。", fail="", suggestion="")
    issues = []
    if index is None or not (index.content or "").strip():
        issues.append(_issue("R40", "REVIEW_INDEX_MISSING", "blocker", "招标要求评审索引表，正文中没有索引表章节或内容为空。"))
        return _result("R40", "评审索引表", issues, ok="", fail="缺评审索引表。", suggestion="在技术分册生成评审索引表。")
    lines = [l for l in index.content.splitlines() if l.strip().startswith("|") and not re.match(r"^\|\s*-", l.strip())]
    factors = [(r, _factor(r.get("text"))) for r in _rows(workflow) if r.get("category") == "scoring" and r.get("score")]
    positions = []
    for row, factor in factors:
        want = _bigrams(factor)
        hit = next((i for i, line in enumerate(lines) if want and len(want & _bigrams(line)) / len(want) >= 0.6), None)
        if hit is None:
            issues.append(_issue("R40", "REVIEW_INDEX_ITEM_MISSING", "blocker", f"评审索引表漏列评分项“{factor}”。",
                                 requirement_id=row["id"], chapter_id=index.id))
        else:
            positions.append(hit)
    if positions != sorted(positions):
        issues.append(_issue("R40", "REVIEW_INDEX_ORDER", "warning", "评审索引表的顺序与评审标准不一致。", chapter_id=index.id))
    for line in lines:
        for number in re.findall(r"第\s*(\d+)\s*章", line):
            if int(number) > len(chapters):
                issues.append(_issue("R40", "REVIEW_INDEX_TARGET_MISSING", "blocker",
                                     f"评审索引表指向第 {number} 章，正文没有这一章。", chapter_id=index.id))
    return _result("R40", "评审索引表", issues, ok="评审索引表覆盖全部评分项，顺序与指向正确。",
                   fail="评审索引表有 {n} 处问题。", suggestion="补齐漏项、按评审标准排序并修正指向；页码列合标后由商务填写。",
                   details={"scoring_items": len(factors), "index_rows": len(lines)})


# ---------------------------------------------------------------------------
# R41 证明材料齐全与盖章
# ---------------------------------------------------------------------------

_PROOF = re.compile(r"证明|证书|复印件|扫描件|营业执照|截图|合同|发票|授权书|审计报告|证明材料")
_SEAL = re.compile(r"加盖(单位)?公章|盖章|骑缝章")


def check_r41(state: Any, project: Any, workflow: dict, volume: str = "all"):
    issues = []
    for row in _rows(workflow, volume):
        text = str(row.get("text") or "")
        if not _PROOF.search(text) or row.get("evidence_ids"):
            continue
        qualification = row.get("section_kind") == "qualification" or row.get("category") in ("qualification", "mandatory")
        scoring = row.get("category") == "scoring" or row.get("section_kind") == "scoring"
        if qualification:
            issues.append(_issue("R41", "PROOF_MATERIAL_MISSING", "blocker", f"资格项要求证明材料，尚未挂接：{text[:50]}",
                                 requirement_id=row["id"]))
        elif scoring:
            issues.append(_issue("R41", "SCORING_PROOF_MISSING", "warning", f"评分项要求证明材料，尚未挂接：{text[:50]}",
                                 requirement_id=row["id"]))
    if _SEAL.search(tender_text(workflow)):
        issues.append(_issue("R41", "SEAL_STATUS_UNVERIFIED", "info",
                             "招标要求盖章：附件尚无“已盖章”标记，盖章状态须人工核对。"))
    return _result("R41", "证明材料齐全与盖章", issues, ok="要求证明材料的资格项与评分项均已挂接附件。",
                   fail="{n} 项证明材料或盖章须处理。", suggestion="到资料库补录并挂接；盖章在系统外完成并核对。",
                   details={"per_person_check": "未核对：资料库尚无逐人证明材料清单"})


# ---------------------------------------------------------------------------
# R42 暗标
# ---------------------------------------------------------------------------

_CONTACT = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)|(?<!\d)0\d{2,3}-?\d{7,8}(?!\d)|[\w.+-]+@[\w-]+\.[\w.]+")


def _company_names(state: Any, project: Any) -> set[str]:
    names = set()
    stored = ((getattr(state, "service_stores", {}) or {}).get("company_settings") or {}).get(project.company_id) or {}
    if hasattr(stored, "model_dump"):
        stored = stored.model_dump()
    for key in ("company_name", "short_name", "company_short_name"):
        value = str(stored.get(key) or "").strip()
        if len(value) >= 2:
            names.add(value)
    for value in (stored.get("custom_settings") or {}).get("blind_bid_names") or []:
        if len(str(value).strip()) >= 2:
            names.add(str(value).strip())
    return names


def blind_volume(workflow: dict) -> str | None:
    """招标要求暗标时的暗标分册：只写商务暗标时为商务分册，否则为技术分册；未要求暗标为 None。导出版式也用它。"""
    tender = tender_text(workflow)
    if "暗标" not in tender:
        return None
    return "business" if re.search(r"商务[^。；\n]{0,10}暗标", tender) and not re.search(r"技术[^。；\n]{0,10}暗标", tender) else "technical"


def check_r42(state: Any, project: Any, workflow: dict, volume: str = "all"):
    blind = blind_volume(workflow)
    if blind is None:
        return _result("R42", "暗标", [], ok="招标未要求暗标。", fail="", suggestion="")
    if volume not in ("all", blind):
        return _result("R42", "暗标", [], ok=f"暗标分册为{VOLUME_NAMES[blind]}，本分册不查。", fail="", suggestion="")
    names = _company_names(state, project) | {p["name"] for p in _library(state, project, "personnel")}
    issues = []
    for chapter in _chapters(state, project, blind):
        for index, paragraph in enumerate(paragraphs_of(chapter.content)):
            found = sorted({n for n in names if n in paragraph} | set(_CONTACT.findall(paragraph)))
            if found:
                issues.append(_issue("R42", "BLIND_BID_IDENTITY", "blocker",
                                     f"暗标分册《{chapter.title}》第 {index + 1} 段出现可识别投标人的信息：{'、'.join(found[:5])}",
                                     chapter_id=chapter.id, details={"paragraph_index": index, "quote": paragraph.strip()[:120]}))
    return _result("R42", "暗标", issues, ok=f"暗标分册（{VOLUME_NAMES[blind]}）正文未出现公司名称、人员姓名或联系方式。",
                   fail="暗标分册有 {n} 处可识别信息。", suggestion="删除或替换为“投标人”“项目经理”等中性称呼。",
                   details={"blind_volume": blind, "checked_names": len(names),
                            "not_checked": "页眉页脚、水印、文档属性、插入附件由导出版式核对"})


# ---------------------------------------------------------------------------
# R43 AI 腔调
# ---------------------------------------------------------------------------

CLICHES = ("全方位", "全流程", "全生命周期", "一站式", "高度重视", "强有力", "有力保障", "坚实保障", "保驾护航", "赋能",
           "深度融合", "无缝衔接", "行业领先", "国内领先", "业界领先", "精益求精", "尽善尽美", "竭诚", "鼎力", "倾力打造",
           "打造", "助力", "全面提升", "显著提升", "大幅提升", "切实保障", "确保万无一失", "高效便捷", "先进的理念",
           "完善的体系", "丰富的经验", "专业的团队", "优质的服务", "持续优化", "不断创新")
PATTERNS = {
    "否定对比“不是……而是……”": (re.compile(r"不是[^。！？\n]{1,30}而是"), 1),
    "递进“不仅……更/还……”": (re.compile(r"不仅[^。！？\n]{1,30}(更|还|而且)"), 1),
    "序列“首先……其次……最后”": (re.compile(r"首先[\s\S]{1,400}?其次[\s\S]{1,400}?最后"), 1),
}
SUMMARY = re.compile(r"^(总之|综上所述|总而言之|综上|由此可见)")
CLICHE_DENSITY = 3.0       # 每千字，PRD 示例值，试运行校准
OPENING_REPEAT = 3


def check_r43(state: Any, project: Any, workflow: dict, volume: str = "all"):
    tender = tender_text(workflow)
    words = [w for w in CLICHES if w not in tender]  # 招标原文出现过的词自动放行
    issues = []
    for chapter in _chapters(state, project, volume):
        content = chapter.content or ""
        if not content.strip() or _system_chapter(workflow, chapter):
            continue
        body = [p.strip() for p in paragraphs_of(content) if p.strip() and not p.strip().startswith(("#", "|"))]
        chars = max(1, len(re.sub(r"\s", "", "".join(body))))
        findings = []
        hits = {w: content.count(w) for w in words if w in content}
        density = sum(hits.values()) * 1000 / chars
        if density > CLICHE_DENSITY:
            findings.append(f"套话每千字 {density:.1f} 次（{'、'.join(sorted(hits, key=lambda w: -hits[w])[:6])}）")
        for label, (pattern, allowed) in PATTERNS.items():
            count = len(pattern.findall(content))
            if count > allowed:
                findings.append(f"{label} {count} 次（允许 {allowed} 次）")
        summaries = [i for i, p in enumerate(body) if SUMMARY.match(p) and 0 < i < len(body) - 1]
        if summaries:
            findings.append(f"段末总结句出现在中间段落 {len(summaries)} 处")
        openings = [p[:3] for p in body]
        for i in range(len(openings) - OPENING_REPEAT + 1):
            window = openings[i:i + OPENING_REPEAT]
            if len(set(window)) == 1 and len(window[0]) == 3:
                findings.append(f"连续 {OPENING_REPEAT} 段以“{window[0]}”开头")
                break
        if findings:
            issues.append(_issue("R43", "AI_TONE", "warning", f"《{chapter.title}》AI 腔调：" + "；".join(findings),
                                 chapter_id=chapter.id, details={"findings": findings}))
    return _result("R43", "AI 腔调检查", issues, ok="未发现超阈值的套话或禁用句式。", fail="{n} 个章节有 AI 腔调问题。",
                   suggestion="只改命中的句子：换成具体做法、数字或案例；系统不自动删除。",
                   details={"cliche_words": len(words), "style_sample_check": "未核对：尚无注入风格样例"})


# ---------------------------------------------------------------------------
# R44 事实密度
# ---------------------------------------------------------------------------

_FACT_NUMBER = re.compile(r"\d+(\.\d+)?\s*(分钟|小时|工作日|天|日|月|年|次|人|名|台|套|个|%|％|TB|GB|万|元|项)")


def check_r44(state: Any, project: Any, workflow: dict, volume: str = "all"):
    from .generation_context import project_facts
    facts = {str(f.get("value") or "") for f in project_facts(state, project.id) if f.get("status") == "confirmed"}
    names = {p["name"] for kind in ("personnel", "performance") for p in _library(state, project, kind)}
    issues = []
    scored = {}
    for row in _rows(workflow, volume):
        if row.get("category") == "scoring" and row.get("chapter_id"):
            scored.setdefault(row["chapter_id"], []).append(row)
    for chapter_id, rows in scored.items():
        chapter = state.chapters.get(chapter_id)
        if chapter is None or not (chapter.content or "").strip() or _system_chapter(workflow, chapter):
            continue
        content = chapter.content
        count = (len(_FACT_NUMBER.findall(content)) + sum(1 for v in facts if len(v) >= 2 and v in content)
                 + sum(1 for n in names if n in content) + len(re.findall(r"\{\{\s*(fact|sla):", content))
                 + len(re.findall(r"\[证:[^\]]+\]", content)))
        if count < max(1, len(rows)):
            issues.append(_issue("R44", "LOW_FACT_DENSITY", "warning",
                                 f"《{chapter.title}》回应 {len(rows)} 个评分项，只找到 {count} 个可核验的具体事实（数字、人员、案例、证据或事实变量）。",
                                 chapter_id=chapter.id, details={"facts_found": count, "scoring_items": len(rows)}))
    return _result("R44", "事实密度检查", issues, ok="得分章节的可核验事实不少于评分项数。",
                   fail="{n} 个得分章节事实不足。", suggestion="补充有来源的数字、人员、案例或挂接证据；没有依据的写【待补】，禁止编造。",
                   details={"unverified_fact_check": "未核对：尚无产品字典与事实锚点识别", "min_facts_per_scoring_item": 1})
