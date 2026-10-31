# 为什么有这个文件：导出递交版时同时生成“合标核对清单”（PRD v1.8 §5.9.2，APP-M2-T200）。
# 它解决什么问题：合标由商务负责人在系统外完成，清单把合标时必须人工核对的 9 类事项和本批次全文检查结论列在一起；
# 只列事实与系统结论，不替代人工核对；某条规则在本批次检查里没有结果时明确写“未运行，须人工核对”，不冒充已检查。
# 清单随导出批次保存；分册解锁或正文改动后标“已过期”，仍可下载。

from __future__ import annotations

import re
from typing import Any

VOLUME_NAMES = {"technical": "技术分册", "business": "商务分册"}
CHARS_PER_PAGE = 700  # A4 宋体小四单倍行距约 700 字/页；只作估算，合标后以 Word 实际页数为准

ITEMS = [
    ("分册与文件", "核对文件齐全，插入系统外编制的内容"),
    ("页码与目录", "按招标要求调整页码，更新目录；以合标后的 Word 核对准确页数是否满足页数限制"),
    ("评审索引表", "合标后填写索引表页码"),
    ("两本之间的一致性结论", "复核合标后没有引入不一致（例如替换了人员表）"),
    ("偏离表与点对点应答", "核对合标后偏离表与正文仍一致"),
    ("密封、份数、装订", "按要求打印、装订、密封"),
    ("签章", "完成签章"),
    ("暗标", "确认合标时没有把带公司名称的内容放入暗标分册"),
    ("文件命名", "核对合标后的文件名符合招标要求，且不含编写人姓名"),
]

_PATTERNS = {
    "outside": re.compile(r"报价文件|开标一览表|报价一览表|分项报价|报价表|投标报价函"),
    "pages": re.compile(r"页码|页数|连续编号|分册编号|不超过\s*\d+\s*页|目录"),
    "seal": re.compile(r"正本|副本|密封|装订|胶装|份数|\d+\s*份"),
    "sign": re.compile(r"签字|盖章|签章|公章|法定代表人.{0,6}签|骑缝章"),
    "blind": re.compile(r"暗标"),
    "naming": re.compile(r"命名|文件名|电子文件|电子版"),
}


def tender_lines(workflow: dict, pattern: re.Pattern, limit: int = 12) -> list[dict]:
    """从招标文件原文逐页取命中行，带文件名和页码，供合标人回查。"""
    found: list[dict] = []
    seen: set[str] = set()
    for record in (workflow.get("files") or {}).values():
        pages = record.get("pages")
        pages = pages if isinstance(pages, list) else [record.get("content") or ""]
        for page_no, text in enumerate(pages, start=1):
            for raw in str(text).splitlines():
                line = raw.strip()
                if len(line) < 4 or not pattern.search(line) or line in seen:
                    continue
                seen.add(line)
                found.append({"text": line[:200], "file": record.get("filename", ""), "page": page_no})
                if len(found) >= limit:
                    return found
    return found


def _source(row: dict) -> str:
    return f"{row['file']} 第 {row['page']} 页" if row.get("file") else f"第 {row['page']} 页"


def estimate_pages(text: str) -> int:
    body = re.sub(r"\s+", "", text or "")
    headings = len(re.findall(r"^#", text or "", re.M))
    return max(1, -(-len(body) // CHARS_PER_PAGE) + headings // 6)


def _rule(check: dict, rule_id: str) -> dict | None:
    return next((r for r in check.get("rules", []) if r.get("rule_id") == rule_id), None)


def _rule_line(check: dict, rule_id: str, label: str) -> dict:
    result = _rule(check, rule_id)
    if result is None:
        return {"text": f"{rule_id} {label}：本系统尚未实现该检查，未运行，须人工核对。", "status": "not_run"}
    released = [i for i in check.get("issues", []) if i.get("rule_id") == rule_id and i.get("released")]
    open_issues = [i for i in check.get("issues", []) if i.get("rule_id") == rule_id and not i.get("released")]
    if result.get("passed"):
        text = f"{rule_id} {label}：通过。{result.get('finding_summary', '')}"
        status = "passed"
    else:
        text = f"{rule_id} {label}：未通过，{len(open_issues)} 项未处理。{result.get('finding_summary', '')}"
        status = "failed"
    if released:
        text += "；已放行：" + "；".join(f"{i.get('message', '')}（理由：{i['released'].get('reason', '')}）" for i in released[:5])
    return {"text": text, "status": status}


def build_merge_checklist(state: Any, project: Any, workflow: dict, record: dict, check: dict, *, now_iso: str) -> dict:
    chapters = [c for c in state.chapters.values() if c.project_id == project.id]
    positions = {cid: i for i, cid in enumerate(workflow.get("chapter_order", []))}
    chapters.sort(key=lambda c: positions.get(c.id, len(positions)))
    exported = [v["volume"] for v in record.get("volumes", [])]
    documents = record.get("documents", {})
    numbering = {c.id: f"{i + 1}" for i, c in enumerate(chapters)}
    sections: list[dict] = []

    def add(index: int, rows: list[dict]) -> None:
        title, action = ITEMS[index]
        sections.append({"no": index + 1, "item": title, "action": action, "rows": rows or [{"text": "（无）"}]})

    # 1 分册与文件
    rows = [{"text": f"{VOLUME_NAMES[v['volume']]}：{v['filename']}，估算 {estimate_pages(documents.get(v['volume'], {}).get('content', ''))} 页"}
            for v in record.get("volumes", [])]
    for line in tender_lines(workflow, _PATTERNS["outside"], 5):
        rows.append({"text": f"系统外编制，需人工插入或另行递交：{line['text']}", "source": _source(line)})
    add(0, rows)

    # 2 页码与目录
    rows = [{"text": "各分册页码从 1 起编排；页数为估算值，以合标后 Word 为准。"}]
    rows += [{"text": f"招标要求：{line['text']}", "source": _source(line)} for line in tender_lines(workflow, _PATTERNS["pages"], 6)]
    r24 = _rule(check, "R24")
    if r24 is not None:
        rows.append({"text": f"R24 格式要求：{'通过' if r24.get('passed') else '未通过'}。{r24.get('finding_summary', '')}"})
    add(1, rows)

    # 3 评审索引表
    index_chapters = [c for c in chapters if re.search(r"评审索引|评分索引|索引表", c.title)]
    rows = [{"text": f"索引表位于{VOLUME_NAMES.get(c.volume, c.volume)}第 {numbering[c.id]} 章《{c.title}》；页码列为空，合标后填写。"}
            for c in index_chapters] or [{"text": "系统内没有评审索引表章节；如招标要求，合标时须人工编制。", "status": "manual"}]
    for req in (workflow.get("requirements") or {}).values():
        if req.get("section_kind") == "scoring" or req.get("category") == "scoring":
            target = next((c for c in chapters if c.id == req.get("chapter_id")), None)
            where = f"第 {numbering[target.id]} 章《{target.title}》" if target else "尚未对应章节"
            score = f"（{req['score']:g} 分）" if isinstance(req.get("score"), (int, float)) else ""
            rows.append({"text": f"评分项{score}：{str(req.get('text', ''))[:60]} → {where}；页码：合标后填写"})
    add(2, rows[:40])

    # 4 两本之间的一致性结论
    rows = []
    if len(exported) < 2:
        rows.append({"text": "只有一个分册在系统内编制：R36 未运行，须人工核对人员、资质、偏离口径与证据版本。", "status": "not_run"})
    else:
        rows.append(_rule_line(check, "R36", "跨册人员、资质、偏离口径与证据版本一致"))
    rows.append(_rule_line(check, "R10", "SLA 数值一致"))
    rows.append(_rule_line(check, "R27", "服务期、质保期等项目事实一致"))
    rows.append({"text": f"依据本批次全文检查 {check.get('id', '')}（{check.get('created_at', '')}）。"})
    add(3, rows)

    # 5 偏离表与点对点应答
    deviations = [r for r in (workflow.get("requirements") or {}).values()
                  if str(r.get("deviation_type") or "").lower() not in ("", "none", "no_deviation", "无偏离", "无")]
    rows = []
    for c in chapters:
        if "偏离" in c.title:
            rows.append({"text": f"偏离表位于{VOLUME_NAMES.get(c.volume, c.volume)}第 {numbering[c.id]} 章《{c.title}》；"
                                 + (f"偏离 {len(deviations)} 条。" if deviations else "无偏离。")})
        if re.search(r"点对点|逐条应答|逐条响应", c.title):
            rows.append({"text": f"点对点应答位于{VOLUME_NAMES.get(c.volume, c.volume)}第 {numbering[c.id]} 章《{c.title}》。"})
    if not rows:
        rows.append({"text": f"系统内没有偏离表或点对点应答章节；矩阵登记偏离 {len(deviations)} 条，合标时须人工核对。", "status": "manual"})
    add(4, rows)

    # 6 密封、份数、装订
    add(5, [{"text": line["text"], "source": _source(line)} for line in tender_lines(workflow, _PATTERNS["seal"])]
        or [{"text": "招标文件中未识别到份数、密封或装订要求，须人工核对原文。", "status": "manual"}])

    # 7 签章
    rows = [{"text": line["text"], "source": _source(line)} for line in tender_lines(workflow, _PATTERNS["sign"])]
    rows.append(_rule_line(check, "R41", "证明材料齐全与盖章"))
    add(6, rows)

    # 8 暗标
    blind = tender_lines(workflow, _PATTERNS["blind"], 5)
    if blind:
        rows = [{"text": line["text"], "source": _source(line)} for line in blind] + [_rule_line(check, "R42", "暗标")]
    else:
        rows = [{"text": "招标文件中未识别到暗标要求。"}]
    add(7, rows)

    # 9 文件命名
    rows = [{"text": f"递交版文件名：{v['filename']}"} for v in record.get("volumes", [])]
    rows += [{"text": f"招标要求：{line['text']}", "source": _source(line)} for line in tender_lines(workflow, _PATTERNS["naming"], 5)]
    add(8, rows)

    return {"export_id": record["id"], "check_id": check.get("id"), "project_name": project.name,
            "generated_at": now_iso, "volumes": exported, "sections": sections,
            "volume_epochs": dict(workflow.get("volume_epochs") or {})}


def checklist_stale(workflow: dict, checklist: dict, current_fingerprint: str, record_fingerprint: str) -> bool:
    """分册解锁（epoch 变化）或正文/资料改动（指纹变化）后清单过期。"""
    return (current_fingerprint != record_fingerprint
            or dict(workflow.get("volume_epochs") or {}) != (checklist.get("volume_epochs") or {}))


def checklist_sheets(checklist: dict, *, stale: bool) -> list[dict]:
    header = [
        [f"合标核对清单 · {checklist['project_name']}"],
        [f"导出批次 {checklist['export_id']} · 全文检查 {checklist.get('check_id') or ''} · 生成 {checklist['generated_at']}"
         + (" · 【已过期：分册已解锁或正文已改动，仅供追溯】" if stale else "")],
        ["本清单只列事实与系统检查结论，不替代人工核对；合标结果不回传系统。"],
        [],
        ["序号", "核对项", "清单内容（系统生成）", "原文位置", "合标时由人做什么", "核对结果（人工填写）"],
    ]
    rows = list(header)
    for section in checklist["sections"]:
        for i, row in enumerate(section["rows"]):
            rows.append([section["no"] if i == 0 else "", section["item"] if i == 0 else "", row.get("text", ""),
                         row.get("source", ""), section["action"] if i == 0 else "", ""])
    return [{"name": "合标核对清单", "rows": rows, "widths": [6, 16, 70, 22, 34, 18], "header_rows": 5}]
