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

# 补遗、澄清文件的标题行（“补遗文件（第1号）”“澄清通知”），不是投标人要响应的条款
TITLE_LINE = re.compile(r"^\s*(招标文件)?(补遗|澄清|答疑|更正)(文件|通知|公告|函|说明)?\s*[（(]?\s*第?\s*[0-9一二三四五六七八九十]*\s*号?\s*[)）]?\s*$")


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
        from icg.domain.tender_files import FILE_ROLES
        role = payload.get("file_role") or "tender"
        if role not in FILE_ROLES:
            raise DomainError(422, "VALIDATION_ERROR", "文件类型无效。", {"fields": {"file_role": "invalid"}})
        from icg.infra.blob_store import put_blob
        blob = put_blob(content)  # 原件写入文件存储，状态里只记摘要
        payload = {"filename": filename, "sha256": blob, "size": len(content), "file_role": role}

        def operation(state, project, workflow):
            identity = new_id("file")
            media_type = DOCX_MEDIA_TYPE if suffix == ".docx" else MEDIA_TYPES.get(suffix, "text/plain; charset=utf-8")
            same = next((f for f in workflow["files"].values() if f.get("sha256") == blob), None)
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
                "warnings": [f"与本项目已上传的「{same['filename']}」内容完全相同（同一文件指纹）。"] if same else [],
                "download_url": f"/api/v1/projects/{project_id}/files/{identity}",
                "pages": [],
                # 文件类型与版本链（APP-M2-T101 / PRD §5.2.3 tender_file）
                "file_role": role, "version_no": 1, "supersedes_id": None, "superseded_by": None,
                "uploaded_by": principal.user.id, "uploaded_by_name": principal.user.name,
                "uploaded_at": iso_time(self.demo._now()),
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
            regions = record.get("regions") or []
            return {
                "file_id": record["id"],
                "filename": record["filename"],
                "pagination": record["pagination"],
                "warnings": record["warnings"],
                "pages": [{"page": i + 1, "text": t, "regions": regions[i] if i < len(regions) else []}
                          for i, t in enumerate(record["pages"])],
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
            if record.get("supersedes_id") or record.get("superseded_by"):
                raise DomainError(409, "FILE_IN_USE", "已在版本链中的文件不能移除，避免替代关系断开。")
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
        from icg.domain import tender_files
        selected = payload.get("file_ids")
        explicit = selected is not None
        selected = [i for i, f in workflow["files"].items() if not tender_files.superseded(f)] if selected is None else selected
        if not selected or len(selected) != len(set(selected)):
            raise DomainError(422, "FILES_REQUIRED", "请选择至少一份未重复的招标文件。")
        if any(identity not in workflow["files"] for identity in selected):
            raise DomainError(404, "NOT_FOUND", "所选文件不存在或不属于本项目。")
        if explicit and any(tender_files.superseded(workflow["files"][i]) for i in selected):
            raise DomainError(409, "FILE_ALREADY_SUPERSEDED", "已被新版替代的文件不再解析。")
        service = payload.get("service") or "auto"
        if service not in tender_files.SERVICES:
            raise DomainError(422, "VALIDATION_ERROR", "解析服务无效。", {"fields": {"service": "invalid"}})
        # 版本链顺序：招标文件、技术规范书等在前，澄清和补遗按上传先后在后，补遗才能对照到原条款
        rank = tender_files.order(workflow)
        selected.sort(key=lambda identity: rank[identity])
        parsed, errors, pending, used, reused, timing = {}, {}, {}, {}, {}, {}
        recognized: set[str] = set()  # 经扫描件文字识别（RAGFlow DeepDOC）取得文字的文件，条目置信度另算
        from time import monotonic
        from icg.domain.tender_remote import RemoteTenderParser
        remote_parser = RemoteTenderParser(getattr(self.demo, "knowledge_base", None))
        company_id = initial.projects[project_id].company_id
        started_at = iso_time(self.demo._now())
        for identity in selected:
            record = workflow["files"][identity]
            clock = monotonic()
            if record.get("status") == "parsing_remote" and record.get("remote_parse"):
                # 上次已交给 RAGFlow：接着查，不重复上传
                outcome = remote_parser.poll(company_id, record["remote_parse"])
                used[identity] = tender_files.REMOTE_SERVICE
            else:
                # 本公司同指纹、同服务、同参数解析过的直接复用（§5.2.1 规则 3，不跨公司）
                hit = None
                for candidate in ([tender_files.LOCAL_SERVICE] if service == "local" else [tender_files.REMOTE_SERVICE]
                                  if service == "ragflow" else [tender_files.LOCAL_SERVICE, tender_files.REMOTE_SERVICE]):
                    hit = tender_files.cached(initial, company_id, record["sha256"], candidate)
                    if hit:
                        parsed[identity], reused[identity] = hit
                        used[identity] = candidate
                        if candidate == tender_files.REMOTE_SERVICE:
                            recognized.add(identity)
                        break
                if hit:
                    timing[identity] = int((monotonic() - clock) * 1000)
                    continue
                if service == "ragflow":
                    outcome = remote_parser.submit(company_id, record["filename"], file_bytes(record))
                    used[identity] = tender_files.REMOTE_SERVICE
                else:
                    try:
                        parsed[identity] = self.parser.parse(record["filename"], file_bytes(record))
                        used[identity] = tender_files.LOCAL_SERVICE
                        timing[identity] = int((monotonic() - clock) * 1000)
                        continue
                    except DomainError as error:
                        if service == "local" or not remote_parser.eligible(record["filename"], error):
                            errors[identity] = error
                            continue
                        outcome = remote_parser.submit(company_id, record["filename"], file_bytes(record))
                        used[identity] = tender_files.REMOTE_SERVICE
                        if outcome.state == "failed":
                            outcome.message = f"{error.message} {outcome.message}"
                    except Exception:
                        errors[identity] = DomainError(502, "PARSER_UNAVAILABLE", "解析适配器失败，原件仍保留。")
                        continue
            timing[identity] = int((monotonic() - clock) * 1000)
            if outcome.state == "done":
                parsed[identity] = outcome.document
                recognized.add(identity)
            elif outcome.state == "pending":
                pending[identity] = outcome
            else:
                errors[identity] = DomainError(422, "OCR_REQUIRED", outcome.message)

        def operation(state, project, actual):
            actual["parse_confirmed"] = False
            actual["plan_confirmed"] = False
            now = iso_time(self.demo._now())
            for identity in selected:
                record = actual["files"][identity]
                service_name, params = used.get(identity, (None, None))
                # RAGFlow 分几次取回时耗时累计；重新解析从零算
                previous = int(record.get("parse_duration_ms") or 0) if record.get("status") == "parsing_remote" else 0
                record.update(parse_service=service_name, parse_params_version=params, parse_started_at=started_at,
                              parse_duration_ms=previous + timing.get(identity, 0))
            for identity, outcome in pending.items():
                actual["files"][identity].update(status="parsing_remote", remote_parse=outcome.remote,
                                                 warnings=[f"{outcome.message}；稍后再次点击“开始解析”取回结果。"])
            if errors:
                for identity, error in errors.items():
                    actual["files"][identity]["status"] = "failed"
                    actual["files"][identity]["warnings"] = [error.message]
                    actual["files"][identity]["parse_finished_at"] = now
                first = next(iter(errors.values()))
                job = self._job(state, project_id, "parse", "解析未完成，请根据错误重新提供文件或换服务重试。",
                                {"code": first.code, "message": first.message})
                return {"job": job}
            new_requirements: set[str] = set()
            new_facts: set[str] = set()
            for identity, result in parsed.items():
                record = actual["files"][identity]
                record.update(
                    status="parsed",
                    page_count=len(result.pages),
                    pagination=result.pagination,
                    pages=result.pages,
                    warnings=list(result.warnings) + ([f"复用本公司 {reused[identity]['parsed_at'][:10]} 用同一解析服务得到的结果（文件指纹相同）。"]
                                                      if identity in reused else []),
                    regions=getattr(result, "regions", []) or [],
                    batches=getattr(result, "batches", []) or [],
                    parse_finished_at=now,
                    reused_from={"parsed_at": reused[identity]["parsed_at"]} if identity in reused else None,
                )
                record.pop("remote_parse", None)
                if identity not in reused and identity in used:
                    tender_files.remember(state, company_id, record["sha256"], used[identity], result, now)
                # 置信度与“原文不可读”（PRD §5.2.2 规则 2、异常与边界）
                from icg.domain.parse_quality import assess, page_ratios
                record["recognized"] = identity in recognized
                ratios = page_ratios(result.pages)

                def quality(quote: str, page: int) -> dict:
                    ratio = ratios[page - 1] if 1 <= page <= len(ratios) else 0.0
                    return assess(quote, recognized=record["recognized"], page_ratio=ratio)
                from icg.domain.post_process import run_scan
                run_scan(actual, identity, result.pages, iso_time(self.demo._now()))
                existing = {
                    (r["source"]["file_id"], r["source"]["page"], r["source"]["quote"])
                    for r in actual["requirements"].values()
                }
                # 事实按原句去重：人工改过取值的事实原句不变，重新解析不会再插入一条原抽取值（§5.2.2 验收 ③）
                existing_facts = {
                    (f["key"], (f.get("source") or {}).get("file_id"), (f.get("source") or {}).get("page"),
                     (f.get("source") or {}).get("quote"))
                    for f in actual["facts"].values()
                }
                from icg.domain.tender_extraction import extract_facts, extract_requirements, is_fact_line
                for item in extract_facts(result.pages):
                    fact_key_tuple = (item.key, identity, item.page, item.quote)
                    if fact_key_tuple in existing_facts:
                        continue
                    fact = {"id": new_id("fact"), "key": item.key, "value": item.value, "status": "pending",
                            "reason": "", "source": {"file_id": identity, "page": item.page, "quote": item.quote},
                            **quality(item.quote, item.page)}
                    actual["facts"][fact["id"]] = fact
                    new_facts.add(fact["id"])
                    existing_facts.add(fact_key_tuple)
                extracted, summary = extract_requirements(result.pages)
                record["extraction"] = summary
                self._mark_stale(actual, identity, result.pages, {(i.page, i.quote) for i in extracted})
                for item in extracted:
                    if is_fact_line(item.quote) and len(item.text) == len(item.quote):
                        continue  # 单行事实（招标编号：…）已进事实表，不重复成条款
                    if item.quote.startswith(("合成招标文件", "招标文件：", "招标文件:")) or TITLE_LINE.match(item.text):
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
                        **quality(item.quote, item.page),
                    }
                    actual["requirements"][requirement["id"]] = requirement
                    new_requirements.add(requirement["id"])
                    existing.add(source_key)
            # 抽取后处理（PRD §5.2.4）：补遗覆盖原文 → 去重合并 → 结构化字段冲突；已有人工决定保持不变
            from icg.domain.parse_decisions import after_extraction, blocking_conflicts
            post = after_extraction(actual, new_requirements, new_facts, now)
            if pending and not parsed:
                job = self._job(state, project_id, "parse",
                                f"{len(pending)} 份文件正在由 RAGFlow 识别版面与文字，稍后再次点击“开始解析”取回结果。")
                return {"job": job, "requirements": list(actual["requirements"].values()),
                        "facts": list(actual["facts"].values())}
            from icg.domain.post_process import suspected
            conflicts = len(blocking_conflicts(actual))
            omissions = len(suspected(actual))
            if conflicts or omissions:
                from icg.domain.notifications import notify, project_leads
                notify(state, project_leads(state, project_id), "parse_pending", "解析结果待处理",
                       f"「{state.projects[project_id].name}」有 {conflicts} 个冲突待选定、{omissions} 条疑似遗漏待处理，处理后才能确认解析结果。",
                       now=iso_time(self.demo._now()), project_id=project_id, target_id="parse")
            notes = [f"合并重复抽取 {post['merged']} 条" if post["merged"] else "",
                     f"补遗替代原条目 {post['amendments']['superseded']} 条" if post["amendments"]["superseded"] else "",
                     f"补遗未定位原条款 {post['amendments']['unlocated']} 条待人工指定" if post["amendments"]["unlocated"] else ""]
            notes = "；".join(n for n in notes if n)
            job = self._job(state, project_id, "parse", "真实文字提取完成；条款、事实及引用仍需人工核对。"
                            + (f"后处理：{notes}。" if notes else "")
                            + (f"另有 {len(pending)} 份文件仍在 RAGFlow 解析中。" if pending else ""))
            from icg.domain.parse_decisions import visible
            return {
                "job": job,
                "requirements": [r for r in actual["requirements"].values() if visible(r)],
                "facts": [f for f in actual["facts"].values() if visible(f)],
                "conflicts": list(actual["conflicts"].values()),
            }

        result = self._write(principal, project_id, "parse.run", payload, expected, key, operation)
        if result["job"]["status"] == "failed":
            from icg.domain.errors import status_for
            error = result["job"]["error"]
            raise DomainError(status_for(error["code"]), error["code"], error["message"],
                              {"job_id": result["job"]["id"], "revision": result["revision"]})
        return result

    @staticmethod
    def _mark_stale(workflow: dict, file_id: str, pages: list[str], fresh: set[tuple[int, str]]) -> None:
        """重新解析（含换服务）后原句在新文字里找不到的旧条目：标“原文已变化”，不删除；
        已确认且未人工修改的回到待确认（只让受影响条目回待确认，§5.2.4 规则 4）。"""
        text = "\n".join(pages)
        for row in workflow["requirements"].values():
            source = row.get("source") or {}
            if source.get("file_id") != file_id or row.get("merged_into"):
                continue
            quote = str(source.get("quote") or "")
            if (source.get("page"), quote) in fresh or (quote and quote in text):
                row.pop("source_stale", None)
                continue
            row["source_stale"] = "重新解析后原文中找不到这句，请对照原件核对。"
            if row.get("status") == "confirmed" and not row.get("manually_edited"):
                row.update(status="pending", reason=row["source_stale"], confirmed_by=None, confirmed_by_name=None,
                           confirmed_at=None)

    def patch_requirement(self, principal: Principal, project_id: str, requirement_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            requirement = workflow["requirements"].get(requirement_id)
            if requirement is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目条款。")
            if requirement.get("merged_into"):
                raise DomainError(409, "REQUIREMENT_MERGED", "这条已并入主条目；如需单独处理，请先在主条目上“拆分”。",
                                  {"merged_into": requirement["merged_into"]})
            if requirement.get("effective_status") == "superseded" and "status" in payload and payload["status"] != "rejected":
                raise DomainError(409, "REQUIREMENT_SUPERSEDED", "这条已被补遗或新版文件替代；如替代有误，请在“冲突待选定”中撤销替代。")
            if payload.get("status") == "confirmed":
                from icg.domain.parse_decisions import INDIVIDUAL, blocking_conflicts
                from icg.domain.parse_review import requirement_category
                involved = [c for c in blocking_conflicts(workflow) if requirement_id in (c.get("requirement_ids") or [])]
                if involved and requirement_category(requirement) in INDIVIDUAL:
                    raise DomainError(409, "CONFLICTS_PENDING", "这条星号/废标/资格条目涉及待处理的冲突，请先在“冲突待选定”中处理。",
                                      {"conflict_ids": [c["id"] for c in involved]})
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
            if "shared_chapter_id" in payload:
                shared_id = payload["shared_chapter_id"]
                if not lead(state, project_id, principal.user.id):
                    raise DomainError(403, "PROJECT_LEAD_REQUIRED", "跨分册共用行的另一分册章节只能由项目负责人对应。")
                if shared_id:
                    shared = self.demo._chapter(state, principal, shared_id)
                    if (shared.project_id != project_id or not requirement.get("is_cross_volume")
                            or shared.volume == payload.get("volume", requirement["volume"])):
                        raise DomainError(409, "CHAPTER_VOLUME_MISMATCH", "只有标为跨分册共用的行能再对应另一分册的章节。")
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
                # 人工改过原文的条目加锁：重新抽取时按原句去重，不会被新的抽取结果覆盖（§5.2.2 操作“修改”）
                updated["manually_edited"] = True
                updated["manually_edited_by"] = principal.user.id
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略条款必须填写理由。")
            if updated["reference_status"] == "unresolved" and updated["status"] == "confirmed":
                if not updated["reason"].strip():
                    raise DomainError(409, "REFERENCE_REASON_REQUIRED", "存在未解析交叉引用，请在理由中写明人工核对结果。")
                updated["reference_status"] = "resolved"
            if text_changed or any(k in payload and payload[k] != requirement[k] for k in ("category", "volume", "status")):
                workflow["parse_confirmed"] = False
                workflow["plan_confirmed"] = False
            if any(k in payload and payload[k] != requirement.get(k) for k in ("chapter_id", "response", "evidence_ids", "shared_chapter_id")):
                workflow["plan_confirmed"] = False
            # 分册分流（PRD §5.3.1 规则 8）：项目负责人改分册或对应章节，即确认了这一行的分流；
            # 其他人改分册只算修改建议，这一行回到“待确认”，确认前不进入写作方案。
            routed = any(k in payload and payload[k] is not None for k in ("volume", "chapter_id"))
            if routed and lead(state, project_id, principal.user.id):
                updated.update(volume_confirmed_by=principal.user.id, volume_confirmed_at=iso_time(self.demo._now()))
            elif "volume" in payload and payload["volume"] != requirement["volume"]:
                updated.update(volume_confirmed_by=None, volume_confirmed_at=None)
            if updated["status"] == "confirmed" and (requirement["status"] != "confirmed" or text_changed):
                # 响应追溯表（APP-M2-T201）需要“确认人”
                updated.update(confirmed_by=principal.user.id, confirmed_by_name=principal.user.name,
                               confirmed_at=iso_time(self.demo._now()))
            elif updated["status"] != "confirmed":
                updated.update(confirmed_by=None, confirmed_by_name=None, confirmed_at=None)
            from icg.domain.parse_quality import unresolved_unreadable
            if updated["status"] == "confirmed" and unresolved_unreadable(updated):
                raise DomainError(409, "REQUIREMENT_NOT_READY", "这条原文不可读，请对照原页补录文字后再确认，或填写理由删除。")
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
            if fact.get("merged_into"):
                raise DomainError(409, "REQUIREMENT_MERGED", "这项事实已并入同值的主事实；如需单独处理，请先拆分。",
                                  {"merged_into": fact["merged_into"]})
            if fact.get("effective_status") == "superseded" and payload.get("status") not in (None, "rejected"):
                raise DomainError(409, "REQUIREMENT_SUPERSEDED", "这项取值已被补遗替代；如替代有误，请在“冲突待选定”中撤销替代。")
            if fact.get("required") and principal.user.role != "manager":
                raise DomainError(403, "FACT_MANAGER_REQUIRED", "必备事实的维护和确认仅限本公司项目负责人。")
            if any(v is None for v in payload.values()):
                raise DomainError(422, "INVALID_FACT", "事实字段不能设为空值。")
            updated = {**fact, **payload}
            if not lead(state, project_id, principal.user.id) and "value" in payload and payload["value"] != fact["value"]:
                updated["status"] = "pending"
            if not updated["value"].strip():
                raise DomainError(422, "EMPTY_FACT", "事实取值不能为空。")
            if "value" in payload and payload["value"] != fact["value"]:
                updated.update(manually_edited=True, manually_edited_by=principal.user.id)
            from icg.domain.parse_quality import unresolved_unreadable
            if updated["status"] == "confirmed" and unresolved_unreadable(updated):
                raise DomainError(409, "FACT_NOT_READY", "这条事实的原文不可读，请对照原页补录取值后再确认，或填写理由忽略。")
            if updated["status"] == "rejected" and not updated["reason"].strip():
                raise DomainError(422, "REASON_REQUIRED", "忽略事实必须填写理由。")
            from icg.domain.parse_decisions import conflict_type, current, refresh_fact_conflicts
            changed = any(k in payload and payload[k] != fact[k] for k in ("value", "status"))
            for conflict in workflow["conflicts"].values():
                # 已选定的冲突里改了取值或状态：选定作废，重新待处理；已按补遗处理、不构成冲突的不受影响
                if (changed and fact_id in (conflict.get("fact_ids") or []) and current(conflict)
                        and conflict.get("status") == "resolved" and conflict_type(conflict) != "addendum_unlocated"):
                    conflict.update(status="pending", selected_fact_id=None, reason="")
            fact.update(updated)
            if fact.get("status") != "rejected":
                fact.pop("rejected_by_conflict", None)
            refresh_fact_conflicts(workflow, iso_time(self.demo._now()))
            workflow["plan_confirmed"] = False
            return {"fact": fact}

        return self._write(principal, project_id, "fact.update:" + fact_id, payload, expected, key, operation)

    def resolve_conflict(self, principal: Principal, project_id: str, conflict_id: str, payload: dict, expected: str | None, key: str | None):
        """PATCH /conflicts/{id}：选定一方取值（等同 decide_conflict 的 choose）。"""
        return self.decide_conflict(principal, project_id, conflict_id, {"action": "choose", **payload}, expected, key)

    def confirm_parse(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            from icg.domain.parse_decisions import blocking_conflicts, conflict_selection_valid
            from icg.domain.tender_files import effective_files
            files = effective_files(workflow)  # 已被新版替代的文件不再要求解析成功
            if not files or any(f["status"] != "parsed" for f in files):
                raise DomainError(409, "PARSE_INCOMPLETE", "所有上传文件必须成功解析后才能确认。")
            if not workflow["requirements"]:
                raise DomainError(409, "REQUIREMENTS_EMPTY", "没有招标条款，不能确认解析。")
            if any(r["status"] == "pending" for r in workflow["requirements"].values()) or any(f["status"] == "pending" for f in workflow["facts"].values()):
                raise DomainError(409, "REVIEW_PENDING", "请先逐条确认或填写理由忽略全部条款和事实。")
            if not any(r["status"] == "confirmed" for r in workflow["requirements"].values()):
                raise DomainError(409, "CONFIRMED_REQUIREMENTS_EMPTY", "至少需要一条已确认条款。")
            if blocking_conflicts(workflow):
                raise DomainError(409, "CONFLICTS_PENDING", "存在待处理的冲突，请先选定一方或写明理由标“不构成冲突”。")
            if not all(conflict_selection_valid(workflow, c) for c in workflow["conflicts"].values()):
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
