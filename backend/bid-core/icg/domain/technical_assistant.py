"""技术服务方案写作助手：按节取上下文、按节改写候选、写入前约束检查。"""
from __future__ import annotations

from typing import Any

from icg.domain.domain import DomainError

REWRITE_RULES = (
    "只改本节正文，保留编号、标题与引用标记。不虚构能力、参数或资质；没有依据写【待确认】。"
    "不得违反废标清单，不得放宽本节硬约束。"
)


def section_heading(workflow: dict, title: str) -> dict | None:
    from icg.domain.technical_volume import _leaves, select_section

    hits = select_section(_leaves(workflow.get("technical_outline") or {}), (title or "").strip())
    return hits[0] if hits else None


def section_context(workflow: dict, title: str) -> dict[str, Any] | None:
    """本节挂载要点、要求编号、评分标准与全部废标条件。不是确认目录里的叶子节返回 None。"""
    from icg.domain.technical_digest import rejection_lines, scoring_criteria
    from icg.domain.technical_volume import _clauses, _requirement_ids, _section_points

    heading = section_heading(workflow, title)
    if heading is None:
        return None
    task = (workflow.get("response_tasks") or {}).get(heading.get("task_id") or "")
    rows = {row.get("id"): row for row in _clauses(workflow)}
    req_ids = list((task or {}).get("requirement_ids") or heading.get("requirement_ids") or [])
    if not req_ids and heading.get("requirement_id"):
        req_ids = [heading["requirement_id"]]
    req_rows = [rows[rid] for rid in req_ids if rid in rows]
    return {
        "heading": heading,
        "task": task,
        "rows": req_rows,
        "ids": _requirement_ids(req_rows, task),
        "points": _section_points(heading.get("title") or "", task, workflow),
        "criteria": scoring_criteria(req_rows),
        "rejections": rejection_lines(workflow),
    }


def context_block(context: dict) -> str:
    def block(lines: list[str]) -> str:
        return "\n".join(f"- {line}" for line in lines) if lines else "（无）"

    return "\n".join([
        f"【本节】{context['heading'].get('number') or ''} {context['heading'].get('title') or ''}".strip(),
        "【挂载要点】", block(context["points"]),
        "【评分标准】", block(context["criteria"]),
        "【废标清单（不得违反）】", block(context["rejections"]),
    ])


def splice_section(content: str, number: str, title: str, body: str) -> str:
    """把一节正文换成 body；标题行与其他节不动。找不到标题时报 409。"""
    from icg.domain.technical_volume import HEADING

    lines = (content or "").splitlines()
    marker = f"{number} {title}".strip()
    start = next((index + 1 for index, line in enumerate(lines) if line.strip() == marker), None)
    if start is None:
        raise DomainError(409, "REVISION_CONFLICT", "正文里找不到这一节的标题，请刷新后重试。")
    end = next((index for index in range(start, len(lines)) if HEADING.match(lines[index].strip())), len(lines))
    tail = [""] if end < len(lines) else []
    merged = [*lines[:start], *body.strip().splitlines(), *tail, *lines[end:]]
    return "\n".join(merged).rstrip("\n") + "\n"


def precheck(workflow: dict, context: dict, body: str, content: str = "") -> dict[str, Any]:
    """候选写入前跑废标约束检查：全部小节一起检查（本节换成候选），挂在别处的硬约束也算。"""
    from icg.domain.technical_constraint_check import evaluate_volume
    from icg.domain.technical_volume import _clauses, _leaf_key, _leaves, section_body

    rows = {row.get("id"): row for row in _clauses(workflow)}
    tasks = workflow.get("response_tasks") or {}
    target = _leaf_key(context["heading"])
    sections = []
    for item in _leaves(workflow.get("technical_outline") or {}):
        key = _leaf_key(item)
        task = tasks.get(item.get("task_id") or "")
        ids = list((task or {}).get("requirement_ids") or item.get("requirement_ids") or [])
        if not ids and item.get("requirement_id"):
            ids = [item["requirement_id"]]
        text = body if key == target else section_body(content, item.get("number") or "", item.get("title") or "")
        sections.append({"key": key, "title": item.get("title") or "", "body": text,
                         "task": task if isinstance(task, dict) else None, "rows": [rows[i] for i in ids if i in rows]})
    result = evaluate_volume(workflow, sections)
    view = (result.get("sections") or {}).get(target) or {}
    return {
        "status": view.get("status") or "passed",
        "missing": [item.get("text") or "" for item in view.get("missing") or []],
        "conflicts": [item.get("text") or item.get("message") or "" for item in view.get("conflicts") or []],
        "notice": view.get("notice") or "",
    }


def _sources(chunks: list[dict]) -> list[dict]:
    return [{
        "name": str(chunk.get("name") or chunk.get("document_name") or "")[:120],
        "dataset_kind": str(chunk.get("dataset_kind") or ""),
        "score": round(float(chunk.get("score") or 0), 4),
    } for chunk in chunks[:5]]


class TechnicalSectionAssistant:
    def __init__(self, demo: Any, rewrite: Any = None) -> None:
        self.demo = demo
        self.selection = rewrite

    def rewrite(self, principal: Any, project_id: str, payload: dict) -> dict:
        from icg.domain.input_snapshot import project_input_fingerprint
        from icg.domain.technical_rag import knowledge_prompt_block, rag_summary, retrieve_for_section, section_query
        from icg.domain.technical_volume import SECTION_SYSTEM, section_body, strip_model_thinking
        from icg.infra.openai_model import SECTION_CALL, AuditIoLabel, call_with_profile

        section = (payload.get("section") or "").strip()
        instruction = (payload.get("instruction") or "").strip()
        if not section or not instruction:
            raise DomainError(422, "VALIDATION_ERROR", "请选择小节并填写修改要求。")
        state = self.demo.repository.read()
        project = self.demo._project(state, principal, project_id)
        if self.selection is not None and not self.selection._policy(state, project.company_id)["enabled"]:
            raise DomainError(403, "FORBIDDEN", "本公司已关闭对话助手。")
        workflow = state.workflows.get(project_id) or {}
        outline = workflow.get("technical_outline") or {}
        chapter = state.chapters.get(outline.get("chapter_id") or "")
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "没有服务方案这一章。")
        self.demo._chapter_writer(state, principal, chapter)
        context = section_context(workflow, section)
        if context is None:
            raise DomainError(404, "NOT_FOUND", "没有这一节。")
        title = context["heading"].get("title") or ""
        original = section_body(chapter.content or "", context["heading"].get("number") or "", title)
        if not original.strip():
            raise DomainError(409, "REQUIREMENT_NOT_READY", "本节还没有正文，请先生成。")
        self.demo.require_allowed_model(project, state=state)
        provider = self.demo.resolve_model_provider(state, project_id, "chapter_generation")
        if not getattr(provider, "is_real_model", False):
            raise DomainError(502, "MODEL_UNAVAILABLE", "尚未接入真实大模型：写作助手不提供模拟修改。")
        fingerprint = project_input_fingerprint(state, project_id)
        base_revision = chapter.revision
        query = section_query(title, points=context["points"][:2])
        chunks, audit = retrieve_for_section(getattr(self.demo, "knowledge_base", None), project.company_id, query, workflow)
        user = "\n".join([
            context_block(context),
            "【知识库】", knowledge_prompt_block(chunks, workflow) or "（无命中）",
            "【当前正文】", original,
            "【修改要求】", instruction,
            "【规则】", REWRITE_RULES,
            "只输出修改后的本节正文，不输出标题。",
        ])
        try:
            with AuditIoLabel("SECTION"):
                body = strip_model_thinking(call_with_profile(provider.suggest, SECTION_SYSTEM, user, profile=SECTION_CALL))
        except DomainError:
            raise
        except Exception as error:
            raise DomainError(502, "MODEL_UNAVAILABLE", "本节修改失败，正文没有改动，可重试。") from error
        if len(body.strip()) < 20:
            raise DomainError(502, "MODEL_UNAVAILABLE", "模型返回的本节正文不完整，正文没有改动，可重试。")
        current = self.demo.repository.read()
        latest = current.chapters.get(chapter.id)
        if latest is None or latest.revision != base_revision or project_input_fingerprint(current, project_id) != fingerprint:
            raise DomainError(409, "VERSION_CONFLICT", "正文或项目资料在修改期间更新，请重新请求。")
        number = context["heading"].get("number") or ""
        return {
            "content": splice_section(latest.content or "", number, title, body),
            "section": title,
            "section_body": body.strip(),
            "original_body": original,
            "base_revision": base_revision,
            "input_fingerprint": fingerprint,
            "provider": getattr(provider, "name", "model"),
            "is_real_model": True,
            "source_scope": "section",
            "rag": rag_summary(audit),
            "sources": _sources(chunks),
            "precheck": precheck(workflow, context, body, latest.content or ""),
        }
