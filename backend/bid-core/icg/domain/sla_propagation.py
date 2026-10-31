# 为什么有这个文件：服务承诺“需复核”传播提示（APP-M2-T122，PRD v1.8 §5.3.2、5.7.8）与矩阵判定汇总（APP-M2-T119）。
# 它解决什么问题：
# 1. 模板、招标来源或取值变化后，哪些承诺指标需要重新核对、为什么，以及哪些章节正文引用了这些指标，一次读清；
# 2. 汇总七类判定、未确认事实和过期承诺函的数量，让负责人先看风险再逐项处理；
# 3. 只读派生：与 public_sla / sla_issues 同源，不另存状态，也不放行任何导出门禁。

from __future__ import annotations

from .sla import TOKEN, public_sla, sla_issues

JUDGMENTS = ("satisfied", "not_satisfied", "exceeds_capability", "missing", "manual", "not_required", "unquantified")
REVIEW_REASONS = {"TEMPLATE_STALE", "SOURCE_STALE", "NEEDS_REVIEW"}


def _reasons(sla: dict, row: dict) -> list[dict]:
    reasons = []
    if sla["template_stale"]:
        reasons.append({"code": "TEMPLATE_STALE", "label": "公司模板已变化或未确认，须刷新并重新核对"})
    if row["source_stale"]:
        reasons.append({"code": "SOURCE_STALE", "label": "招标来源条款已变更或不再是已确认状态"})
    if row["fact_status"] == "needs_review" and not sla["template_stale"] and not row["source_stale"]:
        reasons.append({"code": "NEEDS_REVIEW", "label": "取值、来源或模板变更后，事实尚未重新确认"})
    if row["fact_status"] == "pending":
        reasons.append({"code": "UNCONFIRMED", "label": "尚未由负责人逐项确认"})
    if row["judgment"] in ("missing", "not_satisfied"):
        reasons.append({"code": "VALUE_INVALID", "label": row["message"]})
    if row["judgment"] in ("manual", "unquantified", "exceeds_capability", "not_required") and not row["review"]:
        reasons.append({"code": "RISK_UNREVIEWED", "label": row["message"]})
    return reasons


def sla_propagation(state, project_id: str, chapters: list) -> dict:
    sla = public_sla(state, project_id)
    revision = state.projects[project_id].revision
    if not sla:
        return {"revision": revision, "project_id": project_id, "selected": False, "template_name": "",
                "template_stale": False, "summary": {"total": 0, "by_judgment": {}, "needs_review": 0, "unconfirmed": 0,
                                                     "risk_unreviewed": 0, "invalid": 0, "stale_commitments": 0,
                                                     "affected_chapters": 0},
                "rows": [], "chapters": []}
    used: dict[str, list] = {}
    for chapter in chapters:
        for key in sorted(set(TOKEN.findall(chapter.content or ""))):
            used.setdefault(key, []).append(chapter)
    rows = []
    for row in sla["rows"]:
        reasons = _reasons(sla, row)
        rows.append({"var_key": row["var_key"], "label": row["label"], "group": row["group"],
                     "judgment": row["judgment"], "judgment_label": row["judgment_label"],
                     "fact_status": row["fact_status"], "reasons": reasons,
                     "needs_review": any(r["code"] in REVIEW_REASONS for r in reasons),
                     "chapters": [{"chapter_id": c.id, "title": c.title, "volume": c.volume} for c in used.get(row["var_key"], [])]})
    flagged = {r["var_key"] for r in rows if r["reasons"]}
    chapter_issues: dict[str, list] = {}
    for issue in sla_issues(state, project_id, chapters):
        if issue.get("chapter_id"):
            chapter_issues.setdefault(issue["chapter_id"], []).append({"code": issue["code"], "message": issue["message"]})
    affected = []
    for chapter in chapters:
        keys = sorted(k for k, users in used.items() if k in flagged and any(u.id == chapter.id for u in users))
        issues = chapter_issues.get(chapter.id, [])
        if keys or issues:
            affected.append({"chapter_id": chapter.id, "title": chapter.title, "volume": chapter.volume,
                             "var_keys": keys, "issues": issues})
    by_judgment = {name: 0 for name in JUDGMENTS}
    for row in rows:
        by_judgment[row["judgment"]] += 1
    codes = [{r["code"] for r in row["reasons"]} for row in rows]
    return {"revision": revision, "project_id": project_id, "selected": True, "template_name": sla["template_name"],
            "template_stale": sla["template_stale"],
            "summary": {"total": len(rows), "by_judgment": by_judgment,
                        "needs_review": sum(1 for row in rows if row["needs_review"]),
                        "unconfirmed": sum(1 for c in codes if "UNCONFIRMED" in c),
                        "risk_unreviewed": sum(1 for c in codes if "RISK_UNREVIEWED" in c),
                        "invalid": sum(1 for c in codes if "VALUE_INVALID" in c),
                        "stale_commitments": sum(1 for c in sla["commitments"] if c["status"] == "stale"),
                        "affected_chapters": len(affected)},
            "rows": rows, "chapters": affected}
