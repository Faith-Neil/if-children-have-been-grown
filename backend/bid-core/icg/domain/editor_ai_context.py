# 为什么有这个文件：实现编辑台章节上下文感知问答与划词引用联动（AI-EDITOR-CONTEXT-LINKAGE，PRD v1.8 §5.11.3～5.11.6、§5.7.8）。
# 它解决什么问题：
# 1. 编辑台上下文注入：当助手接收编辑台请求时，支持传入 chapter_id, chapter_title, selected_text（用户划词/选中的段落片段）；
# 2. 段落元数据与依据组装：将章节上下文切分为带编号段落 [P1], [P2]...，并将已确认条款要求、公司证据 [证] 与 RAGFlow 切片 [片]（含溯源指纹）装配进 Prompt；
# 3. 双场景精准支持：
#    - 场景 1 划词优化/润色建议（polish/optimize）：基于选中文本与所在段落给出 Diff 对比建议与改写片段，保留事实变量；
#    - 场景 2 章节合规性与完整度问答（compliance_qa）：基于全文段落与招标要求、证据覆盖度提供合规差距诊断与专业解答；
# 4. 四道安全门禁与编辑锁守护：
#    - 延续 APP-M2-T179 规范：未获编辑锁时严格禁止替换正文，自由问答默认 can_insert=False, action="copy_only"；
#    - 持有有效编辑锁且生成替换建议时，必须携带严格可溯源的 citations；
#    - 敏感项目强制使用本地模型（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
#    - 只读角色拦截（403 FORBIDDEN）与租户隔离（404 NOT_FOUND）。

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .domain import Chapter, DemoState, DomainError, Lease, Principal, Project, iso_time
from .generation_context import evidence_expired, project_facts
from .project_access import READONLY_SYSTEM_ROLES, ROLE_NORMALIZATION_MAP, require_chapter


def decompose_chapter_paragraphs(content: str, selected_text: str | None = None) -> list[dict[str, Any]]:
    """
    将章节正文切分为带编号的段落列表，并在提供选中文本时精准定位所在段落。
    支持无选中文本时的干净兜底。
    """
    if not content:
        return []

    # 规范化换行
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    raw_paragraphs = [p for p in normalized.split("\n") if p.strip()]

    target_selected = selected_text.strip() if selected_text else ""
    paragraphs = []

    current_char = 0
    matched_any = False

    for idx, p_text in enumerate(raw_paragraphs, start=1):
        is_selected = False
        match_start = -1
        match_end = -1

        if target_selected and target_selected in p_text:
            is_selected = True
            matched_any = True
            match_start = p_text.find(target_selected)
            match_end = match_start + len(target_selected)

        paragraphs.append({
            "index": idx,
            "label": f"[P{idx}]",
            "text": p_text,
            "is_selected": is_selected,
            "char_length": len(p_text),
            "match_start": match_start,
            "match_end": match_end,
        })

    # 若选中文本跨段或由于空格标点未在单段精确命中，则尝试模糊匹配
    if target_selected and not matched_any:
        # 寻找与选中文本重合度最高的段落
        for p in paragraphs:
            if any(token in p["text"] for token in target_selected.split() if len(token) >= 4):
                p["is_selected"] = True
                matched_any = True
                break

    return paragraphs


def collect_chapter_citations(
    state: DemoState,
    project: Project,
    chapter_id: str,
    query: str = "",
    evidence_service: Any = None,
    knowledge_base_enabled: bool = True,
) -> list[dict[str, Any]]:
    """
    收集当前章节关联的已确认公司证据 [证] 与检索切片 [片]，并生成唯一溯源指纹。
    """
    citations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    workflow = state.workflows.get(project.id, {})
    requirements = [
        r for r in workflow.get("requirements", {}).values()
        if r.get("chapter_id") == chapter_id and r.get("status") == "confirmed"
    ]

    # 1. 章节已确认条款引用的公司证据 [证]
    for req in requirements:
        for ev_id in req.get("evidence_ids", []):
            if ev_id in seen_ids:
                continue
            item = state.library.get(ev_id)
            if (
                item is not None
                and item.get("company_id") == project.company_id
                and item.get("status") == "confirmed"
            ):
                rev = item.get("revision", 1)
                name = item.get("name", "公司证据")
                valid_until = item.get("valid_until") or item.get("valid_to")
                # 计算不可篡改证据指纹
                fp_payload = f"{item['id']}:{rev}:{name}:{valid_until or ''}"
                fingerprint = hashlib.sha256(fp_payload.encode("utf-8")).hexdigest()[:16]

                citations.append({
                    "id": item["id"],
                    "name": name,
                    "type": item.get("type", "qualification"),
                    "tag": "[证]",
                    "source_type": "company_library",
                    "revision": rev,
                    "valid_until": valid_until,
                    "content": item.get("content", ""),
                    "fingerprint": fingerprint,
                    "requirement_id": req.get("id"),
                })
                seen_ids.add(ev_id)

    # 2. 知识库检索候选切片 [片]（知识库开启且有检索服务时触发）
    if knowledge_base_enabled and evidence_service is not None:
        try:
            search_query = query.strip() or (project.name + " " + chapter_id)
            cands = evidence_service.search(project.company_id, search_query)
            for c in (cands or [])[:5]:
                cid = getattr(c, "id", None) or getattr(c, "chunk_id", str(c))
                if cid in seen_ids:
                    continue
                cname = getattr(c, "name", "资料切片")
                ctext = getattr(c, "text", "") or getattr(c, "content", "")
                fp_payload = f"chunk:{cid}:{cname}:{ctext[:64]}"
                fingerprint = hashlib.sha256(fp_payload.encode("utf-8")).hexdigest()[:16]

                citations.append({
                    "id": cid,
                    "name": cname,
                    "type": getattr(c, "record_type", "snippet"),
                    "tag": "[片]",
                    "source_type": "retrieved_chunk",
                    "revision": 1,
                    "valid_until": None,
                    "content": ctext,
                    "fingerprint": fingerprint,
                })
                seen_ids.add(cid)
        except Exception:
            pass

    return citations


def detect_editor_scene(query: str, selected_text: str | None = None, explicit_scene: str | None = None) -> str:
    """
    智能判定编辑台上下文交互场景：
    - "polish": 划词润色/优化/改写
    - "compliance_qa": 章节合规性/完整度问答
    - "general": 章节通用问答
    """
    if explicit_scene in ("polish", "optimize", "rewrite"):
        return "polish"
    if explicit_scene in ("compliance_qa", "compliance", "completeness"):
        return "compliance_qa"

    q_lower = query.lower()
    polish_keywords = (
        "润色", "优化", "修改", "改写", "重写", "精简", "扩写", "纠错",
        "更通顺", "更专业", "调整句式", "提炼", "polish", "optimize", "rewrite"
    )
    compliance_keywords = (
        "合规", "完整", "缺漏", "条款", "偏离", "响应", "是否充分", "风险",
        "核对", "覆盖", "检查", "评分项", "废标", "星号"
    )

    if selected_text and selected_text.strip():
        if any(w in q_lower for w in polish_keywords):
            return "polish"

    if any(w in q_lower for w in compliance_keywords):
        return "compliance_qa"

    if selected_text and selected_text.strip():
        return "polish"

    return "compliance_qa"


def build_editor_prompt_context(
    state: DemoState,
    project_id: str,
    chapter_id: str,
    query: str,
    selected_text: str | None = None,
    chapter_title: str | None = None,
    scene: str | None = None,
    knowledge_base_enabled: bool = True,
    evidence_service: Any = None,
    injected_tender_clauses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    组装编辑台大模型 Prompt 完整上下文：
    - 切分段落编号 [P1], [P2]...；
    - 组装划词选中文本与所在段落；
    - 挂接项目事实、SLA 变量与已确认证据引用 [证]/[片]；
    - 挂接用户主动注入的招标文件切片与条款约束；
    - 计算上下文指纹 context_fingerprint。
    """
    project = state.projects[project_id]
    chapter = state.chapters[chapter_id]
    workflow = state.workflows.get(project_id, {})

    effective_title = chapter_title or chapter.title
    paragraphs = decompose_chapter_paragraphs(chapter.content, selected_text)
    resolved_scene = detect_editor_scene(query, selected_text, scene)
    citations = collect_chapter_citations(
        state=state,
        project=project,
        chapter_id=chapter_id,
        query=query,
        evidence_service=evidence_service,
        knowledge_base_enabled=knowledge_base_enabled,
    )

    # 收集可用事实与 SLA 变量
    facts = [f for f in project_facts(state, project_id) if f.get("status") == "confirmed"]

    # 组装 System Prompt
    system_lines = [
        "你是一名专业的投标文件编写与合规评审智能助手（集成于编辑台协同写作界面）。",
        "你的职责是协助编写人针对当前章节正文进行合规性诊断或段落语句润色。",
        "",
        "【安全与合规红线】：",
        "1. 事实不可篡改：所有事实变量（形如 {{fact:xxx}} 或 {{sla:xxx}}）严禁修改其变量名或手写替换为静态数值；",
        "2. 严禁凭空捏造：若涉及公司资质、认证、证书、人员持证或历史业绩，必须严格基于【参考依据】中已核对的 [证] 或 [片]，标注引用来源；",
        "3. 结论仅供参考：未获得有效编辑锁并提交正式版本前，助手输出的所有建议仅供复制与参考，不自动生效为正文；",
        "4. 严格遵循招标文件特定条款约束：针对用户主动注入的废标条款、评分标准与商务技术要求，改写和合规诊断必须严格对齐并保持实质性响应。",
    ]

    if resolved_scene == "polish":
        system_lines.extend([
            "",
            "【划词优化/润色建议场景专有要求】：",
            "1. 针对用户选中的文本片段进行润色，提升文字的逻辑性、专业度与投标语言表现力；",
            "2. 保持前后文段落语意通顺连贯，不要破坏段落整体结构；",
            "3. 必须输出明确的 Diff 对比建议，清晰说明【原句】与【建议改写】。",
        ])
    else:
        system_lines.extend([
            "",
            "【章节合规性与完整度问答场景专有要求】：",
            "1. 结合当前章节全文段落与招标文件关联条款要求，深度评估正文响应的完整度与针对性；",
            "2. 明确指出是否存在条款未响应、关键佐证依据缺失或潜在合规风险，并给出具体修改或补全建议。",
        ])

    system_prompt = "\n".join(system_lines)

    # 组装 User Content
    user_lines = [
        f"【项目名称】：{project.name}",
        f"【当前章节】：{effective_title}（分册：{chapter.volume}，版本：r{chapter.revision}）",
        "",
        "【当前章节全文段落】：",
    ]

    if paragraphs:
        for p in paragraphs:
            sel_flag = " (用户选中文本所在段)" if p["is_selected"] else ""
            user_lines.append(f"{p['label']}{sel_flag} {p['text']}")
    else:
        user_lines.append("（本章节正文当前为空）")

    user_lines.append("")

    # 选中文本上下文
    has_selected = bool(selected_text and selected_text.strip())
    if has_selected:
        selected_clean = selected_text.strip()
        matched_para_labels = [p["label"] for p in paragraphs if p["is_selected"]]
        matched_desc = f"（位于 {', '.join(matched_para_labels)}）" if matched_para_labels else "（跨段或未完全对齐）"
        user_lines.extend([
            "【用户划词选中文本】：",
            f"\"{selected_clean}\" {matched_desc}",
            "",
        ])
    else:
        user_lines.extend([
            "【用户划词选中文本】：无选中文本（针对当前章节全局提供分析建议）",
            "",
        ])

    # 招标条款要求
    ch_reqs = [
        r for r in workflow.get("requirements", {}).values()
        if r.get("chapter_id") == chapter_id and r.get("status") == "confirmed"
    ]
    if ch_reqs:
        user_lines.append("【本章节对应招标文件条款要求】：")
        for r in ch_reqs:
            user_lines.append(f"- 条款 {r.get('id', '')}：{r.get('text', '')}")
        user_lines.append("")

    # 注入的特定招标文件条款约束
    injected_clauses = (
        injected_tender_clauses
        if injected_tender_clauses is not None
        else workflow.get("injected_tender_clauses", {}).get(chapter_id, [])
    )
    if injected_clauses:
        user_lines.append("【用户主动注入的招标文件特定条款约束】：")
        for cl in injected_clauses:
            c_num = cl.get("clause_number", "未编号")
            c_lbl = cl.get("clause_type_label", "招标文件条款")
            imp = " (★)" if cl.get("importance") == "star" else ""
            sc = f" [{cl.get('score_weight')}分]" if cl.get("score_weight") is not None else ""
            pg = cl.get("page", 1)
            user_lines.append(f"- [条款 {c_num} · {c_lbl}{imp}{sc}] (原文第 {pg} 页)：{cl.get('content', '')}")
        user_lines.append("")

    # 依据材料
    if citations:
        user_lines.append("【参考依据与证据材料】：")
        for c in citations:
            desc = f"{c['tag']} {c['name']} (ID: {c['id']}, 指纹: {c['fingerprint']})"
            if c.get("valid_until"):
                desc += f" 有效期至: {c['valid_until']}"
            user_lines.append(f"- {desc}")
            if c.get("content"):
                user_lines.append(f"  内容概要：{c['content'][:120]}...")
        user_lines.append("")

    # 可用事实与 SLA
    if facts:
        user_lines.append("【项目可用事实变量清单（正文必须保留变量标记）】：")
        for f in facts[:8]:
            user_lines.append(f"- {f.get('key')}: {f.get('variable_token')} (取值: {f.get('value')} {f.get('unit', '')})")
        user_lines.append("")

    # 用户指令
    user_lines.extend([
        f"【用户具体提问/指令】：{query}",
    ])

    user_content = "\n".join(user_lines)

    # 计算上下文指纹
    fp_seed = {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "revision": chapter.revision,
        "selected_text": selected_text or "",
        "scene": resolved_scene,
        "query": query,
        "citations_fps": [c["fingerprint"] for c in citations],
    }
    if injected_clauses:
        fp_seed["injected_tender_clauses"] = [
            f"{c.get('clause_number')}:{c.get('page')}:{c.get('content', '')[:32]}"
            for c in injected_clauses
        ]
    context_fingerprint = hashlib.sha256(json.dumps(fp_seed, sort_keys=True).encode("utf-8")).hexdigest()

    return {
        "system_prompt": system_prompt,
        "user_content": user_content,
        "scene": resolved_scene,
        "paragraphs": paragraphs,
        "citations": citations,
        "injected_tender_clauses": injected_clauses,
        "context_fingerprint": context_fingerprint,
        "has_selected_text": has_selected,
        "chapter_title": effective_title,
    }


def extract_diff_suggestion(raw_reply: str, selected_text: str | None = None) -> dict[str, Any] | None:
    """
    从模型回答中尝试解析 Diff 润色改写建议结构。
    """
    if not selected_text or not selected_text.strip():
        return None

    orig = selected_text.strip()
    suggested = ""

    # 尝试匹配【建议改写】：... 或 改写为：... 等常见模式
    match = re.search(r"(?:建议改写[为：:\s]*|改写建议[为：:\s]*|改写为[：:\s]*)(?:[\"“`]*)([^\"”`\n]+)(?:[\"”`]*)", raw_reply)
    if match:
        suggested = match.group(1).strip()
    elif raw_reply and len(raw_reply) < 300 and not raw_reply.startswith("关于") and not raw_reply.startswith("针对"):
        suggested = raw_reply.strip()
    else:
        # 默认提取回答中首个非标题、非空且与原句不同的语句
        lines = [line.strip() for line in raw_reply.split("\n") if line.strip() and not line.strip().startswith(("#", "-", "*", "【", "1.", "2."))]
        if lines:
            suggested = lines[0]
        else:
            suggested = raw_reply.strip()[:200]

    return {
        "original": orig,
        "suggested": suggested,
        "diff_mode": "selection",
    }


class EditorAIContextService:
    """
    编辑台上下文感知智能问答服务（AI-EDITOR-CONTEXT-LINKAGE）。
    """

    def __init__(self, demo: Any) -> None:
        self.demo = demo

    def chat_editor_context(
        self,
        principal: Principal,
        project_id: str,
        query: str,
        chapter_id: str,
        chapter_title: str | None = None,
        selected_text: str | None = None,
        scene: str | None = None,
        lease_token: str | None = None,
        knowledge_base_enabled: bool = True,
        history: list[dict[str, str]] | None = None,
        injected_tender_clauses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        落地编辑台章节上下文感知问答与划词引用联动核心服务。
        严格落实四道安全门禁与独占编辑锁校验。
        """
        # 门禁 1：角色权限强校验（拦截只读角色）
        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可使用智能助手提问。")

        state: DemoState = self.demo.repository.read()

        # 门禁 2：租户与项目隔离
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

        # 检查项目级只读分工
        team = state.project_teams.get(project_id, {})
        members = team.get("members", {})
        user_member = members.get(principal.user.id)
        if user_member and user_member.get("project_role") in ("viewer", "readonly"):
            raise DomainError(403, "FORBIDDEN", "项目只读成员不可使用智能助手提问。")

        # 章节归属隔离
        chapter = state.chapters.get(chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")

        # 门禁 3：敏感项目本地模型强门禁
        is_sensitive = getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)
        if is_sensitive:
            bound_id = state.project_model_configs.get(project_id)
            cfg = None
            if bound_id and bound_id in state.model_configs:
                cfg = state.model_configs[bound_id]
            else:
                default_id = f"default-{project.company_id}"
                if default_id in state.model_configs:
                    cfg = state.model_configs[default_id]

            if cfg is not None:
                if not getattr(cfg, "is_local", False) or not getattr(cfg, "allow_sensitive", False):
                    raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
            else:
                provider = self.demo.model_provider
                if getattr(provider, "is_local", False) is False and getattr(provider, "is_real_model", None) is not False:
                    raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型。")

        # 门禁 4：知识库开关联动与常驻说明
        notice = None
        library_query_skipped = False
        if not knowledge_base_enabled:
            library_query_skipped = True
            notice = "知识库已关闭，未查询公司资料库"

        # 组装编辑台上下文与 Prompt
        evidence_svc = getattr(self.demo, "evidence_service", None)
        prompt_ctx = build_editor_prompt_context(
            state=state,
            project_id=project_id,
            chapter_id=chapter_id,
            query=query,
            selected_text=selected_text,
            chapter_title=chapter_title,
            scene=scene,
            knowledge_base_enabled=knowledge_base_enabled,
            evidence_service=evidence_svc,
            injected_tender_clauses=injected_tender_clauses,
        )

        # 门禁 5：独占编辑锁校验与插入/替换意图守卫
        now = self.demo._now()
        lease = chapter.lock
        has_valid_lock = bool(
            lease is not None
            and lease.expires_at > now
            and lease_token
            and lease.token == lease_token
            and lease.owner_id == principal.user.id
            and lease.session_token == principal.session_token
        )

        can_insert = False
        action = "copy_only"
        insert_disabled_reason = "自由问答仅供参考与复制，不可直接插入正文"

        # 若处于划词润色/改写场景
        if prompt_ctx["scene"] == "polish" and prompt_ctx["has_selected_text"]:
            if not has_valid_lock:
                can_insert = False
                action = "copy_only"
                insert_disabled_reason = "未获取当前章节编辑锁，仅供参考与复制，不可直接替换正文"
            else:
                # 持有有效锁，若具备依据溯源，则允许生成带溯源替换建议
                if prompt_ctx["citations"]:
                    can_insert = True
                    action = "suggest_replacement"
                    insert_disabled_reason = ""
                else:
                    # 缺少依据时禁止直接插入正文
                    can_insert = False
                    action = "copy_only"
                    insert_disabled_reason = "缺少已核对依据溯源，不可直接替换正文"

        # 调用模型生成解答
        provider = self.demo.resolve_model_provider(state, project.id)
        try:
            if provider is not None and hasattr(provider, "suggest"):
                raw_reply = provider.suggest(prompt_ctx["system_prompt"], prompt_ctx["user_content"])
                if not isinstance(raw_reply, str):
                    raw_reply = str(raw_reply)
            else:
                if prompt_ctx["scene"] == "polish" and prompt_ctx["has_selected_text"]:
                    raw_reply = (
                        f"针对选中文本“{selected_text}”的润色建议：\n\n"
                        f"【建议改写】：{selected_text}（经过专业化表述优化，契合招标文件技术响应要求）。\n\n"
                        f"（注：已自动保留所有事实与承诺变量）。"
                    )
                else:
                    raw_reply = (
                        f"针对当前章节《{prompt_ctx['chapter_title']}》的合规与完整度分析：\n"
                        f"当前章节共 {len(prompt_ctx['paragraphs'])} 个段落，"
                        f"已关联 {len(prompt_ctx['citations'])} 项参考依据。\n"
                        f"整体响应良好，建议结合招标文件具体技术参数进一步细化交付指标。"
                    )
        except DomainError:
            raise
        except Exception as error:
            raise DomainError(502, "MODEL_UNAVAILABLE", "智能助手回答服务暂时不可用，请稍后重试。") from error

        # 若知识库关闭，确保常驻说明注入
        if not knowledge_base_enabled and "知识库已关闭" not in raw_reply:
            reply = f"{raw_reply}\n\n（说明：知识库已关闭，未查询公司资料库）"
        else:
            reply = raw_reply

        # 提取 Diff 建议
        diff_suggestion = None
        if prompt_ctx["scene"] == "polish" and prompt_ctx["has_selected_text"]:
            diff_suggestion = extract_diff_suggestion(raw_reply, selected_text)

        return {
            "query": query,
            "reply": reply,
            "scene": prompt_ctx["scene"],
            "chapter_id": chapter_id,
            "chapter_title": prompt_ctx["chapter_title"],
            "selected_text": selected_text,
            "has_selected_text": prompt_ctx["has_selected_text"],
            "paragraphs": prompt_ctx["paragraphs"],
            "citations": prompt_ctx["citations"],
            "injected_tender_clauses": prompt_ctx["injected_tender_clauses"],
            "injected_clauses_count": len(prompt_ctx["injected_tender_clauses"]),
            "context_fingerprint": prompt_ctx["context_fingerprint"],
            "can_insert": can_insert,
            "action": action,
            "insert_disabled_reason": insert_disabled_reason,
            "diff_suggestion": diff_suggestion,
            "kb_enabled": knowledge_base_enabled,
            "library_query_skipped": library_query_skipped,
            "notice": notice,
        }

    def accept_ai_suggestion(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        lease_token: str,
        base_revision: int,
        suggested_text: str,
        paragraph_id: str | None = None,
        original_text: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        input_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        """
        落地 APP-M2-T185 AI 助手采纳润色建议原地回写与段落替换协议核心服务：
        1. 必须校验当前调用者是否持有该章节有效排他编辑锁，无锁/失锁强拦截 423 LOCK_LOST / LOCK_HELD；
        2. 严格核对基线版本 base_revision，并发冲突拦截 409 REVISION_CONFLICT；
        3. 原文片段 original_text / 段落编号 paragraph_id 精准定位，原文不匹配拦截 409 REVISION_CONFLICT；
        4. 敏感项目本地模型强门禁拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
        5. 只读系统角色与项目只读成员拦截 403 FORBIDDEN；跨公司租户/跨项目隔离 404 NOT_FOUND；
        6. 原子事务内更新正文、递增章节与项目 revision、留存修订历史（含依据、采纳人与时间戳）、标记增量复查 pending，清理草稿。
        """
        if not suggested_text or not str(suggested_text).strip():
            raise DomainError(422, "VALIDATION_ERROR", "建议改写内容不能为空。")

        if not paragraph_id and (not original_text or not str(original_text).strip()):
            raise DomainError(422, "VALIDATION_ERROR", "必须提供待替换的段落编号（paragraph_id）或原文片段（original_text）。")

        if not lease_token or not str(lease_token).strip():
            raise DomainError(423, "LOCK_LOST", "未提供编辑锁 Token，不能修改章节正文。")

        # 门禁 1：角色权限强校验（拦截只读角色）
        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色无权修改章节正文。")

        def operation(state: DemoState):
            # 门禁 2：租户与项目隔离
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

            team = state.project_teams.get(project_id, {})
            members = team.get("members", {})
            user_member = members.get(principal.user.id)
            if user_member and user_member.get("project_role") in ("viewer", "readonly"):
                raise DomainError(403, "FORBIDDEN", "项目只读成员无权修改章节正文。")

            if principal.user.id not in members and norm_role != "company_admin":
                raise DomainError(403, "FORBIDDEN", "您不是本项目成员，无权修改正文。")

            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")

            # 门禁 3：敏感项目本地模型强门禁
            is_sensitive = getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)
            if is_sensitive:
                bound_id = state.project_model_configs.get(project_id)
                cfg = None
                if bound_id and bound_id in state.model_configs:
                    cfg = state.model_configs[bound_id]
                else:
                    default_id = f"default-{project.company_id}"
                    if default_id in state.model_configs:
                        cfg = state.model_configs[default_id]

                if cfg is not None:
                    if not getattr(cfg, "is_local", False) or not getattr(cfg, "allow_sensitive", False):
                        raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")
                else:
                    provider = self.demo.model_provider
                    if getattr(provider, "is_local", False) is False and getattr(provider, "is_real_model", None) is not False:
                        raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型。")

            # 门禁 4：独占编辑锁强校验
            now = self.demo._now()
            lease = chapter.lock
            if lease is None or lease.expires_at <= now:
                raise DomainError(423, "LOCK_LOST", "未持有当前章节有效编辑锁，编辑权已失效，请重新获取编辑锁。")
            if lease.owner_id != principal.user.id or lease.session_token != principal.session_token:
                raise DomainError(423, "LOCK_HELD", "当前章节编辑锁由其他会话持有，不能写入。")
            if lease.token != lease_token:
                raise DomainError(423, "LOCK_LOST", "编辑锁 Token 不匹配或已失效。")

            # 门禁 5：基线版本校验（防并发覆盖）
            if chapter.revision != base_revision:
                raise DomainError(409, "REVISION_CONFLICT", f"章节正文已被其他人修改（当前版本 r{chapter.revision}，提交基线 r{base_revision}），请刷新并重新核对最新版本。")

            if input_fingerprint is not None:
                from .domain import project_input_fingerprint
                if input_fingerprint != project_input_fingerprint(state, chapter.project_id):
                    raise DomainError(409, "INPUT_FINGERPRINT_STALE", "项目条款、事实或正文已变化，请重新核对来源后再回写。")

            # 门禁 6：段落定位与原地回写
            content = chapter.content or ""
            normalized = content.replace("\r\n", "\n").replace("\r", "\n")
            delimiter = "\n\n" if "\n\n" in normalized else "\n"
            raw_blocks = [p for p in normalized.split("\n") if p.strip()]

            target_idx = None
            updated_p_id = paragraph_id
            updated_p_order = None

            if paragraph_id:
                match = re.search(r"(?:-p|p|^)(\d+)$", paragraph_id)
                if match:
                    target_idx = int(match.group(1)) - 1
                if target_idx is not None and 0 <= target_idx < len(raw_blocks):
                    target_block = raw_blocks[target_idx]
                    updated_p_order = target_idx + 1
                    updated_p_id = f"{chapter.id}-p{updated_p_order}"
                    if original_text and str(original_text).strip():
                        orig_clean = str(original_text).strip()
                        if orig_clean in target_block:
                            raw_blocks[target_idx] = target_block.replace(orig_clean, str(suggested_text).strip(), 1)
                        elif orig_clean == target_block.strip():
                            raw_blocks[target_idx] = str(suggested_text).strip()
                        else:
                            raise DomainError(409, "REVISION_CONFLICT", f"段落原文已被修改，未匹配到待替换文本：{orig_clean[:30]}...")
                    else:
                        raw_blocks[target_idx] = str(suggested_text).strip()
                else:
                    raise DomainError(409, "REVISION_CONFLICT", f"未找到指定的段落编号：{paragraph_id}，章节结构已变更。")
            elif original_text and str(original_text).strip():
                orig_clean = str(original_text).strip()
                found = False
                for idx, block in enumerate(raw_blocks):
                    if orig_clean in block:
                        raw_blocks[idx] = block.replace(orig_clean, str(suggested_text).strip(), 1)
                        updated_p_order = idx + 1
                        updated_p_id = f"{chapter.id}-p{updated_p_order}"
                        found = True
                        break
                if not found:
                    raise DomainError(409, "REVISION_CONFLICT", f"未在章节正文中找到待替换的原文片段：{orig_clean[:30]}...")

            new_content = delimiter.join(raw_blocks)
            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            chapter.content = new_content
            chapter.revision += 1
            state.projects[project_id].revision += 1

            version_entry = {
                "revision": chapter.revision,
                "content": chapter.content,
                "actor_id": principal.user.id,
                "actor_name": principal.user.name,
                "created_at": iso_time(now),
                "version_origin": "ai_polish_accepted",
                "edit_mode": "accept_ai_suggestion",
                "paragraph_id": updated_p_id,
                "original_text": original_text,
                "suggested_text": suggested_text,
                "citations": citations or [],
                "incremental_check_status": "pending",
            }
            chapter.versions.append(version_entry)
            chapter.incremental_check_status = "pending"

            # 状态流转
            workflow = state.workflows.setdefault(project_id, {})
            chapter_status_map = workflow.setdefault("chapter_statuses", {})
            chapter_status_map[chapter.id] = "人工已处理"
            incremental_checks = workflow.setdefault("incremental_checks", {})
            incremental_checks[chapter.id] = {
                "chapter_id": chapter.id,
                "revision": chapter.revision,
                "status": "pending",
                "source_type": "AI润色采纳",
                "operation_type": "accept_ai_suggestion",
                "paragraph_id": updated_p_id,
                "triggered_at": iso_time(now),
            }

            # 清理草稿
            chapter.drafts.pop(principal.user.id, None)

            # 审计留痕
            self.demo._audit(state, principal, chapter, "ai_suggestion.accept", {
                "revision": chapter.revision,
                "paragraph_id": updated_p_id,
            })

            from icg.infra.database import decompose_paragraphs
            updated_paragraphs = decompose_paragraphs(chapter.content, chapter.id)

            return {
                "chapter_id": chapter.id,
                "project_id": project_id,
                "revision": chapter.revision,
                "content": chapter.content,
                "paragraph_id": updated_p_id,
                "updated_paragraph": {
                    "id": updated_p_id,
                    "order": updated_p_order,
                    "text": raw_blocks[updated_p_order - 1] if updated_p_order and updated_p_order <= len(raw_blocks) else str(suggested_text).strip(),
                },
                "paragraphs": updated_paragraphs,
                "version_entry": version_entry,
                "incremental_check_status": "pending",
                "message": "已成功采纳 AI 润色建议并回写正文",
            }

        return self.demo.repository.transaction(operation)
