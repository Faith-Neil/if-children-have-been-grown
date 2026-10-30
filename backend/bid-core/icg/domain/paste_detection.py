# 为什么有这个文件：粘贴识别（PRD v1.8 §5.11.7“粘贴识别”、§5.7.3 第 13 条、风险 K26；公司设置 assistant_paste_match_ratio；APP-M2-T188）。
# 它解决什么问题：用户把对话助手的样例或回答复制后手工粘贴进正文提交，会绕开“模型所写”的处理（数值来源核对等）。
# 提交时把新增或改动的段落与本章近 7 天的对话助手输出比对：一段里被助手输出覆盖的字数占比达到公司阈值（默认 80%）时，
# 该段来源记为“对话助手撰写（粘贴）”，并对这些段落做与助手写入相同的文字复查（对话残留、负偏离、无来源数值等），结果随提交返回；
# 达不到的按人工编写处理。只比对本章、本公司数据。

from __future__ import annotations

import difflib
from datetime import datetime, timedelta, timezone
from typing import Any

WINDOW_DAYS = 7
MIN_PARAGRAPH = 10
MIN_BLOCK = 6
DEFAULT_RATIO = 0.8


def threshold(state: Any, company_id: str) -> float:
    stored = (getattr(state, "service_stores", {}).get("company_settings") or {}).get(company_id) or {}
    value = stored.get("assistant_paste_match_ratio")
    return float(value) if isinstance(value, (int, float)) else DEFAULT_RATIO


def _recent(stamp: str | None, now: float) -> bool:
    if not stamp:
        return False
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    return moment >= datetime.fromtimestamp(now, timezone.utc) - timedelta(days=WINDOW_DAYS)


def assistant_outputs(workflow: dict, chapter_id: str, now: float) -> list[dict]:
    """本章近期对话助手输出：选区改写的样例与自由提问的回答。"""
    outputs = []
    for batch in (workflow.get("assistant_suggestions") or {}).values():
        if batch.get("chapter_id") == chapter_id and _recent(batch.get("created_at"), now):
            outputs += [{"kind": "sample", "id": s["id"], "batch_id": batch["id"], "text": s["text"]} for s in batch.get("samples") or []]
    for session in (workflow.get("assistant_sessions") or {}).values():
        if session.get("chapter_id") != chapter_id:
            continue
        outputs += [{"kind": "answer", "id": m["id"], "session_id": session["id"], "text": m["answer"]}
                    for m in session.get("messages") or [] if m.get("kind") == "answer" and m.get("answer") and _recent(m.get("created_at"), now)]
    return outputs


def coverage(paragraph: str, output: str) -> float:
    """段落里被助手输出逐字覆盖的比例（只算 ≥6 字的连续相同片段）。"""
    plain = "".join(paragraph.split())
    if not plain:
        return 0.0
    blocks = difflib.SequenceMatcher(None, plain, "".join(output.split()), autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks if b.size >= MIN_BLOCK) / len(plain)


def detect(old_content: str, new_content: str, outputs: list[dict], ratio: float) -> list[dict]:
    before = {p.strip() for p in (old_content or "").split("\n") if p.strip()}
    found = []
    for index, paragraph in enumerate(new_content.split("\n")):
        text = paragraph.strip()
        if len(text) < MIN_PARAGRAPH or text in before or not outputs:
            continue
        best = max(outputs, key=lambda o: coverage(text, o["text"]))
        score = coverage(text, best["text"])
        if score >= ratio:
            found.append({"paragraph_index": index, "source": "assistant_pasted", "source_label": "对话助手撰写（粘贴）",
                          "match_ratio": round(score, 2), "origin": {k: v for k, v in best.items() if k != "text"},
                          "text": text[:200], "_full": text})
    return found


def review(state: Any, chapter: Any, workflow: dict, old_content: str, new_content: str, now: float) -> list[dict]:
    """提交时调用：返回识别为粘贴的段落及每段的文字复查问题。"""
    project = state.projects.get(chapter.project_id)
    outputs = assistant_outputs(workflow, chapter.id, now)
    if project is None or not outputs:
        return []
    pasted = detect(old_content, new_content, outputs, threshold(state, project.company_id))
    if not pasted:
        return []
    from .selection_rewrite import _known_numbers, text_issues
    facts = [str(f.get("value")) for f in (workflow.get("facts") or {}).values() if f.get("status") == "confirmed"]
    rows = [str(r.get("text")) for r in (workflow.get("requirements") or {}).values()
            if r.get("chapter_id") == chapter.id and r.get("status") == "confirmed"]
    known = _known_numbers(old_content or "", *facts, *rows)
    for item in pasted:
        item["issues"] = text_issues(item.pop("_full"), known)
    return pasted
