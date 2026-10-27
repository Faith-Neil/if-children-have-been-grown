# 为什么有这个文件：由 workflow_orchestrator 解耦抽取的知识库/资质库与后台任务管理子编排服务（BE-TECH-DEBT-03）。
# 它解决什么问题：
# 1. 公司知识库/证据库列表查询（library）、新增/更新/重新确认（write_library）；
# 2. 证据库 ACL 鉴权、受限资料挂接校验（_reject_unusable_mount）；
# 3. 后台异步任务统一视图与平台管理员脱敏查询（jobs）。

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from icg.domain.domain import DomainError, Principal, new_id
from icg.domain.generation_context import evidence_expired
from icg.domain.idempotency import lookup, remember
from icg.domain.project_access import (
    ROLE_COMPANY_ADMIN,
    ROLE_DATA_ADMIN,
    ROLE_PLATFORM_ADMIN,
    normalize_role,
)


class LibraryOrchestratorMixin:
    """企业资料库与后台任务领域编排 Mixin。"""

    def jobs(self, principal: Principal, masked: bool = False) -> dict:
        state = self.repository.read()
        norm_role = normalize_role(principal.user.role)
        is_platform_admin = (norm_role == ROLE_PLATFORM_ADMIN)
        should_mask = is_platform_admin or bool(masked)

        if not should_mask:
            if norm_role in (ROLE_COMPANY_ADMIN, ROLE_DATA_ADMIN):
                allowed = {p.id for p in state.projects.values() if p.company_id == principal.user.company_id}
            else:
                allowed = {
                    p.id for p in state.projects.values()
                    if p.company_id == principal.user.company_id
                    and principal.user.id in state.project_teams.get(p.id, {}).get("members", {})
                }
            return {"jobs": [j for j in state.jobs.values() if j.get("project_id") in allowed]}

        all_jobs_dict = {}
        for j in state.jobs.values():
            all_jobs_dict[j["id"]] = dict(j)
        for j in state.recoverable_jobs.values():
            all_jobs_dict[j["id"]] = dict(j)
        records = getattr(state, "_job_records", {})
        for jid, rec in records.items():
            if jid not in all_jobs_dict:
                all_jobs_dict[jid] = dict(rec)

        projects_by_id = {p.id: p for p in state.projects.values()}

        masked_jobs = []
        for j in all_jobs_dict.values():
            pid = j.get("project_id", "")
            if not is_platform_admin:
                proj = projects_by_id.get(pid)
                if not proj or proj.company_id != principal.user.company_id:
                    continue

            company_id = "unknown"
            if pid in projects_by_id:
                company_id = projects_by_id[pid].company_id
            elif j.get("company_id"):
                company_id = j["company_id"]

            masked_company = (company_id[:2] + "***") if len(company_id) > 2 else "**"

            duration_ms = j.get("duration_ms")
            if duration_ms is None:
                try:
                    c_at = j.get("created_at")
                    f_at = j.get("completed_at") or j.get("updated_at")
                    if c_at and f_at:
                        t1 = datetime.fromisoformat(str(c_at).replace("Z", "+00:00"))
                        t2 = datetime.fromisoformat(str(f_at).replace("Z", "+00:00"))
                        duration_ms = max(0, int((t2 - t1).total_seconds() * 1000))
                    else:
                        duration_ms = 0
                except Exception:
                    duration_ms = 0

            raw_status = j.get("status", "pending")
            status = "queued" if raw_status == "pending" else raw_status
            error = j.get("error_json") or j.get("error")
            err_code = None
            if isinstance(error, dict):
                err_code = error.get("code")
            elif isinstance(error, str):
                err_code = error

            job_type = j.get("job_type", j.get("type", "generation"))
            type_labels = {
                "parse_tender": "招标文件解析",
                "generate": "章节生成",
                "generate_chapter": "章节生成",
                "check_compliance": "合规检查",
                "export_docx": "两卷导出",
            }
            type_label = type_labels.get(job_type, "后台计算")
            if status in ("running", "queued", "pending"):
                masked_summary = f"{type_label}任务正在执行（业务细节已脱敏）"
            elif status in ("completed", "succeeded"):
                masked_summary = f"{type_label}任务已完成（业务细节已脱敏）"
            elif status == "cancelled":
                masked_summary = f"{type_label}任务已取消（业务细节已脱敏）"
            else:
                masked_summary = f"{type_label}任务执行异常（业务细节已脱敏）"

            masked_job = {
                "id": j["id"],
                "project_id": "prj-***",
                "type": job_type,
                "status": status,
                "progress": int(j.get("progress", 0)),
                "message": masked_summary,
                "created_at": str(j.get("created_at") or ""),
                "completed_at": str(j["completed_at"]) if j.get("completed_at") else None,
                "error": {"code": err_code, "message": "执行异常（已脱敏）"} if err_code else None,
                "recoverable": False,
                "duration_ms": duration_ms,
                "company_id": masked_company,
                "masked_company": masked_company,
                "summary": masked_summary,
                "masked_summary": masked_summary,
                "is_masked": True,
                "error_code": err_code,
                "allowed_actions": [],
                "allowedActions": [],
            }
            masked_jobs.append(masked_job)

        return {"jobs": masked_jobs}

    @staticmethod
    def _public_library(item: dict) -> dict:
        public = {
            "reason": "",
            "source_tier": "own",
            "is_restricted": False,
            "is_long_term": False,
            "valid_to": None,
            "partner_entity_id": None,
            **item,
            "usable_as_evidence": item["status"] == "confirmed" and item["type"] != "history",
        }
        public.pop("acl_user_ids", None)
        public.pop("restricted", None)
        return public

    @staticmethod
    def _replace_library_acl(state: Any, company_id: str, evidence_id: str, user_ids: list[str]) -> None:
        state.resource_acl = [
            row for row in state.resource_acl
            if not (row["ref_type"] == "library" and row["ref_id"] == evidence_id)
        ]
        seen = set()
        for user_id in user_ids:
            if user_id in seen:
                continue
            seen.add(user_id)
            account = state.accounts.get(user_id)
            if account is None or account.company_id != company_id:
                raise DomainError(422, "INVALID_LIBRARY_FIELD", "授权用户必须属于本公司。")
            state.resource_acl.append({
                "ref_type": "library",
                "ref_id": evidence_id,
                "user_id": user_id,
                "company_id": company_id,
            })

    @staticmethod
    def _agreement_present(state: Any, project_id: str, evidence: dict) -> bool:
        partner_id = evidence.get("partner_entity_id")
        if not partner_id:
            return False
        for row in state.project_partners.get(project_id, []):
            if row.get("partner_entity_id") == partner_id and str(row.get("agreement_attachment_id") or "").strip():
                return True
        return False

    @staticmethod
    def _restricted_allowed(state: Any, principal: Principal, evidence: dict) -> bool:
        if principal.user.role in ("company_admin", "data_admin"):
            return True
        company_id = principal.user.company_id
        return any(
            row["ref_type"] == "library"
            and row["ref_id"] == evidence["id"]
            and row["user_id"] == principal.user.id
            and row["company_id"] == company_id
            for row in state.resource_acl
        )

    def _reject_unusable_mount(self, state: Any, principal: Principal, project: Any, evidence: dict) -> None:
        if evidence.get("is_restricted") and not self._restricted_allowed(state, principal, evidence):
            raise DomainError(403, "FORBIDDEN", "受限资料需公司管理员、资料管理员或资源授权后才能挂接。")
        if evidence.get("source_tier") == "reference":
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "仅供参考资料不能作为投标证据挂接。")
        if evidence.get("source_tier") == "partner" and not self._agreement_present(state, project.id, evidence):
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "合作方资料缺协议，不能作为投标证据挂接。")
        if evidence_expired(evidence, project.deadline):
            raise DomainError(409, "EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。")

    def library(self, principal: Principal) -> dict:
        state = self.repository.read()
        return {
            "revision": state.library_revisions.get(principal.user.company_id, 1),
            "items": [
                self._public_library(item)
                for item in state.library.values()
                if item["company_id"] == principal.user.company_id
            ],
        }

    def write_library(self, principal: Principal, payload: dict, expected: str | None, key: str | None, item_id: str | None = None) -> dict:
        self.demo._writer(principal)
        key = self._idempotency(key)
        company = principal.user.company_id
        scope_id = "library:" + company
        action = "library.update:" + item_id if item_id else "library.create"
        request_fingerprint = self._request_hash(action, payload, expected)

        def operation(state):
            revision = state.library_revisions.get(company, 1)
            replay = lookup(state, scope_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            self._version(revision, expected)
            for date_key in ("valid_until", "valid_to"):
                if payload.get(date_key):
                    if len(payload[date_key]) != 10:
                        raise DomainError(422, "INVALID_DATE", "资料有效期请使用 YYYY-MM-DD。")
                    self._date(payload[date_key])
            replace_acl = "acl_user_ids" in payload
            acl_user_ids = payload.pop("acl_user_ids", None)
            if any(v is None and k not in ("valid_until", "valid_to", "partner_entity_id") for k, v in payload.items()):
                raise DomainError(422, "INVALID_LIBRARY_FIELD", "资料字段不能设为空值。")
            if any(k in payload and not payload[k].strip() for k in ("name", "content")):
                raise DomainError(422, "EMPTY_LIBRARY_FIELD", "资料名称和正文不能为空。")
            if item_id:
                item = state.library.get(item_id)
                if item is None or item["company_id"] != company:
                    raise DomainError(404, "NOT_FOUND", "未找到本公司资料。")
                updated_fields = dict(payload)
                changed = any(
                    k in payload and payload[k] != item.get(k)
                    for k in (
                        "name", "type", "content", "valid_until", "valid_to", "is_long_term",
                        "source_tier", "partner_entity_id", "is_restricted",
                    )
                )
                if changed:
                    if payload.get("status") == "confirmed":
                        if not payload.get("reason", "").strip():
                            raise DomainError(409, "REVIEW_REASON_REQUIRED", "资料实质内容已变化；重新确认时请填写本次核对依据。")
                    else:
                        updated_fields.update(status="pending", reason="")
                item.update(updated_fields)
                item["revision"] += 1
            else:
                item = {"id": new_id("evidence"), "company_id": company, **payload, "revision": 1}
                state.library[item["id"]] = item
            if replace_acl:
                self._replace_library_acl(state, company, item["id"], acl_user_ids or [])
            state.library_revisions[company] = revision + 1
            result = {"revision": revision + 1, "item": self._public_library(item)}
            remember(state, scope_id, principal.user.id, key, request_fingerprint, result, self.demo._now())
            return result

        return self.repository.transaction(operation)


class LibraryOrchestrator(LibraryOrchestratorMixin):
    """企业资料库与后台任务独立领域编排服务。"""

    def __init__(self, workflow: Any = None):
        self._workflow_service = workflow

    def __getattr__(self, name: str) -> Any:
        if hasattr(self, "_workflow_service") and self._workflow_service is not None and hasattr(self._workflow_service, name):
            return getattr(self._workflow_service, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
