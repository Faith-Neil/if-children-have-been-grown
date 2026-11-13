# 为什么有这个文件：技术分册项目只收招标文件、技术规范书和其他辅助文件。
# 它解决什么问题：文件类型、格式和“同一批文件不能再抽”集中在一处，两册旧项目仍走原来的上传规则。

from __future__ import annotations

import hashlib
import json
from typing import Any

from icg.domain.domain import DomainError

TECHNICAL_ROLES = {
    "tender": "招标文件",
    "tech_spec": "技术规范书",
    "attachment": "其他辅助文件",
}
TECHNICAL_SUFFIXES = {".pdf", ".doc", ".docx"}


def technical_only(state: Any, project_id: str) -> bool:
    from icg.domain.project_access import project_volume_mode
    return project_volume_mode(state, project_id) == "technical_only"


def guard_technical_upload(state: Any, project_id: str, suffix: str, role: str) -> None:
    """技术分册只接受 pdf、doc、docx，以及招标文件、技术规范书、其他辅助文件。"""
    if not technical_only(state, project_id):
        return
    if suffix not in TECHNICAL_SUFFIXES:
        raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "技术分册只接受 pdf、doc、docx。图纸请转成 pdf 后再上传。")
    if role not in TECHNICAL_ROLES:
        raise DomainError(422, "VALIDATION_ERROR", "技术分册的文件类型只能是招标文件、技术规范书或其他辅助文件。",
                          {"fields": {"file_role": "invalid"}})


def source_fingerprint(workflow: dict) -> str:
    """当前仍有效的文件集合。增删或改类型后指纹会变。"""
    from icg.domain.tender_files import role, superseded
    rows = sorted(
        (record["id"], record.get("sha256") or "", role(record))
        for record in (workflow.get("files") or {}).values()
        if not superseded(record)
    )
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()


def assert_can_extract(state: Any, project_id: str, workflow: dict) -> None:
    if not technical_only(state, project_id):
        return
    from icg.domain.tender_files import role, superseded
    files = [record for record in (workflow.get("files") or {}).values() if not superseded(record)]
    if not any(role(record) == "tender" for record in files):
        raise DomainError(422, "FILES_REQUIRED", "技术分册必须先上传一份招标文件。")
    saved = workflow.get("parsed_source_fingerprint") or ""
    if saved and saved == source_fingerprint(workflow) and not _layout_missing(workflow) and not _remote_in_progress(workflow):
        raise DomainError(409, "SAME_SOURCE_FILES", "这批文件已经抽取过。请先增加、替换或删除文件，再重新抽取。")


def _layout_missing(workflow: dict) -> bool:
    """上次解析没有版面位置时允许再抽取。Word 直接进 RAGFlow 会出现这种情况。"""
    from icg.domain.tender_files import superseded
    for record in (workflow.get("files") or {}).values():
        if superseded(record):
            continue
        if any("未返回版面位置" in str(item) for item in (record.get("warnings") or [])):
            return True
    return False


def _remote_in_progress(workflow: dict) -> bool:
    """RAGFlow 还在识别时，下一次解析是接着取结果，不是同一批文件的重复抽取。"""
    from icg.domain.tender_files import superseded
    return any(
        not superseded(record) and record.get("status") == "parsing_remote"
        for record in (workflow.get("files") or {}).values()
    )


def remember_parsed_sources(workflow: dict) -> None:
    workflow["parsed_source_fingerprint"] = source_fingerprint(workflow)


def invalidate_after_file_change(state: Any, project_id: str, workflow: dict) -> None:
    """文件变动后取消目录确认和矩阵确认。已有正文保留，有字的章节标成需要重新生成。"""
    if not technical_only(state, project_id):
        return
    workflow["parse_confirmed"] = False
    workflow["plan_confirmed"] = False
    for row in (workflow.get("requirements") or {}).values():
        row["volume_confirmed_by"] = None
        row["volume_confirmed_at"] = None
    workflow.pop("technical_extract_empty", None)
    workflow["needs_regeneration"] = sorted(
        chapter.id for chapter in state.chapters.values()
        if chapter.project_id == project_id and (chapter.content or "").strip()
    )
