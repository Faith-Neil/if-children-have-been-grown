# 为什么有这个文件：编辑台“问题”页签的本章问题清单与段落定位（APP-M2-T166 / PRD v1.8 §5.11.2 问题侧栏、§5.11.6 第 5 项、§5.7.3）。
# 它解决什么问题：
# 1. 本章问题原先分散在三处：合规检查批次（workflow.checks）、章节循环与人工处理队列（workflow.human_queue）、
#    对话助手写入后的增量复查（workflow.chapter_edit_operations[].recheck）与粘贴识别复查（workflow.edit_rechecks）；
#    编辑台只读了最近一次任意分册的检查，不看队列、不看编辑后复查，也不能定位到段落。
# 2. 问题只记了行号（paragraph_index）与原句（quote），正文一改行号就错位。这里统一折算成段落键（APP-M2-T161）：
#    先认问题产生时记下的段落键，再按原句在当前正文中唯一找到的段落，最后只在正文版本没变时才信行号；都对不上的标“未能定位”，不猜。
# 3. 编辑后复查的问题按当前正文重跑同一套文字规则：段落里已不再出现的标“已解决”（§5.11.6 第 5 项末段）。

from __future__ import annotations

from typing import Any

from . import paragraph_keys
from .domain import DemoState, DomainError, Principal

ORIGIN_LABELS = {"check": "合规检查", "loop": "章节循环", "edit_recheck": "编辑后复查"}

# 处理路径：章节循环沿用 §5.7.4 第 4 条的判定；检查批次按严重程度，阻断须改正文，警告可改或由负责人放行。
ROUTE_LABELS = {
    "auto_fix": "自动修正",
    "direct_human": "直接转人工",
    "escalated_human": "修正两次仍在，转人工",
    "must_fix": "须修改",
    "fix_or_release": "修改或放行",
    "hint": "仅提示",
}

STATUS_LABELS = {
    "open": "待处理",
    "pending_fix": "待自动修正",
    "pending_human": "待人工处理",
    "released": "已放行",
    "resolved": "已解决",
    "human_handled": "人工已处理",
    "rejected": "已驳回",
}
OPEN_STATES = {"open", "pending_fix", "pending_human"}

_BLOCKER = {"blocker", "blocking", "critical", "high"}
_WARNING = {"warning", "medium"}


def _severity(value: str | None) -> str:
    value = (value or "").lower()
    if value in _BLOCKER:
        return "blocker"
    if value in _WARNING:
        return "warning"
    return "info"


def _blocks(chapter: Any) -> list[dict]:
    lines = chapter.content.splitlines()
    out = []
    for p in paragraph_keys.current(chapter):
        out.append({**p, "text": "\n".join(lines[p["line_start"]:p["line_end"] + 1])})
    return out


def _quote_core(quote: str | None) -> str:
    text = (quote or "").strip().rstrip("…").strip()
    return text[:60]


def _block_for_line(blocks: list[dict], line: int | None) -> dict | None:
    if not isinstance(line, int):
        return None
    return next((b for b in blocks if b["line_start"] <= line <= b["line_end"]), None)


def key_for_line(chapter: Any, line: int | None) -> str | None:
    """产生问题时把行号折算成段落键记下来；以后正文改了，段落键仍跟着这一段走。"""
    try:
        block = _block_for_line(_blocks(chapter), line)
    except Exception:  # 段落表补算失败时不影响检查本身
        return None
    return block["key"] if block else None


def annotate_check_issues(state: DemoState, issues: list[dict]) -> None:
    """检查批次里带段落下标的问题补上段落键（字典 v1.9 chapter_check_issue.paragraph_key）。"""
    cache: dict[str, list[dict]] = {}
    for issue in issues:
        chapter = state.chapters.get(issue.get("chapter_id") or "")
        index = (issue.get("details") or {}).get("paragraph_index")
        if chapter is None or not isinstance(index, int) or issue.get("paragraph_key"):
            continue
        if chapter.id not in cache:
            try:
                cache[chapter.id] = _blocks(chapter)
            except Exception:
                cache[chapter.id] = []
        block = _block_for_line(cache[chapter.id], index)
        if block:
            issue["paragraph_key"] = block["key"]


def locate(blocks: list[dict], *, key: str | None, quote: str | None, line: int | None,
           line_trusted: bool) -> tuple[dict | None, str]:
    """返回 (段落, 定位方式)。定位方式：key / quote / line / none / chapter。"""
    if key:
        block = next((b for b in blocks if b["key"] == key), None)
        if block:
            return block, "key"
    core = _quote_core(quote)
    if len(core) >= 4:
        hits = [b for b in blocks if core in b["text"]]
        if len(hits) == 1:
            return hits[0], "quote"
    if line_trusted:
        block = _block_for_line(blocks, line)
        if block:
            return block, "line"
    if key or core or isinstance(line, int):
        return None, "none"
    return None, "chapter"


LOCATE_NOTES = {
    "none": "原段落已改动或删除，未能定位",
    "chapter": "整章问题",
}


def _latest_check(workflow: dict, volume: str) -> dict | None:
    candidates = [c for c in (workflow.get("checks") or {}).values()
                  if c.get("volume") in (volume, "all")]
    return max(candidates, key=lambda c: c.get("created_at") or "", default=None)


def _check_items(state: DemoState, project_id: str, chapter: Any, workflow: dict, blocks: list[dict],
                 fingerprint: str | None) -> tuple[list[dict], dict | None]:
    check = _latest_check(workflow, chapter.volume)
    if check is None:
        return [], None
    stale = bool(fingerprint) and check.get("fingerprint") != fingerprint
    revisions = check.get("chapter_revisions") or {}
    line_trusted = revisions.get(chapter.id) == chapter.revision
    items = []
    for issue in check.get("issues") or []:
        if issue.get("chapter_id") != chapter.id:
            continue
        details = issue.get("details") or {}
        severity = _severity(issue.get("severity"))
        quote = details.get("quote") or ""
        block, how = locate(blocks, key=issue.get("paragraph_key"), quote=quote,
                            line=details.get("paragraph_index"), line_trusted=line_trusted)
        status = "released" if issue.get("released") else "open"
        items.append({
            "id": f"check:{check['id']}:{issue['id']}", "origin": "check", "origin_label": ORIGIN_LABELS["check"],
            "rule_id": issue.get("rule_id") or "", "code": issue.get("code") or "",
            "severity": severity, "message": issue.get("message") or "", "quote": quote,
            "route": "must_fix" if severity == "blocker" else "fix_or_release" if severity == "warning" else "hint",
            "status": status, "stale": stale,
            "paragraph_key": block["key"] if block else None,
            "line_start": block["line_start"] if block else None, "line_end": block["line_end"] if block else None,
            "located_by": how, "check_id": check["id"], "issue_id": issue["id"],
            "created_at": check.get("created_at"),
        })
    return items, {"id": check["id"], "volume": check.get("volume"), "created_at": check.get("created_at"),
                   "stale": stale, "passed": bool(check.get("passed"))}


def _loop_items(chapter: Any, workflow: dict, blocks: list[dict]) -> tuple[list[dict], dict | None]:
    store = workflow.get("human_queue") or {}
    loop = (store.get("loops") or {}).get(chapter.id)
    line_trusted = bool(loop) and loop.get("result_revision") == chapter.revision
    items = []
    for issue in (store.get("issues") or {}).values():
        if issue.get("chapter_id") != chapter.id or issue.get("status") == "void":
            continue
        block, how = locate(blocks, key=issue.get("paragraph_key"), quote=issue.get("quote"),
                            line=issue.get("paragraph_index"), line_trusted=line_trusted and issue.get("status") in OPEN_STATES)
        items.append({
            "id": f"loop:{issue['id']}", "origin": "loop", "origin_label": ORIGIN_LABELS["loop"],
            "rule_id": issue.get("rule") or "", "code": issue.get("code") or "",
            "severity": _severity(issue.get("level") or issue.get("severity")),
            "message": issue.get("message") or "", "quote": issue.get("quote") or "",
            "suggestion": issue.get("suggestion") or "",
            "route": issue.get("route") or "direct_human", "status": issue.get("status") or "pending_human",
            "human_reason_label": issue.get("human_reason_label") or "", "stale": False,
            "paragraph_key": block["key"] if block else None,
            "line_start": block["line_start"] if block else None, "line_end": block["line_end"] if block else None,
            "located_by": how, "human_issue_id": issue["id"], "number": issue.get("number"),
            "created_at": issue.get("updated_at") or issue.get("created_at"),
        })
    summary = None
    if loop:
        summary = {"loop_no": loop.get("loop_no"), "status": loop.get("status"),
                   "result_revision": loop.get("result_revision"), "started_at": loop.get("started_at")}
    return items, summary


def _known(state: DemoState, project_id: str, chapter_id: str, workflow: dict, *extra: str) -> set[str]:
    from .selection_rewrite import _known_numbers
    facts = [str(f.get("value")) for f in (workflow.get("facts") or {}).values() if f.get("status") == "confirmed"]
    rows = [str(r.get("text")) for r in (workflow.get("requirements") or {}).values()
            if r.get("chapter_id") == chapter_id and r.get("status") == "confirmed"]
    return _known_numbers(*extra, *facts, *rows)


def _edit_records(workflow: dict, chapter_id: str) -> list[dict]:
    """编辑后复查的来源：对话助手写入（chapter_edit_operations）与粘贴识别（edit_rechecks）。"""
    out = []
    for op in workflow.get("chapter_edit_operations") or []:
        if op.get("chapter_id") != chapter_id:
            continue
        for index, issue in enumerate((op.get("recheck") or {}).get("issues") or []):
            out.append({"id": f"{op['id']}:{index}", "issue": issue, "revision": op.get("result_revision") or 0,
                        "text": op.get("written_text") or "", "known_extra": op.get("original_text") or "",
                        "at": op.get("created_at"), "operation_id": op["id"],
                        "edit_mode_label": op.get("edit_mode_label") or "对话助手写入"})
    for record in workflow.get("edit_rechecks") or []:
        if record.get("chapter_id") != chapter_id:
            continue
        for index, issue in enumerate(record.get("issues") or []):
            out.append({"id": f"{record['id']}:{index}", "issue": issue, "revision": record.get("revision") or 0,
                        "text": record.get("text") or "", "known_extra": "", "at": record.get("at"),
                        "operation_id": record["id"], "edit_mode_label": record.get("label") or "粘贴自对话助手"})
    return out


def _edit_items(state: DemoState, project_id: str, chapter: Any, workflow: dict, blocks: list[dict],
                after_revision: int) -> list[dict]:
    from .selection_rewrite import text_issues
    items = []
    for record in _edit_records(workflow, chapter.id):
        if record["revision"] <= after_revision:
            continue  # 之后跑过的章节循环或重新检查已覆盖这些段落
        issue = record["issue"]
        block, how = locate(blocks, key=None, quote=record["text"], line=None, line_trusted=False)
        if block is None:
            status = "resolved"   # 写入的段落已改掉或删除
        else:
            again = text_issues(block["text"], _known(state, project_id, chapter.id, workflow, record["known_extra"]))
            status = "open" if any(i.get("rule_id") == issue.get("rule_id") for i in again) else "resolved"
        severity = _severity(issue.get("severity"))
        items.append({
            "id": f"edit:{record['id']}", "origin": "edit_recheck", "origin_label": ORIGIN_LABELS["edit_recheck"],
            "rule_id": issue.get("rule_id") or "", "code": issue.get("code") or issue.get("rule_id") or "",
            "severity": severity, "message": issue.get("message") or "", "quote": record["text"][:80],
            "route": "direct_human" if issue.get("rule_id") == "R30" else ("must_fix" if severity == "blocker" else "hint"),
            "status": status, "stale": False,
            "paragraph_key": block["key"] if block else None,
            "line_start": block["line_start"] if block else None, "line_end": block["line_end"] if block else None,
            "located_by": how if block else "none", "operation_id": record["operation_id"],
            "edit_mode_label": record["edit_mode_label"], "created_at": record["at"],
        })
    return items


_ORDER = {"blocker": 0, "warning": 1, "info": 2}


def chapter_issues(service: Any, principal: Principal, project_id: str, chapter_id: str) -> dict:
    """本章问题清单（只读）：权限同读取章节；不写任何数据。"""
    state = service.repository.read()
    chapter = service._chapter(state, principal, chapter_id)
    if chapter.project_id != project_id:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
    workflow = state.workflows.get(project_id) or {}
    blocks = _blocks(chapter)
    from .input_snapshot import project_input_fingerprint
    # 与检查页“结果已过期”同一口径（WorkflowService._public_check）
    fingerprint = project_input_fingerprint(state, project_id)
    check_items, check = _check_items(state, project_id, chapter, workflow, blocks, fingerprint)
    loop_items, loop = _loop_items(chapter, workflow, blocks)
    edit_items = _edit_items(state, project_id, chapter, workflow, blocks,
                             after_revision=int((loop or {}).get("result_revision") or 0))
    items = check_items + loop_items + edit_items
    for item in items:
        item["status_label"] = STATUS_LABELS.get(item["status"], item["status"])
        item["route_label"] = ROUTE_LABELS.get(item["route"], item["route"])
        item["open"] = item["status"] in OPEN_STATES
        item["locate_note"] = LOCATE_NOTES.get(item["located_by"], "")
    items.sort(key=lambda i: (not i["open"], _ORDER.get(i["severity"], 3),
                              i["line_start"] if i["line_start"] is not None else 10 ** 6))
    return {
        "project_id": project_id, "chapter_id": chapter.id, "revision": chapter.revision,
        "check": check, "loop": loop, "items": items,
        "counts": {
            "open": sum(1 for i in items if i["open"]),
            "blocker": sum(1 for i in items if i["open"] and i["severity"] == "blocker"),
            "unlocated": sum(1 for i in items if i["open"] and i["paragraph_key"] is None),
        },
    }
