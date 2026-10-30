# 为什么有这个文件：响应矩阵（PRD v1.8 §5.3.1，APP-M2-T112～T117）的后台：列表与风险、响应方式、批量匹配候选、分册分流确认、Excel。
# 它解决什么问题：矩阵页原先只是条款列表——没有响应方式（满足/优于/偏离/不适用）、没有风险标记、
# “智能匹配证据”按钮是灰的、不能导出 Excel、分流没有确认记录。
# 规则：星号/废标条款不能标“不适用”；如实登记“偏离”时列为阻断项（PRD §5.3.1 规则 5，由检查挡住递交）；
# 在矩阵里选“偏离/不适用”必须写说明；候选只给依据，不自动挂接，
# 已挂证据不被替换；状态与风险分开显示；历史标书只作参考，不是证据候选。

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .domain import DomainError, Principal, iso_time
from .generation_context import evidence_expired

RESPONSE_TYPES = {
    "comply": ("满足", "none", "无偏离"),
    "exceed": ("优于", "positive", "正偏离"),
    "deviate": ("偏离", "negative", "负偏离"),
    "not_applicable": ("不适用", "not_applicable", "不适用"),
}
DEVIATION_TO_RESPONSE = {"none": "comply", "无偏离": "comply", "positive": "exceed", "正偏离": "exceed",
                         "negative": "deviate", "负偏离": "deviate", "not_applicable": "not_applicable"}
RISK_LABELS = {
    "star_deviation": "星号/废标条款偏离", "evidence_invalid": "证据失效", "evidence_missing": "缺证据",
    "placeholder": "含【待补】", "response_missing": "未写响应", "unmapped": "未对应章节", "routing_pending": "分流待确认",
}
_EVIDENCE_WORDS = re.compile(r"资质|证书|证明|业绩|授权|执照|认证|合同|复印件|扫描件")
_CRITICAL = re.compile(r"[★▲]|废标|无效投标|否决")


def critical(row: dict) -> bool:
    return (str(row.get("category", "")) in ("mandatory", "star", "disqualification")
            or str(row.get("importance", "")).lower() in ("star", "critical", "disqualification")
            or bool(_CRITICAL.search(str(row.get("text", "")))))


def response_type(row: dict) -> str | None:
    if row.get("response_type") in RESPONSE_TYPES:
        return row["response_type"]
    return DEVIATION_TO_RESPONSE.get(str(row.get("deviation_type") or ""))


def default_volume(row: dict, active: tuple[str, ...]) -> str:
    """PRD §5.3.1 规则 8 的默认分流：主观评分与技术服务归技术，客观评分与资格归商务。"""
    if len(active) == 1:
        return active[0]
    kind, text = row.get("section_kind") or row.get("category"), str(row.get("text") or "")
    if kind == "qualification":
        return "business"
    if kind == "scoring" or row.get("category") == "scoring":
        objective = bool(re.search(r"每(提供|有)|提供.{0,10}得\s*\d|证书|业绩|认证|得\d+(\.\d+)?分[，,；;]?最多", text))
        return "business" if objective else "technical"
    return row.get("volume") or "technical"


def risk_flags(state: Any, project: Any, row: dict) -> list[str]:
    flags = []
    if critical(row) and response_type(row) in ("deviate", "not_applicable"):
        flags.append("star_deviation")
    for eid in row.get("evidence_ids") or []:
        item = state.library.get(eid)
        if (item is None or item.get("status") != "confirmed" or item.get("type") == "history"
                or evidence_expired(item, project.deadline)):
            flags.append("evidence_invalid")
            break
    if _EVIDENCE_WORDS.search(str(row.get("text") or "")) and not row.get("evidence_ids"):
        flags.append("evidence_missing")
    if "【待补" in str(row.get("response") or ""):
        flags.append("placeholder")
    if not str(row.get("response") or "").strip() and response_type(row) != "not_applicable":
        flags.append("response_missing")
    if not row.get("chapter_id") and response_type(row) != "not_applicable":
        flags.append("unmapped")
    if not row.get("volume_confirmed_at"):
        flags.append("routing_pending")
    return flags


def validate_response(row: dict, explicit: bool = True) -> None:
    """行编辑写入前的业务核对（PRD §5.3.1 规则 5、9）。

    星号/废标条款做不到时必须能如实登记“偏离”（系统不能逼人写满足），它会成为阻断项；
    但不能用“不适用”绕开。explicit=False 表示调用方只写了旧的 deviation_type，说明由 R37 继续提醒。
    """
    kind = response_type(row)
    if kind is None:
        return
    if critical(row) and kind == "not_applicable":
        raise DomainError(409, "REQUIREMENT_NOT_READY", "星号或废标条款不能标为不适用；做不到请如实选“偏离”，导出会被阻断。")
    if explicit and kind in ("deviate", "not_applicable") and not str(row.get("deviation_reason") or row.get("reason") or "").strip():
        raise DomainError(422, "REASON_REQUIRED", "偏离或不适用必须填写说明。")


def apply_response_type(row: dict, payload: dict) -> dict:
    """response_type 与原有 deviation_type 保持同一口径（满足=无偏离、优于=正偏离、偏离=负偏离）。"""
    kind = payload.get("response_type")
    if kind:
        payload = {**payload, "deviation_type": RESPONSE_TYPES[kind][1]}
    elif payload.get("deviation_type") and payload["deviation_type"] in DEVIATION_TO_RESPONSE:
        payload = {**payload, "response_type": DEVIATION_TO_RESPONSE[payload["deviation_type"]]}
    return payload


def _grams(text: str) -> set[str]:
    value = re.sub(r"[\s\W_]+", "", str(text or ""))
    return {value[i:i + 2] for i in range(len(value) - 1)}


def _attachable(state: Any, project: Any, item: dict) -> tuple[bool, str]:
    if item.get("type") == "history":
        return False, "历史标书仅供参考"
    if item.get("status") != "confirmed":
        return False, "资料未确认"
    if item.get("source_tier") == "reference":
        return False, "仅供参考资料"
    if item.get("source_tier") == "partner" and not any(
            p.get("partner_entity_id") == item.get("partner_entity_id") and str(p.get("agreement_attachment_id") or "").strip()
            for p in (state.project_partners.get(project.id) or [])):
        return False, "合作方资料缺协议"
    if evidence_expired(item, project.deadline):
        return False, "有效期不能覆盖投标截止时间"
    return True, ""


from .system_chapters import SystemChapterMixin  # noqa: E402


from .parse_review import ParseReviewMixin  # noqa: E402  解析结果分类树与批量确认（APP-M2-T104）
from .staff_proof_rules import ProposedStaffMixin  # noqa: E402  拟派人员（APP-M2-T241）


class MatrixMixin(SystemChapterMixin, ParseReviewMixin, ProposedStaffMixin):
    """WorkflowService 的响应矩阵能力。"""

    def _matrix_item(self, state, project, workflow, row, active, names) -> dict:
        kind = response_type(row)
        evidence = []
        for eid in row.get("evidence_ids") or []:
            item = state.library.get(eid) or {}
            ok, why = _attachable(state, project, item) if item else (False, "资料已删除")
            evidence.append({"id": eid, "name": item.get("name", "资料已删除"), "revision": item.get("revision"),
                             "valid_until": item.get("valid_until") or item.get("valid_to"), "usable": ok, "reason": why})
        flags = risk_flags(state, project, row)
        return {
            "id": row["id"], "text": row.get("text", ""), "source": row.get("source"), "category": row.get("category"),
            "section_kind": row.get("section_kind"), "score": row.get("score"), "critical": critical(row),
            "volume": row.get("volume"), "suggested_volume": default_volume(row, active),
            "volume_confirmed_by": row.get("volume_confirmed_by"), "volume_confirmed_at": row.get("volume_confirmed_at"),
            "is_cross_volume": bool(row.get("is_cross_volume")),
            "response_type": kind, "response_label": RESPONSE_TYPES[kind][0] if kind else "未选择",
            "deviation_label": RESPONSE_TYPES[kind][2] if kind else "", "response": row.get("response", ""),
            "deviation_reason": row.get("deviation_reason") or "", "chapter_id": row.get("chapter_id"),
            "assignee_id": row.get("assignee_id"), "assignee_name": names.get(row.get("assignee_id")),
            "status": row.get("status"), "out_of_scope": bool(row.get("out_of_scope")),
            "evidence": evidence, "risk_flags": flags, "risk_labels": [RISK_LABELS[f] for f in flags],
        }

    def matrix(self, principal: Principal, project_id: str, volume: str = "all") -> dict:
        from .project_access import project_volumes
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        active = project_volumes(state, project_id)
        names = {aid: a.name for aid, a in state.accounts.items()}
        rows = [r for r in workflow.get("requirements", {}).values() if volume == "all" or r.get("volume") == volume]
        items = [self._matrix_item(state, project, workflow, r, active, names) for r in rows]
        live = [i for i in items if i["status"] != "rejected"]
        stats = {
            "total": len(live), "confirmed": sum(1 for i in live if i["status"] == "confirmed"),
            "critical_unconfirmed": sum(1 for i in live if i["critical"] and i["status"] != "confirmed"),
            "evidence_missing": sum(1 for i in live if "evidence_missing" in i["risk_flags"]),
            "evidence_invalid": sum(1 for i in live if "evidence_invalid" in i["risk_flags"]),
            "placeholder": sum(1 for i in live if "placeholder" in i["risk_flags"]),
            "routing_pending": sum(1 for i in live if "routing_pending" in i["risk_flags"]),
            "out_of_scope": sum(1 for i in items if i["out_of_scope"]),
        }
        responded = sum(1 for i in live if i["response"].strip() or i["response_type"] == "not_applicable")
        stats["coverage"] = round(responded * 100 / len(live)) if live else 0
        return {"revision": project.revision, "project_id": project_id, "volume": volume, "volumes": list(active),
                "stats": stats, "items": items}

    def match_evidence(self, principal: Principal, project_id: str, requirement_ids: list[str]) -> dict:
        """批量智能匹配：只返回候选与依据，不挂接（PRD §5.3.1 规则 11：结果逐行确认）。"""
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        rows = workflow.get("requirements", {})
        if not requirement_ids or any(rid not in rows for rid in requirement_ids):
            raise DomainError(404, "NOT_FOUND", "所选条款不存在或不属于本项目。")
        library = [i for i in state.library.values() if i.get("company_id") == project.company_id]
        kb = getattr(self.demo, "knowledge_base", None)
        results = []
        for rid in requirement_ids[:50]:
            row = rows[rid]
            want = _grams(row.get("text"))
            structured, history = [], []
            for item in library:
                overlap = len(want & _grams(f"{item.get('name', '')}{item.get('content', '')}")) / max(1, len(want))
                if overlap < 0.12:
                    continue
                ok, why = _attachable(state, project, item)
                entry = {"id": item["id"], "name": item.get("name"), "type": item.get("type"), "revision": item.get("revision"),
                         "valid_until": item.get("valid_until") or item.get("valid_to"), "score": round(overlap, 3),
                         "attachable": ok, "reason": why, "already_attached": item["id"] in (row.get("evidence_ids") or []),
                         "basis": "资料名称与内容和条款原文字面重合"}
                (history if item.get("type") == "history" else structured).append(entry)
            snippets = []
            if kb is not None:
                try:
                    hits, _skip = kb.search(project.company_id, str(row.get("text", ""))[:300], limit=5, user=principal.user)
                    for hit in hits:
                        public = hit.to_public()
                        target = history if public.get("reference_only") else snippets
                        target.append({**public, "attachable": False if public.get("reference_only") else public.get("attachable", False),
                                       "basis": "公司知识库检索"})
                except Exception:  # 知识库不可用时只给结构化候选，并说明
                    snippets = [{"unavailable": True, "reason": "知识库暂不可用，只给出资料库规则匹配结果"}]
            structured.sort(key=lambda c: (not c["attachable"], -c["score"]))
            results.append({"requirement_id": rid, "structured": structured[:8], "snippets": snippets,
                            "history_reference": history[:5]})
        return {"project_id": project_id, "results": results,
                "notice": "候选不会自动挂接；逐行勾选后点“挂接”才写入，已挂证据不会被替换。"}

    def confirm_routing(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        """分册分流确认（PRD §5.3.1 规则 8）：项目负责人逐行确认归属分册与跨分册共用。"""
        from .project_access import project_volumes, require_lead

        def operation(state, project, workflow):
            require_lead(state, principal, project_id)
            active = project_volumes(state, project_id)
            now = iso_time(self.demo._now())
            confirmed = []
            for item in payload.get("rows") or []:
                row = workflow["requirements"].get(item.get("id"))
                if row is None:
                    raise DomainError(404, "NOT_FOUND", "所选条款不存在或不属于本项目。")
                volume = item.get("volume") or row.get("volume")
                if volume not in active:
                    raise DomainError(404, "NOT_FOUND", "本项目只编写技术标，没有商务分册。")
                if volume != row.get("volume") and row.get("chapter_id"):
                    chapter = state.chapters.get(row["chapter_id"])
                    if chapter is not None and chapter.volume != volume:
                        row["chapter_id"] = None  # 换了分册，原章节对应失效，须重新对应
                row.update(volume=volume, is_cross_volume=bool(item.get("is_cross_volume")) and len(active) > 1,
                           volume_confirmed_by=principal.user.id, volume_confirmed_at=now)
                confirmed.append(row["id"])
            if confirmed:
                workflow["plan_confirmed"] = False
            return {"confirmed_ids": confirmed}

        return self._write(principal, project_id, "matrix.routing", payload, expected, key, operation)

    def matrix_xlsx(self, principal: Principal, project_id: str, volume: str = "all") -> bytes:
        from icg.infra.xlsx import build_xlsx
        data = self.matrix(principal, project_id, volume)
        state = self.repository.read()
        chapters = {c.id: c.title for c in state.chapters.values() if c.project_id == project_id}
        project = state.projects[project_id]
        warn = data["stats"]["critical_unconfirmed"]
        rows = [[f"响应矩阵 · {project.name}"],
                [f"导出 {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')} · 共 {data['stats']['total']} 条 · 覆盖率 {data['stats']['coverage']}%"
                 + (f" · 【注意】{warn} 条星号/废标条款尚未确认" if warn else "")],
                [],
                ["序号", "要求原文", "页码", "类别", "分值", "星号/废标", "归属分册", "分流确认", "响应方式", "偏离口径",
                 "响应要点", "偏离/不适用说明", "对应章节", "证据（版本）", "负责人", "状态", "风险"]]
        status_names = {"confirmed": "已确认", "pending": "待确认", "rejected": "已忽略", "needs_review": "需复核"}
        for n, item in enumerate(data["items"], start=1):
            rows.append([n, item["text"], (item.get("source") or {}).get("page") or "", item.get("category") or "",
                         item.get("score") if item.get("score") is not None else "", "是" if item["critical"] else "",
                         {"technical": "技术", "business": "商务"}.get(item.get("volume"), item.get("volume") or ""),
                         "已确认" if item.get("volume_confirmed_at") else "待确认", item["response_label"], item["deviation_label"],
                         item["response"], item["deviation_reason"], chapters.get(item.get("chapter_id"), ""),
                         "；".join(f"{e['name']}（v{e['revision']}）{'' if e['usable'] else '·' + e['reason']}" for e in item["evidence"]),
                         item.get("assignee_name") or "", status_names.get(item["status"], item["status"]),
                         "、".join(item["risk_labels"])])
        self.repository.transaction(lambda st: self._audit(st, principal, project_id, "matrix.export", {"rows": len(data["items"])}))
        return build_xlsx([{"name": "响应矩阵", "rows": rows, "header_rows": 4,
                            "widths": [6, 50, 6, 10, 6, 8, 8, 8, 8, 8, 36, 24, 20, 28, 10, 8, 20]}])
