# 为什么有这个文件：实现大纲写作计划输入组装（APP-M2-T124）与逐节确认启动章节生成（APP-M2-T126）。
# 它解决什么问题：
# 1. 写作方案输入上下文组装（APP-M2-T124）：将各章节得分要点小标题、已关联的公司证据版本（含 [证] 标记）、RAGFlow 候选切片（含 [片] 溯源）、项目可用事实及 SLA 变量组装为标准模型 Prompt 写作计划，包含字数预期、事实变量不可篡改约束及 [证] 引用标记规范；
# 2. 逐节确认启动生成（APP-M2-T126）：落地 start_chapter_generation(project_id, chapter_id, principal)，按逐节确认结果独立启动已确认章节的生成任务，未确认分册或未确认章节绝对不阻塞已确认章节的独立启动；未确认方案的章节企图启动生成前置抛出 400 PLAN_NOT_CONFIRMED；
# 3. 异步任务与进度流转：在 demo_job 中创建异步任务（job_type="generate_chapter", status="running", progress=0），并与 JobProgress 进度流转对接；
# 4. 敏感项目本地模型强门禁：敏感项目强制使用本地模型配置，企图使用云端模型抛出 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。

from __future__ import annotations

import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .domain import Chapter, DemoState, DomainError, Principal, Project, iso_time, new_id
from .generation_context import (
    build_generation_context,
    chapter_plan,
    plan_is_current,
    project_facts,
    project_input_fingerprint,
    refuse_source_change,
    require_ready,
    validate_model_output,
    writing_source_fingerprint,
)
from .project_access import (
    READONLY_SYSTEM_ROLES,
    ROLE_NORMALIZATION_MAP,
    writable,
)
from .prompt_budget import (
    DEFAULT_MAX_CONTEXT_TOKENS,
    DynamicPromptContextManager,
    check_sensitive_model_gate,
)

VARIABLE_PATTERN = re.compile(r"\{\{([A-Za-z0-9_.:\u4e00-\u9fa5-]+)\}\}")
CITATION_PATTERN = re.compile(r"\[(证|片|cite)(?::([^\]]+))?\]")


def parse_scoring_points(writing_points: str | list[str] | None) -> list[str]:
    """解析章节写作计划中的评分要点清单。"""
    if not writing_points:
        return []
    items = writing_points if isinstance(writing_points, list) else str(writing_points).split("\n")
    points = []
    for item in items:
        line = str(item).strip()
        if not line:
            continue
        cleaned = re.sub(r"^[0-9]+[、.．\s-]+\s*", "", line).strip()
        if cleaned:
            points.append(cleaned)
    return points


def extract_paragraph_citations(
    text: str,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """提取段落内的 [证:xxx] 与 [片:xxx] 引用标记，并校验是否在有效依据范围内。"""
    citations = []
    for match in CITATION_PATTERN.finditer(text):
        tag_type = match.group(1)
        ref_id = (match.group(2) or "").strip()
        full_tag = match.group(0)
        cit_type = "evidence" if tag_type == "证" else ("snippet" if tag_type == "片" else "cite")

        is_valid = True
        if ref_id:
            if cit_type == "evidence" and allowed_evidence_ids is not None:
                is_valid = ref_id in allowed_evidence_ids
            elif cit_type == "snippet" and allowed_snippet_ids is not None:
                is_valid = ref_id in allowed_snippet_ids

        citations.append({
            "tag": full_tag,
            "type": cit_type,
            "id": ref_id,
            "valid": is_valid,
        })
    return citations


def parse_structured_paragraphs(
    raw_content: str,
    scoring_points: str | list[str] | None = None,
    allowed_evidence_ids: set[str] | None = None,
    allowed_snippet_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """将大模型生成的正文解析为带有 [P1]~[Pn] 编号、小标题与引用绑定的结构化段落列表。"""
    if not raw_content or not raw_content.strip():
        return []

    parsed_points = parse_scoring_points(scoring_points)
    lines = raw_content.strip().split("\n")

    paragraphs: list[dict[str, Any]] = []
    current_subheading: str | None = None
    current_title: str | None = None
    current_scoring_point: str | None = None
    accumulated_lines: list[str] = []

    def flush_paragraph():
        nonlocal accumulated_lines, current_subheading, current_title, current_scoring_point
        if not accumulated_lines:
            return
        p_text = " ".join(l.strip() for l in accumulated_lines if l.strip()).strip()
        accumulated_lines = []
        if not p_text:
            return

        order = len(paragraphs) + 1
        label = f"[P{order}]"

        m_label = re.match(r"^\[P(\d+)\]\s*(.*)", p_text, re.DOTALL)
        if m_label:
            clean_text = m_label.group(2).strip()
            label = f"[P{order}]"
        else:
            clean_text = p_text

        subhead = current_subheading
        title = current_title
        sc_point = current_scoring_point
        if not subhead and parsed_points:
            sp_idx = min(order - 1, len(parsed_points) - 1)
            sc_point = parsed_points[sp_idx]
            subhead = f"### 1.{sp_idx + 1} {sc_point}"
            title = sc_point

        citations = extract_paragraph_citations(clean_text, allowed_evidence_ids, allowed_snippet_ids)
        variables = [m.group(1) for m in VARIABLE_PATTERN.finditer(clean_text)]

        paragraphs.append({
            "id": f"p-{order}",
            "paragraph_id": f"p-{order}",
            "order": order,
            "label": label,
            "subheading": subhead,
            "title": title,
            "text": clean_text,
            "content": f"{label} {clean_text}",
            "citations": citations,
            "scoring_point": sc_point,
            "variables": variables,
            "char_length": len(clean_text),
        })

    heading_pattern = re.compile(r"^(#{1,6})\s*(.+)$")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue

        h_match = heading_pattern.match(stripped)
        if h_match:
            flush_paragraph()
            current_subheading = stripped
            raw_title = h_match.group(2).strip()
            current_title = re.sub(r"^[0-9]+[、.．\s-]+\s*", "", raw_title).strip()
            current_scoring_point = None
            if parsed_points:
                for sp in parsed_points:
                    if sp in current_title or current_title in sp:
                        current_scoring_point = sp
                        break
                if not current_scoring_point and parsed_points:
                    sp_idx = min(len(paragraphs), len(parsed_points) - 1)
                    current_scoring_point = parsed_points[sp_idx]
            continue

        if re.match(r"^\[P\d+\]", stripped):
            flush_paragraph()

        accumulated_lines.append(stripped)

    flush_paragraph()
    return paragraphs


def format_structured_chapter_content(paragraphs: list[dict[str, Any]]) -> str:
    """将结构化段落列表格式化为标准 Markdown 章节正文。"""
    if not paragraphs:
        return ""

    blocks = []
    emitted_subheadings = set()

    for p in paragraphs:
        subheading = p.get("subheading")
        if subheading and subheading not in emitted_subheadings:
            blocks.append(subheading)
            emitted_subheadings.add(subheading)

        blocks.append(p.get("content") or f"{p.get('label', '')} {p.get('text', '')}".strip())

    return "\n\n".join(blocks).strip()


def format_writing_plan_prompt(snapshot: dict) -> str:
    """将写作方案快照渲染为大模型 Prompt 写作计划文本（APP-M2-T124）。"""
    chapter = snapshot["chapter"]
    plan = snapshot["plan"]
    project = snapshot["project"]

    lines = [
        "【章节与分册目标】",
        f"章节：{chapter['title']}（分册：{chapter['volume']}）",
        f"项目：{project['name']}",
        "提示：本生成内容为待人工核对的草稿候选，不会自动成为正式承诺。",
        "",
        "【得分要点小标题与写作计划】",
        f"{plan.get('writing_points') or '未指定小标题与写作要点'}",
        "",
        "【字数预期】",
        f"目标字数：{plan.get('target_length') or '未限制'} 字（供人工审核参考）",
        "",
        "【事实约束规范】",
        "1. 正文引用事实必须保留变量标记（如 {{fact:xxx}} 或 {{sla:xxx}}），严禁修改取值或将变量替换为手写文字；",
        "2. 严禁私自修改事实来源取值，若有差异需在响应矩阵中修正；",
        "",
        "【证据引用规范】",
        "1. 必须使用 [证] 或 [证:编号] 标记引用已核对的公司资质、证书或业绩，严禁捏造未核对的公司证明；",
        "2. [片] 检索切片仅供写作方案参考，不得作为正式附着证据；",
        "",
    ]

    # 招标文件条款
    reqs = snapshot.get("requirements", [])
    if reqs:
        lines.append("【招标文件条款与响应要求】")
        for req in reqs:
            lines.append(f"• 条款：{req['text']}")
            lines.append(f"  响应：{req['response'].strip() or '【待补】请填写经核对的响应'}")
            if any(w in req["text"] for w in ("资质", "证书", "证明", "业绩", "授权")) and not req.get("evidence_ids"):
                lines.append("  注意：本条款缺少已核对证据，不得编造证明材料。")
        lines.append("")

    # 公司资质与已关联证据
    evs = snapshot.get("evidence", [])
    if evs:
        lines.append("【已关联公司证据清单】")
        for ev in evs:
            tag = ev.get("tag", "[证]")
            lines.append(
                f"{tag} 已确认可引用证据：{ev['name']}（标识 {ev['id']}，记录版本 {ev.get('revision', 1)}，有效期至 {ev.get('valid_until') or '未登记'}）"
            )
            if ev.get("content"):
                lines.append(f"  证据内容摘要：{ev['content']}")
        lines.append("")

    # RAGFlow 检索证据切片
    retrieved = snapshot.get("retrieved_evidence", [])
    if retrieved:
        lines.append("【RAGFlow 检索证据候选切片】")
        for chunk in retrieved:
            tag = chunk.get("tag", "[片]")
            chunk_id = chunk.get("chunk_id", chunk.get("id", ""))
            doc_id = chunk.get("document_id", "")
            prov_parts = []
            if chunk_id:
                prov_parts.append(f"chunk_id: {chunk_id}")
            if doc_id:
                prov_parts.append(f"document_id: {doc_id}")
            prov = f"（{', '.join(prov_parts)}）" if prov_parts else ""
            ref_notice = "【仅供参考，不得作为正式附着证据】" if chunk.get("reference_only") else ""
            lines.append(f"{tag} 检索切片{prov}{ref_notice}：")
            lines.append(f"  {chunk.get('content', '')}")
        lines.append("")

    # 项目事实与 SLA 变量
    facts = snapshot.get("facts", [])
    if facts:
        lines.append("【已确认项目事实与变量清单】")
        for fact in facts:
            val = fact["value"] + (" " + fact["unit"] if fact.get("unit") else "")
            src = fact.get("source")
            src_str = (
                f"来源：{src.get('filename', src.get('file_id'))} 第{src.get('page')}页"
                if src
                else "来源：已确认项目事实"
            )
            lines.append(f"• {fact['key']}：变量 {fact['variable']}；核对取值：{val}；{src_str}")
        lines.append("")

    if snapshot.get("official_content", "").strip():
        lines.append("【当前已提交正文（所有事实变量必须保留）】")
        lines.append(snapshot["official_content"])
        lines.append("")

    return "\n".join(lines)


def assemble_writing_prompt_plan(
    state: DemoState,
    project_id: str,
    chapter_id: str,
    evidence_service: Any | None = None,
    now: float | None = None,
    max_context_tokens: int | None = None,
    snippet_matches: list[dict] | None = None,
) -> dict:
    """组装各章节得分要点小标题、已关联公司证据版本、RAGFlow候选切片及项目事实要点为模型Prompt写作计划（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）。"""
    project = state.projects.get(project_id)
    if project is None:
        raise DomainError(404, "NOT_FOUND", "未找到项目。")
    chapter = state.chapters.get(chapter_id)
    if chapter is None or chapter.project_id != project_id:
        raise DomainError(404, "NOT_FOUND", "未找到章节。")

    # 涉密项目本地模型强门禁拦截
    check_sensitive_model_gate(state, project_id)

    # 动态上下文 Token 预算与最大窗口解析
    effective_max_tokens = max_context_tokens
    if effective_max_tokens is None:
        bound_id = state.project_model_configs.get(project_id)
        cfg = state.model_configs.get(bound_id) if bound_id else state.model_configs.get(f"default-{project.company_id}")
        if cfg:
            effective_max_tokens = getattr(cfg, "context_window", None) or getattr(cfg, "max_context_tokens", None)
        if effective_max_tokens is None:
            effective_max_tokens = DEFAULT_MAX_CONTEXT_TOKENS

    current_time = now if now is not None else time.time()
    service = evidence_service if evidence_service is not None else getattr(state, "evidence_service", None)
    assembled = build_generation_context(state, project_id, chapter, current_time, evidence_service=service)
    snapshot = assembled["input_snapshot"]
    plan = snapshot.get("plan", {})

    # 自适应 Prompt 动态上下文裁剪与 Token 预算控制
    manager = DynamicPromptContextManager(max_context_tokens=effective_max_tokens)
    budget_result = manager.assemble_budgeted_prompt(snapshot, snippet_matches=snippet_matches)

    return {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "title": chapter.title,
        "volume": chapter.volume,
        "prompt": budget_result["prompt"],
        "token_budget_usage": budget_result["token_budget_usage"],
        "context_fingerprint": budget_result["context_fingerprint"],
        "missing_variables": budget_result["missing_variables"],
        "has_missing_variables": budget_result["has_missing_variables"],
        "truncated_items_count": budget_result["truncated_items_count"],
        "truncated_items": budget_result["truncated_items"],
        "retained_counts": budget_result["retained_counts"],
        "writing_points": plan.get("writing_points", ""),
        "target_length": plan.get("target_length"),
        "fact_constraints": "正文引用事实必须保留变量标记（如 {{fact:xxx}} 或 {{sla:xxx}}），严禁修改事实取值或手写替换。",
        "citation_rules": "[证] 证据引用必须注明来源编号，严禁编造未核对的公司资质或业绩证明；[片] 检索切片仅供参考，不得作为正式附着证据。",
        "evidence": snapshot.get("evidence", []),
        "retrieved_evidence": snapshot.get("retrieved_evidence", []),
        "facts": snapshot.get("facts", []),
        "requirements": snapshot.get("requirements", []),
        "input_snapshot": snapshot,
    }


class ChapterGenerationService:
    """章节写作计划组装与按逐节确认结果启动生成服务（APP-M2-T124 / T126 / AI-DYNAMIC-PROMPT-CONTEXT）。"""

    def __init__(self, demo: Any, repository: Any | None = None, evidence_service: Any | None = None):
        self.demo = demo
        self.repository = repository or getattr(demo, "repository", None)
        self.evidence_service = evidence_service or getattr(demo, "evidence_service", None)

    def assemble_writing_prompt_plan(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal | None = None,
        state: DemoState | None = None,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
    ) -> dict:
        """组装章节写作方案 Prompt 输入（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）。"""
        st = state if state is not None else self.repository.read()
        if principal is not None:
            self._check_access(st, project_id, chapter_id, principal)
        return assemble_writing_prompt_plan(
            st,
            project_id,
            chapter_id,
            evidence_service=self.evidence_service,
            now=self.demo._now() if hasattr(self.demo, "_now") else time.time(),
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )

    def start_chapter_generation(
        self,
        project_id: str,
        chapter_id: str,
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches: list[dict] | None = None,
    ) -> dict:
        """按逐节确认结果独立启动已确认章节的生成任务（APP-M2-T126 / AI-OUTLINE-GENERATE-EXPAND）。"""
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截）
        self._check_access(state, project_id, chapter_id, principal)

        project = state.projects[project_id]
        chapter = state.chapters[chapter_id]

        # 门禁 2：逐节确认门禁
        # 核心约束：按逐节确认结果独立启动已确认章节，未确认分册或未确认章节绝对不阻塞已确认章节的独立启动
        workflow = state.workflows.get(project_id, {})
        saved_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(chapter_id, {})
        if not saved_plan.get("confirmed_at") or not plan_is_current(state, project_id, chapter_id):
            raise DomainError(409, "PLAN_NOT_CONFIRMED", "本章写作方案尚未确认或方案已过期，不能启动生成。")

        # 门禁 3：敏感项目本地模型隔离门禁
        self._check_model_gate(state, project)

        # 组装 Prompt 写作计划（APP-M2-T124 / AI-DYNAMIC-PROMPT-CONTEXT）
        prompt_plan = self.assemble_writing_prompt_plan(
            project_id,
            chapter_id,
            principal,
            state=state,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )
        input_snapshot = prompt_plan["input_snapshot"]
        prompt = prompt_plan["prompt"]
        token_budget_usage = prompt_plan.get("token_budget_usage")
        context_fingerprint = prompt_plan.get("context_fingerprint")

        # 在 demo_job 中创建异步任务（job_type="generate_chapter", status="running", progress=0）
        now_time = self.demo._now() if hasattr(self.demo, "_now") else time.time()
        now_iso = iso_time(now_time)
        job_id = new_id("job")

        job_data = {
            "id": job_id,
            "job_type": "generate_chapter",
            "type": "generate_chapter",
            "project_id": project_id,
            "chapter_id": chapter_id,
            "status": "running",
            "progress": 0,
            "step_name": "准备生成提示词",
            "created_by": principal.user.id,
            "created_at": now_iso,
            "updated_at": now_iso,
            "error_json": None,
            "result_json": None,
            "token_budget_usage": token_budget_usage,
            "context_fingerprint": context_fingerprint,
        }

        # 持久化或存入仓储与状态机
        self.repository.save_job(job_data)

        def sync_job_to_state(st: DemoState):
            st.jobs[job_id] = deepcopy(job_data)
            st.recoverable_jobs[job_id] = {
                "id": job_id,
                "project_id": project_id,
                "type": "generate_chapter",
                "status": "running",
                "progress": 0,
                "message": "已启动章节生成任务。",
                "created_at": now_iso,
                "completed_at": None,
                "error": None,
                "events": [],
                "recoverable": True,
                "chapter_ids": [chapter_id],
            }

        self.repository.transaction(sync_job_to_state)

        # 推进中间步骤进度流转，与 JobProgress 对接
        self.repository.update_job_progress(
            job_id,
            progress=25,
            status="running",
            step_name="组装上下文提示词完成",
        )

        candidate = None
        # 如果需要同步执行或存在模型推理
        if sync_execute:
            self.repository.update_job_progress(
                job_id,
                progress=60,
                status="running",
                step_name="调用模型推理中",
            )
            provider = self.demo.resolve_model_provider(state, project_id)
            instruction = "按本章已确认条款、响应、证据和事实组织候选；不能编造证据与承诺。引用事实保留变量，不能改取值。"
            refuse_source_change(prompt_plan["writing_points"], input_snapshot)
            try:
                content = provider.suggest(instruction, prompt)
            except DomainError:
                self.repository.update_job_progress(
                    job_id,
                    progress=60,
                    status="failed",
                    step_name="模型调用失败",
                    error_json={"code": "MODEL_FAILED"},
                )
                raise
            except Exception as error:
                self.repository.update_job_progress(
                    job_id,
                    progress=60,
                    status="failed",
                    step_name="模型调用异常",
                    error_json={"code": "MODEL_UNAVAILABLE", "message": str(error)},
                )
                raise DomainError(502, "MODEL_UNAVAILABLE", "候选生成失败，正式正文没有修改。") from error

            validate_model_output(state, project_id, content, input_snapshot)

            # 解析结构化多段落与评分小标题
            scoring_points = prompt_plan.get("writing_points", "")
            allowed_evidence_ids = {e.get("id") for e in prompt_plan.get("evidence", []) if e.get("id")}
            allowed_snippet_ids = {s.get("snippet_id") or s.get("id") for s in (snippet_matches or []) if s.get("snippet_id") or s.get("id")}

            paragraphs = parse_structured_paragraphs(
                content,
                scoring_points=scoring_points,
                allowed_evidence_ids=allowed_evidence_ids,
                allowed_snippet_ids=allowed_snippet_ids,
            )
            structured_content = format_structured_chapter_content(paragraphs)
            seen_subheads = set()
            scoring_subheadings = []
            for p in paragraphs:
                sh = p.get("title") or p.get("subheading")
                if sh and sh not in seen_subheads:
                    seen_subheads.add(sh)
                    scoring_subheadings.append(sh)

            cand_id = new_id("candidate")
            candidate = {
                "id": cand_id,
                "content": content,
                "structured_content": structured_content,
                "paragraphs": paragraphs,
                "scoring_subheadings": scoring_subheadings,
                "base_revision": chapter.revision,
                "input_fingerprint": project_input_fingerprint(state, project_id),
                "context_fingerprint": context_fingerprint,
                "token_budget_usage": token_budget_usage,
                "provider": getattr(provider, "name", "model"),
                "is_real_model": bool(getattr(provider, "is_real_model", False)),
                "created_at": now_iso,
                "source_scope": "whole_chapter",
                "input_snapshot": input_snapshot,
            }

            def save_candidate_op(st: DemoState):
                wf = st.workflows.setdefault(project_id, {})
                wf.setdefault("candidates", {})[chapter_id] = candidate

            self.repository.transaction(save_candidate_op)

            self.repository.update_job_progress(
                job_id,
                progress=100,
                status="completed",
                step_name="章节生成完成",
                result_json={
                    "candidate_id": cand_id,
                    "chapter_id": chapter_id,
                    "token_budget_usage": token_budget_usage,
                    "context_fingerprint": context_fingerprint,
                    "paragraph_count": len(paragraphs),
                },
            )

        final_job = self.repository.read_job(job_id) or job_data
        if token_budget_usage and "token_budget_usage" not in final_job:
            final_job["token_budget_usage"] = token_budget_usage
        if context_fingerprint and "context_fingerprint" not in final_job:
            final_job["context_fingerprint"] = context_fingerprint

        return {
            "job_id": job_id,
            "job": final_job,
            "project_id": project_id,
            "chapter_id": chapter_id,
            "status": final_job.get("status", "running"),
            "progress": final_job.get("progress", 0),
            "step_name": final_job.get("step_name"),
            "prompt_plan": prompt_plan,
            "candidate": candidate,
            "token_budget_usage": token_budget_usage,
            "context_fingerprint": context_fingerprint,
            "paragraphs": candidate.get("paragraphs") if candidate else [],
            "structured_content": candidate.get("structured_content") if candidate else None,
            "scoring_subheadings": candidate.get("scoring_subheadings") if candidate else [],
        }

    def batch_generate_chapters(
        self,
        project_id: str,
        chapter_ids: list[str],
        principal: Principal,
        sync_execute: bool = False,
        max_context_tokens: int | None = None,
        snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
    ) -> dict[str, Any]:
        """批量启动多章节结构化写作方案生成（PRD MVP v1.8 §5.7.2 / AI-OUTLINE-GENERATE-EXPAND）。"""
        state = self.repository.read()

        # 门禁 1：角色与操作权限核验（只读角色拦截）
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可启动章节生成。")

        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或启动章节生成。")

        # 门禁 2：敏感项目本地模型隔离门禁（前置阻断）
        self._check_model_gate(state, project)

        successful_results: dict[str, Any] = {}
        failed_chapters: dict[str, Any] = {}
        all_jobs: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        total_prompt_tokens = 0
        total_estimated_tokens = 0

        for cid in chapter_ids:
            chapter = state.chapters.get(cid)
            if chapter is None or chapter.project_id != project_id:
                failed_chapters[cid] = {
                    "code": "NOT_FOUND",
                    "message": f"章节 {cid} 不存在或不属于当前项目。",
                }
                continue

            workflow = state.workflows.get(project_id, {})
            saved_plan = workflow.get("writing_plan", {}).get("chapters", {}).get(cid, {})
            if not saved_plan.get("confirmed_at") or not plan_is_current(state, project_id, cid):
                # 核心约束：未确认分册或未确认章节绝对不阻塞已确认章节的独立启动
                failed_chapters[cid] = {
                    "code": "PLAN_NOT_CONFIRMED",
                    "message": f"章节 {cid} 写作方案尚未确认或方案已过期，不能启动生成。",
                }
                continue

            try:
                snips = (snippet_matches_by_chapter or {}).get(cid)
                res = self.start_chapter_generation(
                    project_id=project_id,
                    chapter_id=cid,
                    principal=principal,
                    sync_execute=sync_execute,
                    max_context_tokens=max_context_tokens,
                    snippet_matches=snips,
                )
                successful_results[cid] = res
                if res.get("job"):
                    all_jobs.append(res["job"])
                if res.get("context_fingerprint"):
                    fingerprints[cid] = res["context_fingerprint"]
                usage = res.get("token_budget_usage", {})
                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_estimated_tokens += usage.get("total_estimated_tokens", 0)
            except DomainError as err:
                failed_chapters[cid] = {
                    "code": err.code,
                    "message": err.message,
                }
            except Exception as exc:
                failed_chapters[cid] = {
                    "code": "GENERATION_FAILED",
                    "message": str(exc),
                }

        return {
            "project_id": project_id,
            "total_chapters": len(chapter_ids),
            "total_requested": len(chapter_ids),
            "successful_count": len(successful_results),
            "failed_count": len(failed_chapters),
            "results": successful_results,
            "failed_chapters": failed_chapters,
            "jobs": all_jobs,
            "fingerprints": fingerprints,
            "aggregate_summary": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_estimated_tokens": total_estimated_tokens,
                "context_fingerprints": fingerprints,
            },
            "token_budget_usage_summary": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_estimated_tokens": total_estimated_tokens,
            },
        }

    def _check_access(self, state: DemoState, project_id: str, chapter_id: str, principal: Principal) -> None:
        role = getattr(principal.user, "role", "")
        norm_role = ROLE_NORMALIZATION_MAP.get(role, role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可启动章节生成。")

        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "项目不存在或不属于当前公司。")

        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "章节不存在或不属于当前项目。")

        if not writable(state, project_id, principal.user.id):
            raise DomainError(403, "PROJECT_WRITER_REQUIRED", "当前角色无权编辑或启动章节生成。")

    def _check_model_gate(self, state: DemoState, project: Project) -> None:
        is_sensitive = getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)
        if not is_sensitive:
            return

        bound_id = state.project_model_configs.get(project.id)
        cfg = state.model_configs.get(bound_id) if bound_id else state.model_configs.get(f"default-{project.company_id}")

        if cfg is not None:
            if not getattr(cfg, "is_local", False) or not getattr(cfg, "allow_sensitive", False):
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
        else:
            provider = getattr(self.demo, "model_provider", None)
            if provider and getattr(provider, "is_local", False) is False and getattr(provider, "is_real_model", None) is not False:
                raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")


def start_chapter_generation(
    project_id_or_service: Any,
    chapter_id_or_proj: str | None = None,
    principal_or_chap: Any = None,
    principal: Principal | None = None,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    evidence_service: Any | None = None,
    sync_execute: bool = False,
    max_context_tokens: int | None = None,
    snippet_matches: list[dict] | None = None,
) -> dict:
    """按逐节确认结果独立启动已确认章节的生成任务（模块顶层快捷入口，兼容多种传参形式）。"""
    if hasattr(project_id_or_service, "start_chapter_generation") and not isinstance(project_id_or_service, str):
        # 形式 1: start_chapter_generation(service, project_id, chapter_id, principal)
        service = project_id_or_service
        return service.start_chapter_generation(
            chapter_id_or_proj,
            principal_or_chap,
            principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches=snippet_matches,
        )

    # 形式 2: start_chapter_generation(project_id, chapter_id, principal, demo=...)
    project_id = str(project_id_or_service)
    chapter_id = str(chapter_id_or_proj)
    prin = principal_or_chap if principal is None else principal

    if demo is None:
        raise ValueError("demo or service must be provided to start_chapter_generation")

    service = ChapterGenerationService(demo, repository=repository, evidence_service=evidence_service)
    return service.start_chapter_generation(
        project_id,
        chapter_id,
        prin,
        sync_execute=sync_execute,
        max_context_tokens=max_context_tokens,
        snippet_matches=snippet_matches,
    )


def batch_generate_chapters(
    project_id_or_service: Any,
    chapter_ids_or_proj: list[str] | None = None,
    principal_or_chap: Any = None,
    principal: Principal | None = None,
    *,
    demo: Any | None = None,
    repository: Any | None = None,
    evidence_service: Any | None = None,
    sync_execute: bool = False,
    max_context_tokens: int | None = None,
    snippet_matches_by_chapter: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """批量启动多章节结构化写作方案生成（模块顶层快捷入口）。"""
    if hasattr(project_id_or_service, "batch_generate_chapters") and not isinstance(project_id_or_service, str):
        service = project_id_or_service
        return service.batch_generate_chapters(
            chapter_ids_or_proj,
            principal_or_chap,
            principal=principal,
            sync_execute=sync_execute,
            max_context_tokens=max_context_tokens,
            snippet_matches_by_chapter=snippet_matches_by_chapter,
        )

    project_id = str(project_id_or_service)
    chapter_ids = list(chapter_ids_or_proj or [])
    prin = principal_or_chap if principal is None else principal

    if demo is None:
        raise ValueError("demo or service must be provided to batch_generate_chapters")

    service = ChapterGenerationService(demo, repository=repository, evidence_service=evidence_service)
    return service.batch_generate_chapters(
        project_id,
        chapter_ids,
        prin,
        sync_execute=sync_execute,
        max_context_tokens=max_context_tokens,
        snippet_matches_by_chapter=snippet_matches_by_chapter,
    )
