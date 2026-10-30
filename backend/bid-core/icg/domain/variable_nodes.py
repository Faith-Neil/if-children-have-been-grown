# 为什么有这个文件：编辑台的变量节点（APP-M2-T164，PRD v1.8 §5.11.2 正文编辑区“变量带底色”、§5.7.3 规则 7）。
# 它解决什么问题：
# 1. 正文里的 {{fact:…}} / {{sla:…}} 变量按当前已确认的取值显示；身份证号、手机号、银行账号这类取值显示掩码（与导出同一套掩码）。
# 2. 不存在、未确认、来源失效、单位对不上的变量标为失效，并指明去哪个数据源改（项目事实表 / 服务承诺矩阵）。
# 3. 提交正文与版本回退时，后台拒绝新写入的失效变量（409）；正文里原有、之后才失效的变量不挡提交，由检查拦截导出。
# 取值只在数据源里改：编辑台不提供改变量取值的入口。

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .domain import DemoState, DomainError, Principal

FACT = re.compile(r"\{\{fact:([A-Za-z0-9_.:-]+)\}\}")
SLA = re.compile(r"\{\{\s*sla:([A-Za-z0-9_.-]+)\s*\}\}")
# 残缺写法：{{fact: / {{ sla : 开头但不是完整变量
BROKEN = re.compile(r"\{\{\s*(fact|sla)\s*:[^{}\n]{0,120}\}?\}?")
TAIL = 12  # 变量后面参与单位核对的字符数


def _mask(text: str) -> str:
    from .export_service import ExportServiceMixin
    return ExportServiceMixin._mask(text)


def _line_of(content: str, offset: int) -> int:
    return content.count("\n", 0, offset)


def nodes(state: DemoState, project_id: str, content: str) -> list[dict]:
    """正文中每个变量出现处一条：位置、当前显示值（或掩码）、是否有效、失效原因、去哪个数据源改。"""
    from .generation_context import project_facts, resolve_fact_variables
    from .sla import public_sla
    facts = {fact["id"]: fact for fact in project_facts(state, project_id)}
    sla = public_sla(state, project_id)
    rows = {row["var_key"]: row for row in sla["rows"]} if sla else {}
    out: list[dict] = []
    spans: list[tuple[int, int]] = []
    for kind, pattern in (("fact", FACT), ("sla", SLA)):
        for match in pattern.finditer(content):
            ref = match.group(1)
            token = match.group(0)
            spans.append(match.span())
            known = facts.get(ref) if kind == "fact" else rows.get(ref)
            label = (known.get("key") if kind == "fact" else known.get("label")) if known else ref
            node = {"token": token, "kind": kind, "ref": ref, "label": label or ref,
                    "start": match.start(), "end": match.end(), "line": _line_of(content, match.start()),
                    "source": "facts" if kind == "fact" and not (known or {}).get("sla_var_key") else "matrix",
                    "display": "", "masked": False, "status": "valid", "code": None, "message": ""}
            if known is None:
                node.update(status="unknown", code="FACT_VARIABLE_INVALID" if kind == "fact" else "SLA_VARIABLE_UNKNOWN",
                            message="数据源里没有这个变量" if kind == "fact" else "服务承诺矩阵里没有这个变量")
                out.append(node)
                continue
            tail = content[match.end():match.end() + TAIL].split("\n", 1)[0].split("{{", 1)[0]
            try:
                resolve_fact_variables(state, project_id, token + tail)
                display = resolve_fact_variables(state, project_id, token)
            except DomainError as error:
                node.update(status="invalid", code=error.code, message=error.message)
                out.append(node)
                continue
            shown = _mask(display)
            node.update(display=shown, masked=shown != display)
            out.append(node)
    for match in BROKEN.finditer(content):
        if any(start <= match.start() < end for start, end in spans):
            continue
        kind = match.group(1)
        out.append({"token": match.group(0), "kind": kind, "ref": "", "label": "格式不完整",
                    "start": match.start(), "end": match.end(), "line": _line_of(content, match.start()),
                    "source": "facts" if kind == "fact" else "matrix", "display": "", "masked": False,
                    "status": "unknown", "code": "FACT_VARIABLE_INVALID" if kind == "fact" else "SLA_VARIABLE_UNKNOWN",
                    "message": "变量格式不完整，请从数据源重新插入"})
    return sorted(out, key=lambda item: item["start"])


def refuse_new_invalid(state: DemoState, chapter: Any, new_content: str) -> None:
    """写入前核对：本次新写入的变量必须有效。原正文已有的同一失效变量不挡提交（由检查拦截导出）。"""
    if "{{" not in new_content:
        return
    bad = [n for n in nodes(state, chapter.project_id, new_content) if n["status"] != "valid"]
    if not bad:
        return
    existing = Counter(n["token"] for n in nodes(state, chapter.project_id, chapter.content or "") if n["status"] != "valid")
    fresh = []
    for node in bad:
        if existing.get(node["token"]):
            existing[node["token"]] -= 1
        else:
            fresh.append(node)
    if not fresh:
        return
    first = fresh[0]
    names = "、".join(dict.fromkeys(n["label"] for n in fresh))
    raise DomainError(409, first["code"],
                      f"本次修改写入了 {len(fresh)} 个失效变量（{names}）：{first['message']}。请到数据源核对后从“插入变量”重新插入。",
                      {"variables": [{k: n[k] for k in ("token", "kind", "ref", "label", "line", "status", "code", "message", "source")}
                                     for n in fresh]})


class VariableNodeService:
    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def resolve(self, principal: Principal, project_id: str, chapter_id: str, content: str | None) -> dict:
        state = self.demo.repository.read()
        chapter = self.demo._chapter(state, principal, chapter_id)
        if chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")
        text = (chapter.content or "") if content is None else content
        items = nodes(state, project_id, text)
        return {"chapter_id": chapter_id, "revision": chapter.revision, "variables": items,
                "invalid": sum(1 for n in items if n["status"] != "valid")}
