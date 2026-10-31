# 为什么有这个文件：五类“系统生成章节”（PRD v1.8 §5.7.2 规则 9，APP-M2-T191～T195）：点对点应答、评审索引表、
# 偏离表、年度服务计划表、证明材料清单。
# 它解决什么问题：这些章节必须完全由数据（矩阵、项目事实、SLA、资料库）生成，不调用模型、不能在正文里手改；
# 数据源变了要重新生成，检查会挡住过期内容。缺来源时写【待补】，不编造日期、次数或页码。

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .domain import DomainError, Principal, iso_time

KINDS = {
    "point_to_point": ("点对点应答", ("点对点应答", "逐条应答", "逐条响应")),
    "review_index": ("评审索引表", ("评审索引", "评分索引", "索引表")),
    "deviation": ("偏离表", ("偏离表",)),
    "service_plan": ("年度服务计划表", ("年度服务计划", "服务计划表")),
    "proof_list": ("证明材料清单", ("证明材料清单",)),
}
RESPONSE_LABEL = {"comply": "满足", "exceed": "优于", "deviate": "偏离", "not_applicable": "不适用"}
_CELL = re.compile(r"[|\n\r]+")


def kind_of(title: str) -> str | None:
    for kind, (_label, words) in KINDS.items():
        if any(word in (title or "") for word in words):
            return kind
    return None


def _cell(text: Any, limit: int = 300) -> str:
    value = _CELL.sub(" ", str(text if text is not None else "")).strip()
    return value[:limit] + ("…" if len(value) > limit else "")


def _rows(workflow: dict, volume: str | None = None) -> list[dict]:
    rows = [r for r in (workflow.get("requirements") or {}).values()
            if r.get("status") != "rejected" and not r.get("out_of_scope") and (volume is None or r.get("volume") == volume)]
    files = list((workflow.get("files") or {}).keys())

    def order(row):
        source = row.get("source") or {}
        return (files.index(source.get("file_id")) if source.get("file_id") in files else 99, source.get("page") or 0)
    return sorted(rows, key=order)


def _table(header: list[str], body: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in body]
    return "\n".join(lines)


def _chapter_numbers(state: Any, project_id: str, workflow: dict) -> dict[str, str]:
    order = workflow.get("chapter_order") or [c.id for c in state.chapters.values() if c.project_id == project_id]
    return {cid: f"第 {i + 1} 章" for i, cid in enumerate(order)}


def _response_kind(row: dict) -> str | None:
    from .matrix import response_type
    return response_type(row)


def point_to_point(state, project, workflow, chapter) -> tuple[str, list[str]]:
    gaps, body = [], []
    for n, row in enumerate([r for r in _rows(workflow, chapter.volume) if r.get("section_kind") != "scoring"], start=1):
        kind = _response_kind(row)
        answer = str(row.get("response") or "").strip()
        if not answer:
            answer = "【待补：请在响应矩阵填写响应要点】"
            gaps.append(row["id"])
        body.append([n, ("★ " if "★" in str(row.get("text")) else "") + str(row.get("text")), answer,
                     RESPONSE_LABEL.get(kind, "【待补：响应方式】")])
    if not body:
        return "本分册没有需要逐条应答的条款。", gaps
    return _table(["序号", "招标条款", "应答", "响应方式"], body), gaps


def review_index(state, project, workflow, chapter) -> tuple[str, list[str]]:
    numbers = _chapter_numbers(state, project.id, workflow)
    titles = {c.id: c.title for c in state.chapters.values() if c.project_id == project.id}
    gaps, body = [], []
    for n, row in enumerate([r for r in _rows(workflow) if r.get("category") == "scoring" or r.get("section_kind") == "scoring"], start=1):
        target = row.get("chapter_id")
        where = f"{numbers.get(target, '')} {titles.get(target, '')}".strip() if target else ""
        if not where:
            where = "【待补：在矩阵中对应章节】"
            gaps.append(row["id"])
        score = row.get("score")
        body.append([n, str(row.get("text")), f"{score:g}" if isinstance(score, (int, float)) else "",
                     str(row.get("response") or ""), where, "合标后由商务填写"])
    if not body:
        return "招标文件未列出评分项，无需评审索引表。", gaps
    return _table(["序号", "评分项", "分值", "得分要点", "对应章节", "页码"], body), gaps


def deviation(state, project, workflow, chapter) -> tuple[str, list[str]]:
    gaps, body = [], []
    for row in _rows(workflow):
        kind = _response_kind(row)
        if kind not in ("deviate", "exceed"):
            continue
        reason = str(row.get("deviation_reason") or "").strip()
        if not reason:
            reason = "【待补：偏离说明】"
            gaps.append(row["id"])
        body.append([len(body) + 1, str(row.get("text")), str(row.get("response") or ""),
                     "负偏离" if kind == "deviate" else "正偏离", reason])
    if not body:
        return "无偏离。\n\n投标人对招标文件的技术与商务要求全部响应，无正偏离、无负偏离。", gaps
    return _table(["序号", "招标条款", "投标响应", "偏离", "说明"], body), gaps


SERVICE_ITEMS = (("inspection", "巡检"), ("report", "服务报告 / 总结"), ("training", "培训"), ("resident", "驻场"))


def service_plan(state, project, workflow, chapter) -> tuple[str, list[str]]:
    from .generation_context import project_facts
    from .sla import public_sla
    gaps = []
    facts = {f["key"]: f for f in project_facts(state, project.id) if f.get("status") == "confirmed"}
    period = facts.get("服务期限")
    lines = [f"服务期：{{{{fact:{period['id']}}}}}" if period and not period.get("sla_var_key") else
             "服务期：【待补：项目事实“服务期限”未确认】"]
    if not period:
        gaps.append("服务期限")
    sla = public_sla(state, project.id) or {"rows": []}
    body = []
    for group, label in SERVICE_ITEMS:
        rows = [r for r in sla["rows"] if r.get("group") == group]
        if not rows:
            body.append([label, "【待补：SLA 模板未登记该项频次】", "—"])
            gaps.append(group)
            continue
        for row in rows:
            confirmed = row.get("fact_status") == "confirmed" and row.get("project_value") not in (None, "")
            value = row["variable_token"] if confirmed else "【待补：该 SLA 取值未确认】"
            if not confirmed:
                gaps.append(row.get("var_key") or group)
            body.append([row.get("label") or label, value, "SLA 承诺（已确认）" if confirmed else "SLA 待确认"])
    return "\n".join(lines) + "\n\n" + _table(["服务项目", "频次 / 人数", "依据"], body), gaps


_PROOF = re.compile(r"证明|证书|复印件|扫描件|营业执照|合同|发票|授权|审计报告|截图|认证")


def proof_list(state, project, workflow, chapter) -> tuple[str, list[str]]:
    from .generation_context import evidence_expired
    gaps, body = [], []
    for row in _rows(workflow):
        qualification = row.get("section_kind") == "qualification" or row.get("category") == "qualification"
        objective = (row.get("category") == "scoring" or row.get("section_kind") == "scoring") and _PROOF.search(str(row.get("text")))
        if not (qualification or objective):
            continue
        attached = []
        for eid in row.get("evidence_ids") or []:
            item = state.library.get(eid) or {}
            expiry = "长期" if item.get("is_long_term") else (item.get("valid_to") or item.get("valid_until") or "未登记")
            mark = "（已失效）" if item and evidence_expired(item, project.deadline) else ""
            attached.append(f"{item.get('name', '资料已删除')} v{item.get('revision', '?')} · 有效期 {expiry}{mark}")
        if not attached:
            gaps.append(row["id"])
        seal = "须盖章（人工核对）" if re.search(r"盖章|公章", str(row.get("text"))) else ""
        body.append([len(body) + 1, "资格" if qualification else "客观评分", str(row.get("text")),
                     "；".join(attached) or "【待补：资料库尚未挂接证明材料】", "缺项" if not attached else "已挂接", seal])
    if not body:
        return "招标文件的资格项与客观评分项未要求证明材料。", gaps
    return _table(["序号", "类型", "条款", "应附材料（版本 / 有效期）", "状态", "盖章"], body), gaps


GENERATORS = {"point_to_point": point_to_point, "review_index": review_index, "deviation": deviation,
              "service_plan": service_plan, "proof_list": proof_list}


def source_fingerprint(state, project, workflow, chapter, kind: str) -> str:
    content, _ = GENERATORS[kind](state, project, workflow, chapter)
    return hashlib.sha256(json.dumps([kind, content], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def render(state, project, workflow, chapter) -> dict:
    kind = kind_of(chapter.title)
    if kind is None:
        raise DomainError(409, "SYSTEM_CHAPTER_READONLY", "本章不是系统生成章节。")
    body, gaps = GENERATORS[kind](state, project, workflow, chapter)
    label = KINDS[kind][0]
    content = f"{body}\n\n（本节为系统生成的{label}，内容来自响应矩阵、项目事实与资料库；要修改请改数据源后重新生成。）"
    return {"kind": kind, "label": label, "content": content, "gaps": gaps,
            "fingerprint": hashlib.sha256(json.dumps([kind, body], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]}


def is_system_chapter(workflow: dict, chapter) -> bool:
    return chapter.id in (workflow.get("system_chapters") or {})


def refuse_manual_edit(state, chapter) -> None:
    """系统生成章节不能在正文里手改（含编辑台提交、AI 建议采纳、答案卡插入）。"""
    workflow = state.workflows.get(chapter.project_id) or {}
    if is_system_chapter(workflow, chapter):
        raise DomainError(409, "SYSTEM_CHAPTER_READONLY", "本节由系统根据数据生成，不能在正文中修改；请回到响应矩阵、项目事实或资料库修改后重新生成。")


def stale_system_chapters(state, project, workflow) -> list[dict]:
    stale = []
    for cid, record in (workflow.get("system_chapters") or {}).items():
        chapter = state.chapters.get(cid)
        if chapter is None:
            continue
        current = render(state, project, workflow, chapter)
        if current["fingerprint"] != record.get("fingerprint") or chapter.content != record.get("content"):
            stale.append({"chapter_id": cid, "title": chapter.title, "kind": current["kind"]})
    return stale


class SystemChapterMixin:
    """WorkflowService 的系统生成章节能力。"""

    def preview_system_chapter(self, principal: Principal, project_id: str, chapter_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
        workflow = self._workflow(state, project_id)
        result = render(state, project, workflow, chapter)
        record = (workflow.get("system_chapters") or {}).get(chapter_id)
        return {**result, "chapter_id": chapter_id, "generated": bool(record),
                "generated_at": (record or {}).get("generated_at"),
                "stale": bool(record) and (record.get("fingerprint") != result["fingerprint"] or chapter.content != record.get("content"))}

    def generate_system_chapter(self, principal: Principal, project_id: str, chapter_id: str, payload: dict,
                                expected: str | None, key: str | None) -> dict:
        def operation(state, project, workflow):
            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")
            if (workflow.get("volumes") or {}).get(chapter.volume, {}).get("is_finalized"):
                raise DomainError(409, "VOLUME_FINALIZED", "所在分册已定稿，须先解锁再重新生成。")
            if chapter.lock and chapter.lock.expires_at > self.demo._now():
                raise DomainError(409, "CHAPTER_IN_USE", "本节正在被编辑，请先释放编辑权。")
            result = render(state, project, workflow, chapter)
            now = iso_time(self.demo._now())
            if chapter.content != result["content"]:
                chapter.content = result["content"]
                chapter.revision += 1
                chapter.versions.append({"revision": chapter.revision, "content": chapter.content, "actor_id": principal.user.id,
                                         "created_at": now, "source": "system_generated", "note": f"系统生成{result['label']}"})
            workflow.setdefault("system_chapters", {})[chapter_id] = {
                "kind": result["kind"], "fingerprint": result["fingerprint"], "content": chapter.content,
                "generated_at": now, "generated_by": principal.user.id, "gaps": result["gaps"]}
            return {"chapter_id": chapter_id, "chapter_revision": chapter.revision, "kind": result["kind"], "gaps": result["gaps"]}

        return self._write(principal, project_id, f"chapter.system:{chapter_id}", payload, expected, key, operation)
