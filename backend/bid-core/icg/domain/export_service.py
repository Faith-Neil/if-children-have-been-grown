# 为什么有这个文件：由原 workflow.py 模块化解耦生成的导出领域服务。
# 它解决什么问题：
# 1. 提供双卷 Word 导出（APP-M2-T012）、内部评审稿脱敏与正式递交版定稿门禁核验（PRD §5.8.5）；
# 2. 导出 Word 文档 SHA-256 指纹校验与下载权限控制；
# 3. 继承 CheckOrchestratorMixin 提供平滑合规检查向下兼容。

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from icg.domain.domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from icg.domain.project_access import VOLUMES, lead
from icg.domain.generation_context import resolve_fact_variables
from icg.domain.check_orchestrator import (
    CheckBlockerError,
    CheckOrchestratorMixin,
    SHANGHAI,
)

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def chapter_export_block(title: str, body: str) -> str:
    # 分册里的章节名要成为一级标题，正文仍按原行保留。
    return f"# {title}\n{body}"


WORD_DEFAULT_FORMAT_METADATA = {
    "page_size": "A4",
    "orientation": "portrait",
    "margins": {
        "top": 72,
        "bottom": 72,
        "left": 72,
        "right": 72,
        "top_cm": 2.5,
        "bottom_cm": 2.5,
        "left_cm": 2.8,
        "right_cm": 2.6,
    },
    "font_family": "SimSun",
    "fonts": {
        "cover_title": "方正小标宋",
        "cover_project": "黑体",
        "h1": "黑体",
        "h2": "楷体_GB2312",
        "h3": "仿宋_GB2312",
        "body": "仿宋_GB2312",
        "table": "宋体",
        "header": "宋体",
        "toc": "宋体",
    },
    "font_sizes_pt": {
        "cover_title": 22.0,
        "cover_project": 16.0,
        "h1": 16.0,
        "h2": 15.0,
        "h3": 14.0,
        "body": 14.0,
        "table": 10.5,
        "header": 10.5,
        "toc": 12.0,
    },
    "line_spacing": {
        "body_line_pt": 28.0,
        "body_first_line_chars": 200,
        "body_first_line_twips": 560,
    },
    "h1_align": "center",
}


class ExportServiceMixin(CheckOrchestratorMixin):
    """导出与下载领域编排 Mixin。"""

    @staticmethod
    def _mask(text: str) -> str:
        # 内部稿不能主动输出身份证、手机号、银行账户长号码。
        text = re.sub(r"(?<![0-9])([0-9]{3})[0-9]{11}([0-9]{3}[0-9Xx])(?![0-9])", r"\1***********\2", text)
        text = re.sub(r"(?<![0-9])([1][3-9][0-9])[0-9]{4}([0-9]{4})(?![0-9])", r"\1****\2", text)
        return re.sub(r"(?<![0-9])[0-9]{12,}([0-9]{4})(?![0-9])", r"************\1", text)

    def export(self, principal: Principal, project_id: str, payload: dict, expected: str | None, key: str | None):
        def operation(state, project, workflow):
            check = workflow["checks"].get(payload["check_id"])
            if check is None:
                raise DomainError(404, "NOT_FOUND", "未找到本项目检查批次。")
            if check["fingerprint"] != self._fingerprint(state, project_id):
                raise DomainError(409, "CHECK_STALE", "正文、项目资料或证据已更新，请重新检查。")

            check_issues = check.get("issues", [])
            has_blockers = any(i.get("severity") == "blocker" for i in check_issues)

            if payload.get("kind") == "submission" and has_blockers:
                raise CheckBlockerError("分册最新检查结果存在未解决的废标或星号条款阻断项，无法导出正式递交版。")

            scope = payload.get("volume", "all")
            from icg.domain.project_access import project_volumes, rule_scope
            technical_only = len(project_volumes(state, project_id)) == 1
            rule_scope(state, project_id, scope)  # 只写技术标时请求商务分册 → 404
            required_volumes = set(project_volumes(state, project_id)) if scope == "all" else {scope}

            if payload.get("kind") == "submission":
                # 分册定稿闸门（PRD §5.8.5）：所选分册必须全部经负责人或管理员定稿锁定
                volumes_state = workflow.get("volumes", {})
                unfinalized = [
                    vol for vol in sorted(required_volumes)
                    if not volumes_state.get(vol, {}).get("is_finalized")
                ]
                if unfinalized:
                    unfinalized_names = "、".join("技术分册" if v == "technical" else "商务分册" for v in unfinalized)
                    raise DomainError(
                        409,
                        "RULES_INCOMPLETE",
                        f"完整合规规则与分册定稿未完成：{unfinalized_names}尚未完成责任人定稿锁定，不能把本地内部稿冒充递交版。"
                    )
                from icg.domain.volume_review import volume_snapshot
                drifted = [vol for vol in sorted(required_volumes)
                           if volumes_state.get(vol, {}).get("snapshot") is not None
                           and volumes_state[vol]["snapshot"] != volume_snapshot(state, project_id, vol)]
                if drifted:
                    raise DomainError(409, "RULES_INCOMPLETE", "定稿后正文有改动，须解锁、重新检查和复核后再定稿。",
                                      {"volumes": drifted})

            is_internal_review = payload.get("kind") == "internal_review"
            if not is_internal_review and not check["passed"]:
                raise DomainError(409, "CHECK_FAILED", "当前已实现的流程检查仍有阻断项。")

            if check["volume"] != scope:
                raise DomainError(409, "ALL_VOLUMES_CHECK_REQUIRED", "导出范围必须和已完成的检查一致；两册导出需要检查全部分册。")
            chapters = self._ordered_chapters(state, project_id, workflow)
            chapters = [c for c in chapters if scope == "all" or c.volume == scope]
            if {c.volume for c in chapters} != required_volumes:
                raise DomainError(422, "TWO_VOLUMES_REQUIRED",
                                  "导出缺少技术分册正文。" if technical_only else "导出必须包含技术和商务两册。")
            identity = new_id("project-export")
            from icg.domain.export_batch import ExportRenderError, failed_record, next_batch_no, render_batch, volume_bindings
            now = self.demo._now()
            batch_no = next_batch_no(workflow, payload["kind"], datetime.fromtimestamp(now, SHANGHAI))
            documents, volumes = {}, []
            for volume, name in (("technical", "技术分册"), ("business", "商务分册")):
                if volume not in required_volumes:
                    continue
                selected = [c for c in chapters if c.volume == volume]
                filename = f"icg-{volume}-{identity}.docx"
                doc_title = self._mask(project.name) + " — " + name
                doc_content = "\n\n".join(
                    chapter_export_block(
                        self._mask(c.title),
                        self._mask(resolve_fact_variables(state, project_id, c.content)),
                    )
                    for c in selected
                )
                vol_sha = hashlib.sha256(doc_content.encode("utf-8")).hexdigest()
                documents[volume] = {
                    "title": doc_title,
                    "project_name": self._mask(project.name),
                    "content": doc_content,
                    "sha256": vol_sha,
                    "format_metadata": WORD_DEFAULT_FORMAT_METADATA,
                }
                volumes.append({
                    "volume": volume,
                    "filename": filename,
                    "download_url": f"/api/v1/projects/{project_id}/exports/{identity}/{volume}",
                    "sha256": vol_sha,
                    "format_metadata": WORD_DEFAULT_FORMAT_METADATA,
                    "batch_no": batch_no,
                })
            try:
                # 原子批次（APP-M2-T202）：全部分册都生成成功才保存；一册失败整批记“失败”，不留可下载文件
                render_batch(documents, volumes, **self._render_override())
            except ExportRenderError as error:
                failed = failed_record(identity, batch_no, payload["kind"], check, iso_time(now), error, scope)
                failed["created_by"] = principal.user.id
                workflow["exports"][identity] = failed
                job = self._job(state, project_id, "export", failed["error_message"],
                                {"code": "EXPORT_FAILED", "message": failed["error_message"]})
                return {"export": self._public_export(state, project_id, failed), "job": job}
            combined_content = "\n---\n".join(documents[v]["content"] for v in documents)
            record_sha = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()
            compliance_notice = (
                "存在未解决的废标或星号条款阻断项，仅供内部评审，不可作为正式递交文件。"
                if has_blockers else (
                    "仅供内部评审，不可作为正式递交文件。"
                    if is_internal_review else None
                )
            )
            record = {
                "id": identity,
                "kind": payload["kind"],
                "check_id": check["id"],
                "fingerprint": check["fingerprint"],
                "created_at": iso_time(self.demo._now()),
                "excludes_drafts": True,
                "volumes": volumes,
                "documents": documents,
                "has_blockers": has_blockers,
                "compliance_notice": compliance_notice,
                "sha256": record_sha,
                "format_metadata": WORD_DEFAULT_FORMAT_METADATA,
                "is_submission": payload.get("kind") == "submission",
                "batch_no": batch_no,
                "export_status": "completed",
                "volume": scope,
                "created_by": principal.user.id,
                "bound_volumes": volume_bindings(workflow, sorted(required_volumes)),
            }
            record["volume_mode"] = "technical_only" if technical_only else "both"
            if record["is_submission"] and not technical_only:
                # PRD §5.9.2：导出递交版时必定同时生成合标核对清单，随批次保存；只写技术标的项目不合标
                from icg.domain.merge_checklist import build_merge_checklist
                record["merge_checklist"] = build_merge_checklist(state, project, workflow, record, check,
                                                                  now_iso=record["created_at"])
                record["merge_checklist_url"] = f"/api/v1/projects/{project_id}/exports/{identity}/merge-checklist.xlsx"
            workflow["exports"][identity] = record
            if payload.get("kind") == "submission":
                job_desc = ("技术标 Word 正式递交版已生成（本项目只写技术标，不合标）" if technical_only
                            else "两个独立 Word 正式递交版已生成" if scope == "all" else "本册 Word 正式递交版已生成") + "；已完成责任人定稿与门禁核验。"
            else:
                job_desc = ("两个独立 Word 内部稿已生成" if scope == "all" else "本册 Word 内部稿已生成") + "；只含已提交正文。"
            self._job(state, project_id, "export", job_desc)
            return {"export": self._public_export(state, project_id, record)}

        result = self._write(principal, project_id, "project.export", payload, expected, key, operation)
        if result.get("export", {}).get("status") == "failed":
            exported = result["export"]
            raise DomainError(500, "EXPORT_FAILED", exported["error_message"],
                              {"export_id": exported["id"], "batch_no": exported["batch_no"], "revision": result.get("revision")})
        return result

    def _render_override(self) -> dict:
        """测试可替换分册生成函数以模拟某册失败；生产使用默认 Word 生成。"""
        render = getattr(self, "export_renderer", None)
        return {"render": render} if render is not None else {}

    def download(self, principal: Principal, project_id: str, export_id: str, volume: str):
        def operation(state):
            self.demo._project(state, principal, project_id)
            record = self._workflow(state, project_id)["exports"].get(export_id)
            if record is None or volume not in ("technical", "business"):
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的分册文件。")
            if record["kind"] == "submission" and not lead(state, project_id, principal.user.id):
                raise DomainError(403, "SUBMISSION_FORBIDDEN", "递交版下载仅限项目经理。")
            if record.get("export_status") == "failed":
                raise DomainError(404, "NOT_FOUND", "该批次生成失败，没有可下载的分册文件。")
            stale = record["fingerprint"] != self._fingerprint(state, project_id)
            entry = next((v for v in record["volumes"] if v["volume"] == volume), None)
            if entry is None:
                raise DomainError(404, "NOT_FOUND", "本次导出不包含该分册。")
            if stale and not entry.get("blob"):
                # 早期批次没有存 Word 快照，无法保证与当时内容一致
                raise DomainError(409, "EXPORT_STALE", "项目输入已更新，旧导出文件已过期。")
            self._audit(state, principal, project_id, "project-export.download",
                        {"export_id": export_id, "volume": volume, "batch_no": record.get("batch_no"), "stale": stale})
            document = {**record["documents"][volume], "filename": entry["filename"], "stale": stale,
                        "batch_no": record.get("batch_no")}
            if entry.get("blob"):
                from icg.infra.blob_store import get_blob
                document["content_bytes"] = get_blob(entry["blob"])  # 生成时的快照原文件，过期后仍原样提供
            return document

        return self.repository.transaction(operation)


    def _export_reader(self, state, principal: Principal, project_id: str):
        """合标核对清单与响应追溯表的读取方（PRD §5.10 权限表）：本公司的公司管理员不必是项目成员。

        返回 (项目, 是否公司管理员)。其他人仍须是项目成员（_project 的原有规则）。
        """
        from icg.domain.project_access import normalize_role
        project = state.projects.get(project_id)
        account = state.accounts.get(principal.user.id)
        if (project is not None and not project.is_deleted and account is not None
                and normalize_role(account.role) == "company_admin" and account.company_id == project.company_id
                and state.sessions.get(principal.session_token) == account.id):
            return project, True
        return self.demo._project(state, principal, project_id), False

    def merge_checklist(self, principal: Principal, project_id: str, export_id: str) -> dict:
        """读取递交批次的合标核对清单。公司管理员、项目负责人与分册负责人（合标负责人默认商务分册负责人）可看可下载。"""
        from icg.domain.merge_checklist import checklist_stale
        from icg.domain.project_access import project_volumes, volume_owner

        def operation(state):
            project, company_admin = self._export_reader(state, principal, project_id)
            workflow = self._workflow(state, project_id)
            record = workflow["exports"].get(export_id)
            if record is None or not record.get("merge_checklist"):
                raise DomainError(404, "NOT_FOUND", "该导出批次没有合标核对清单（只有递交版批次生成）。")
            identity = principal.user.id
            allowed = (company_admin or lead(state, project_id, identity)
                       or any(volume_owner(state, project_id, volume, identity) for volume in project_volumes(state, project_id)))
            if not allowed:
                raise DomainError(403, "SUBMISSION_FORBIDDEN", "合标核对清单仅限项目负责人、分册负责人和公司管理员下载。")
            checklist = record["merge_checklist"]
            stale = checklist_stale(workflow, checklist, self._fingerprint(state, project_id), record["fingerprint"])
            self._audit(state, principal, project_id, "project-export.merge-checklist", {"export_id": export_id, "stale": stale})
            return {"checklist": checklist, "stale": stale}

        return self.repository.transaction(operation)


    def response_trace(self, principal: Principal, project_id: str, volume: str = "all") -> dict:
        """内部响应追溯表（PRD §5.9.1 规则 12）：任何时候可导出；项目负责人全部，分册负责人本册。"""
        from icg.domain.project_access import volume_owner
        from icg.domain.response_trace import VOLUME_NAMES, build_trace_rows, trace_sheets
        from icg.infra.xlsx import build_xlsx

        def operation(state):
            project, company_admin = self._export_reader(state, principal, project_id)
            workflow = self._workflow(state, project_id)
            from icg.domain.project_access import project_volumes, rule_scope
            rule_scope(state, project_id, volume)
            wanted = set(project_volumes(state, project_id)) if volume == "all" else {volume}
            identity = principal.user.id
            if not (company_admin or lead(state, project_id, identity)):
                wanted = {v for v in wanted if volume_owner(state, project_id, v, identity)}
                if not wanted:
                    raise DomainError(403, "FORBIDDEN", "响应追溯表仅限项目负责人或本册负责人导出。")
            now = iso_time(self.demo._now())
            rows = build_trace_rows(state, project, workflow, wanted)
            scope = "、".join(VOLUME_NAMES[v] for v in VOLUMES if v in wanted)
            self._audit(state, principal, project_id, "project-export.response-trace", {"volumes": sorted(wanted), "rows": len(rows)})
            return {"content": build_xlsx(trace_sheets(project, rows, scope=scope, generated_at=now)),
                    "filename": f"response-trace-{project_id}-{'-'.join(sorted(wanted))}.xlsx"}

        return self.repository.transaction(operation)


class ExportService(ExportServiceMixin):
    def __init__(self, workflow=None):
        self._workflow = workflow

    def __getattr__(self, name: str) -> Any:
        if self._workflow is not None and hasattr(self._workflow, name):
            return getattr(self._workflow, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
