# 为什么有这个文件：由 workflow_orchestrator 解耦抽取的招标文件解析与响应矩阵子编排服务（BE-TECH-DEBT-03）。
# 它解决什么问题：
# 1. 招标文件上传（upload）、下载/预览（file）与安全删除（delete_file）；
# 2. 文本解析提取（parse）、事实冲突识别与消解（resolve_conflict）；
# 3. 响应矩阵条款维护（patch_requirement）与已确认条款状态固化（confirm_parse）。

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from pathlib import PurePosixPath
from typing import Any

from icg.domain.domain import DomainError, Principal, iso_time, new_id
from icg.infra.blob_store import file_bytes


def out_of_scope_fields(state, project_id, volume):
    """只写技术标：商务/资格条款由他人负责，标为不在本项目范围（忽略并写明理由），仍保留原文可查。"""
    from icg.domain.project_access import project_volumes
    if volume in project_volumes(state, project_id):
        return {}
    return {"status": "rejected", "out_of_scope": True,
            "reason": "本项目只写技术标：商务/资格条款不在本项目编写范围，由商务标负责人另行响应。"}
from icg.domain.generation_context import evidence_expired
from icg.domain.project_access import lead, writable
from icg.domain.export_service import DOCX_MEDIA_TYPE


class TenderOrchestratorMixin:
    """招标文件解析与响应矩阵编排 Mixin。"""

    def upload(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        filename = payload["filename"]
        if filename != PurePosixPath(filename.replace("\\", "/")).name or any(c in filename for c in '\r\n\x00'):
            raise DomainError(422, "INVALID_FILENAME", "请提供文件名，不包含目录或控制字符。")
        suffix = PurePosixPath(filename).suffix.lower()
        from icg.domain.tender_remote import MEDIA_TYPES, REMOTE_SUFFIXES
        if suffix not in {".txt", ".md", *REMOTE_SUFFIXES}:
            raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "可上传文本、Word（.docx/.doc）、PDF（含扫描件）、Excel 与图片。")
        from icg.domain.upload_limits import max_upload_bytes, too_large_message
        content = payload.get("content_bytes")
        if content is None:
            try:
                content = base64.b64decode(payload["content_base64"], validate=True)
            except (binascii.Error, ValueError) as error:
                raise DomainError(422, "INVALID_FILE_ENCODING", "文件编码不正确，请重新选择文件。") from error
        if not content or len(content) > max_upload_bytes():
            raise DomainError(413, "FILE_SIZE_LIMIT", too_large_message())
        from icg.infra.blob_store import put_blob
        blob = put_blob(content)  # 原件写入文件存储，状态里只记摘要
        payload = {"filename": filename, "sha256": blob, "size": len(content)}

        def operation(state, project, workflow):
            identity = new_id("file")
            media_type = DOCX_MEDIA_TYPE if suffix == ".docx" else MEDIA_TYPES.get(suffix, "text/plain; charset=utf-8")
            record = {
                "id": identity,
                "filename": filename,
                "size": len(content),
                "sha256": blob,
                "blob": blob,
                "media_type": media_type,
                "status": "uploaded",
                "page_count": 0,
                "pagination": "not_parsed",
                "warnings": [],
                "download_url": f"/api/v1/projects/{project_id}/files/{identity}",
                "pages": [],
            }
            workflow["files"][identity] = record
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            job = self._job(state, project_id, "upload", "原件已保存，尚未解析。")
            return {"file": self._public_file(record), "job": job}

        return self._write(principal, project_id, "file.upload", payload, expected, key, operation)

    def file(self, principal: Principal, project_id: str, file_id: str, *, preview: bool = False):
        state = self.repository.read()
        self.demo._project(state, principal, project_id)
        record = self._workflow(state, project_id)["files"].get(file_id)
        if record is None:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的文件。")
        if preview:
            if record["status"] != "parsed":
                raise DomainError(409, "FILE_NOT_PARSED", "文件尚未成功解析，暂时没有原文预览。")
            return {
                "file_id": record["id"],
                "filename": record["filename"],
                "pagination": record["pagination"],
                "warnings": record["warnings"],
                "pages": [{"page": i + 1, "text": t} for i, t in enumerate(record["pages"])],
            }
        return record

    def delete_file(self, principal: Principal, project_id: str, file_id: str, payload: dict, expected: str | None, key: str | None):
        reason = payload["reason"].strip()
        if not reason:
            raise DomainError(422, "REASON_REQUIRED", "移除无法解析或误传文件必须填写理由。")

        def operation(state, project, workflow):
            record = workflow["files"].get(file_id)
            if record is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目文件。")
            referenced = any(
                item["source"]["file_id"] == file_id
                for collection in (workflow["requirements"], workflow["facts"])
                for item in collection.values()
            )
            if record["status"] not in ("uploaded", "failed", "parsing_remote") or referenced:
                raise DomainError(409, "FILE_IN_USE", "已有解析结果或条款来源的文件不能移除。")
            del workflow["files"][file_id]
            workflow["parse_confirmed"] = False
            workflow["plan_confirmed"] = False
            return {"deleted_file_id": file_id}

        return self._write(principal, project_id, "file.delete:" + file_id, payload, expected, key,
                           operation, {"file_id": file_id, "reason": reason})

    def parse(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
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
        parsed, errors, pending = {}, {}, {}
        from icg.domain.tender_remote import RemoteTenderParser
        remote_parser = RemoteTenderParser(getattr(self.demo, "knowledge_base", None))
        company_id = initial.projects[project_id].company_id
        for identity in selected:
            record = workflow["files"][identity]
            if record.get("status") == "parsing_remote" and record.get("remote_parse"):
                # 上次已交给 RAGFlow：接着查，不重复上传
                outcome = remote_parser.poll(company_id, record["remote_parse"])
            else:
                try:
                    parsed[identity] = self.parser.parse(record["filename"], file_bytes(record))
                    continue
                except DomainError as error:
                    if not remote_parser.eligible(record["filename"], error):
                        errors[identity] = error
                        continue
                    outcome = remote_parser.submit(company_id, record["filename"], file_bytes(record))
                    if outcome.state == "failed":
                        outcome.message = f"{error.message} {outcome.message}"
                except Exception:
                    errors[identity] = DomainError(502, "PARSER_UNAVAILABLE", "解析适配器失败，原件仍保留。")
                    continue
            if outcome.state == "done":
                parsed[identity] = outcome.document
            elif outcome.state == "pending":
                pending[identity] = outcome
            else:
                errors[identity] = DomainError(422, "OCR_REQUIRED", outcome.message)

        def operation(state, project, actual):
            actual["parse_confirmed"] = False
            actual["plan_confirmed"] = False
            for identity, outcome in pending.items():
                actual["files"][identity].update(status="parsing_remote", remote_parse=outcome.remote,
                                                 warnings=[f"{outcome.message}；稍后再次点击“开始解析”取回结果。"])
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
                record.update(
                    status="parsed",
                    page_count=len(result.pages),
                    pagination=result.pagination,
                    pages=result.pages,
                    warnings=result.warnings,
                )
                record.pop("remote_parse", None)
                from icg.domain.post_process import run_scan
                run_scan(actual, identity, result.pages, iso_time(self.demo._now()))
                existing = {
                    (r["source"]["file_id"], r["source"]["page"], r["source"]["quote"])
                    for r in actual["requirements"].values()
                }
                existing_facts = {
                    (f["key"], f["value"], f["source"]["file_id"], f["source"]["page"])
                    for f in actual["facts"].values()
                }
                from icg.domain.tender_extraction import extract_facts, extract_requirements, is_fact_line
                for item in extract_facts(result.pages):
                    fact_key_tuple = (item.key, item.value, identity, item.page)
                    if fact_key_tuple in existing_facts:
                        continue
                    fact = {"id": new_id("fact"), "key": item.key, "value": item.value, "status": "pending",
                            "reason": "", "source": {"file_id": identity, "page": item.page, "quote": item.quote}}
                    actual["facts"][fact["id"]] = fact
                    existing_facts.add(fact_key_tuple)
                extracted, summary = extract_requirements(result.pages)
                record["extraction"] = summary
                for item in extracted:
                    if is_fact_line(item.quote) and len(item.text) == len(item.quote):
                        continue  # 单行事实（招标编号：…）已进事实表，不重复成条款
                    if item.quote.startswith(("合成招标文件", "招标文件：", "招标文件:")):
                        continue
                    source_key = (identity, item.page, item.quote)
                    if source_key in existing:
                        continue
                    references = re.findall(r"(?:见|详见|参照)(?:附件|第)[^，。；\n]{0,40}", item.text)
                    requirement = {
                        "id": new_id("req"),
                        "text": item.text,
                        "category": item.category,
                        "volume": item.volume,
                        "chapter_id": None,
                        "status": "pending",
                        "response": "",
                        "reason": "",
                        "evidence_ids": [],
                        "source": {"file_id": identity, "page": item.page, "quote": item.quote},
                        "references": references,
                        "reference_status": "unresolved" if references else "none",
                        "section_path": list(item.section_path),
                        **out_of_scope_fields(state, project_id, item.volume),
                        "section_kind": item.section_kind,
                        "score": item.score,
                    }
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
                        conflict = {
                            "id": new_id("conflict"),
                            "key": fact_key,
                            "fact_ids": ids,
                            "selected_fact_id": None,
                            "status": "pending",
                            "reason": "",
                        }
                        actual["conflicts"][conflict["id"]] = conflict
                    elif set(previous["fact_ids"]) != set(ids):
                        previous.update(fact_ids=ids, selected_fact_id=None, status="pending", reason="")
            if pending and not parsed:
                job = self._job(state, project_id, "parse",
                                f"{len(pending)} 份文件正在由 RAGFlow 识别版面与文字，稍后再次点击“开始解析”取回结果。")
                return {"job": job, "requirements": list(actual["requirements"].values()),
                        "facts": list(actual["facts"].values())}
            job = self._job(state, project_id, "parse", "真实文字提取完成；条款、事实及引用仍需人工核对。"
                            + (f"另有 {len(pending)} 份文件仍在 RAGFlow 解析中。" if pending else ""))
            return {
                "job": job,
                "requirements": list(actual["requirements"].values()),
                "facts": list(actual["facts"].values()),
                "conflicts": list(actual["conflicts"].values()),
            }

        result = self._write(principal, project_id, "parse.run", payload, expected, key, operation)
        if result["job"]["status"] == "failed":
            from icg.domain.errors import status_for
            error = result["job"]["error"]
            raise DomainError(status_for(error["code"]), error["code"], error["message"],
                              {"job_id": result["job"]["id"], "revision": result["revision"]})
        return result

    def patch_requirement(self, principal: Principal, project_id: str, requirement_id: str, payload: dict, expected: str | None, key: str | None):
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
            if "volume" in payload:
                from icg.domain.project_access import require_project_volume
                require_project_volume(state, project_id, volume)
                if requirement.get("out_of_scope") and volume == "technical":
                    requirement["out_of_scope"] = False  # 人工把商务条款纳入技术标
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
            from icg.domain.matrix import apply_response_type, validate_response
            explicit_response = "response_type" in payload
            payload.update(apply_response_type(requirement, payload))
            if payload.get("assignee_id") and not writable(state, project_id, payload["assignee_id"]):
                raise DomainError(422, "ASSIGNEE_NOT_WRITABLE", "负责人必须是本项目可以编写的成员。")
            updated = {**requirement, **payload}
            validate_response(updated, explicit_response)
            if updated.get("out_of_scope") and updated.get("status") == "confirmed" and requirement.get("out_of_scope"):
                from icg.domain.project_access import project_volumes
                if updated.get("volume") not in project_volumes(state, project_id):
                    raise DomainError(409, "REQUIREMENT_NOT_READY", "本项目只写技术标：要响应这条商务条款，请先把分册改为技术分册。")
            if requirement["category"] == "sla" or payload.get("category") == "sla":
                updated["sla_required"] = True
            text_changed = "text" in payload and payload["text"] != requirement["text"]
            if text_changed:
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
            if updated["status"] == "confirmed" and (requirement["status"] != "confirmed" or text_changed):
                # 响应追溯表（APP-M2-T201）需要“确认人”
                updated.update(confirmed_by=principal.user.id, confirmed_by_name=principal.user.name,
                               confirmed_at=iso_time(self.demo._now()))
            elif updated["status"] != "confirmed":
                updated.update(confirmed_by=None, confirmed_by_name=None, confirmed_at=None)
            requirement.update(updated)
            return {"requirement": requirement}

        return self._write(principal, project_id, "requirement.update:" + requirement_id, payload, expected, key, operation)

    def patch_fact(self, principal: Principal, project_id: str, fact_id: str, payload: dict, expected: str | None, key: str | None):
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

    def resolve_conflict(self, principal: Principal, project_id: str, conflict_id: str, payload: dict, expected: str | None, key: str | None):
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

    def confirm_parse(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
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
                if (
                    selected not in conflict["fact_ids"]
                    or workflow["facts"].get(selected, {}).get("status") != "confirmed"
                    or any(workflow["facts"].get(identity, {}).get("status") != "rejected"
                           for identity in conflict["fact_ids"] if identity != selected)
                ):
                    raise DomainError(409, "CONFLICT_SELECTION_INVALID", "冲突必须有且只有一个确认取值，其余候选需忽略。")
            from icg.domain.post_process import require_no_omissions
            require_no_omissions(workflow)
            workflow["parse_confirmed"] = True
            return {"parse_confirmed": True}

        return self._write(principal, project_id, "parse.confirm", payload, expected, key, operation)


class TenderOrchestrator(TenderOrchestratorMixin):
    """招标文件与响应矩阵独立领域编排服务。"""

    def __init__(self, workflow: Any = None):
        self._workflow_service = workflow

    def __getattr__(self, name: str) -> Any:
        if hasattr(self, "_workflow_service") and self._workflow_service is not None and hasattr(self._workflow_service, name):
            return getattr(self._workflow_service, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
