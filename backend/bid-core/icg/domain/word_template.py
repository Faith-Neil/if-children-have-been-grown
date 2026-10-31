# 为什么有这个文件：公司 Word 模板的保存与导出取用（PRD v1.8 §5.6.1、§5.6.2 写作档案“Word 模板”、§5.9.1 规则 1；
# 权限矩阵“公司写作档案、Word 模板”只有公司管理员可改；APP-M2-T086、T196）。
# 它解决什么问题：
# 1. 每家公司一份当前 Word 模板：原件按内容摘要存文件存储，读出的样式与“读到 / 沿用默认”说明存公司级数据；
# 2. 换模板只影响之后的导出；已导出的批次是快照，不受影响；
# 3. 导出时可选“本公司 Word 模板”或“平台默认模板”，所用模板的文件名与摘要记进导出批次，便于追查；
# 4. 只读取样式，不复制模板里的属性、批注、宏和正文，导出文件不带模板残留。

from __future__ import annotations

from typing import Any

from .domain import DemoState, DomainError, Principal, iso_time, new_id

STORE = "word_templates"


def _can_read(principal: Principal, company_id: str) -> None:
    from .auth_service import is_super_admin
    if not is_super_admin(principal.user) and principal.user.company_id != company_id:
        raise DomainError(404, "NOT_FOUND", "未找到该公司或当前账号无权访问。")


def _can_write(principal: Principal, company_id: str) -> None:
    from .auth_service import is_super_admin
    from .project_access import normalize_role
    _can_read(principal, company_id)
    if not is_super_admin(principal.user) and normalize_role(principal.user.role) != "company_admin":
        raise DomainError(403, "FORBIDDEN", "只有公司管理员可以上传或删除公司 Word 模板。")


def current(state: DemoState, company_id: str) -> dict | None:
    return (state.service_stores.get(STORE) or {}).get(company_id)


def public(record: dict | None) -> dict:
    if record is None:
        return {"template": None}
    keys = ("id", "filename", "sha256", "size_bytes", "uploaded_by", "uploaded_at", "applied", "defaults")
    return {"template": {k: record[k] for k in keys}}


def export_style(state: DemoState, company_id: str, choice: str) -> tuple[dict | None, dict]:
    """导出用样式：auto 有公司模板就用、没有用平台默认；company 没有模板时报错；platform 固定平台默认。"""
    record = current(state, company_id)
    if choice == "company" and record is None:
        raise DomainError(409, "WORD_TEMPLATE_MISSING", "本公司还没有上传 Word 模板，请先在企业设置里上传，或改用平台默认模板。")
    if choice == "platform" or record is None:
        return None, {"source": "platform", "filename": None, "sha256": None}
    return record["style"], {"source": "company", "filename": record["filename"], "sha256": record["sha256"]}


class WordTemplateService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def get(self, principal: Principal, company_id: str) -> dict:
        _can_read(principal, company_id)
        return public(current(self.demo.repository.read(), company_id))

    def upload(self, principal: Principal, company_id: str, filename: str, data: bytes) -> dict:
        from icg.infra.blob_store import put_blob
        from icg.infra.docx_template import TemplateError, parse_template, style_to_dict
        _can_write(principal, company_id)
        if not filename.lower().endswith(".docx"):
            raise DomainError(422, "WORD_TEMPLATE_INVALID", "Word 模板只接受 .docx 文件（.doc、.dotx、.docm 请先另存为 .docx）。")
        try:
            style, applied, defaults = parse_template(data)
        except TemplateError as error:
            raise DomainError(422, "WORD_TEMPLATE_INVALID", str(error)) from error
        import hashlib
        digest = put_blob(data)
        record = {"id": new_id("word-template"), "filename": filename, "blob": digest,
                  "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "uploaded_by": principal.user.id,
                  "uploaded_at": iso_time(self.demo._now()), "style": style_to_dict(style),
                  "applied": applied, "defaults": defaults}

        def write(state: DemoState):
            previous = current(state, company_id)
            state.service_stores.setdefault(STORE, {})[company_id] = record
            state.audit.append({"id": new_id("event"), "action": "word_template.upload", "actor_id": principal.user.id,
                                "company_id": company_id, "at": record["uploaded_at"],
                                "details": {"filename": filename, "sha256": record["sha256"],
                                            "replaced": previous["sha256"] if previous else None}})
            return public(record)
        return self.demo.repository.transaction(write)

    def delete(self, principal: Principal, company_id: str) -> dict:
        _can_write(principal, company_id)

        def write(state: DemoState):
            previous = (state.service_stores.get(STORE) or {}).pop(company_id, None)
            if previous is None:
                raise DomainError(404, "NOT_FOUND", "本公司没有已上传的 Word 模板。")
            state.audit.append({"id": new_id("event"), "action": "word_template.delete", "actor_id": principal.user.id,
                                "company_id": company_id, "at": iso_time(self.demo._now()),
                                "details": {"filename": previous["filename"], "sha256": previous["sha256"]}})
            return public(None)
        return self.demo.repository.transaction(write)

    def original(self, principal: Principal, company_id: str) -> tuple[str, bytes]:
        from icg.infra.blob_store import get_blob
        _can_read(principal, company_id)
        record = current(self.demo.repository.read(), company_id)
        if record is None:
            raise DomainError(404, "NOT_FOUND", "本公司没有已上传的 Word 模板。")
        return record["filename"], get_blob(record["blob"])
