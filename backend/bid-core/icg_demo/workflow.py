# 为什么有这个文件：把上传、解析确认、矩阵、写作和两册导出接成同一业务流程。
# 它解决什么问题：页面操作真实改变同一存储；检查和文件绑定全部已提交输入，避免旧检查假通过。

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Callable

from .domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from .ports import ParserProvider
from .input_snapshot import project_input_fingerprint
from .sla import SlaService, public_sla, resolve_variables, sla_facts, sla_issues
from .generation_context import (build_generation_context, chapter_plan, evidence_expired, plan_is_current, project_facts,
                                 public_plan, refuse_source_change, render_model_input, require_ready,
                                 resolve_fact_variables, validate_model_output, writing_source_fingerprint)
from .project_access import (VOLUMES, writable, lead, volume_owner, require_lead, require_chapter,
                             chapter_structure, chapter_edit, chapter_permissions, project_permissions, public_team)


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def chapter_export_block(title: str, body: str) -> str:
    # 分册里的章节名要成为一级标题，正文仍按原行保留。
    return f"# {title}\n{body}"

SHANGHAI = timezone(timedelta(hours=8))
SAMPLE_TENDER = """合成招标文件：星河数据库维保服务项目
招标编号：DEMO-2026-001
投标截止时间：2026-12-31T17:00:00+08:00
服务期限：12个月
采购人：星河科技（虚构）
★技术要求：提供数据库日常巡检，每月提交巡检报告。
技术要求：重大故障响应不超过30分钟，处理方案由双方核对。
商务要求：投标人应提供有效企业资质证明。
商务要求：提供同类项目业绩证明，所有资料仅使用合成测试数据。
"""


def _blank_workflow() -> dict:
    return {"files": {}, "requirements": {}, "facts": {}, "conflicts": {},
            "candidates": {}, "checks": {}, "exports": {}, "parse_confirmed": False,
            "plan_confirmed": False, "chapter_order": [], "sla": None, "sla_commitments": {}, "writing_plan": {}}


class WorkflowService:
    MAX_UPLOAD = 5 * 1024 * 1024
    IMPLEMENTED_RULES = ["parse-confirmation", "fact-conflicts", "matrix-completeness",
                         "evidence-company-and-review", "evidence-validity", "committed-content",
                         "pending-markers", "two-volumes", "input-fingerprint", "export-permission",
                         "sla-values-and-capability-subset", "sla-variables-and-labelled-numbers-subset"]
    UNIMPLEMENTED_RULES = ["参考合规规则尚未逐条完成（按一期完整/一期简化/二期分组）", "语义事实与承诺核对",
                           "公司全文查重", "结构化敏感变量", "交叉复核和完整分册定稿"]

    def __init__(self, demo: DemoService, parser: ParserProvider):
        self.demo = demo
        self.repository = demo.repository
        self.parser = parser
        self.sla = SlaService(self)
        from .project_team import ProjectTeamService
        self.team = ProjectTeamService(self)

    @staticmethod
    def _workflow(state: DemoState, project_id: str, *, create=False) -> dict:
        if create:
            return state.workflows.setdefault(project_id, _blank_workflow())
        return state.workflows.get(project_id, _blank_workflow())

    @staticmethod
    def _version(actual: int, expected: str | None):
        if expected is None:
            raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面再保存。")
        raw = expected.strip().strip('"')
        if not raw.isdigit() or int(raw) != actual:
            raise DomainError(409, "VERSION_CONFLICT", "数据已被更新，请刷新核对后再保存。", {"current_revision": actual})

    @staticmethod
    def _idempotency(key: str | None) -> str:
        from .idempotency import validate_key
        return validate_key(key)

    @staticmethod
    def _request_hash(action: str, payload: dict, expected: str | None) -> str:
        from .idempotency import fingerprint
        return fingerprint(action, payload, expected)

    def _preflight(self, principal, project_id, action, payload, expected, key):
        from .idempotency import lookup
        key = self._idempotency(key)
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        self._authorize(state, principal, project_id, action, payload)
        replay = lookup(state, project_id, principal.user.id, key,
                        self._request_hash(action, payload, expected), self.demo._now())
        if replay is not None:
            return state, replay
        self._version(project.revision, expected)
        return state, None

    @staticmethod
    def _ordered_chapters(state, project_id, workflow):
        chapters = [c for c in state.chapters.values() if c.project_id == project_id]
        positions = {identity: index for index, identity in enumerate(workflow.get("chapter_order", []))}
        return sorted(chapters, key=lambda c: positions.get(c.id, len(positions)))

    def _audit(self, state: DemoState, principal: Principal, project_id: str, action: str, details=None):
        state.audit.append({"id": new_id("event"), "action": action, "actor_id": principal.user.id,
                            "project_id": project_id, "chapter_id": "", "revision": state.projects[project_id].revision,
                            "at": iso_time(self.demo._now()), "details": details or {}})

    def _write(self, principal: Principal, project_id: str, action: str, payload: dict,
               expected: str | None, key: str | None, operation: Callable, audit_details: dict | None = None) -> dict:
        from .idempotency import lookup, remember
        key = self._idempotency(key)
        request_fingerprint = self._request_hash(action, payload, expected)

        def transaction(state: DemoState):
            project = self.demo._project(state, principal, project_id)
            self._authorize(state, principal, project_id, action, payload)
            replay = lookup(state, project_id, principal.user.id, key, request_fingerprint, self.demo._now())
            if replay is not None:
                return replay
            self._version(project.revision, expected)
            workflow = self._workflow(state, project_id, create=True)
            result = operation(state, project, workflow)
            project.revision += 1
            self._audit(state, principal, project_id, action, audit_details)
            result = {"revision": project.revision, **result}
            if "project" in result:
                result["project"] = asdict(project)
            remember(state, project_id, principal.user.id, key, request_fingerprint, result, self.demo._now())
            return result
        return self.repository.transaction(transaction)

    def _authorize(self, state, principal, project_id, action, payload):
        identity = principal.user.id
        if not writable(state, project_id, identity):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前公司角色和项目角色只允许查看，不能办理此操作。")
        name, _, resource_id = action.partition(":")
        if name in ("team.update", "project.update", "file.upload", "file.delete", "parse.run", "parse.confirm", "conflict.resolve") or name.startswith("sla."):
            require_lead(state, principal, project_id)
        elif name in ("chapter.plan.save", "chapter.plan.confirm", "chapter.assignment"):
            chapter = self.demo._chapter(state, principal, resource_id)
            if chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")
            if name == "chapter.assignment":
                if not chapter_structure(state, chapter, identity):
                    raise DomainError(403, "CHAPTER_STRUCTURE_REQUIRED", "只有项目负责人或本册负责人可以分配本节。")
            else:
                require_chapter(state, principal, chapter)
        elif name == "chapter.generate":
            chapters = [c for c in state.chapters.values() if c.project_id == project_id]
            selected = payload.get("chapter_ids")
            if selected is not None:
                known = {c.id for c in chapters}
                if not selected or len(selected) != len(set(selected)) or set(selected) - known:
                    raise DomainError(404, "NOT_FOUND", "所选章节不存在或不属于本项目。")
                chapters = [c for c in chapters if c.id in selected]
            for chapter in chapters:
                require_chapter(state, principal, chapter)
        elif name == "plan.confirm":
            scope = payload.get("scope", "all")
            if scope == "all":
                require_lead(state, principal, project_id)
            elif not (lead(state, project_id, identity) or volume_owner(state, project_id, scope, identity)):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能调整和批量确认自己负责的分册。")
        elif name in ("project.check", "project.export"):
            volume = payload.get("volume", "all")
            if volume == "all" or payload.get("kind") == "submission":
                require_lead(state, principal, project_id)
            elif not (lead(state, project_id, identity) or volume_owner(state, project_id, volume, identity)):
                raise DomainError(403, "VOLUME_OWNER_REQUIRED", "只能检查或导出自己负责的分册。")
        elif name == "fact.update":
            fact = self._workflow(state, project_id)["facts"].get(resource_id, {})
            if resource_id.startswith("sla:") or fact.get("required") or "status" in payload:
                require_lead(state, principal, project_id)
        elif name == "requirement.update":
            row = self._workflow(state, project_id)["requirements"].get(resource_id)
            if row is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条款。")
            if set(payload) - {"response", "evidence_ids", "reason"}:
                require_lead(state, principal, project_id)
            elif not lead(state, project_id, identity):
                chapter = state.chapters.get(row["chapter_id"] or "")
                if not (volume_owner(state, project_id, row["volume"], identity)
                        or chapter and chapter_edit(state, chapter, identity)):
                    raise DomainError(403, "MATRIX_RESPONSE_FORBIDDEN", "只能填写本人负责分册或章节的响应和证据。")

    def _chapter_summary(self, state: DemoState, workflow: dict, chapter: Chapter, user_id=None) -> dict:
        active = chapter.lock and chapter.lock.expires_at > self.demo._now()
        candidate = workflow["candidates"].get(chapter.id)
        if candidate:
            candidate = {**candidate, "status": "valid" if candidate.get("input_fingerprint") == self._fingerprint(state, chapter.project_id) else "stale"}
        return {**self.demo._summary(chapter), "content": chapter.content,
                "lock": {"owner_id": chapter.lock.owner_id, "expires_at": iso_time(chapter.lock.expires_at)} if active else None,
                "candidate": candidate, "writing_input": {**chapter_plan(workflow, chapter.id), "is_current": plan_is_current(state, chapter.project_id, chapter.id)},
                "assignee_id": chapter.assignee_id,
                "assignee_name": state.accounts[chapter.assignee_id].name if chapter.assignee_id in state.accounts else None,
                "permissions": chapter_permissions(state, chapter, user_id) if user_id else {},
                "requirement_ids": [r["id"] for r in workflow["requirements"].values() if r["chapter_id"] == chapter.id]}

    def _fingerprint(self, state: DemoState, project_id: str) -> str:
        return project_input_fingerprint(state, project_id)

    def _public_check(self, state: DemoState, project_id: str, check: dict) -> dict:
        result = dict(check)
        if check["fingerprint"] != self._fingerprint(state, project_id):
            result["status"] = "stale"
        return result

    def _public_export(self, state: DemoState, project_id: str, record: dict) -> dict:
        return {k: v for k, v in record.items() if k != "documents"} | {
            "status": "valid" if record["fingerprint"] == self._fingerprint(state, project_id) else "stale"}

    @staticmethod
    def _public_file(record: dict) -> dict:
        return {key: value for key, value in record.items() if key not in ("content", "pages")}

    def workspace(self, principal: Principal, project_id: str) -> dict:
        state = self.repository.read()
        project = self.demo._project(state, principal, project_id)
        workflow = self._workflow(state, project_id)
        chapters = [self._chapter_summary(state, workflow, c, principal.user.id) for c in self._ordered_chapters(state, project_id, workflow)]
        stage = ("exported" if any(e["fingerprint"] == self._fingerprint(state, project_id) for e in workflow["exports"].values()) else "writing" if plan_is_current(state, project_id) else
                 "matrix" if workflow["parse_confirmed"] else "review" if workflow["requirements"] else "upload")
        return {"revision": project.revision, "input_fingerprint": self._fingerprint(state, project_id),
                "project": asdict(project), "stage": stage,
                "files": [self._public_file(f) for f in workflow["files"].values()],
                "requirements": [{**row, "permissions": {"edit": lead(state, project_id, principal.user.id),
                                   "route": lead(state, project_id, principal.user.id),
                                   "response": lead(state, project_id, principal.user.id) or volume_owner(state, project_id, row["volume"], principal.user.id)
                                   or bool(row["chapter_id"] in state.chapters and chapter_edit(state, state.chapters[row["chapter_id"]], principal.user.id))}}
                                 for row in workflow["requirements"].values()], "facts": project_facts(state, project_id),
                "conflicts": list(workflow["conflicts"].values()), "chapters": chapters,
                "checks": [self._public_check(state, project_id, c) for c in workflow["checks"].values()],
                "exports": [self._public_export(state, project_id, e) for e in workflow["exports"].values()],
                "jobs": [j for j in state.jobs.values() if j["project_id"] == project_id],
                "parse_confirmed": workflow["parse_confirmed"], "plan_confirmed": workflow["parse_confirmed"] and plan_is_current(state, project_id),
                "writing_plan": public_plan(workflow, state, project_id),
                "team": public_team(state, project_id, principal.user.id), "permissions": project_permissions(state, project_id, principal.user.id),
                "sla": public_sla(state, project_id)}

    def writing_input(self, principal, project_id, chapter_id):
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不属于当前项目。")
        return build_generation_context(state, project_id, chapter, self.demo._now())

    def patch_project(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            partners = payload.pop("project_partners", None)
            if partners is not None:
                state.project_partners[project.id] = partners
            for field, value in payload.items():
                if value is None:
                    raise DomainError(422, "INVALID_PROJECT_FIELD", "项目字段不能设为空值，请使用空字符串清空文本。")
                if field == "name" and not value.strip():
                    raise DomainError(422, "INVALID_PROJECT_NAME", "项目名称不能为空。")
                if field == "deadline" and value:
                    self._date(value)
                setattr(project, field, value.strip() if isinstance(value, str) else value)
            return {"project": asdict(project)}
        return self._write(principal, project_id, "project.update", payload, expected, key, operation)

    def _job(self, state, project_id, kind, message, error=None) -> dict:
        now = iso_time(self.demo._now())
        job = {"id": new_id("job"), "project_id": project_id, "type": kind,
               "status": "failed" if error else "completed", "progress": 100,
               "message": message, "created_at": now, "completed_at": now, "error": error,
               "recoverable": False}
        state.jobs[job["id"]] = job
        return job

    def upload(self, principal, project_id, payload, expected, key):
        filename = payload["filename"]
        if filename != PurePosixPath(filename.replace("\\", "/")).name or any(c in filename for c in '\r\n\x00'):
            raise DomainError(422, "INVALID_FILENAME", "请提供文件名，不包含目录或控制字符。")
        suffix = PurePosixPath(filename).suffix.lower()
        if suffix not in (".txt", ".md", ".docx", ".pdf"):
            raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "当前可上传文本、DOCX 与 PDF。")
        try:
            content = base64.b64decode(payload["content_base64"], validate=True)
        except (binascii.Error, ValueError) as error:
            raise DomainError(422, "INVALID_FILE_ENCODING", "文件编码不正确，请重新选择文件。") from error
        if not content or len(content) > self.MAX_UPLOAD:
            raise DomainError(413, "FILE_SIZE_LIMIT", "文件须有内容且不超过 5MB。")
        def operation(state, project, workflow):
            identity = new_id("file")
            media_type = DOCX_MEDIA_TYPE if suffix == ".docx" else "application/pdf" if suffix == ".pdf" else "text/plain; charset=utf-8"
            record = {"id": identity, "filename": filename, "size": len(content),
                      "sha256": hashlib.sha256(content).hexdigest(), "media_type": media_type,
                      "status": "uploaded", "page_count": 0, "pagination": "not_parsed", "warnings": [],
                      "download_url": f"/api/v1/projects/{project_id}/files/{identity}",
                      "content": content, "pages": []}
            workflow["files"][identity] = record
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            job = self._job(state, project_id, "upload", "原件已保存到演示内存，尚未解析。")
            return {"file": self._public_file(record), "job": job}
        return self._write(principal, project_id, "file.upload", payload, expected, key, operation)

    def file(self, principal, project_id, file_id, *, preview=False):
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        record = self._workflow(state, project_id)["files"].get(file_id)
        if record is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的文件。")
        if preview:
            if record["status"] != "parsed":
                raise DomainError(409, "FILE_NOT_PARSED", "文件尚未成功解析，暂时没有原文预览。")
            return {"file_id": record["id"], "filename": record["filename"], "pagination": record["pagination"],
                    "warnings": record["warnings"], "pages": [{"page": i + 1, "text": t} for i, t in enumerate(record["pages"])]}
        return record

    def delete_file(self, principal, project_id, file_id, payload, expected, key):
        reason = payload["reason"].strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "移除无法解析或误传文件必须填写理由。")

        def operation(state, project, workflow):
            record = workflow["files"].get(file_id)
            if record is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
            referenced = any(item["source"]["file_id"] == file_id
                             for collection in (workflow["requirements"], workflow["facts"])
                             for item in collection.values())
            if record["status"] not in ("uploaded", "failed") or referenced:
                raise DomainError(409, "FILE_IN_USE", "已有解析结果或条款来源的文件不能移除。")
            del workflow["files"][file_id]
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"deleted_file_id": file_id}

        # 解析适配器在事务外运行；文件移除会增加项目版本，旧解析快照无法写回。
        return self._write(principal, project_id, "file.delete:" + file_id, payload, expected, key,
                           operation, {"file_id": file_id, "reason": reason})

    def parse(self, principal, project_id, payload, expected, key):
        initial, previous = self._preflight(principal, project_id, "parse.run", payload, expected, key)
        if previous:
            return previous
        workflow = self._workflow(initial, project_id)
        selected = payload.get("file_ids")
        selected = list(workflow["files"]) if selected is None else selected
        if not selected or len(selected) != len(set(selected)):
            raise DomainError(422, "FILES_REQUIRED", "请选择至少一份未重复的招标文件。")
        if any(identity not in workflow["files"] for identity in selected):
            raise DomainError(404, "NOT_FOUND", "所选文件不存在或不属于本项目。")
        parsed, errors = {}, {}
        for identity in selected:
            record = workflow["files"][identity]
            try:
                result = self.parser.parse(record["filename"], record["content"])
                parsed[identity] = result
            except DomainError as error:
                errors[identity] = error
            except Exception:
                errors[identity] = DomainError(502, "PARSER_UNAVAILABLE", "解析适配器失败，原件仍保留。")

        def operation(state, project, actual):
            actual["parse_confirmed"] = False
            actual["plan_confirmed"] = False
            if errors:
                for identity, error in errors.items():
                    actual["files"][identity]["status"] = "failed"
                    actual["files"][identity]["warnings"] = [error.message]
                first = next(iter(errors.values()))
                job = self._job(state, project_id, "parse", "解析未完成，请根据错误重新提供文件。",
                                {"code": first.code, "message": first.message})
                return {"job": job}
            for identity, result in parsed.items():
                record = actual["files"][identity]
                record.update(status="parsed", page_count=len(result.pages), pagination=result.pagination,
                              pages=result.pages, warnings=result.warnings)
                existing = {(r["source"]["file_id"], r["source"]["page"], r["source"]["quote"])
                            for r in actual["requirements"].values()}
                existing_facts = {(f["key"], f["value"], f["source"]["file_id"], f["source"]["page"])
                                  for f in actual["facts"].values()}
                for page, text in enumerate(result.pages, start=1):
                    for raw in text.splitlines():
                        line = raw.strip()
                        if not line:
                            continue
                        source = {"file_id": identity, "page": page, "quote": line}
                        match = re.match(r"^(招标编号|投标截止时间|服务期限|采购人|项目名称|服务地点|响应时间)\s*[:：]\s*(.+)$", line)
                        if match:
                            fact_key, value = match.groups()
                            fact_key_tuple = (fact_key, value, identity, page)
                            if fact_key_tuple not in existing_facts:
                                fact = {"id": new_id("fact"), "key": fact_key, "value": value,
                                        "status": "pending", "reason": "", "source": source}
                                actual["facts"][fact["id"]] = fact
                                existing_facts.add(fact_key_tuple)
                            continue
                        if line.startswith(("合成招标文件", "招标文件：", "招标文件:")):
                            continue
                        source_key = (identity, page, line)
                        if source_key in existing:
                            continue
                        business = any(word in line for word in ("商务", "资质", "报价", "业绩", "授权", "证书"))
                        references = re.findall(r"(?:见|详见|参照)(?:附件|第)[^，。；\n]{0,40}", line)
                        requirement = {"id": new_id("req"), "text": line,
                                       "category": "mandatory" if "★" in line or "废标" in line or "必须" in line else "business" if business else "technical",
                                       "volume": "business" if business else "technical", "chapter_id": None,
                                       "status": "pending", "response": "", "reason": "", "evidence_ids": [],
                                       "source": source, "references": references,
                                       "reference_status": "unresolved" if references else "none"}
                        actual["requirements"][requirement["id"]] = requirement
                        existing.add(source_key)
            groups = {}
            for fact in actual["facts"].values():
                groups.setdefault(fact["key"], []).append(fact)
            for fact_key, group in groups.items():
                if len({f["value"] for f in group}) > 1:
                    previous = next((c for c in actual["conflicts"].values() if c["key"] == fact_key), None)
                    ids = [f["id"] for f in group]
                    if previous is None:
                        conflict = {"id": new_id("conflict"), "key": fact_key, "fact_ids": ids,
                                    "selected_fact_id": None, "status": "pending", "reason": ""}
                        actual["conflicts"][conflict["id"]] = conflict
                    elif set(previous["fact_ids"]) != set(ids):
                        previous.update(fact_ids=ids, selected_fact_id=None, status="pending", reason="")
            job = self._job(state, project_id, "parse", "真实文字提取完成；条款、事实及引用仍需人工核对。")
            return {"job": job, "requirements": list(actual["requirements"].values()),
                    "facts": list(actual["facts"].values()), "conflicts": list(actual["conflicts"].values())}
        result = self._write(principal, project_id, "parse.run", payload, expected, key, operation)
        if result["job"]["status"] == "failed":
            from .errors import status_for
            error = result["job"]["error"]
            raise DomainError(status_for(error["code"]), error["code"], error["message"],
                              {"job_id": result["job"]["id"], "revision": result["revision"]})
        return result

    def patch_requirement(self, principal, project_id, requirement_id, payload, expected, key):
        def operation(state, project, workflow):
            requirement = workflow["requirements"].get(requirement_id)
            if requirement is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条款。")
            if any(v is None and k != "chapter_id" for k, v in payload.items()):
                raise DomainError(422, "INVALID_REQUIREMENT", "条款字段不能设为空值。")
            if payload.get("text") is not None and not payload["text"].strip():
                raise DomainError(422, "EMPTY_REQUIREMENT", "条款原文不能为空。")
            chapter_id = payload.get("chapter_id", requirement["chapter_id"])
            volume = payload.get("volume", requirement["volume"])
            if chapter_id:
                chapter = self.demo._chapter(state, principal, chapter_id)
                if chapter.project_id != project_id or chapter.volume != volume:
                    raise DomainError(409, "CHAPTER_VOLUME_MISMATCH", "条款只能映射到本项目同分册章节。")
            for evidence_id in payload.get("evidence_ids", requirement["evidence_ids"]):
                evidence = state.library.get(evidence_id)
                if evidence is None or evidence["company_id"] != principal.user.company_id:
                    raise DomainError(404, "NOT_FOUND", "证据不存在或不属于当前公司。")
                if evidence["type"] == "history" or evidence["status"] != "confirmed":
                    raise DomainError(409, "EVIDENCE_NOT_USABLE", "历史标书仅可参考；其他证据必须先确认。")
                self._reject_unusable_mount(state, principal, project, evidence)
            if "evidence_ids" in payload and len(payload["evidence_ids"]) != len(set(payload["evidence_ids"])):
                raise DomainError(422, "DUPLICATE_EVIDENCE", "同一证据不能重复挂接。")
            updated = {**requirement, **payload}
            if requirement["category"] == "sla" or payload.get("category") == "sla":
                updated["sla_required"] = True
            text_changed = "text" in payload and payload["text"] != requirement["text"]
            if text_changed:
                # 新原文不能继承旧引用的人工确认，也不能同一次改字时顺便假确认。
                references = re.findall(r"(?:见|详见|参照)(?:附件|第)[^，。；\n]{0,40}", updated["text"])
                updated.update(references=references, reference_status="unresolved" if references else "none",
                               status="pending", reason="")
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略条款必须填写理由。")
            if updated["reference_status"] == "unresolved" and updated["status"] == "confirmed":
                if not updated["reason"].strip():
                    raise DomainError(409, "REFERENCE_REASON_REQUIRED", "存在未解析交叉引用，请在理由中写明人工核对结果。")
                updated["reference_status"] = "resolved"
            if text_changed or any(k in payload and payload[k] != requirement[k] for k in ("category", "volume", "status")):
                workflow["parse_confirmed"] = False
                workflow["plan_confirmed"] = False
            if any(k in payload and payload[k] != requirement[k] for k in ("chapter_id", "response", "evidence_ids")):
                workflow["plan_confirmed"] = False
            requirement.update(updated)
            return {"requirement": requirement}
        return self._write(principal, project_id, "requirement.update:" + requirement_id, payload, expected, key, operation)

    def patch_fact(self, principal, project_id, fact_id, payload, expected, key):
        def operation(state, project, workflow):
            if fact_id.startswith("sla:"):
                return self.sla.confirm_fact(state, principal, project_id, workflow, fact_id[4:], payload)
            fact = workflow["facts"].get(fact_id)
            if fact is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目事实。")
            if fact.get("required") and principal.user.role != "manager":
                raise DomainError(403, "FACT_MANAGER_REQUIRED", "必备事实的维护和确认仅限本公司项目负责人。")
            if any(v is None for v in payload.values()):
                raise DomainError(422, "INVALID_FACT", "事实字段不能设为空值。")
            updated = {**fact, **payload}
            if not lead(state, project_id, principal.user.id) and "value" in payload and payload["value"] != fact["value"]:
                updated["status"] = "pending"
            if not updated["value"].strip():
                raise DomainError(422, "EMPTY_FACT", "事实取值不能为空。")
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略事实必须填写理由。")
            for conflict in workflow["conflicts"].values():
                if fact_id in conflict["fact_ids"] and any(k in payload and payload[k] != fact[k] for k in ("value", "status")):
                    conflict.update(status="pending", selected_fact_id=None, reason="")
            fact.update(updated)
            workflow["plan_confirmed"] = False
            return {"fact": fact}
        return self._write(principal, project_id, "fact.update:" + fact_id, payload, expected, key, operation)

    def resolve_conflict(self, principal, project_id, conflict_id, payload, expected, key):
        def operation(state, project, workflow):
            conflict = workflow["conflicts"].get(conflict_id)
            if conflict is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目冲突。")
            selected = payload["selected_fact_id"]
            if selected not in conflict["fact_ids"]:
                raise DomainError(409, "INVALID_CONFLICT_SELECTION", "只能选择本冲突中的事实取值。")
            if not payload["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "选择冲突取值必须说明依据。")
            conflict.update(selected_fact_id=selected, reason=payload["reason"].strip(), status="resolved")
            for fact_id in conflict["fact_ids"]:
                workflow["facts"][fact_id].update(status="confirmed" if fact_id == selected else "rejected", reason=payload["reason"].strip())
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"conflict": conflict, "facts": list(workflow["facts"].values())}
        return self._write(principal, project_id, "conflict.resolve:" + conflict_id, payload, expected, key, operation)

    def confirm_parse(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            if not workflow["files"] or any(f["status"] != "parsed" for f in workflow["files"].values()):
                raise DomainError(409, "PARSE_INCOMPLETE", "所有上传文件必须成功解析后才能确认。")
            if not workflow["requirements"]:
                raise DomainError(409, "REQUIREMENTS_EMPTY", "没有招标条款，不能确认解析。")
            if any(r["status"] == "pending" for r in workflow["requirements"].values()) or any(f["status"] == "pending" for f in workflow["facts"].values()):
                raise DomainError(409, "REVIEW_PENDING", "请先逐条确认或填写理由忽略全部条款和事实。")
            if not any(r["status"] == "confirmed" for r in workflow["requirements"].values()):
                raise DomainError(409, "CONFIRMED_REQUIREMENTS_EMPTY", "至少需要一条已确认条款。")
            if any(c["status"] != "resolved" for c in workflow["conflicts"].values()):
                raise DomainError(409, "CONFLICTS_PENDING", "存在事实冲突，请先选择有效取值并填写依据。")
            for conflict in workflow["conflicts"].values():
                selected = conflict["selected_fact_id"]
                if (selected not in conflict["fact_ids"]
                        or workflow["facts"].get(selected, {}).get("status") != "confirmed"
                        or any(workflow["facts"].get(identity, {}).get("status") != "rejected"
                               for identity in conflict["fact_ids"] if identity != selected)):
                    raise DomainError(409, "CONFLICT_SELECTION_INVALID", "冲突必须有且只有一个确认取值，其余候选需忽略。")
            workflow["parse_confirmed"] = True
            return {"parse_confirmed": True}
        return self._write(principal, project_id, "parse.confirm", payload, expected, key, operation)

    def plan(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            if not workflow["parse_confirmed"]:
                raise DomainError(409, "PARSE_NOT_CONFIRMED", "请先确认解析结果，再确认写作大纲。")
            issues = sla_issues(state, project_id)
            if issues:
                raise DomainError(409, "SLA_NOT_READY", "服务承诺或必备事实仍待处理，请先逐条核对。", {"issues": issues})
            requested = payload["chapters"]
            scope = payload.get("scope", "all")
            expected_volumes = set(VOLUMES) if scope == "all" else {scope}
            if {c["volume"] for c in requested} != expected_volumes:
                raise DomainError(422, "TWO_VOLUMES_REQUIRED", "本期大纲必须同时包含技术和商务两册。")
            all_old = {c.id: c for c in state.chapters.values() if c.project_id == project_id}
            old = {identity: c for identity, c in all_old.items() if c.volume in expected_volumes}
            seen, retained, planned = set(), [], {}
            facts = {fact["id"]: fact for fact in project_facts(state, project_id)}
            if any(fact["required"] and fact["status"] != "confirmed" for fact in facts.values()):
                raise DomainError(409, "FACT_NOT_READY", "全部必备事实确认后才能确认写作方案。")
            for item in requested:
                ids = item.get("fact_ids", [])
                if len(ids) != len(set(ids)):
                    raise DomainError(422, "DUPLICATE_FACT", "本章同一事实不能重复选择。")
                if any(identity not in facts for identity in ids):
                    raise DomainError(409, "FACT_NOT_FOUND", "所选事实不属于本项目或已经删除。")
                if any(facts[identity]["status"] != "confirmed" for identity in ids):
                    raise DomainError(409, "FACT_NOT_READY", "本章所选事实须先确认取值。")
                from .parsing import LocalTextParser
                LocalTextParser._validate_text(item.get("writing_points", ""))
                if not item["title"].strip():
                    raise DomainError(422, "EMPTY_CHAPTER_TITLE", "章节标题不能为空。")
                identity = item.get("id")
                if identity:
                    chapter = old.get(identity)
                    if chapter is None:
                        raise DomainError(404, "NOT_FOUND", "大纲章节不属于本项目。")
                else:
                    chapter = next((c for c in old.values() if c.id not in seen and c.title == item["title"] and c.volume == item["volume"]), None)
                    if chapter is None:
                        # 默认两册可按分册复用空章节，不丢弃旧正文。
                        chapter = next((c for c in old.values() if c.id not in seen and c.volume == item["volume"] and not c.content.strip() and not c.drafts and c.lock is None), None)
                    if chapter is None:
                        chapter = Chapter(new_id("chapter"), project_id, item["title"], item["volume"], "")
                        chapter.versions.append({"revision": 1, "content": "", "actor_id": principal.user.id, "created_at": iso_time(self.demo._now())})
                        state.chapters[chapter.id] = chapter
                if chapter.id in seen:
                    raise DomainError(422, "DUPLICATE_CHAPTER", "同一章节不能重复出现在大纲。")
                if chapter.title != item["title"] or chapter.volume != item["volume"]:
                    if chapter.drafts or (chapter.lock and chapter.lock.expires_at > self.demo._now()):
                        raise DomainError(409, "CHAPTER_IN_USE", "章节有草稿或编辑权，不能改动大纲。")
                    if chapter.volume != item["volume"] and chapter.content.strip():
                        raise DomainError(409, "CHAPTER_HAS_CONTENT", "有正文的章节不能直接改分册。")
                    chapter.title, chapter.volume = item["title"], item["volume"]
                if "assignee_id" in item:
                    self.team.eligible(state, project_id, item["assignee_id"], chapter.volume)
                    if chapter.assignee_id != item["assignee_id"]:
                        self.team.handoff(state, principal, project_id, [chapter], payload.get("reason", ""), [chapter.assignee_id])
                        chapter.assignee_id = item["assignee_id"]
                self.team.eligible(state, project_id, chapter.assignee_id, chapter.volume)
                seen.add(chapter.id)
                retained.append(chapter)
                planned[chapter.id] = {"id": chapter.id, "fact_ids": list(ids),
                                       "writing_points": item.get("writing_points", ""), "target_length": item.get("target_length")}
            removed = set(old) - seen
            for identity in removed:
                chapter = old[identity]
                if (chapter.content.strip() or any(version["content"].strip() for version in chapter.versions)
                        or chapter.drafts or (chapter.lock and chapter.lock.expires_at > self.demo._now())):
                    raise DomainError(409, "CHAPTER_HAS_CONTENT", "不能删除有正文、草稿或有效编辑权的章节。")
                if any(r["chapter_id"] == identity for r in workflow["requirements"].values()):
                    raise DomainError(409, "CHAPTER_MAPPED", "章节已关联矩阵条款，先解除映射。")
                del state.chapters[identity]
                workflow["candidates"].pop(identity, None)
            workflow["plan_confirmed"] = True
            workflow["outline_revision"] = int(workflow.get("outline_revision") or 0) + 1
            old_order = workflow.get("chapter_order", [])
            unaffected = [identity for identity in old_order if identity in all_old and all_old[identity].volume not in expected_volumes]
            unaffected += [identity for identity, c in all_old.items() if c.volume not in expected_volumes and identity not in unaffected]
            workflow["chapter_order"] = [c.id for c in retained] + unaffected
            previous_plan = workflow.get("writing_plan", {}).get("chapters", {})
            preserved = {identity: item for identity, item in previous_plan.items() if identity not in old}
            workflow["writing_plan"] = {"confirmed_by": principal.user.id, "confirmed_by_name": principal.user.name,
                                        "confirmed_at": iso_time(self.demo._now()), "chapters": {**preserved, **planned}}
            for chapter in retained:
                self._confirm_chapter_plan(state, principal, project_id, chapter, workflow)
            # 方案确认检查实际来源资格；不把证据过期等缺项留到模型输出以后。
            for chapter in retained:
                require_ready(build_generation_context(state, project_id, chapter, self.demo._now()))
            return {"plan_confirmed": plan_is_current(state, project_id), "writing_plan": public_plan(workflow, state, project_id),
                    "chapters": [self._chapter_summary(state, workflow, c, principal.user.id) for c in retained]}
        return self._write(principal, project_id, "plan.confirm", payload, expected, key, operation)

    def _confirm_chapter_plan(self, state, principal, project_id, chapter, workflow):
        if not writable(state, project_id, state.project_teams[project_id]["owners"].get(chapter.volume)):
            raise DomainError(403, "VOLUME_OWNER_REQUIRED", "本册尚未指定负责人，不能确认写作方案。")
        unmapped = [r["id"] for r in workflow["requirements"].values()
                    if r["volume"] == chapter.volume and r["status"] != "rejected" and
                    (r["chapter_id"] not in state.chapters or state.chapters[r["chapter_id"]].project_id != project_id
                     or state.chapters[r["chapter_id"]].volume != chapter.volume)]
        if unmapped:
            raise DomainError(409, "MATRIX_MAPPING_MISSING", "本册还有未分配章节的招标条款，请先完成响应矩阵映射。", {"requirement_ids": unmapped})
        saved = workflow.setdefault("writing_plan", {}).setdefault("chapters", {}).setdefault(chapter.id, chapter_plan(workflow, chapter.id))
        saved.update(confirmed_by=principal.user.id, confirmed_by_name=principal.user.name,
                     confirmed_at=iso_time(self.demo._now()), confirmation_pending=False)
        saved["confirmed_input_fingerprint"] = writing_source_fingerprint(state, project_id, chapter.id)
        require_ready(build_generation_context(state, project_id, chapter, self.demo._now()))
        self._audit(state, principal, project_id, "chapter-plan.confirmed", {"chapter_id": chapter.id,
                    "confirmed_input_fingerprint": saved["confirmed_input_fingerprint"], "confirmed_by": principal.user.id})

    def chapter_plan_save(self, principal, project_id, chapter_id, payload, expected, key):
        def operation(state, project, workflow):
            chapter = self.demo._chapter(state, principal, chapter_id)
            facts = {fact["id"] for fact in project_facts(state, project_id)}
            ids = payload["fact_ids"]
            if len(ids) != len(set(ids)):
                raise DomainError(422, "DUPLICATE_FACT", "本章同一事实不能重复选择。")
            if set(ids) - facts:
                raise DomainError(409, "FACT_NOT_FOUND", "所选事实不属于本项目或已经删除。")
            old = chapter_plan(workflow, chapter_id)
            workflow.setdefault("writing_plan", {}).setdefault("chapters", {})[chapter_id] = {**old, **payload, "confirmation_pending": True}
            return {"chapter": self._chapter_summary(state, workflow, chapter, principal.user.id), "writing_plan": public_plan(workflow, state, project_id)}
        return self._write(principal, project_id, "chapter.plan.save:" + chapter_id, payload, expected, key, operation)

    def chapter_plan_confirm(self, principal, project_id, chapter_id, payload, expected, key):
        def operation(state, project, workflow):
            chapter = self.demo._chapter(state, principal, chapter_id)
            self._confirm_chapter_plan(state, principal, project_id, chapter, workflow)
            return {"chapter": self._chapter_summary(state, workflow, chapter, principal.user.id), "writing_plan": public_plan(workflow, state, project_id)}
        return self._write(principal, project_id, "chapter.plan.confirm:" + chapter_id, payload, expected, key, operation)

    def generate(self, principal, project_id, payload, expected, key):
        snapshot, previous = self._preflight(principal, project_id, "chapter.generate", payload, expected, key)
        if previous:
            return previous
        project = self.demo._project(snapshot, principal, project_id)
        self.demo.require_allowed_model(project)
        workflow = self._workflow(snapshot, project_id)
        if not workflow["parse_confirmed"]:
            raise DomainError(409, "PARSE_NOT_CONFIRMED", "解析确认后才能生成章节候选。")
        chapters = self._ordered_chapters(snapshot, project_id, workflow)
        selected = payload.get("chapter_ids")
        if selected is not None:
            if not selected or len(selected) != len(set(selected)) or set(selected) - {c.id for c in chapters}:
                raise DomainError(404, "NOT_FOUND", "所选章节不存在或不属于本项目。")
            chapters = [c for c in chapters if c.id in selected]
        candidates = {}
        def check_model_access():
            current = self.repository.read()
            actual_project = self.demo._project(current, principal, project_id)
            self._authorize(current, principal, project_id, "chapter.generate", payload)
            self.demo.require_allowed_model(actual_project)
            if self._fingerprint(current, project_id) != self._fingerprint(snapshot, project_id):
                raise DomainError(409, "VERSION_CONFLICT", "项目输入在生成期间发生变化，不能继续把旧资料交给模型或保存候选。")
        for chapter in chapters:
            assembled = build_generation_context(snapshot, project_id, chapter, self.demo._now())
            require_ready(assembled)
            input_snapshot = assembled["input_snapshot"]
            context = render_model_input(input_snapshot)
            instruction = "按本章已确认条款、响应、证据和事实组织候选；不能编造证据与承诺。引用事实保留变量，不能改取值。"
            refuse_source_change(input_snapshot["plan"]["writing_points"], input_snapshot)
            check_model_access()
            try:
                content = self.demo.model_provider.suggest(instruction, context)
            except Exception as error:
                raise DomainError(502, "MODEL_UNAVAILABLE", "候选生成失败，正式正文没有修改。") from error
            check_model_access()
            validate_model_output(snapshot, project_id, content, input_snapshot)
            input_snapshot.update(model_input=context, model_instruction=instruction)
            candidates[chapter.id] = {"id": new_id("candidate"), "content": content,
                                      "base_revision": chapter.revision,
                                      "input_fingerprint": self._fingerprint(snapshot, project_id),
                                      "provider": getattr(self.demo.model_provider, "name", "injected"),
                                      "is_real_model": bool(getattr(self.demo.model_provider, "is_real_model", False)),
                                      "created_at": iso_time(self.demo._now()), "source_scope": "whole_chapter",
                                      "input_snapshot": input_snapshot}
        def operation(state, project, current):
            self.demo.require_allowed_model(project)
            if self._fingerprint(state, project_id) != self._fingerprint(snapshot, project_id):
                raise DomainError(409, "VERSION_CONFLICT", "项目资料在生成期间更新，请重新生成候选。")
            # 旧编辑接口也可能在模型调用期间提交版本，必须重新核对。
            for chapter in chapters:
                actual = state.chapters.get(chapter.id)
                if actual is None or actual.revision != chapter.revision:
                    raise DomainError(409, "VERSION_CONFLICT", "正文在生成期间更新，请重新生成候选。")
                require_ready(build_generation_context(state, project_id, actual, self.demo._now()))
            current["candidates"].update(candidates)
            job = self._job(state, project_id, "generate", "章节候选已生成；需在编辑台人工核对、取得编辑权后提交。")
            return {"job": job, "chapters": [self._chapter_summary(state, current, state.chapters[c.id], principal.user.id) for c in chapters]}
        return self._write(principal, project_id, "chapter.generate", payload, expected, key, operation)

    @staticmethod
    def _date(value: str) -> date:
        try:
            return date.fromisoformat(value) if len(value) == 10 else WorkflowService._instant(value).astimezone(SHANGHAI).date()
        except (ValueError, TypeError) as error:
            raise DomainError(422, "INVALID_DATE", "日期请使用 YYYY-MM-DD 或包含日期的 ISO 时间格式。") from error

    @staticmethod
    def _instant(value: str) -> datetime:
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (moment.replace(tzinfo=SHANGHAI) if moment.tzinfo is None else moment).astimezone(timezone.utc)
        except (ValueError, TypeError) as error:
            raise DomainError(422, "INVALID_DATE", "截止时间请使用 ISO 时间格式；未带时区时按北京时间理解。") from error

    @staticmethod
    def _issue(code, message, **links):
        return {"id": new_id("issue"), "code": code, "severity": "blocking", "message": message, **links}

    def run_check(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            volume = payload.get("volume", "all")
            issues = []
            add = lambda code, message, **links: issues.append(self._issue(code, message, **links))
            if not workflow["parse_confirmed"]:
                add("PARSE_NOT_CONFIRMED", "解析结果尚未确认。")
            checked_chapters = [c for c in state.chapters.values() if c.project_id == project_id
                                and (volume == "all" or c.volume == volume)]
            if not checked_chapters or not all(plan_is_current(state, project_id, c.id) for c in checked_chapters):
                add("PLAN_NOT_CONFIRMED", "写作大纲尚未确认。")
            if not project.tender_number.strip() or not project.deadline:
                add("PROJECT_DETAILS_MISSING", "项目招标编号或投标截止时间未填写。")
            if any(c["status"] != "resolved" for c in workflow["conflicts"].values()):
                add("FACT_CONFLICT", "项目事实仍有未处理冲突。")
            if any(f["status"] == "pending" for f in workflow["facts"].values()):
                add("FACT_PENDING", "项目事实仍待确认。")
            for fact in workflow["facts"].values():
                if fact["status"] != "confirmed":
                    continue
                if fact["key"] == "招标编号" and project.tender_number.strip() != fact["value"].strip():
                    add("PROJECT_FACT_MISMATCH", "已确认招标编号与项目基本信息不一致。")
                if fact["key"] == "投标截止时间" and project.deadline:
                    try:
                        fact_value = fact["value"].strip()
                        matching_date = (self._date(fact_value) == self._date(project.deadline) if len(fact_value) == 10
                                         else self._instant(fact_value) == self._instant(project.deadline))
                    except DomainError:
                        matching_date = False
                    if not matching_date:
                        add("PROJECT_FACT_MISMATCH", "已确认投标截止时间与项目基本信息不一致。")
            if not workflow["requirements"]:
                add("REQUIREMENTS_EMPTY", "没有可核对的招标条款。")
            for row in workflow["requirements"].values():
                if volume != "all" and row["volume"] != volume:
                    continue
                links = {"requirement_id": row["id"]}
                if row["status"] == "pending":
                    add("REQUIREMENT_PENDING", "条款尚待确认：" + row["text"][:60], **links)
                if row["status"] == "rejected":
                    if not row["reason"].strip():
                        add("REJECTION_REASON_MISSING", "忽略条款没有理由。", **links)
                    continue
                if row["reference_status"] == "unresolved":
                    add("REFERENCE_UNRESOLVED", "条款引用尚未人工核对。", **links)
                chapter = state.chapters.get(row["chapter_id"] or "")
                if chapter is None or chapter.project_id != project_id or chapter.volume != row["volume"]:
                    add("MATRIX_MAPPING_MISSING", "条款没有映射到本分册有效章节。", **links)
                if not row["response"].strip() or "待补" in row["response"]:
                    add("MATRIX_RESPONSE_MISSING", "条款响应为空或仍有待补。", **links)
                need_evidence = any(word in row["text"] for word in ("资质", "证书", "证明", "业绩", "授权"))
                if need_evidence and not row["evidence_ids"]:
                    add("EVIDENCE_MISSING", "证明类条款缺少已确认的企业证据。", **links)
                for evidence_id in row["evidence_ids"]:
                    evidence = state.library.get(evidence_id)
                    if (evidence is None or evidence["company_id"] != project.company_id
                            or evidence["status"] != "confirmed" or evidence["type"] == "history"):
                        add("EVIDENCE_NOT_USABLE", "条款引用的证据已失效或不能作为证据。", evidence_id=evidence_id, **links)
                        continue
                    today = datetime.fromtimestamp(self.demo._now(), SHANGHAI).date()
                    if evidence_expired(evidence, project.deadline, today=today):
                        add("EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。", evidence_id=evidence_id, **links)
            chapters = [c for c in state.chapters.values() if c.project_id == project_id and (volume == "all" or c.volume == volume)]
            required_volumes = {"technical", "business"} if volume == "all" else {volume}
            if {c.volume for c in chapters} != required_volumes:
                add("VOLUME_MISSING", "所检查分册缺少章节。")
            for chapter in chapters:
                if not chapter.content.strip():
                    add("EMPTY_CONTENT", "已提交正文为空：" + chapter.title, chapter_id=chapter.id)
                if "待补" in chapter.content:
                    add("PENDING_CONTENT", "已提交正文仍有待补：" + chapter.title, chapter_id=chapter.id)
                try:
                    resolve_fact_variables(state, project_id, chapter.content)
                except DomainError as error:
                    add(error.code, error.message, chapter_id=chapter.id)
            issues.extend(sla_issues(state, project_id, chapters))
            check = {"id": new_id("project-check"), "volume": volume, "passed": not issues,
                     "status": "failed" if issues else "passed", "issues": issues,
                     "coverage": {"implemented_rules": self.IMPLEMENTED_RULES,
                                  "unimplemented_rules": self.UNIMPLEMENTED_RULES, "complete": False},
                     "fingerprint": self._fingerprint(state, project_id), "created_at": iso_time(self.demo._now())}
            workflow["checks"][check["id"]] = check
            self._job(state, project_id, "check", "已实现的流程检查完成；不代表全部一期合规规则通过。")
            return {"check": check}
        return self._write(principal, project_id, "project.check", payload, expected, key, operation)

    def checks(self, principal, project_id):
        workspace = self.workspace(principal, project_id)
        return {"revision": workspace["revision"], "checks": workspace["checks"]}

    @staticmethod
    def _mask(text: str) -> str:
        # 内部稿不能主动输出身份证、手机号、银行账户长号码。
        text = re.sub(r"(?<![0-9])([0-9]{3})[0-9]{11}([0-9]{3}[0-9Xx])(?![0-9])", r"\1***********\2", text)
        text = re.sub(r"(?<![0-9])([1][3-9][0-9])[0-9]{4}([0-9]{4})(?![0-9])", r"\1****\2", text)
        return re.sub(r"(?<![0-9])[0-9]{12,}([0-9]{4})(?![0-9])", r"************\1", text)

    def export(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            check = workflow["checks"].get(payload["check_id"])
            if check is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目检查批次。")
            if check["fingerprint"] != self._fingerprint(state, project_id):
                raise DomainError(409, "CHECK_STALE", "正文、项目资料或证据已更新，请重新检查。")
            if not check["passed"]:
                raise DomainError(409, "CHECK_FAILED", "当前已实现的流程检查仍有阻断项。")
            scope = payload.get("volume", "all")
            if check["volume"] != scope:
                raise DomainError(409, "ALL_VOLUMES_CHECK_REQUIRED", "导出范围必须和已完成的检查一致；两册导出需要检查全部分册。")
            if payload["kind"] == "submission":
                raise DomainError(409, "RULES_INCOMPLETE", "完整合规规则与分册定稿未实现，不能把本地内部稿冒充递交版。")
            chapters = self._ordered_chapters(state, project_id, workflow)
            chapters = [c for c in chapters if scope == "all" or c.volume == scope]
            required_volumes = set(VOLUMES) if scope == "all" else {scope}
            if {c.volume for c in chapters} != required_volumes:
                raise DomainError(422, "TWO_VOLUMES_REQUIRED", "导出必须包含技术和商务两册。")
            identity = new_id("project-export")
            documents, volumes = {}, []
            for volume, name in (("technical", "技术分册"), ("business", "商务分册")):
                if volume not in required_volumes:
                    continue
                selected = [c for c in chapters if c.volume == volume]
                filename = f"icg-{volume}-{identity}.docx"
                documents[volume] = {"title": self._mask(project.name) + " — " + name,
                                     "project_name": self._mask(project.name),
                                     "content": "\n\n".join(chapter_export_block(self._mask(c.title), self._mask(resolve_fact_variables(state, project_id, c.content))) for c in selected)}
                volumes.append({"volume": volume, "filename": filename,
                                "download_url": f"/api/v1/projects/{project_id}/exports/{identity}/{volume}"})
            record = {"id": identity, "kind": payload["kind"], "check_id": check["id"],
                      "fingerprint": check["fingerprint"], "created_at": iso_time(self.demo._now()),
                      "excludes_drafts": True, "volumes": volumes, "documents": documents}
            workflow["exports"][identity] = record
            self._job(state, project_id, "export", ("两个独立 Word 内部稿已生成" if scope == "all" else "本册 Word 内部稿已生成") + "；只含已提交正文。")
            return {"export": self._public_export(state, project_id, record)}
        return self._write(principal, project_id, "project.export", payload, expected, key, operation)

    def download(self, principal, project_id, export_id, volume):
        def operation(state):
            self.demo._project(state, principal, project_id)
            record = self._workflow(state, project_id)["exports"].get(export_id)
            if record is None or volume not in ("technical", "business"):
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的分册文件。")
            if record["kind"] == "submission" and not lead(state, project_id, principal.user.id):
                raise DomainError(403, "SUBMISSION_FORBIDDEN", "递交版下载仅限项目经理。")
            if record["fingerprint"] != self._fingerprint(state, project_id):
                raise DomainError(409, "EXPORT_STALE", "项目输入已更新，旧导出文件已过期。")
            self._audit(state, principal, project_id, "project-export.download", {"export_id": export_id, "volume": volume})
            entry = next((v for v in record["volumes"] if v["volume"] == volume), None)
            if entry is None:
                raise DomainError(404, "NOT_FOUND", "本次导出不包含该分册。")
            return {**record["documents"][volume], "filename": entry["filename"]}
        return self.repository.transaction(operation)

    def jobs(self, principal):
        state = self.repository.read()
        allowed = {p.id for p in state.projects.values() if p.company_id == principal.user.company_id
                   and principal.user.id in state.project_teams.get(p.id, {}).get("members", {})}
        return {"jobs": [j for j in state.jobs.values() if j["project_id"] in allowed]}

    @staticmethod
    def _public_library(item):
        public = {"reason": "", "source_tier": "own", "is_restricted": False, "is_long_term": False,
                  "valid_to": None, "partner_entity_id": None, **item,
                  "usable_as_evidence": item["status"] == "confirmed" and item["type"] != "history"}
        public.pop("acl_user_ids", None)
        public.pop("restricted", None)
        return public

    @staticmethod
    def _replace_library_acl(state, company_id, evidence_id, user_ids):
        state.resource_acl = [row for row in state.resource_acl
                              if not (row["ref_type"] == "library" and row["ref_id"] == evidence_id)]
        seen = set()
        for user_id in user_ids:
            if user_id in seen:
                continue
            seen.add(user_id)
            account = state.accounts.get(user_id)
            if account is None or account.company_id != company_id:
                raise DomainError(422, "INVALID_LIBRARY_FIELD", "授权用户必须属于本公司。")
            state.resource_acl.append({"ref_type": "library", "ref_id": evidence_id,
                                       "user_id": user_id, "company_id": company_id})

    @staticmethod
    def _agreement_present(state, project_id, evidence):
        partner_id = evidence.get("partner_entity_id")
        if not partner_id:
            return False
        for row in state.project_partners.get(project_id, []):
            if row.get("partner_entity_id") == partner_id and str(row.get("agreement_attachment_id") or "").strip():
                return True
        return False

    @staticmethod
    def _restricted_allowed(state, principal, evidence):
        if principal.user.role in ("company_admin", "data_admin"):
            return True
        company_id = principal.user.company_id
        return any(row["ref_type"] == "library" and row["ref_id"] == evidence["id"]
                   and row["user_id"] == principal.user.id and row["company_id"] == company_id
                   for row in state.resource_acl)

    def _reject_unusable_mount(self, state, principal, project, evidence):
        if evidence.get("is_restricted") and not self._restricted_allowed(state, principal, evidence):
            raise DomainError(403, "FORBIDDEN", "受限资料需公司管理员、资料管理员或资源授权后才能挂接。")
        if evidence.get("source_tier") == "reference":
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "仅供参考资料不能作为投标证据挂接。")
        if evidence.get("source_tier") == "partner" and not self._agreement_present(state, project.id, evidence):
            raise DomainError(409, "EVIDENCE_NOT_USABLE", "合作方资料缺协议，不能作为投标证据挂接。")
        if evidence_expired(evidence, project.deadline):
            raise DomainError(409, "EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。")

    def library(self, principal):
        state = self.repository.read()
        return {"revision": state.library_revisions.get(principal.user.company_id, 1),
                "items": [self._public_library(item) for item in state.library.values() if item["company_id"] == principal.user.company_id]}

    def write_library(self, principal, payload, expected, key, item_id=None):
        from .idempotency import lookup, remember
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
                changed = any(k in payload and payload[k] != item.get(k) for k in (
                    "name", "type", "content", "valid_until", "valid_to", "is_long_term",
                    "source_tier", "partner_entity_id", "is_restricted"))
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
            # 资料变更使用同一仓储，旧检查通过内容指纹自动过期。
            return result
        return self.repository.transaction(operation)
