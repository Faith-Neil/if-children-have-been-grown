# 为什么有这个文件：实现 PRD §5.8.5 分册定稿（finalize）状态机与安全门禁。
# 它解决什么问题：
# 1. 严格权限校验：仅当前公司项目负责人（project_lead）或公司管理员（company_admin）可定稿；编写人拦截 403 FORBIDDEN；跨租户拦截 404 NOT_FOUND。
# 2. 前置安全门禁：
#    - 该分册所有章节必须已有正式版本正文且当前未被排他锁定；
#    - 该分册不能存在未消解的 severity == "blocker" 缺陷（废标红线与关键星号条款未满足）；
#    - 该分册没有待人工处理的问题，且已由非本册编写人完成交叉复核、复核对应的仍是当前正文（Wave 11）；
# 3. 状态流转与持久化：标记 is_finalized = True，记录定稿人 ID 与时间戳 finalized_at，支持定稿查询与先解锁后修改。

from __future__ import annotations

import time
from typing import Any

from icg.domain.domain import DemoState, DomainError, Principal, Project, iso_time, new_id
from icg.domain.project_access import VOLUMES, normalize_role, lead, volume_owner
from icg.domain.export_service import ExportServiceMixin
from icg.domain.volume_review import pending_human_issues, public_review, require_cross_review, reset_review_on_unlock


class VolumeGateError(DomainError):
    """分册定稿门禁专用异常，支持细粒度业务错误码与 409 状态码。"""

    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        Exception.__init__(self, message)


def is_chapter_locked(chapter: Any, now: float) -> bool:
    """检查章节当前是否处于有效排他锁定状态。"""
    if chapter.lock is None:
        return False
    if chapter.lock.released_at is not None:
        return False
    return float(chapter.lock.expires_at) > now


def check_finalize_permissions(state: DemoState, principal: Principal, project: Project, volume_id: str | None = None) -> None:
    """权限校验：项目负责人、公司管理员或本分册负责人（PRD v1.8 §2.3）。跨租户 404，其它角色 403。"""
    if project.company_id != principal.user.company_id:
        raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

    norm_role = normalize_role(principal.user.role)
    if norm_role == "company_admin":
        return

    # 项目负责人判定（需是项目成员且 project_role == "lead"）
    if lead(state, project.id, principal.user.id):
        return
    if volume_id and volume_owner(state, project.id, volume_id, principal.user.id):
        return

    raise DomainError(403, "FORBIDDEN", "分册定稿仅限项目负责人、本册负责人或公司管理员办理。")


def check_volume_blockers(
    state: DemoState,
    project_id: str,
    volume_id: str,
    workflow: dict,
    check_id: str | None = None,
) -> None:
    """核验分册是否存在未解决的 blocker 严重度缺陷。"""
    checks = workflow.get("checks", {})

    # 1. 如果指定了 check_id，校验该检查批次
    if check_id:
        chk = checks.get(check_id)
        if chk is None:
            raise DomainError(404, "NOT_FOUND", "未找到指定检查批次。")
        if chk.get("volume") not in (volume_id, "all"):
            raise VolumeGateError(409, "VOLUME_MISMATCH", "指定的检查批次未覆盖当前分册。")
        for issue in chk.get("issues", []):
            if issue.get("severity") == "blocker":
                raise VolumeGateError(
                    409,
                    "CHECK_BLOCKER_EXISTS",
                    f"分册最新检查结果存在未解决的 blocker 缺陷：{issue.get('message', '废标或关键星号条款未满足')}。",
                )
    else:
        # 否则检查最新一次覆盖当前分册的检查结果
        vol_checks = [c for c in checks.values() if c.get("volume") in (volume_id, "all")]
        if vol_checks:
            latest_check = vol_checks[-1]
            for issue in latest_check.get("issues", []):
                if issue.get("severity") == "blocker":
                    raise VolumeGateError(
                        409,
                        "CHECK_BLOCKER_EXISTS",
                        f"分册最新检查结果存在未解决的 blocker 缺陷：{issue.get('message', '废标或关键星号条款未满足')}。",
                    )

    # 2. 实时核对该分册的条款状态，杜绝带病定稿
    for req in workflow.get("requirements", {}).values():
        if req.get("volume") != volume_id:
            continue
        if ExportServiceMixin._is_critical_requirement(req):
            text_snippet = (req.get("text") or "")[:30]
            if req.get("status") == "pending":
                raise VolumeGateError(
                    409,
                    "CHECK_BLOCKER_EXISTS",
                    f"关键条款「{text_snippet}」尚未确认，存在 blocker 缺陷，无法定稿。",
                )
            ch_id = req.get("chapter_id")
            ch = state.chapters.get(ch_id) if ch_id else None
            if ch is None or ch.project_id != project_id or ch.volume != volume_id:
                raise VolumeGateError(
                    409,
                    "CHECK_BLOCKER_EXISTS",
                    f"关键条款「{text_snippet}」未映射有效章节，存在 blocker 缺陷，无法定稿。",
                )
            resp = str(req.get("response", "") or "")
            if not resp.strip() or "待补" in resp:
                raise VolumeGateError(
                    409,
                    "CHECK_BLOCKER_EXISTS",
                    f"关键条款「{text_snippet}」未有效响应或仍有待补，存在 blocker 缺陷，无法定稿。",
                )
            need_evidence = any(
                word in (req.get("text") or "") for word in ("资质", "证书", "证明", "业绩", "授权")
            ) or req.get("need_evidence") is True
            if need_evidence and not req.get("evidence_ids"):
                raise VolumeGateError(
                    409,
                    "CHECK_BLOCKER_EXISTS",
                    f"关键证明类条款「{text_snippet}」缺少已确认企业证据，存在 blocker 缺陷，无法定稿。",
                )


class VolumeFinalizeMixin:
    """分册定稿状态机与门禁领域服务 Mixin。"""

    def _resolve_project(self, state: DemoState, principal: Principal, project_id: str) -> Project:
        """解析项目并校验租户隔离与账号有效性。"""
        project = state.projects.get(project_id)
        account = state.accounts.get(principal.user.id)
        if (
            project is None
            or project.is_deleted
            or account is None
            or project.company_id != account.company_id
            or state.sessions.get(principal.session_token) != account.id
        ):
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")
        return project

    def finalize_volume(
        self,
        principal: Principal,
        project_id: str,
        volume_id: str,
        payload: dict | None = None,
        expected: str | None = None,
        key: str | None = None,
    ) -> dict:
        """执行分册定稿并锁定。"""
        if volume_id not in VOLUMES:
            raise DomainError(404, "NOT_FOUND", f"未找到指定分册：{volume_id}")

        payload = payload or {}
        from icg.domain.idempotency import fingerprint, lookup, remember

        action = f"volume.finalize:{volume_id}"
        request_fingerprint = fingerprint(action, payload, expected) if key else ""

        def transaction(state: DemoState) -> dict:
            # 1. 查找项目与租户强隔离
            project = self._resolve_project(state, principal, project_id)

            # 2. 权限校验
            check_finalize_permissions(state, principal, project, volume_id)

            # 3. 幂等与版本检查
            if key:
                replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
                if replay is not None:
                    return replay

            if expected is not None:
                self._version(project.revision, expected)

            workflow = self._workflow(state, project_id, create=True)

            # 4. 章节前置门禁：该分册所有章节必须已有正式版本正文且当前未被排他锁定
            vol_chapters = [
                c for c in state.chapters.values()
                if c.project_id == project_id and c.volume == volume_id
            ]
            if not vol_chapters:
                raise VolumeGateError(409, "VOLUME_CHAPTERS_EMPTY", f"分册「{volume_id}」尚未划分章节，无法定稿。")

            now_ts = self.demo._now() if hasattr(self.demo, "_now") else time.time()
            for chapter in vol_chapters:
                # 排他锁门禁
                if is_chapter_locked(chapter, now_ts):
                    raise VolumeGateError(
                        409,
                        "LOCK_HELD",
                        f"分册章节「{chapter.title}」当前正被排他锁定，需先解锁或释放租约后方可定稿。",
                    )
                # 正式正文门禁
                if not chapter.content or not chapter.content.strip():
                    raise VolumeGateError(
                        409,
                        "CHAPTER_CONTENT_EMPTY",
                        f"分册章节「{chapter.title}」缺少正式版本正文，无法定稿。",
                    )

            # 5. 缺陷门禁：该分册不能存在未消解的 blocker 缺陷
            check_id = payload.get("check_id")
            check_volume_blockers(state, project_id, volume_id, workflow, check_id=check_id)

            # 5b. 待人工问题清零 + 交叉复核通过且对应当前正文；定稿绑定章节版本快照
            snapshot = require_cross_review(state, project_id, volume_id, workflow)

            # 6. 状态流转与持久化标记
            now_iso = iso_time(now_ts)
            volume_record = {
                "volume_id": volume_id,
                "project_id": project_id,
                "is_finalized": True,
                "finalized_by": principal.user.id,
                "finalized_at": now_iso,
                "unlocked_by": None,
                "unlocked_at": None,
                "unlock_reason": None,
                "snapshot": snapshot,
                "cross_reviewer_id": workflow.get("volume_reviews", {}).get(volume_id, {}).get("reviewer_id"),
            }
            workflow.setdefault("volumes", {})[volume_id] = volume_record

            project.revision += 1
            self._audit(
                state,
                principal,
                project_id,
                "volume.finalize",
                {"volume_id": volume_id, "finalized_by": principal.user.id, "finalized_at": now_iso},
            )

            self._job(
                state,
                project_id,
                "volume.finalize",
                f"{'技术分册' if volume_id == 'technical' else '商务分册'}已完成前置门禁核对并定稿锁定。",
            )

            result = {
                "volume_id": volume_id,
                "project_id": project_id,
                "is_finalized": True,
                "finalized_by": principal.user.id,
                "finalized_at": now_iso,
                "revision": project.revision,
                "volume": volume_record,
            }

            if key:
                remember(state, project_id, principal.user.id, key, request_fingerprint, result, self.demo._now())

            return result

        return self.repository.transaction(transaction)

    def unlock_volume(
        self,
        principal: Principal,
        project_id: str,
        volume_id: str,
        payload: dict | None = None,
        expected: str | None = None,
        key: str | None = None,
    ) -> dict:
        """解锁已定稿的分册以支持定稿后修改（记录原因与时间戳）。"""
        if volume_id not in VOLUMES:
            raise DomainError(404, "NOT_FOUND", f"未找到指定分册：{volume_id}")

        payload = payload or {}
        reason = str(payload.get("reason", "") or "").strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "解锁已定稿分册必须填写修改原因。")

        from icg.domain.idempotency import fingerprint, lookup, remember

        action = f"volume.unlock:{volume_id}"
        request_fingerprint = fingerprint(action, payload, expected) if key else ""

        def transaction(state: DemoState) -> dict:
            project = self._resolve_project(state, principal, project_id)
            check_finalize_permissions(state, principal, project, volume_id)

            if key:
                replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
                if replay is not None:
                    return replay

            if expected is not None:
                self._version(project.revision, expected)

            workflow = self._workflow(state, project_id, create=True)

            now_ts = self.demo._now() if hasattr(self.demo, "_now") else time.time()
            now_iso = iso_time(now_ts)

            vol_record = workflow.setdefault("volumes", {}).get(volume_id)
            if vol_record is None:
                vol_record = {
                    "volume_id": volume_id,
                    "project_id": project_id,
                    "is_finalized": False,
                    "finalized_by": None,
                    "finalized_at": None,
                }
                workflow["volumes"][volume_id] = vol_record

            vol_record["is_finalized"] = False
            vol_record["unlocked_by"] = principal.user.id
            vol_record["unlocked_at"] = now_iso
            vol_record["unlock_reason"] = reason
            reset_review_on_unlock(workflow, volume_id, principal.user.id, now_iso, reason)

            project.revision += 1
            self._audit(
                state,
                principal,
                project_id,
                "volume.unlock",
                {"volume_id": volume_id, "unlocked_by": principal.user.id, "unlocked_at": now_iso, "reason": reason},
            )

            self._job(
                state,
                project_id,
                "volume.unlock",
                f"{'技术分册' if volume_id == 'technical' else '商务分册'}已解锁（原因：{reason}）。",
            )

            result = {
                "volume_id": volume_id,
                "project_id": project_id,
                "is_finalized": False,
                "unlocked_by": principal.user.id,
                "unlocked_at": now_iso,
                "unlock_reason": reason,
                "revision": project.revision,
                "volume": vol_record,
            }

            if key:
                remember(state, project_id, principal.user.id, key, request_fingerprint, result, self.demo._now())

            return result

        return self.repository.transaction(transaction)

    def get_volume_status(
        self,
        principal: Principal,
        project_id: str,
        volume_id: str,
    ) -> dict:
        """查询指定分册的定稿状态与元数据。"""
        if volume_id not in VOLUMES:
            raise DomainError(404, "NOT_FOUND", f"未找到指定分册：{volume_id}")

        state = self.repository.read()
        project = self._resolve_project(state, principal, project_id)

        workflow = self._workflow(state, project_id)
        vol_record = workflow.get("volumes", {}).get(volume_id)
        if vol_record is None:
            vol_record = {
                "volume_id": volume_id,
                "project_id": project_id,
                "is_finalized": False,
                "finalized_by": None,
                "finalized_at": None,
                "unlocked_by": None,
                "unlocked_at": None,
                "unlock_reason": None,
            }

        return {
            "volume_id": volume_id,
            "project_id": project_id,
            "is_finalized": vol_record.get("is_finalized", False),
            "finalized_by": vol_record.get("finalized_by"),
            "finalized_at": vol_record.get("finalized_at"),
            "unlocked_by": vol_record.get("unlocked_by"),
            "unlocked_at": vol_record.get("unlocked_at"),
            "unlock_reason": vol_record.get("unlock_reason"),
            "cross_review": public_review(state, project_id, volume_id, workflow),
            "revision": project.revision,
            "volume": {k: v for k, v in vol_record.items() if k != "snapshot"},
        }

    def list_volumes_status(
        self,
        principal: Principal,
        project_id: str,
    ) -> dict:
        """查询项目中所有分册的定稿状态列表。"""
        state = self.repository.read()
        project = self._resolve_project(state, principal, project_id)

        workflow = self._workflow(state, project_id)
        volumes_map = workflow.get("volumes", {})

        items = []
        for vid in VOLUMES:
            rec = volumes_map.get(vid, {})
            items.append({
                "volume_id": vid,
                "project_id": project_id,
                "is_finalized": rec.get("is_finalized", False),
                "finalized_by": rec.get("finalized_by"),
                "finalized_at": rec.get("finalized_at"),
                "unlocked_by": rec.get("unlocked_by"),
                "unlocked_at": rec.get("unlocked_at"),
                "unlock_reason": rec.get("unlock_reason"),
                "cross_review": public_review(state, project_id, vid, workflow),
                "pending_human_issues": len(pending_human_issues(workflow, state, project_id, vid)),
            })

        return {
            "project_id": project_id,
            "revision": project.revision,
            "volumes": items,
        }
