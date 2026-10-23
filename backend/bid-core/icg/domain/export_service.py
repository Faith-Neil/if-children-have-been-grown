# 为什么有这个文件：由原 workflow.py 模块化解耦生成的领域服务。
# 它解决什么问题：按领域上下文治理巨石 workflow.py，保持 100% 行为兼容。

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Callable

from icg_demo.domain import Chapter, DemoService, DemoState, DomainError, Principal, iso_time, new_id
from icg_demo.ports import ParserProvider
from icg_demo.input_snapshot import project_input_fingerprint
from icg_demo.sla import SlaService, public_sla, resolve_variables, sla_facts, sla_issues
from icg_demo.generation_context import (
    build_generation_context,
    chapter_plan,
    evidence_expired,
    plan_is_current,
    project_facts,
    public_plan,
    refuse_source_change,
    render_model_input,
    require_ready,
    resolve_fact_variables,
    validate_model_output,
    writing_source_fingerprint,
)
from icg_demo.project_access import (
    VOLUMES,
    writable,
    lead,
    volume_owner,
    require_lead,
    require_chapter,
    chapter_structure,
    chapter_edit,
    chapter_permissions,
    project_permissions,
    public_team,
)
from icg_demo.outline_service import OutlinePlanService, OutlinePlanError, infer_chapter_type
from icg_demo.answer_card import AnswerCardService
from icg_demo.tender_retrieval import TenderRetrievalService
from icg_demo.editor_ai_context import build_editor_prompt_context
from icg_demo.parsing import LocalTextParser
from icg_demo.idempotency import lookup, remember
from icg.infra.repositories.chapters import decompose_paragraphs

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def chapter_export_block(title: str, body: str) -> str:
    # 分册里的章节名要成为一级标题，正文仍按原行保留。
    return f"# {title}\n{body}"

SHANGHAI = timezone(timedelta(hours=8))
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

class CheckBlockerError(DomainError):
    def __init__(self, message: str, details: dict | None = None):
        self.status = 400
        self.code = "CHECK_BLOCKER_EXISTS"
        self.message = message
        self.details = details or {}
        Exception.__init__(self, message)


class ExportServiceMixin:
    @staticmethod
    def _date(value: str) -> date:
        try:
            return date.fromisoformat(value) if len(value) == 10 else ExportServiceMixin._instant(value).astimezone(SHANGHAI).date()
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
    def _is_critical_requirement(row: dict) -> bool:
        text = str(row.get("text", "") or "")
        is_disqual = bool(
            row.get("is_disqualification") is True
            or row.get("category") == "disqualification"
            or "废标" in text
            or "否决" in text
        )
        is_star = bool(
            row.get("importance") == "star"
            or row.get("category") == "star"
            or "★" in text
            or "标星" in text
        )
        return is_disqual or is_star

    @staticmethod
    def _issue(code, message, severity="blocking", **links):
        return {"id": new_id("issue"), "code": code, "severity": severity, "message": message, **links}

    def run_check(self, principal, project_id, payload, expected, key):
        def operation(state, project, workflow):
            volume = payload.get("volume", "all")
            issues = []
            add = lambda code, message, severity="blocking", **links: issues.append(self._issue(code, message, severity=severity, **links))
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
                is_crit = self._is_critical_requirement(row)
                crit_sev = "blocker" if is_crit else "blocking"

                if row["status"] == "pending":
                    add("REQUIREMENT_PENDING", "条款尚待确认：" + row["text"][:60], severity=crit_sev, **links)
                if row["status"] == "rejected":
                    if not row["reason"].strip():
                        add("REJECTION_REASON_MISSING", "忽略条款没有理由。", **links)
                    continue
                if row["reference_status"] == "unresolved":
                    add("REFERENCE_UNRESOLVED", "条款引用尚未人工核对。", **links)
                chapter = state.chapters.get(row["chapter_id"] or "")
                if chapter is None or chapter.project_id != project_id or chapter.volume != row["volume"]:
                    add("MATRIX_MAPPING_MISSING", "条款没有映射到本分册有效章节。", severity=crit_sev, **links)
                if not row["response"].strip() or "待补" in row["response"]:
                    add("MATRIX_RESPONSE_MISSING", "条款响应为空或仍有待补。", severity=crit_sev, **links)
                elif chapter is not None:
                    if not chapter.content.strip():
                        add("CHAPTER_CONTENT_EMPTY", "条款映射章节正文为空：" + chapter.title, severity=crit_sev, chapter_id=chapter.id, **links)
                    elif "待补" in chapter.content:
                        add("CHAPTER_CONTENT_PENDING", "条款映射章节正文仍有待补：" + chapter.title, severity=crit_sev, chapter_id=chapter.id, **links)

                need_evidence = any(word in row["text"] for word in ("资质", "证书", "证明", "业绩", "授权")) or row.get("need_evidence") is True
                if need_evidence and not row["evidence_ids"]:
                    add("EVIDENCE_MISSING", "证明类条款缺少已确认的企业证据。", severity=crit_sev, **links)
                for evidence_id in row["evidence_ids"]:
                    evidence = state.library.get(evidence_id)
                    if (evidence is None or evidence["company_id"] != project.company_id
                            or evidence["status"] != "confirmed" or evidence["type"] == "history"):
                        add("EVIDENCE_NOT_USABLE", "条款引用的证据已失效或不能作为证据。", severity=crit_sev, evidence_id=evidence_id, **links)
                        continue
                    today = datetime.fromtimestamp(self.demo._now(), SHANGHAI).date()
                    if evidence_expired(evidence, project.deadline, today=today):
                        add("EVIDENCE_EXPIRED", "证据不能覆盖投标截止时间。", severity=crit_sev, evidence_id=evidence_id, **links)
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
            from icg.domain.compliance_rules import ComplianceRulesEngine
            rule_results = ComplianceRulesEngine.evaluate_p0_rules(
                state, project, workflow, volume=volume, now_ts=self.demo._now()
            )
            for r in rule_results:
                for rule_issue in r.issues:
                    is_dup = any(
                        existing.get("code") == rule_issue.get("code")
                        and existing.get("requirement_id") == rule_issue.get("requirement_id")
                        and existing.get("chapter_id") == rule_issue.get("chapter_id")
                        for existing in issues
                    )
                    if not is_dup:
                        issues.append(rule_issue)
                    else:
                        for existing in issues:
                            if (
                                existing.get("code") == rule_issue.get("code")
                                and existing.get("requirement_id") == rule_issue.get("requirement_id")
                                and existing.get("chapter_id") == rule_issue.get("chapter_id")
                            ):
                                existing["rule_id"] = r.rule_id
            check = {"id": new_id("project-check"), "volume": volume, "passed": not issues,
                     "status": "failed" if issues else "passed", "issues": issues,
                     "rules": [r.to_dict() for r in rule_results],
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

            check_issues = check.get("issues", [])
            has_blockers = any(i.get("severity") == "blocker" for i in check_issues)

            if payload.get("kind") == "submission" and has_blockers:
                raise CheckBlockerError("分册最新检查结果存在未解决的废标或星号条款阻断项，无法导出正式递交版。")

            scope = payload.get("volume", "all")
            required_volumes = set(VOLUMES) if scope == "all" else {scope}

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

            is_internal_review = payload.get("kind") == "internal_review"
            if not is_internal_review and not check["passed"]:
                raise DomainError(409, "CHECK_FAILED", "当前已实现的流程检查仍有阻断项。")

            if check["volume"] != scope:
                raise DomainError(409, "ALL_VOLUMES_CHECK_REQUIRED", "导出范围必须和已完成的检查一致；两册导出需要检查全部分册。")
            chapters = self._ordered_chapters(state, project_id, workflow)
            chapters = [c for c in chapters if scope == "all" or c.volume == scope]
            if {c.volume for c in chapters} != required_volumes:
                raise DomainError(422, "TWO_VOLUMES_REQUIRED", "导出必须包含技术和商务两册。")
            identity = new_id("project-export")
            documents, volumes = {}, []
            for volume, name in (("technical", "技术分册"), ("business", "商务分册")):
                if volume not in required_volumes:
                    continue
                selected = [c for c in chapters if c.volume == volume]
                filename = f"icg-{volume}-{identity}.docx"
                doc_title = self._mask(project.name) + " — " + name
                doc_content = "\n\n".join(chapter_export_block(self._mask(c.title), self._mask(resolve_fact_variables(state, project_id, c.content))) for c in selected)
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
                })
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
            }
            workflow["exports"][identity] = record
            if payload.get("kind") == "submission":
                job_desc = ("两个独立 Word 正式递交版已生成" if scope == "all" else "本册 Word 正式递交版已生成") + "；已完成责任人定稿与门禁核验。"
            else:
                job_desc = ("两个独立 Word 内部稿已生成" if scope == "all" else "本册 Word 内部稿已生成") + "；只含已提交正文。"
            self._job(state, project_id, "export", job_desc)
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


class ExportService(ExportServiceMixin):
    def __init__(self, workflow=None):
        self._workflow = workflow
