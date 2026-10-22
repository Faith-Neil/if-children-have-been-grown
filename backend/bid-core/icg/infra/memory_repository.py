# 为什么有这个文件：用于离线单测的内存持久化仓储实现（MemoryRepository）。
# 它解决什么问题：实现与 MySQL 仓储 100% 同构的多态接口，供无需运行真实数据库的离线单元测试使用。

from __future__ import annotations

import time
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, TypeVar
from uuid import uuid4

from icg_demo.domain import Account, Chapter, DemoState, DomainError, Project, iso_time

T = TypeVar("T")


def seed_state() -> DemoState:
    """构建单元测试与演示使用的初始合成数据状态。"""
    state = DemoState()
    for user in (
        Account("alpha-editor", "甲公司编写人（合成）", "alpha", "editor"),
        Account("alpha-manager", "甲公司项目经理（合成）", "alpha", "manager"),
        Account("alpha-viewer", "甲公司查看人（合成）", "alpha", "viewer"),
        Account("beta-editor", "乙公司编写人（合成）", "beta", "editor"),
        Account("alpha-tech", "甲公司技术编写人（合成）", "alpha", "editor"),
        Account("alpha-business", "甲公司商务编写人（合成）", "alpha", "editor"),
        Account("alpha-outsider-manager", "甲公司其他项目经理（合成）", "alpha", "manager"),
        Account("beta-manager", "乙公司项目经理（合成）", "beta", "manager"),
        Account("alpha-company-admin", "甲公司管理员（合成）", "alpha", "company_admin"),
        Account("alpha-data-admin", "甲公司资料管理员（合成）", "alpha", "data_admin"),
    ):
        state.accounts[user.id] = user
    for company in ("alpha", "beta"):
        project = Project(f"{company}-project", f"{'甲' if company == 'alpha' else '乙'}公司合成投标项目", company)
        state.projects[project.id] = project
        from icg_demo.project_access import initial_team
        state.project_teams[project.id] = initial_team("alpha-manager" if company == "alpha" else "beta-manager")
        if company == "alpha":
            state.project_teams[project.id]["members"].update({
                "alpha-editor": {"user_id": "alpha-editor", "project_role": "writer", "volumes": ["technical", "business"]},
                "alpha-viewer": {"user_id": "alpha-viewer", "project_role": "readonly", "volumes": ["technical", "business"]}})
        else:
            state.project_teams[project.id]["members"]["beta-editor"] = {"user_id": "beta-editor", "project_role": "writer", "volumes": ["technical", "business"]}
        for suffix, volume, title in (("tech", "technical", "技术方案"),
                                      ("business", "business", "商务响应")):
            content = (f"{'甲' if company == 'alpha' else '乙'}公司合成项目的{title}。\n"
                       "本内容仅用于本地演示，不可作为真实承诺或正式递交文件。")
            chapter = Chapter(f"{company}-{suffix}", project.id, title, volume, content)
            chapter.assignee_id = "alpha-editor" if company == "alpha" else "beta-editor"
            chapter.versions.append({"revision": 1, "content": content,
                                     "actor_id": "demo-seed", "created_at": "2026-10-10T00:00:00+00:00"})
            state.chapters[chapter.id] = chapter
    return state


class MemoryRepository:
    """仅用于测试环境的内存持久化仓储。"""
    mode = "memory"

    def __init__(self, initial_state: DemoState | None = None):
        self._lock = RLock()
        self._state = deepcopy(initial_state if initial_state is not None else seed_state())

    def read(self) -> DemoState:
        with self._lock:
            return deepcopy(self._state)

    def transaction(self, operation: Callable[[DemoState], T]) -> T:
        with self._lock:
            working = deepcopy(self._state)
            result = operation(working)
            safe_result = deepcopy(result)
            committed = deepcopy(working)
            self._state = committed
            return safe_result

    def read_chapter(self, chapter_id: str) -> dict | None:
        state = self.read()
        ch = state.chapters.get(chapter_id)
        if ch is None:
            return None
        return {
            "id": ch.id,
            "project_id": ch.project_id,
            "volume": ch.volume,
            "title": ch.title,
            "content": ch.content,
            "revision": ch.revision,
            "assignee_id": ch.assignee_id,
            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "versions": [dict(v) for v in ch.versions],
        }

    def save_chapter(self, chapter: Chapter | dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            if hasattr(chapter, "id"):
                cid = chapter.id
                pid = chapter.project_id
                volume = chapter.volume
                title = chapter.title
                content = chapter.content
                rev = int(chapter.revision)
                assignee_id = chapter.assignee_id
                versions = list(getattr(chapter, "versions", []))
            else:
                cid = chapter["id"]
                pid = chapter["project_id"]
                volume = chapter["volume"]
                title = chapter["title"]
                content = chapter.get("content", "")
                rev = int(chapter.get("revision", 1))
                assignee_id = chapter.get("assignee_id")
                versions = list(chapter.get("versions", []))
            existing = state.chapters.get(cid)
            if existing is not None and expected_revision is not None:
                if existing.revision != expected_revision:
                    raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")
            if existing is None:
                state.chapters[cid] = Chapter(
                    id=cid,
                    project_id=pid,
                    title=title,
                    volume=volume,
                    content=content,
                    revision=rev,
                    assignee_id=assignee_id,
                    versions=versions,
                )
            else:
                existing.project_id = pid
                existing.volume = volume
                existing.title = title
                existing.content = content
                existing.revision = rev
                existing.assignee_id = assignee_id
                if versions:
                    existing.versions = versions
        self.transaction(op)

    def commit_chapter_version(self, chapter_id: str, content: str, expected_revision: int,
                               new_revision: int, created_by: str, updated_at: datetime | None = None) -> dict:
        def op(state: DemoState):
            ch = state.chapters.get(chapter_id)
            if ch is None:
                raise DomainError(404, "NOT_FOUND", "章节不存在。")
            if ch.revision != expected_revision:
                raise DomainError(409, "REVISION_CONFLICT", "章节已被其他会话更新，请刷新并核对最新版本。")
            ch.content = content
            ch.revision = new_revision
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            ts = now.timestamp() if isinstance(now, datetime) else time.time()
            record = {
                "id": f"ver-{uuid4().hex}",
                "chapter_id": chapter_id,
                "revision": new_revision,
                "version_number": new_revision,
                "content": content,
                "actor_id": created_by,
                "created_by": created_by,
                "created_at": iso_time(ts),
            }
            ch.versions.append(record)
            return record
        return self.transaction(op)

    def save_check(self, check_data: dict, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            if not hasattr(state, "_checks_map"):
                state._checks_map = {}
            cid = check_data["id"]
            issues = list(check_data.get("issues_json", check_data.get("issues", [])))
            if "blocking_count" in check_data:
                blocking_count = int(check_data["blocking_count"])
            else:
                blocking_count = sum(1 for i in issues if i.get("severity") in ("blocking", "blocker"))
            if "warning_count" in check_data:
                warning_count = int(check_data["warning_count"])
            else:
                warning_count = sum(1 for i in issues if i.get("severity") == "warning")
            status = check_data.get("status")
            if not status:
                if blocking_count > 0:
                    status = "blocked"
                elif warning_count > 0:
                    status = "warning"
                else:
                    status = "passed"
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            created_at = check_data.get("created_at") or now
            record = {
                "id": cid,
                "project_id": check_data["project_id"],
                "volume_id": check_data.get("volume_id"),
                "status": status,
                "blocking_count": blocking_count,
                "warning_count": warning_count,
                "issues": list(check_data.get("issues_json", check_data.get("issues", []))),
                "issues_json": list(check_data.get("issues_json", check_data.get("issues", []))),
                "created_at": created_at,
                "updated_at": now,
            }
            state._checks_map[cid] = record
        self.transaction(op)

    def read_check(self, check_id: str) -> dict | None:
        state = self.read()
        checks_map = getattr(state, "_checks_map", {})
        res = checks_map.get(check_id)
        return deepcopy(res) if res is not None else None

    def list_checks_by_project(self, project_id: str, volume_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        state = self.read()
        checks_map = getattr(state, "_checks_map", {})
        matched = [
            deepcopy(c) for c in checks_map.values()
            if c["project_id"] == project_id and (volume_id is None or c.get("volume_id") == volume_id)
        ]
        matched.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return matched[offset:offset + limit]

    def delete_check(self, check_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            if not hasattr(state, "_checks_map"):
                state._checks_map = {}
            if check_id in state._checks_map:
                del state._checks_map[check_id]
                deleted = True
        self.transaction(op)
        return deleted

    def save_export(self, export_data: dict, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            if not hasattr(state, "_exports_map"):
                state._exports_map = {}
            eid = export_data["id"]
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            created_at = export_data.get("created_at") or now
            record = {
                "id": eid,
                "project_id": export_data["project_id"],
                "export_type": export_data.get("export_type", "internal"),
                "status": export_data.get("status", "pending"),
                "format": export_data.get("format", "docx"),
                "file_path": export_data.get("file_path"),
                "file_size": export_data.get("file_size"),
                "snapshot": deepcopy(export_data.get("snapshot_json", export_data.get("snapshot"))),
                "snapshot_json": deepcopy(export_data.get("snapshot_json", export_data.get("snapshot"))),
                "created_by": export_data.get("created_by", "system"),
                "created_at": created_at,
            }
            state._exports_map[eid] = record
        self.transaction(op)

    def read_export(self, export_id: str) -> dict | None:
        state = self.read()
        exports_map = getattr(state, "_exports_map", {})
        res = exports_map.get(export_id)
        return deepcopy(res) if res is not None else None

    def update_export_status(self, export_id: str, status: str, file_path: str | None = None, file_size: int | None = None) -> bool:
        updated = False
        def op(state: DemoState):
            nonlocal updated
            if not hasattr(state, "_exports_map"):
                state._exports_map = {}
            exp = state._exports_map.get(export_id)
            if exp is not None:
                exp["status"] = status
                if file_path is not None:
                    exp["file_path"] = file_path
                if file_size is not None:
                    exp["file_size"] = file_size
                updated = True
        self.transaction(op)
        return updated

    def list_exports_by_project(self, project_id: str, export_type: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        state = self.read()
        exports_map = getattr(state, "_exports_map", {})
        matched = [
            deepcopy(e) for e in exports_map.values()
            if e["project_id"] == project_id and (export_type is None or e.get("export_type") == export_type)
        ]
        matched.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        total = len(matched)
        return matched[offset:offset + limit], total

    def delete_export(self, export_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            if not hasattr(state, "_exports_map"):
                state._exports_map = {}
            if export_id in state._exports_map:
                del state._exports_map[export_id]
                deleted = True
        self.transaction(op)
        return deleted

    def save_library_item(self, item_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            iid = item_data["id"]
            existing = state.library.get(iid)
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            if existing is not None:
                if expected_revision is not None and existing.get("revision", 1) != int(expected_revision):
                    raise DomainError(409, "REVISION_CONFLICT", "资料已被其他会话更新，请刷新并核对最新版本。")
                rev = existing.get("revision", 1) if expected_revision is None else int(expected_revision) + 1
            else:
                rev = int(item_data.get("revision", 1))

            payload = deepcopy(item_data.get("payload_json", item_data.get("payload", {})))
            created_at = item_data.get("created_at") or (existing.get("created_at") if existing else now)

            rec = {
                "id": iid,
                "company_id": item_data["company_id"],
                "category": item_data.get("category", "qualification"),
                "name": item_data.get("name", ""),
                "status": item_data.get("status", "draft"),
                "is_starred": bool(item_data.get("is_starred", False)),
                "can_insert": bool(item_data.get("can_insert", True)),
                "is_sensitive": bool(item_data.get("is_sensitive", False)),
                "payload_json": payload,
                "payload": payload,
                "revision": rev,
                "created_at": created_at,
                "updated_at": now,
            }
            state.library[iid] = rec
        self.transaction(op)

    def read_library_item(self, item_id: str) -> dict | None:
        state = self.read()
        item = state.library.get(item_id)
        return deepcopy(item) if item is not None else None

    def list_library_items(self, company_id: str, category: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        state = self.read()
        matched = [
            deepcopy(it) for it in state.library.values()
            if it.get("company_id") == company_id
            and (category is None or it.get("category") == category)
            and (status is None or it.get("status") == status)
        ]
        matched.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        total = len(matched)
        return matched[offset:offset + limit], total

    def delete_library_item(self, item_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            if item_id in state.library:
                del state.library[item_id]
                deleted = True
            if hasattr(state, "_lib_revisions_map") and item_id in state._lib_revisions_map:
                del state._lib_revisions_map[item_id]
        self.transaction(op)
        return deleted

    def commit_library_revision(self, item_id: str, payload: dict, expected_revision: int, new_revision: int, changed_by: str, change_reason: str | None = None, updated_at: datetime | None = None) -> dict:
        record = None
        def op(state: DemoState):
            nonlocal record
            item = state.library.get(item_id)
            if item is None:
                raise DomainError(404, "NOT_FOUND", "未找到指定资料条目。")
            if item.get("revision", 1) != int(expected_revision):
                raise DomainError(409, "REVISION_CONFLICT", "资料已被其他会话更新，请刷新并核对最新版本。")

            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            item["payload_json"] = deepcopy(payload)
            item["payload"] = deepcopy(payload)
            item["revision"] = int(new_revision)
            item["updated_at"] = now

            if not hasattr(state, "_lib_revisions_map"):
                state._lib_revisions_map = {}
            rev_list = state._lib_revisions_map.setdefault(item_id, [])

            rev_id = f"rev-{uuid4().hex}"
            record = {
                "id": rev_id,
                "item_id": item_id,
                "version_number": int(new_revision),
                "revision": int(new_revision),
                "payload_json": deepcopy(payload),
                "payload": deepcopy(payload),
                "changed_by": changed_by,
                "change_reason": change_reason,
                "created_at": now,
            }
            rev_list.append(record)
        self.transaction(op)
        return record

    def list_library_revisions(self, item_id: str) -> list[dict]:
        state = self.read()
        rev_map = getattr(state, "_lib_revisions_map", {})
        revisions = rev_map.get(item_id, [])
        return sorted([deepcopy(r) for r in revisions], key=lambda x: int(x["version_number"]))

    def save_sla_template(self, template_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            tid = template_data["id"]
            existing = state.sla_templates.get(tid)
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            if existing is not None:
                if expected_revision is not None and existing.get("revision", 1) != int(expected_revision):
                    raise DomainError(409, "REVISION_CONFLICT", "SLA 模板已被其他会话更新，请刷新并核对最新版本。")
                rev = existing.get("revision", 1) if expected_revision is None else int(expected_revision) + 1
            else:
                rev = int(template_data.get("revision", 1))

            rules = deepcopy(template_data.get("rules_json", template_data.get("rules", template_data.get("variables", {}))))
            created_at = template_data.get("created_at") or (existing.get("created_at") if existing else now)

            rec = {
                "id": tid,
                "company_id": template_data["company_id"],
                "level": template_data.get("level", "standard"),
                "name": template_data.get("name", ""),
                "rules_json": rules,
                "rules": rules,
                "revision": rev,
                "created_at": created_at,
                "updated_at": now,
            }
            state.sla_templates[tid] = rec
        self.transaction(op)

    def read_sla_template(self, template_id: str) -> dict | None:
        state = self.read()
        tmpl = state.sla_templates.get(template_id)
        return deepcopy(tmpl) if tmpl is not None else None

    def list_sla_templates(self, company_id: str, level: str | None = None) -> list[dict]:
        state = self.read()
        matched = [
            deepcopy(tmpl) for tmpl in state.sla_templates.values()
            if tmpl.get("company_id") == company_id and (level is None or tmpl.get("level") == level)
        ]
        matched.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        return matched

    def delete_sla_template(self, template_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            if template_id in state.sla_templates:
                del state.sla_templates[template_id]
                deleted = True
        self.transaction(op)
        return deleted

    def save_workflow(self, workflow_data: dict, expected_revision: int | None = None, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            pid = workflow_data["project_id"]
            if not hasattr(state, "_workflow_records"):
                state._workflow_records = {}
            existing = state._workflow_records.get(pid)
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            if existing is not None:
                if expected_revision is not None and existing.get("revision", 1) != int(expected_revision):
                    raise DomainError(409, "REVISION_CONFLICT", "工作流已被其他会话更新，请刷新并核对最新版本。")
                if expected_revision is not None:
                    rev = int(workflow_data.get("revision", int(expected_revision) + 1))
                    if rev == int(expected_revision):
                        rev = int(expected_revision) + 1
                else:
                    rev = int(workflow_data.get("revision", existing.get("revision", 1)))
            else:
                rev = int(workflow_data.get("revision", 1))

            stages = deepcopy(workflow_data.get("stages_json", workflow_data.get("stages", {})))
            incremental = deepcopy(workflow_data.get("incremental_checks_json", workflow_data.get("incremental_checks", [])))
            rec = {
                "project_id": pid,
                "current_stage": workflow_data.get("current_stage", "parsing"),
                "stages_json": stages,
                "stages": stages,
                "incremental_checks_json": incremental,
                "incremental_checks": incremental,
                "revision": rev,
                "updated_at": now,
            }
            state._workflow_records[pid] = rec
        self.transaction(op)

    def read_workflow(self, project_id: str) -> dict | None:
        state = self.read()
        records = getattr(state, "_workflow_records", {})
        rec = records.get(project_id)
        return deepcopy(rec) if rec is not None else None

    def delete_workflow(self, project_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            records = getattr(state, "_workflow_records", {})
            if project_id in records:
                del records[project_id]
                deleted = True
        self.transaction(op)
        return deleted

    def save_job(self, job_data: dict, updated_at: datetime | None = None) -> None:
        def op(state: DemoState):
            jid = job_data["id"]
            now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
            raw_created = job_data.get("created_at") or now
            job_type = job_data.get("job_type", job_data.get("type", "parse_tender"))
            status = job_data.get("status", "pending")
            progress = int(job_data.get("progress", 0))
            step_name = job_data.get("step_name")
            error_json = deepcopy(job_data.get("error_json", job_data.get("error")))
            result_json = deepcopy(job_data.get("result_json", job_data.get("result")))
            created_by = job_data.get("created_by", "system")

            rec = {
                "id": jid,
                "job_type": job_type,
                "type": job_type,
                "project_id": job_data["project_id"],
                "status": status,
                "progress": progress,
                "step_name": step_name,
                "error_json": error_json,
                "error": error_json,
                "result_json": result_json,
                "result": result_json,
                "created_by": created_by,
                "created_at": raw_created,
                "updated_at": now,
            }
            if not hasattr(state, "_job_records"):
                state._job_records = {}
            state._job_records[jid] = rec
            state.jobs[jid] = rec
        self.transaction(op)

    def read_job(self, job_id: str) -> dict | None:
        state = self.read()
        records = getattr(state, "_job_records", {})
        rec = records.get(job_id) or state.jobs.get(job_id)
        return deepcopy(rec) if rec is not None else None

    def update_job_progress(self, job_id: str, progress: int, status: str | None = None, step_name: str | None = None, error_json: Any = None, result_json: Any = None, updated_at: datetime | None = None) -> bool:
        updated = False
        def op(state: DemoState):
            nonlocal updated
            records = getattr(state, "_job_records", {})
            rec = records.get(job_id) or state.jobs.get(job_id)
            if rec is not None:
                now = updated_at or datetime.now(timezone.utc).replace(tzinfo=None)
                rec["progress"] = int(progress)
                if status is not None:
                    rec["status"] = status
                if step_name is not None:
                    rec["step_name"] = step_name
                if error_json is not None:
                    rec["error_json"] = deepcopy(error_json)
                    rec["error"] = deepcopy(error_json)
                if result_json is not None:
                    rec["result_json"] = deepcopy(result_json)
                    rec["result"] = deepcopy(result_json)
                rec["updated_at"] = now
                updated = True
        self.transaction(op)
        return updated

    def list_jobs_by_project(self, project_id: str, job_type: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        state = self.read()
        records = getattr(state, "_job_records", {})
        all_jobs = list(records.values()) if records else list(state.jobs.values())
        matched = [
            deepcopy(j) for j in all_jobs
            if j.get("project_id") == project_id
            and (job_type is None or j.get("job_type") == job_type or j.get("type") == job_type)
            and (status is None or j.get("status") == status)
        ]
        matched.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        total = len(matched)
        return matched[offset:offset + limit], total

    def delete_job(self, job_id: str) -> bool:
        deleted = False
        def op(state: DemoState):
            nonlocal deleted
            records = getattr(state, "_job_records", {})
            if job_id in records:
                del records[job_id]
                deleted = True
            if job_id in state.jobs:
                del state.jobs[job_id]
                deleted = True
        self.transaction(op)
        return deleted
