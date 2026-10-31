# 为什么有这个文件：抽取后处理写入状态与人工决定（APP-M2-T101、T107、T109、T110 / PRD v1.8 §5.2.1～5.2.4）。
# 它解决什么问题：
# 1. 每次解析新增条目后按 §5.2.4 顺序处理：补遗覆盖原文 → 去重合并 → 结构化字段冲突检测（星号/废标兜底扫描在 post_process.py）；
# 2. 冲突四种状态：待处理（阻断确认）、已选定、不构成冲突、已按补遗处理（不阻断，供核对）；选定、不构成冲突、撤销替代都须写理由；
#    已有决定的冲突在重跑后保持不变，出现新取值时另记一条新冲突（旧记录留作历史）；
# 3. 合并可拆分，拆过的两条不再自动合并；人工改过的条目只给“建议合并”，由负责人决定合并或不合并；
# 4. 文件版本链“设为被替代”：旧版条目标“所在文件已被替代”，不删除；人工改过的回到待确认由人核对；
# 5. 补遗差异：逐条列出补遗修改了哪条原条款（逐字对照）、新增了什么、哪些没定位到原条款；
# 6. 被并入、被替代的条目状态记为“已忽略”并注明原因，矩阵、写作方案、检查与导出照常把它们排除在外；拆分、撤销替代时恢复原状态。
# 规则本身（相似度、单位折算、定位原条款）在 parse_postprocess.py；全部写操作经 _write 留痕。

from __future__ import annotations

from typing import Any, Callable

from . import parse_postprocess as rules
from . import tender_files
from .domain import DomainError, Principal, iso_time, new_id

CONFLICT_STATUS = {"pending": "待处理", "resolved": "已选定", "not_conflict": "不构成冲突", "by_addendum": "已按补遗处理"}
CONFLICT_TYPES = {"field_value": "字段取值不同", "addendum_override": "补遗覆盖原文", "addendum_unlocated": "补遗未定位原条款"}
DECIDED = {"resolved", "not_conflict", "by_addendum"}
INDIVIDUAL = {"star", "disqualification", "qualification"}
SYSTEM = "system"


def _category_of(row: dict) -> str:
    from .parse_review import requirement_category
    return requirement_category(row)


def _short(text: Any, limit: int = 40) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[:limit] + "…"


def conflict_type(conflict: dict) -> str:
    return conflict.get("conflict_type") or "field_value"


def current(conflict: dict) -> bool:
    """未被新记录取代、也未因条目失效而关闭的冲突。"""
    return not conflict.get("superseded_by") and not conflict.get("obsolete_at")


def blocking_conflicts(workflow: dict) -> list[dict]:
    """“冲突待选定 N”：状态为待处理的当前冲突；已按补遗处理的不阻断（§5.2.4 规则 1）。"""
    return [c for c in (workflow.get("conflicts") or {}).values() if c.get("status") == "pending" and current(c)]


def inactive_fact(fact: dict) -> bool:
    return bool(fact.get("merged_into")) or fact.get("effective_status") == "superseded"


def visible(item: dict) -> bool:
    """解析页列出的条目：被并入主条目的不单列，由主条目“已合并 N 条”展示。"""
    return not item.get("merged_into")


def _file_of(item: dict) -> str:
    return (item.get("source") or {}).get("file_id") or ""


def _source_label(workflow: dict, item: dict) -> str:
    source = item.get("source") or {}
    filename = (workflow.get("files", {}).get(source.get("file_id")) or {}).get("filename", "")
    return f"{filename} 第 {source.get('page', '?')} 页" if filename else f"第 {source.get('page', '?')} 页"


def _new_conflict(workflow: dict, kind: str, now: str, **fields) -> dict:
    conflict = {"id": new_id("conflict"), "conflict_type": kind, "key": fields.pop("key", ""), "fact_ids": [],
                "requirement_ids": [], "selected_fact_id": None, "chosen_requirement_id": None, "status": "pending",
                "reason": "", "detect_method": "rule", "created_at": now, "decided_by": None, "decided_by_name": "",
                "decided_at": None, "history": [], **fields}
    workflow["conflicts"][conflict["id"]] = conflict
    return conflict


def _decide(conflict: dict, status: str, reason: str, by: str, by_name: str, now: str, action: str) -> None:
    conflict.update(status=status, reason=reason, decided_by=by, decided_by_name=by_name, decided_at=now)
    conflict.setdefault("history", []).append({"action": action, "status": status, "reason": reason, "by": by,
                                               "by_name": by_name, "at": now})


# ---------------------------------------------------------------- 替代与恢复

def supersede(item: dict, *, by_item: str | None, by_file: str | None, reason: str, now: str) -> None:
    """标“已被补遗替代 / 所在文件已被替代”：不删除，状态记已忽略并保存原状态，撤销时恢复。"""
    if item.get("effective_status") == "superseded":
        return
    item["pre_supersede"] = {"status": item.get("status"), "reason": item.get("reason", "")}
    item.update(status="rejected", reason=reason, effective_status="superseded", superseded_by=by_item,
                superseded_by_file=by_file, superseded_at=now)


def restore(item: dict) -> None:
    previous = item.pop("pre_supersede", None) or {"status": "pending", "reason": ""}
    for key in ("effective_status", "superseded_by", "superseded_by_file", "superseded_at"):
        item.pop(key, None)
    item.update(status=previous["status"] if previous["status"] != "rejected" else "pending",
                reason=previous.get("reason", "") if previous["status"] != "rejected" else "")


# ---------------------------------------------------------------- 第③步 a：补遗覆盖原文

def _earlier(workflow: dict, item: dict, other: dict) -> bool:
    order = tender_files.order(workflow)
    return order.get(_file_of(other), (9, 9)) < order.get(_file_of(item), (9, 9))


def _amending_item(workflow: dict, item: dict) -> bool:
    record = workflow.get("files", {}).get(_file_of(item))
    return bool(record) and tender_files.amending(record)


def _apply_requirement_amendment(workflow: dict, row: dict, found: dict, now: str) -> str:
    rows = workflow["requirements"]
    row["amend_kind"], row["amend_method"] = found["kind"], found.get("method")
    if found["kind"] == "modified":
        target = rows[found["target"]]
        row["amends"] = target["id"]
        for key in ("volume", "chapter_id"):  # 沿用原条款的分册和对应章节，补遗条款接着原位置写
            if target.get(key):
                row[key] = target[key]
        values = [_requirement_value(workflow, target), _requirement_value(workflow, row)]
        if target.get("manually_edited"):
            # 原条款人工改过：不自动替代，转人工选定（§5.2.4 规则 4）
            _new_conflict(workflow, "addendum_override", now, key=_short(target.get("text"), 30),
                          requirement_ids=[target["id"], row["id"]], values=values)
            return "pending"
        supersede(target, by_item=row["id"], by_file=None,
                  reason=f"已被补遗替代：{_source_label(workflow, row)}", now=now)
        conflict = _new_conflict(workflow, "addendum_override", now, key=_short(target.get("text"), 30),
                                 requirement_ids=[target["id"], row["id"]], chosen_requirement_id=row["id"], values=values)
        _decide(conflict, "by_addendum", "按招标文件版本链：补遗修改了原条款，原条款标“已被补遗替代”。", SYSTEM, "系统",
                now, "auto_addendum")
        return "superseded"
    if found["kind"] == "unlocated":
        _new_conflict(workflow, "addendum_unlocated", now, key=_short(row.get("text"), 30), requirement_ids=[row["id"]],
                      candidate_ids=found.get("candidates") or [], values=[_requirement_value(workflow, row)])
        return "unlocated"
    if found["kind"] == "same":
        row["amend_same_as"] = found["target"]  # 补遗重述了原条款，内容未变；去重时并入原条款
    return found["kind"]


def _apply_fact_amendment(workflow: dict, fact: dict, now: str) -> str | None:
    facts = workflow["facts"]
    base = [f for f in facts.values() if f is not fact and f.get("key") == fact.get("key") and not inactive_fact(f)
            and _earlier(workflow, fact, f)]
    mine = rules.canonical_value(fact.get("value"))
    differing = [f for f in base if rules.canonical_value(f.get("value")) != mine]
    if not differing:
        return None
    fact["amends"] = [f["id"] for f in differing]
    values = [_fact_value(workflow, f) for f in [*differing, fact]]
    touched = [f for f in differing if f.get("manually_edited") or f.get("required")]
    if touched:
        _new_conflict(workflow, "addendum_override", now, key=fact["key"], fact_ids=[*fact["amends"], fact["id"]],
                      values=values)
        return "pending"
    for old in differing:
        supersede(old, by_item=fact["id"], by_file=None, reason=f"已被补遗替代：{_source_label(workflow, fact)}", now=now)
    conflict = _new_conflict(workflow, "addendum_override", now, key=fact["key"], fact_ids=[*fact["amends"], fact["id"]],
                             selected_fact_id=fact["id"], values=values)
    _decide(conflict, "by_addendum", "按招标文件版本链：补遗修改了该项取值，原取值标“已被补遗替代”。", SYSTEM, "系统", now,
            "auto_addendum")
    return "superseded"


def apply_amendments(workflow: dict, new_requirement_ids: set[str], new_fact_ids: set[str], now: str) -> dict:
    """补遗、澄清里新抽出的条目对照版本链上更早文件的有效条目；更早文件后解析时，也回头对照尚无关系的补遗条目。"""
    rows = workflow["requirements"]
    counts = {"superseded": 0, "pending": 0, "unlocated": 0, "added": 0, "same": 0}
    if not any(tender_files.amending(f) for f in workflow.get("files", {}).values()):
        return counts
    for row in [rows[i] for i in rows if i in new_requirement_ids]:
        if not _amending_item(workflow, row) or not rules.candidate(row):
            continue
        # 版本链上更早文件里仍有效的条目（同一次解析里先处理的原文条目也算）；前面的补遗条目替代过的不再参与
        base = [b for b in rows.values() if b is not row and rules.candidate(b) and _earlier(workflow, row, b)]
        outcome = _apply_requirement_amendment(workflow, row, rules.amend_target(row, base), now)
        counts[outcome] = counts.get(outcome, 0) + 1
    new_base = [r for i, r in rows.items() if i in new_requirement_ids and not _amending_item(workflow, r) and rules.candidate(r)]
    if new_base:
        for row in rows.values():
            if (row["id"] in new_requirement_ids or not _amending_item(workflow, row) or row.get("amend_kind") != "added"
                    or not rules.candidate(row)):
                continue
            found = rules.amend_target(row, [b for b in new_base if _earlier(workflow, row, b)])
            if found["kind"] == "modified":
                outcome = _apply_requirement_amendment(workflow, row, found, now)
                counts[outcome] = counts.get(outcome, 0) + 1
    facts = workflow["facts"]
    for fact in [facts[i] for i in facts if i in new_fact_ids]:
        if _amending_item(workflow, fact) and not inactive_fact(fact):
            outcome = _apply_fact_amendment(workflow, fact, now)
            if outcome:
                counts[outcome] = counts.get(outcome, 0) + 1
    return counts


# ---------------------------------------------------------------- 第①步：去重合并

def _ensure_primary(item: dict) -> None:
    if item.get("merge_status") != "primary":
        item.update(merge_status="primary", merged_ids=[],
                    sources=[{**(item.get("source") or {}), "requirement_id": item["id"], "own": True}])


def _attach(primary: dict, member: dict, reason: str, now: str) -> None:
    member["pre_merge"] = {"status": member.get("status"), "reason": member.get("reason", "")}
    member.update(merge_status="merged", merged_into=primary["id"], status="rejected", reason=reason, merged_at=now)
    primary["merged_ids"].append(member["id"])
    primary["sources"].append({**(member.get("source") or {}), "requirement_id": member["id"], "own": False,
                               "text": member.get("text", "")})


def _raise_importance(primary: dict, level: str) -> None:
    current_level = rules.importance(primary, _category_of)
    if rules.IMPORTANCE_RANK.get(level, 0) <= rules.IMPORTANCE_RANK.get(current_level, 0):
        return
    primary.setdefault("base_category", primary.get("category"))
    primary.setdefault("base_importance", primary.get("importance"))
    primary["importance"] = level
    if level in ("star", "disqualification"):
        primary["category"] = "mandatory" if level == "star" else "disqualification"
    if primary.get("status") == "confirmed" and level in INDIVIDUAL:
        # 重要性升为星号/废标/资格：这一类须逐条确认，回到待确认（受影响条目回待确认，§5.2.4 规则 4）
        primary.update(status="pending", reason=f"合并重复条目后重要性升为“{rules.IMPORTANCE_LABELS[level]}”，须逐条确认。",
                       confirmed_by=None, confirmed_by_name=None, confirmed_at=None)


def apply_merges(workflow: dict, now: str) -> dict:
    rows = workflow["requirements"]
    plan = rules.plan_merges(list(rows.values()), _category_of)
    merged = 0
    for group in plan["groups"]:
        primary = rows[group["primary"]]
        _ensure_primary(primary)
        for member_id in group["members"]:
            _attach(primary, rows[member_id], f"已并入「{_short(primary.get('text'))}」（重复抽取，来源已挂到主条目）。", now)
            merged += 1
        _raise_importance(primary, group["importance"])
    store = _suggestions(workflow)
    known = {frozenset(s["requirement_ids"]) for s in store.values()}
    for a, b, score in plan["suggestions"]:
        if frozenset((a, b)) in known:
            continue
        identity = new_id("merge")
        store[identity] = {"id": identity, "requirement_ids": [a, b], "similarity": score, "status": "open",
                           "created_at": now, "handled_by": None, "handled_at": None, "reason": ""}
    for suggestion in store.values():  # 一方已被并入、忽略或替代时建议作废
        if suggestion["status"] == "open" and not all(rules.candidate(rows.get(i) or {"status": "rejected"})
                                                      for i in suggestion["requirement_ids"]):
            suggestion["status"] = "void"
    facts = _merge_facts(workflow, now)
    return {"merged": merged, "facts_merged": facts,
            "suggestions": sum(1 for s in store.values() if s["status"] == "open")}


def _fact_untouched(fact: dict) -> bool:
    return (fact.get("status") == "pending" and not fact.get("manually_edited") and not fact.get("required")
            and not fact.get("amends"))


def _merge_facts(workflow: dict, now: str) -> int:
    """同一字段、统一单位后取值相同的事实只留一条，来源挂到主事实上。"""
    groups: dict[tuple[str, str], list[dict]] = {}
    for fact in workflow["facts"].values():
        if inactive_fact(fact) or fact.get("status") == "rejected":
            continue
        groups.setdefault((fact.get("key", ""), rules.canonical_value(fact.get("value"))), []).append(fact)
    merged = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        primary = next((f for f in members if f.get("merge_status") == "primary"), None) \
            or next((f for f in members if not _fact_untouched(f)), None) or members[0]
        for fact in members:
            if fact is primary or not _fact_untouched(fact):
                continue
            _ensure_primary(primary)
            _attach(primary, fact, "已并入同一字段、同一取值的事实（重复抽取，来源已挂到主事实）。", now)
            merged += 1
    return merged


def _suggestions(workflow: dict) -> dict:
    from .post_process import store
    return store(workflow).setdefault("merge_suggestions", {})


# ---------------------------------------------------------------- 第③步 b：结构化字段冲突

def refresh_fact_conflicts(workflow: dict, now: str) -> None:
    """同一字段统一单位后取值不同即为冲突。已选定、不构成冲突的记录保持不变；出现新取值时另记一条（§5.2.4 规则 4）。"""
    facts, conflicts = workflow["facts"], workflow["conflicts"]
    groups: dict[str, list[dict]] = {}
    for fact in facts.values():
        if not inactive_fact(fact):
            groups.setdefault(fact.get("key", ""), []).append(fact)
    keys = set(groups) | {c.get("key", "") for c in conflicts.values() if conflict_type(c) == "field_value"}
    for key in keys:
        active = groups.get(key, [])
        values = {rules.canonical_value(f.get("value")) for f in active}
        live = [c for c in conflicts.values() if c.get("key") == key and conflict_type(c) == "field_value" and current(c)]
        latest = live[-1] if live else None
        ids = [f["id"] for f in active]
        if len(values) <= 1:
            if latest and latest["status"] == "pending":
                del conflicts[latest["id"]]
            elif latest:
                latest.update(obsolete_at=now, obsolete_reason="冲突一方已被补遗替代或并入同值条目，不再冲突。")
            continue
        if latest is None:
            _new_conflict(workflow, "field_value", now, key=key, fact_ids=ids)
            continue
        if latest["status"] == "pending":
            latest["fact_ids"] = [i for i in latest["fact_ids"] if i in ids] + [i for i in ids if i not in latest["fact_ids"]]
            continue
        covered = [f for f in active if f["id"] in latest["fact_ids"]]
        known = {rules.canonical_value(f.get("value")) for f in covered}
        fresh = {rules.canonical_value(f.get("value")) for f in active if f["id"] not in latest["fact_ids"]} - known
        selected_lost = latest["status"] == "resolved" and latest.get("selected_fact_id") not in ids
        if fresh or selected_lost:
            replacement = _new_conflict(workflow, "field_value", now, key=key, fact_ids=ids,
                                        previous_id=latest["id"], previous_selected_fact_id=latest.get("selected_fact_id"))
            latest["superseded_by"] = replacement["id"]


def conflict_selection_valid(workflow: dict, conflict: dict) -> bool:
    """已选定的冲突：选中的取值已确认，其余取值不同的有效候选已忽略。"""
    if conflict.get("status") != "resolved" or not current(conflict):
        return True
    facts = workflow["facts"]
    if conflict.get("fact_ids"):
        selected = facts.get(conflict.get("selected_fact_id") or "")
        if not selected or selected.get("status") != "confirmed":
            return False
        chosen = rules.canonical_value(selected.get("value"))
        return all(facts[i].get("status") == "rejected" for i in conflict["fact_ids"]
                   if i in facts and i != selected["id"] and not inactive_fact(facts[i])
                   and rules.canonical_value(facts[i].get("value")) != chosen)
    return True


def after_extraction(workflow: dict, new_requirement_ids: set[str], new_fact_ids: set[str], now: str) -> dict:
    """§5.2.4 后处理顺序：补遗覆盖 → 去重合并 → 结构化字段冲突（兜底扫描在解析时逐文件执行）。"""
    amendments = apply_amendments(workflow, new_requirement_ids, new_fact_ids, now)
    merges = apply_merges(workflow, now)
    refresh_fact_conflicts(workflow, now)
    summary = {"amendments": amendments, **merges, "finished_at": now}
    from .post_process import store
    store(workflow)["last_run"] = summary
    return summary


# ---------------------------------------------------------------- 读模型

def _requirement_value(workflow: dict, row: dict) -> dict:
    source = row.get("source") or {}
    return {"requirement_id": row["id"], "value": row.get("text", ""), "file_id": source.get("file_id"),
            "filename": (workflow.get("files", {}).get(source.get("file_id")) or {}).get("filename", ""),
            "page": source.get("page"), "quote": source.get("quote", ""), "status": row.get("status"),
            "effective_status": row.get("effective_status") or "effective"}


def _fact_value(workflow: dict, fact: dict) -> dict:
    source = fact.get("source") or {}
    return {"fact_id": fact["id"], "value": fact.get("value", ""), "file_id": source.get("file_id"),
            "filename": (workflow.get("files", {}).get(source.get("file_id")) or {}).get("filename", ""),
            "page": source.get("page"), "quote": source.get("quote", ""), "status": fact.get("status"),
            "effective_status": fact.get("effective_status") or "effective",
            "canonical": rules.canonical_value(fact.get("value"))}


def public_conflict(workflow: dict, conflict: dict) -> dict:
    """当前取值快照：各方取值、原文、文件与页码并列显示。"""
    facts, rows = workflow["facts"], workflow["requirements"]
    values = ([_fact_value(workflow, facts[i]) for i in conflict.get("fact_ids") or [] if i in facts]
              + [_requirement_value(workflow, rows[i]) for i in conflict.get("requirement_ids") or [] if i in rows])
    candidates = [_requirement_value(workflow, rows[i]) for i in conflict.get("candidate_ids") or [] if i in rows]
    kind = conflict_type(conflict)
    return {**conflict, "conflict_type": kind, "conflict_type_label": CONFLICT_TYPES[kind],
            "status_label": CONFLICT_STATUS.get(conflict.get("status"), conflict.get("status")),
            "current": current(conflict), "blocking": conflict.get("status") == "pending" and current(conflict),
            "values": values, "candidates": candidates}


class ParseDecisionMixin:
    """挂在 WorkflowService 上：冲突列表与处理、合并拆分、文件版本链、补遗差异与后处理汇总。"""

    def list_conflicts(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        items = [public_conflict(workflow, c) for c in workflow["conflicts"].values()]
        items.sort(key=lambda c: (not c["blocking"], not c["current"], c.get("created_at") or ""))
        count = lambda status: sum(1 for c in items if c["current"] and c["status"] == status)  # noqa: E731
        return {"revision": project.revision, "project_id": project_id, "can_handle": self._is_lead(state, principal, project_id),
                "summary": {"pending": count("pending"), "by_addendum": count("by_addendum"), "resolved": count("resolved"),
                            "not_conflict": count("not_conflict"), "history": sum(1 for c in items if not c["current"])},
                "conflicts": items}

    def decide_conflict(self, principal: Principal, project_id: str, conflict_id: str, payload: dict,
                        expected: str | None, key: str | None) -> dict:
        action = payload.get("action")
        reason = str(payload.get("reason") or "").strip()
        if action != "confirm" and not reason:
            raise DomainError(422, "REASON_REQUIRED", "处理冲突必须写明理由。")

        def operation(state, project, workflow):
            conflict = workflow["conflicts"].get(conflict_id)
            if conflict is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目冲突。")
            if not current(conflict):
                raise DomainError(409, "VERSION_CONFLICT", "这条冲突已有新的记录，请刷新后处理最新一条。",
                                  {"superseded_by": conflict.get("superseded_by")})
            now = iso_time(self.demo._now())
            handler = {"choose": self._choose, "not_conflict": self._not_conflict, "revert": self._revert_addendum,
                       "assign_target": self._assign_target, "confirm": self._confirm_addendum}.get(action)
            if handler is None:
                raise DomainError(422, "VALIDATION_ERROR", "不支持的处理方式。", {"fields": {"action": "invalid"}})
            handler(workflow, conflict, payload, reason or "已核对补遗处理结果。", principal, now)
            refresh_fact_conflicts(workflow, now)
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"conflict": public_conflict(workflow, conflict), "facts": list(workflow["facts"].values())}

        return self._write(principal, project_id, "conflict.resolve:" + conflict_id, payload, expected, key, operation,
                           {"conflict_id": conflict_id, "action": action, "reason": reason})

    # 选定一方：事实冲突选中的确认、取值不同的忽略；条款冲突选补遗则替代原条款，选原条款则忽略补遗条目
    def _choose(self, workflow, conflict, payload, reason, principal, now):
        if conflict["status"] == "by_addendum":
            raise DomainError(409, "INVALID_CONFLICT_SELECTION", "已按补遗处理的冲突请用“撤销替代”或“确认”。")
        facts, rows = workflow["facts"], workflow["requirements"]
        if conflict.get("fact_ids"):
            selected = payload.get("selected_fact_id")
            picked = facts.get(selected or "")
            if selected not in conflict["fact_ids"] or picked is None or inactive_fact(picked):
                raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只能选择本冲突中仍有效的取值。")
            chosen = rules.canonical_value(facts[selected].get("value"))
            for identity in conflict["fact_ids"]:
                fact = facts.get(identity)
                if not fact or inactive_fact(fact):
                    continue
                if identity == selected:
                    fact.update(status="confirmed", reason=reason)
                elif rules.canonical_value(fact.get("value")) != chosen:
                    fact.update(status="rejected", reason=reason, rejected_by_conflict=conflict["id"])
            conflict["selected_fact_id"] = selected
        else:
            selected = payload.get("requirement_id")
            if conflict_type(conflict) != "addendum_override" or selected not in conflict.get("requirement_ids", []):
                raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只能选择本冲突中的条目。")
            original, addendum = (rows[i] for i in conflict["requirement_ids"])
            if selected == addendum["id"]:
                supersede(original, by_item=addendum["id"], by_file=None,
                          reason=f"已被补遗替代：{_source_label(workflow, addendum)}（{reason}）", now=now)
            else:
                addendum.update(status="rejected", reason=f"保留原条款：{reason}", rejected_by_conflict=conflict["id"])
            conflict["chosen_requirement_id"] = selected
        _decide(conflict, "resolved", reason, principal.user.id, principal.user.name, now, "choose")

    def _not_conflict(self, workflow, conflict, payload, reason, principal, now):
        if conflict["status"] == "by_addendum":
            return self._revert_addendum(workflow, conflict, payload, reason, principal, now)
        for identity in conflict.get("fact_ids") or []:  # 改判“不构成冲突”：此前因本冲突忽略的取值回到待确认
            fact = workflow["facts"].get(identity)
            if fact and fact.get("rejected_by_conflict") == conflict["id"]:
                fact.update(status="pending", reason="")
                fact.pop("rejected_by_conflict", None)
        for identity in conflict.get("requirement_ids") or []:
            row = workflow["requirements"].get(identity)
            if row and row.get("rejected_by_conflict") == conflict["id"]:
                row.update(status="pending", reason="")
                row.pop("rejected_by_conflict", None)
            elif row and row.get("effective_status") == "superseded" and conflict_type(conflict) == "addendum_override":
                restore(row)
        if conflict_type(conflict) == "addendum_unlocated":
            for identity in conflict.get("requirement_ids") or []:
                if identity in workflow["requirements"]:
                    workflow["requirements"][identity]["amend_kind"] = "added"
        conflict["selected_fact_id"] = None
        conflict["chosen_requirement_id"] = None
        _decide(conflict, "not_conflict", reason, principal.user.id, principal.user.name, now, "not_conflict")

    # 撤销替代：补遗没有改到这一条，原条目恢复原状态，两条都保留
    def _revert_addendum(self, workflow, conflict, payload, reason, principal, now):
        if conflict["status"] != "by_addendum":
            raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只有“已按补遗处理”的冲突可以撤销替代。")
        for collection, ids in ((workflow["facts"], conflict.get("fact_ids") or []),
                                (workflow["requirements"], conflict.get("requirement_ids") or [])):
            for identity in ids:
                item = collection.get(identity)
                if item and item.get("effective_status") == "superseded":
                    restore(item)
                if item and item.get("amends"):
                    item["amend_reverted"] = True
        conflict["selected_fact_id"] = None
        conflict["chosen_requirement_id"] = None
        _decide(conflict, "not_conflict", reason, principal.user.id, principal.user.name, now, "revert")

    def _confirm_addendum(self, workflow, conflict, payload, reason, principal, now):
        if conflict["status"] != "by_addendum":
            raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只有“已按补遗处理”的冲突可以确认核对。")
        conflict.update(reviewed_by=principal.user.id, reviewed_by_name=principal.user.name, reviewed_at=now)
        conflict.setdefault("history", []).append({"action": "confirm", "status": "by_addendum", "reason": reason,
                                                   "by": principal.user.id, "by_name": principal.user.name, "at": now})

    # 为未定位的补遗条目手工指定被替代的原条款
    def _assign_target(self, workflow, conflict, payload, reason, principal, now):
        if conflict_type(conflict) != "addendum_unlocated" or conflict["status"] != "pending":
            raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只有待处理的“补遗未定位原条款”可以指定原条款。")
        rows = workflow["requirements"]
        addendum = rows.get((conflict.get("requirement_ids") or [""])[0])
        target = rows.get(str(payload.get("requirement_id") or ""))
        if addendum is None or target is None or target is addendum or not rules.candidate(target) \
                or not _earlier(workflow, addendum, target):
            raise DomainError(409, "INVALID_CONFLICT_SELECTION", "请选择版本链上更早文件中仍有效的条目。")
        supersede(target, by_item=addendum["id"], by_file=None,
                  reason=f"已被补遗替代：{_source_label(workflow, addendum)}（人工指定：{reason}）", now=now)
        addendum.update(amends=target["id"], amend_kind="modified", amend_method="manual")
        conflict.update(requirement_ids=[target["id"], addendum["id"]], chosen_requirement_id=addendum["id"],
                        target_requirement_id=target["id"],
                        values=[_requirement_value(workflow, target), _requirement_value(workflow, addendum)])
        _decide(conflict, "by_addendum", reason, principal.user.id, principal.user.name, now, "assign_target")

    # ------------------------------------------------------------ 合并与拆分

    def split_item(self, principal: Principal, project_id: str, kind: str, item_id: str, payload: dict,
                   expected: str | None, key: str | None) -> dict:
        reason = str(payload.get("reason") or "").strip()

        def operation(state, project, workflow):
            from .project_access import require_lead
            require_lead(state, principal, project_id)
            collection = workflow["requirements" if kind == "requirement" else "facts"]
            primary = collection.get(item_id)
            if primary is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条目。")
            if primary.get("merge_status") != "primary" or not primary.get("merged_ids"):
                raise DomainError(409, "NOT_MERGED", "这条没有合并其他条目，不需要拆分。")
            wanted = payload.get("item_ids") or list(primary["merged_ids"])
            if any(i not in primary["merged_ids"] for i in wanted):
                raise DomainError(409, "NOT_MERGED", "只能拆出并入这条主条目的条目。")
            group = [primary["id"], *primary["merged_ids"]]
            for identity in wanted:
                member = collection[identity]
                previous = member.pop("pre_merge", None) or {"status": "pending", "reason": ""}
                for field in ("merge_status", "merged_into", "merged_at"):
                    member.pop(field, None)
                member.update(status=previous["status"] if previous["status"] != "rejected" else "pending",
                              reason=previous.get("reason", ""))
                member["merge_blocked"] = sorted(set(member.get("merge_blocked") or []) | (set(group) - {identity}))
            primary["merged_ids"] = [i for i in primary["merged_ids"] if i not in wanted]
            primary["sources"] = [s for s in primary["sources"] if s.get("requirement_id") not in wanted]
            primary["merge_blocked"] = sorted(set(primary.get("merge_blocked") or []) | set(wanted))
            if not primary["merged_ids"]:
                primary.update(merge_status="independent", sources=[])
                if "base_category" in primary:  # 合并时升过的重要性还原
                    primary["category"] = primary.pop("base_category")
                    primary["importance"] = primary.pop("base_importance", None)
            if kind == "fact":
                refresh_fact_conflicts(workflow, iso_time(self.demo._now()))
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"item": primary, "split_ids": wanted}

        return self._write(principal, project_id, f"parse.split:{kind}:{item_id}", payload, expected, key, operation,
                           {"kind": kind, "item_id": item_id, "reason": reason})

    def merge_requirements(self, principal: Principal, project_id: str, requirement_id: str, payload: dict,
                           expected: str | None, key: str | None) -> dict:
        ids = list(dict.fromkeys(payload.get("requirement_ids") or []))
        reason = str(payload.get("reason") or "").strip()
        if not ids or not reason:
            raise DomainError(422, "REASON_REQUIRED", "请选择要并入的条目并写明理由。")

        def operation(state, project, workflow):
            from .project_access import require_lead
            require_lead(state, principal, project_id)
            rows = workflow["requirements"]
            primary = rows.get(requirement_id)
            members = [rows.get(i) for i in ids]
            if primary is None or any(m is None for m in members):
                raise DomainError(404, "NOT_FOUND", "所选条目不存在或不属于本项目。")
            if requirement_id in ids or not rules.candidate(primary) or not all(rules.candidate(m) for m in members):
                raise DomainError(409, "REQUIREMENT_NOT_READY", "只能合并仍有效、未并入其他条目的条目。")
            if any(rules.numbers(m.get("text")) != rules.numbers(primary.get("text")) for m in members):
                raise DomainError(409, "REQUIREMENT_VALUES_DIFFER", "取值（数字）不同的条目不能合并，请作为冲突核对。")
            in_use = [m["id"] for m in members if m.get("chapter_id") or m.get("evidence_ids") or str(m.get("response") or "").strip()]
            if in_use:
                raise DomainError(409, "REQUIREMENT_IN_USE", "已对应章节、挂了证据或写了响应的条目不能并入，请先移除。",
                                  {"requirement_ids": in_use})
            now = iso_time(self.demo._now())
            _ensure_primary(primary)
            for member in members:
                _attach(primary, member, f"人工合并到「{_short(primary.get('text'))}」：{reason}", now)
                _raise_importance(primary, rules.importance(member, _category_of))
            for suggestion in _suggestions(workflow).values():
                if suggestion["status"] == "open" and set(suggestion["requirement_ids"]) & set(ids):
                    suggestion.update(status="merged", reason=reason, handled_by=principal.user.id, handled_at=now)
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"requirement": primary, "merged_ids": ids}

        return self._write(principal, project_id, "parse.merge:" + requirement_id, payload, expected, key, operation,
                           {"requirement_id": requirement_id, "merged_ids": ids, "reason": reason})

    def dismiss_merge_suggestion(self, principal: Principal, project_id: str, suggestion_id: str, payload: dict,
                                 expected: str | None, key: str | None) -> dict:
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "不合并须写明理由。")

        def operation(state, project, workflow):
            from .project_access import require_lead
            require_lead(state, principal, project_id)
            suggestion = _suggestions(workflow).get(suggestion_id)
            if suggestion is None:
                raise DomainError(404, "NOT_FOUND", "未找到这条合并建议。")
            if suggestion["status"] != "open":
                raise DomainError(409, "VERSION_CONFLICT", "这条建议已处理，请刷新。")
            now = iso_time(self.demo._now())
            suggestion.update(status="dismissed", reason=reason, handled_by=principal.user.id, handled_at=now)
            a, b = suggestion["requirement_ids"]
            rows = workflow["requirements"]
            for one, other in ((a, b), (b, a)):
                if one in rows:
                    rows[one]["merge_blocked"] = sorted(set(rows[one].get("merge_blocked") or []) | {other})
            return {"suggestion": suggestion}

        return self._write(principal, project_id, "parse.merge.dismiss:" + suggestion_id, payload, expected, key,
                           operation, {"suggestion_id": suggestion_id, "reason": reason})

    # ------------------------------------------------------------ 文件类型与版本链

    def set_file_role(self, principal: Principal, project_id: str, file_id: str, payload: dict,
                      expected: str | None, key: str | None) -> dict:
        role = payload.get("file_role")
        if role not in tender_files.FILE_ROLES:
            raise DomainError(422, "VALIDATION_ERROR", "文件类型无效。", {"fields": {"file_role": "invalid"}})

        def operation(state, project, workflow):
            record = workflow["files"].get(file_id)
            if record is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
            if record.get("status") == "parsed" and tender_files.amending(record) != (role in tender_files.AMENDING_ROLES):
                raise DomainError(409, "FILE_ALREADY_PARSED", "已解析的文件不能在“补遗/澄清”与其他类型之间切换；请重新上传并选对类型。")
            record["file_role"] = role
            return {"file": self._public_file(record)}

        return self._write(principal, project_id, "file.role:" + file_id, payload, expected, key, operation,
                           {"file_id": file_id, "file_role": role})

    def supersede_file(self, principal: Principal, project_id: str, file_id: str, payload: dict,
                       expected: str | None, key: str | None) -> dict:
        replacement_id = str(payload.get("replacement_file_id") or "")
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "设为被替代须写明理由。")

        def operation(state, project, workflow):
            files = workflow["files"]
            old, new = files.get(file_id), files.get(replacement_id)
            if old is None or new is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
            if old is new or tender_files.role(old) != tender_files.role(new):
                raise DomainError(409, "FILE_ROLE_MISMATCH", "只能用同一类型的新版文件替代旧版。")
            if tender_files.superseded(old) or tender_files.superseded(new) or new.get("supersedes_id"):
                raise DomainError(409, "FILE_ALREADY_SUPERSEDED", "这两份文件已在版本链中，不能重复替代。")
            if list(files).index(replacement_id) < list(files).index(file_id):
                raise DomainError(409, "FILE_ROLE_MISMATCH", "新版文件须在旧版之后上传。")
            now = iso_time(self.demo._now())
            old.update(superseded_by=new["id"], superseded_at=now, superseded_reason=reason)
            new.update(supersedes_id=old["id"], version_no=int(old.get("version_no") or 1) + 1)
            note = f"所在文件「{old['filename']}」已被新版「{new['filename']}」替代：{reason}"
            rechecks = 0
            for collection in (workflow["requirements"], workflow["facts"]):
                for item in collection.values():
                    if _file_of(item) != old["id"] or item.get("merged_into") or item.get("effective_status") == "superseded":
                        continue
                    if item.get("manually_edited"):
                        # 人工改过的条目不自动作废：回到待确认，由人核对是否仍有效
                        item.update(status="pending", needs_recheck=note)
                        rechecks += 1
                    elif item.get("status") != "rejected":
                        supersede(item, by_item=None, by_file=new["id"], reason=note, now=now)
            from .post_process import store
            for hit in store(workflow)["hits"].values():
                if hit.get("file_id") == old["id"] and hit.get("status") == "open":
                    hit.update(status="excluded", reason=note, handled_by=principal.user.id, handled_at=now)
            refresh_fact_conflicts(workflow, now)
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"file": self._public_file(old), "replacement": self._public_file(new), "rechecks": rechecks}

        return self._write(principal, project_id, "file.supersede:" + file_id, payload, expected, key, operation,
                           {"file_id": file_id, "replacement_file_id": replacement_id, "reason": reason})

    # ------------------------------------------------------------ 补遗差异与后处理汇总

    def addendum_diff(self, principal: Principal, project_id: str, file_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        record = workflow["files"].get(file_id)
        if record is None:
            raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
        rows, facts = workflow["requirements"], workflow["facts"]
        by_row = {}
        for conflict in workflow["conflicts"].values():
            for identity in conflict.get("requirement_ids") or []:
                by_row.setdefault(identity, conflict)
        items = []
        for row in rows.values():
            if _file_of(row) != file_id:
                continue
            if row.get("merged_into"):
                if _file_of(rows.get(row["merged_into"]) or {}) == file_id:
                    continue  # 同一份补遗里的重复抽取，主条目已列出
                kind = "same"
            else:
                kind = "added" if row.get("amend_reverted") else (row.get("amend_kind") or "added")
            conflict = by_row.get(row["id"])
            entry = {"kind": kind, "requirement": _requirement_value(workflow, row), "conflict_id": (conflict or {}).get("id"),
                     "conflict_status": (conflict or {}).get("status")}
            target_id = (row.get("amends") if kind == "modified" else
                         row.get("amend_same_as") or row.get("merged_into") if kind == "same" else None)
            target = rows.get(target_id or "")
            if target is not None:
                entry["target"] = _requirement_value(workflow, target)
                after = rules.amended_text(target.get("text", ""), row.get("text", "")) if kind == "modified" else row.get("text", "")
                entry["amended_text"] = after
                entry["diff"] = rules.text_diff(target.get("text", ""), after)
            if kind == "unlocated" and conflict:
                entry["candidates"] = public_conflict(workflow, conflict)["candidates"]
            items.append(entry)
        order = {"modified": 0, "unlocated": 1, "added": 2, "same": 3}
        items.sort(key=lambda e: (order.get(e["kind"], 9), e["requirement"].get("page") or 0))
        fact_items = []
        for fact in facts.values():
            if _file_of(fact) != file_id or not fact.get("amends"):
                continue
            fact_items.append({"key": fact.get("key"), "new": _fact_value(workflow, fact),
                               "old": [_fact_value(workflow, facts[i]) for i in fact["amends"] if i in facts]})
        superseded_rows = [_requirement_value(workflow, r) for r in rows.values()
                           if r.get("superseded_by_file") == file_id]
        count = lambda kind: sum(1 for e in items if e["kind"] == kind)  # noqa: E731
        return {"revision": project.revision, "file": self._public_file(record),
                "amending": tender_files.amending(record),
                "summary": {"modified": count("modified"), "added": count("added"), "unlocated": count("unlocated"),
                            "same": count("same"), "facts": len(fact_items), "replaced_items": len(superseded_rows)},
                "items": items, "facts": fact_items, "replaced_items": superseded_rows}

    def post_process_summary(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        from .post_process import PLATFORM_SCAN_VERSION, suspected
        data = workflow.get("post_process") or {}
        rows = workflow["requirements"]
        suggestions = [s for s in (data.get("merge_suggestions") or {}).values() if s["status"] == "open"]
        return {
            "revision": project.revision, "project_id": project_id,
            "conflicts_pending": len(blocking_conflicts(workflow)),
            "conflicts_by_addendum": sum(1 for c in workflow["conflicts"].values() if c.get("status") == "by_addendum" and current(c)),
            "omissions_pending": len(suspected(workflow)),
            "references_unresolved": sum(1 for r in rows.values() if r.get("reference_status") == "unresolved"
                                         and r.get("status") != "rejected"),
            "merged_groups": sum(1 for r in rows.values() if r.get("merge_status") == "primary" and r.get("merged_ids")),
            "merged_items": sum(1 for r in rows.values() if r.get("merged_into")),
            "superseded_items": sum(1 for r in rows.values() if r.get("effective_status") == "superseded"),
            "merge_suggestions": [{**s, "texts": [_short(rows.get(i, {}).get("text"), 80) for i in s["requirement_ids"]]}
                                  for s in suggestions],
            "scan_version": data.get("scan_version") or PLATFORM_SCAN_VERSION,
            "last_run": data.get("last_run"),
        }
