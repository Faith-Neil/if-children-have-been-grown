# 为什么有这个文件：实现自适应 Prompt 动态上下文裁剪与 Token 预算控制（AI-DYNAMIC-PROMPT-CONTEXT）。
# 它解决什么问题：
# 1. Token 预算分配策略：根据模型上下文窗口动态分配 Token 预算，支持 max_context_tokens 动态设定并预留生成空间；
# 2. 四级优先级动态自适应裁剪：
#    - Priority 1（最高，绝对不裁剪）：System Prompt、章节标题与评分项必须达标要点、硬性限制规则与格式要求；
#    - Priority 2（高）：高置信度方案片段（相关度 >= 0.70）与强制项目事实变量；
#    - Priority 3（中）：招标文件相关切片与条款；超出预算按相关度降序截取；
#    - Priority 4（低）：补充背景与历史参考片段，超出预算时自适应丢弃；
# 3. 上下文指纹与 Token 统计：中英文字符加权估算（中文字符约 0.7 token，英文单词约 1.3 token），输出完整 token_budget_usage 指标与不可篡改 16 位 SHA-256 context_fingerprint；
# 4. 涉密隔离与防编造红线：涉密项目强制使用本地模型（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL），未匹配变量如实标入 missing_variables，严禁凭空编造。

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from icg.domain.domain import DemoState, DomainError


CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fa5]")
WORD_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
VARIABLE_PATTERN = re.compile(r"\{\{([A-Za-z0-9_.:\u4e00-\u9fa5-]+)\}\}")

# 默认上下文预算与预留参数
DEFAULT_MAX_CONTEXT_TOKENS = 4096
DEFAULT_RESERVED_GENERATION_TOKENS = 1024


def estimate_tokens(text: str) -> int:
    """加权估算文本的 Token 消耗量。

    计算规则（依据 PRD 与业界主流中文模型 Tokenizer 特征）：
    - 中文字符：1 个中文字符约 0.7 token；
    - 英文单词与数字序列：1 个单词约 1.3 token；
    - 其它符号（空白、标点）：加权 0.3 token。
    空文本返回 0，非空文本至少为 1。
    """
    if not text:
        return 0

    chinese_count = len(CHINESE_CHAR_PATTERN.findall(text))
    words = WORD_PATTERN.findall(text)
    word_count = len(words)
    total_len = len(text)
    word_chars = sum(len(w) for w in words)
    other_count = max(0, total_len - chinese_count - word_chars)

    raw_tokens = (chinese_count * 0.7) + (word_count * 1.3) + (other_count * 0.3)
    return max(1, math.ceil(raw_tokens))


@dataclass
class TokenBudgetUsage:
    max_context_tokens: int
    reserved_generation_tokens: int
    prompt_budget: int
    prompt_tokens: int
    remaining_prompt_tokens: int
    total_estimated_tokens: int
    truncated_items_count: int
    priority_breakdown: dict[str, int]
    truncated_items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_context_fingerprint(
    chapter_id: str,
    core_summary: str,
    retained_p2_ids: list[str],
    retained_p3_ids: list[str],
    retained_p4_ids: list[str],
    facts_snapshot: dict[str, str],
) -> str:
    """计算装配后上下文唯一不可伪造的 16 位 SHA-256 指纹。"""
    payload = {
        "chapter_id": chapter_id,
        "core": core_summary,
        "p2": sorted(retained_p2_ids),
        "p3": sorted(retained_p3_ids),
        "p4": sorted(retained_p4_ids),
        "facts": facts_snapshot,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def check_sensitive_model_gate(state: DemoState, project_id: str, model_config: Any | None = None) -> None:
    """涉密项目本地模型强门禁拦截。"""
    project = state.projects.get(project_id)
    if not project or not (getattr(project, "sensitive", False) or getattr(project, "is_sensitive", False)):
        return

    cfg = model_config
    if cfg is None:
        cfg_id = state.project_model_configs.get(project_id)
        if cfg_id and cfg_id in state.model_configs:
            cfg = state.model_configs[cfg_id]
        else:
            company_default_id = f"default-{project.company_id}"
            if company_default_id in state.model_configs:
                cfg = state.model_configs[company_default_id]

    if cfg is not None:
        is_local = getattr(cfg, "is_local", False)
        allow_sensitive = getattr(cfg, "allow_sensitive", True)
        if not is_local or not allow_sensitive:
            raise DomainError(
                403,
                "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL",
                "敏感项目只能使用本地模型配置，严禁向外网暴露数据或调用云端模型。",
                {"project_id": project_id, "is_local": is_local},
            )


class DynamicPromptContextManager:
    """自适应 Prompt 动态上下文裁剪与 Token 预算管理器。"""

    def __init__(
        self,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        reserved_generation_tokens: int | None = None,
    ) -> None:
        self.max_context_tokens = max(512, max_context_tokens)
        self.reserved_generation_tokens = (
            reserved_generation_tokens
            if reserved_generation_tokens is not None
            else min(DEFAULT_RESERVED_GENERATION_TOKENS, self.max_context_tokens // 4)
        )
        self.prompt_budget = max(128, self.max_context_tokens - self.reserved_generation_tokens)

    def assemble_budgeted_prompt(
        self,
        snapshot: dict[str, Any],
        snippet_matches: list[dict[str, Any]] | None = None,
        custom_facts_map: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """根据四级优先级动态裁剪装配 Prompt 上下文。"""
        chapter = snapshot.get("chapter", {})
        plan = snapshot.get("plan", {})
        project = snapshot.get("project", {})

        truncated_items: list[dict[str, Any]] = []
        missing_variables: list[str] = []
        priority_breakdown = {
            "priority_1_system_and_core": 0,
            "priority_2_snippets_and_facts": 0,
            "priority_3_tender_clauses": 0,
            "priority_4_background_references": 0,
        }

        # -------------------------------------------------------------
        # Priority 1（最高，绝对不裁剪）：核心指令、章节分册目标、写作要点与硬性规则约束
        # -------------------------------------------------------------
        p1_lines = [
            "【章节与分册目标】",
            f"章节：{chapter.get('title', '')}（分册：{chapter.get('volume', '')}）",
            f"项目：{project.get('name', '未命名项目')}",
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
        p1_text = "\n".join(p1_lines)
        p1_tokens = estimate_tokens(p1_text)
        priority_breakdown["priority_1_system_and_core"] = p1_tokens

        # 剩余可用 Prompt 预算（P1 绝对不裁剪，即使超出也保留）
        remaining_budget = max(0, self.prompt_budget - p1_tokens)

        # -------------------------------------------------------------
        # Priority 2（高）：高置信度方案片段（精确匹配度 >= 0.70）与强制项目事实变量
        # -------------------------------------------------------------
        p2_lines: list[str] = []
        retained_p2_ids: list[str] = []

        # 2.1 高置信度方案片段
        snippets_to_consider = list(snippet_matches or [])
        high_conf_snippets = [
            s for s in snippets_to_consider
            if s.get("score", 0.0) >= 0.70 or s.get("similarity_score", 0.0) >= 0.70
        ]
        high_conf_snippets.sort(key=lambda x: x.get("score", x.get("similarity_score", 0.0)), reverse=True)

        if high_conf_snippets:
            p2_lines.append("【高置信度企业成熟方案片段（优先吸纳）】")
            for snip in high_conf_snippets:
                snip_id = snip.get("snippet_id") or snip.get("id", "snip-unknown")
                body = snip.get("rendered_body") or snip.get("original_body", "")
                cite_tag = snip.get("cite_tag") or f"[片:{snip_id}]"
                snip_text = f"{cite_tag} 《{snip.get('product', '')}》（{snip.get('snippet_type', '')}）：\n{body}\n"
                tokens = estimate_tokens(snip_text)

                if tokens <= remaining_budget:
                    p2_lines.append(snip_text)
                    retained_p2_ids.append(snip_id)
                    remaining_budget -= tokens
                    priority_breakdown["priority_2_snippets_and_facts"] += tokens
                elif remaining_budget >= 80:
                    char_limit = int(remaining_budget / 0.8)
                    truncated_snip = snip_text[:char_limit] + "\n...[因Token预算限制，该方案片段后续内容已截断]\n"
                    actual_tokens = estimate_tokens(truncated_snip)
                    p2_lines.append(truncated_snip)
                    retained_p2_ids.append(snip_id)
                    remaining_budget = max(0, remaining_budget - actual_tokens)
                    priority_breakdown["priority_2_snippets_and_facts"] += actual_tokens
                    truncated_items.append({
                        "id": snip_id,
                        "category": "snippet",
                        "priority": "P2",
                        "reason": "partially_truncated_by_budget",
                        "original_tokens": tokens,
                        "retained_tokens": actual_tokens,
                    })
                else:
                    truncated_items.append({
                        "id": snip_id,
                        "category": "snippet",
                        "priority": "P2",
                        "reason": "omitted_due_to_budget",
                        "original_tokens": tokens,
                    })
            p2_lines.append("")

        # 2.2 强制项目事实变量
        facts = snapshot.get("facts", [])
        facts_map: dict[str, str] = dict(custom_facts_map or {})
        if facts:
            fact_block_lines = ["【已确认项目事实与变量清单】"]
            for f in facts:
                val = f.get("value", "") + (" " + f.get("unit") if f.get("unit") else "")
                var_key = f.get("variable") or f.get("variable_token") or f"{{{{fact:{f.get('id')}}}}}"
                facts_map[f.get("key", "")] = val
                src = f.get("source")
                src_str = (
                    f"来源：{src.get('filename', src.get('file_id'))} 第{src.get('page')}页"
                    if src
                    else "来源：已确认项目事实"
                )
                fact_line = f"• {f.get('key')}：变量 {var_key}；核对取值：{val}；{src_str}"
                fact_tokens = estimate_tokens(fact_line)
                if fact_tokens <= remaining_budget:
                    fact_block_lines.append(fact_line)
                    retained_p2_ids.append(f.get("id", "fact"))
                    remaining_budget -= fact_tokens
                    priority_breakdown["priority_2_snippets_and_facts"] += fact_tokens
                else:
                    truncated_items.append({
                        "id": f.get("id", "fact"),
                        "category": "fact",
                        "priority": "P2",
                        "reason": "omitted_due_to_budget",
                        "original_tokens": fact_tokens,
                    })
            fact_block_lines.append("")
            p2_lines.extend(fact_block_lines)

        # 检查未匹配变量（来自 snippet_matches）
        if snippet_matches:
            for s in snippet_matches:
                for mv in s.get("missing_variables", []):
                    if mv not in missing_variables:
                        missing_variables.append(mv)

        # -------------------------------------------------------------
        # Priority 3（中）：招标文件条款与公司已核对证据
        # -------------------------------------------------------------
        p3_lines: list[str] = []
        retained_p3_ids: list[str] = []

        # 3.1 招标文件条款
        reqs = list(snapshot.get("requirements", []))
        if reqs and remaining_budget > 0:
            req_block_lines = ["【招标文件条款与响应要求】"]
            for req in reqs:
                req_id = req.get("id", "req")
                resp_text = req.get("response", "").strip() or "【待补】请填写经核对的响应"
                req_text = f"• 条款：{req.get('text', '')}\n  响应：{resp_text}"
                if any(w in req.get("text", "") for w in ("资质", "证书", "证明", "业绩", "授权")) and not req.get("evidence_ids"):
                    req_text += "\n  注意：本条款缺少已核对证据，不得编造证明材料。"
                req_tokens = estimate_tokens(req_text)
                if req_tokens <= remaining_budget:
                    req_block_lines.append(req_text)
                    retained_p3_ids.append(req_id)
                    remaining_budget -= req_tokens
                    priority_breakdown["priority_3_tender_clauses"] += req_tokens
                else:
                    truncated_items.append({
                        "id": req_id,
                        "category": "requirement",
                        "priority": "P3",
                        "reason": "omitted_due_to_budget",
                        "original_tokens": req_tokens,
                    })
            req_block_lines.append("")
            p3_lines.extend(req_block_lines)

        # 3.2 公司已核对资质与证据
        evs = list(snapshot.get("evidence", []))
        if evs and remaining_budget > 0:
            ev_block_lines = ["【已关联公司证据清单】"]
            for ev in evs:
                ev_id = ev.get("id", "ev")
                tag = ev.get("tag", "[证]")
                ev_text = (
                    f"{tag} 已确认可引用证据：{ev.get('name', '')}（标识 {ev.get('id', '')}，"
                    f"记录版本 {ev.get('revision', 1)}，有效期至 {ev.get('valid_until') or '未登记'}）"
                )
                if ev.get("content"):
                    ev_text += f"\n  证据内容摘要：{ev.get('content')}"
                ev_tokens = estimate_tokens(ev_text)
                if ev_tokens <= remaining_budget:
                    ev_block_lines.append(ev_text)
                    retained_p3_ids.append(ev_id)
                    remaining_budget -= ev_tokens
                    priority_breakdown["priority_3_tender_clauses"] += ev_tokens
                else:
                    truncated_items.append({
                        "id": ev_id,
                        "category": "evidence",
                        "priority": "P3",
                        "reason": "omitted_due_to_budget",
                        "original_tokens": ev_tokens,
                    })
            ev_block_lines.append("")
            p3_lines.extend(ev_block_lines)

        # -------------------------------------------------------------
        # Priority 4（低）：补充背景、历史参考切片与低相关度候选
        # -------------------------------------------------------------
        p4_lines: list[str] = []
        retained_p4_ids: list[str] = []

        retrieved_chunks = list(snapshot.get("retrieved_evidence", []))
        if retrieved_chunks and remaining_budget > 0:
            chunk_block_lines = ["【RAGFlow 检索证据候选切片】"]
            for rc in retrieved_chunks:
                rc_id = rc.get("id") or rc.get("chunk_id", "chunk")
                tag = rc.get("tag", "[片]")
                chunk_id = rc.get("chunk_id", rc.get("id", ""))
                doc_id = rc.get("document_id", "")
                prov_parts = []
                if chunk_id:
                    prov_parts.append(f"chunk_id: {chunk_id}")
                if doc_id:
                    prov_parts.append(f"document_id: {doc_id}")
                prov = f"（{', '.join(prov_parts)}）" if prov_parts else ""
                ref_notice = "【仅供参考，不得作为正式附着证据】" if rc.get("reference_only") else ""
                rc_text = f"{rc.get('cite_tag') or tag} 检索切片{prov}{ref_notice}：\n  {rc.get('content', '')}"
                tokens = estimate_tokens(rc_text)
                if tokens <= remaining_budget:
                    chunk_block_lines.append(rc_text)
                    retained_p4_ids.append(rc_id)
                    remaining_budget -= tokens
                    priority_breakdown["priority_4_background_references"] += tokens
                else:
                    truncated_items.append({
                        "id": rc_id,
                        "category": "ragflow_chunk",
                        "priority": "P4",
                        "reason": "dropped_low_priority_due_to_budget",
                        "original_tokens": tokens,
                    })
            chunk_block_lines.append("")
            p4_lines.extend(chunk_block_lines)

        low_conf_snippets = [
            s for s in snippets_to_consider
            if s.get("score", 0.0) < 0.70 and s.get("similarity_score", 0.0) < 0.70
        ]
        if low_conf_snippets and remaining_budget > 0:
            low_block_lines = ["【方案片段与背景拓展参考】"]
            for lcs in low_conf_snippets:
                lcs_id = lcs.get("snippet_id") or lcs.get("id", "snip-p4")
                body = lcs.get("rendered_body") or lcs.get("original_body", "")
                cite_tag = lcs.get("cite_tag") or f"[片:{lcs_id}]"
                lcs_text = f"{cite_tag} 《{lcs.get('product', '')}》（{lcs.get('snippet_type', '')}）：\n{body}\n"
                tokens = estimate_tokens(lcs_text)
                if tokens <= remaining_budget:
                    low_block_lines.append(lcs_text)
                    retained_p4_ids.append(lcs_id)
                    remaining_budget -= tokens
                    priority_breakdown["priority_4_background_references"] += tokens
                else:
                    truncated_items.append({
                        "id": lcs_id,
                        "category": "snippet_low_conf",
                        "priority": "P4",
                        "reason": "dropped_low_priority_due_to_budget",
                        "original_tokens": tokens,
                    })
            low_block_lines.append("")
            p4_lines.extend(low_block_lines)

        # -------------------------------------------------------------
        # 组装最终 Prompt 并计算指纹
        # -------------------------------------------------------------
        final_sections = [p1_text]
        if p2_lines:
            final_sections.append("\n".join(p2_lines))
        if p3_lines:
            final_sections.append("\n".join(p3_lines))
        if p4_lines:
            final_sections.append("\n".join(p4_lines))

        if snapshot.get("official_content", "").strip():
            official_text = f"【当前已提交正文（所有事实变量必须保留）】\n{snapshot['official_content']}\n"
            final_sections.append(official_text)

        final_prompt = "\n".join(final_sections).strip()
        actual_prompt_tokens = estimate_tokens(final_prompt)

        # 上下文指纹
        fingerprint = compute_context_fingerprint(
            chapter_id=chapter.get("id", ""),
            core_summary=f"{chapter.get('title', '')}:{plan.get('writing_points', '')}",
            retained_p2_ids=retained_p2_ids,
            retained_p3_ids=retained_p3_ids,
            retained_p4_ids=retained_p4_ids,
            facts_snapshot=facts_map,
        )

        budget_usage = TokenBudgetUsage(
            max_context_tokens=self.max_context_tokens,
            reserved_generation_tokens=self.reserved_generation_tokens,
            prompt_budget=self.prompt_budget,
            prompt_tokens=actual_prompt_tokens,
            remaining_prompt_tokens=max(0, self.prompt_budget - actual_prompt_tokens),
            total_estimated_tokens=actual_prompt_tokens + self.reserved_generation_tokens,
            truncated_items_count=len(truncated_items),
            priority_breakdown=priority_breakdown,
            truncated_items=truncated_items,
        )

        return {
            "prompt": final_prompt,
            "token_budget_usage": budget_usage.to_dict(),
            "context_fingerprint": fingerprint,
            "missing_variables": sorted(list(set(missing_variables))),
            "has_missing_variables": bool(missing_variables),
            "truncated_items_count": len(truncated_items),
            "truncated_items": truncated_items,
            "retained_counts": {
                "p2_count": len(retained_p2_ids),
                "p3_count": len(retained_p3_ids),
                "p4_count": len(retained_p4_ids),
            },
        }
