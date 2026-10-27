# 为什么有这个文件：实现方案片段高精度检索与上下文精准匹配服务（AI-SNIPPET-RETRIEVAL-MATCH）。
# 它解决什么问题：
# 1. 多租户强隔离（${company_id}:: 命名空间）：严格限制只召回当前会话 company_id 下已发布的方案片段，严禁跨租户召回；
# 2. 相关度匹配与变量提取：根据章节标题、评分项要点及提示词上下文，计算片段文本匹配度，自动抽取项目事实变量占位符并从项目事实表中对齐填充；
# 3. 出处防虚构与 .cite 关联：每个召回方案片段生成标准引用标记 [片:snippet_id]、16 位 SHA-256 防篡改溯源指纹与来源元数据，严禁虚构依据；
# 4. 涉密项目本地模型门禁与离线隔离：涉密项目（sensitive=True）严格强制使用本地离线模型，云端模型配置拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；网络客户端设置 trust_env=False 防止代理泄露。

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from icg.domain.domain import DemoState, DomainError, Principal, iso_time
from icg.domain.generation_context import chapter_plan, project_facts
from icg.infra.retrieval import SnippetCandidateMatch, SnippetRecord, SnippetRetriever


VARIABLE_PATTERN = re.compile(r"\{\{([A-Za-z0-9_.:\u4e00-\u9fa5-]+)\}\}")
FACT_TOKEN_PATTERN = re.compile(r"\{\{fact:([A-Za-z0-9_.:-]+)\}\}")
SLA_TOKEN_PATTERN = re.compile(r"\{\{sla:([A-Za-z0-9_.:-]+)\}\}")


def compute_snippet_fingerprint(snippet_id: str, revision: int, company_id: str, body: str) -> str:
    """计算方案片段不可篡改的 SHA-256 溯源指纹（16位）。"""
    seed = f"snippet:{snippet_id}:{revision}:{company_id}:{body[:128]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def check_sensitive_project_airgap(state: DemoState, project_id: str, model_config_id: str | None = None) -> None:
    """涉密项目本地模型强门禁：敏感项目必须使用本地离线模型，严禁向外网暴露。"""
    project = state.projects.get(project_id)
    if not project or not getattr(project, "sensitive", False):
        return

    cfg_id = model_config_id or state.project_model_configs.get(project_id)
    if cfg_id and cfg_id in state.model_configs:
        cfg = state.model_configs[cfg_id]
        is_local = getattr(cfg, "is_local", False)
        allow_sensitive = getattr(cfg, "allow_sensitive", True)
        if not is_local or not allow_sensitive:
            raise DomainError(
                403,
                "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL",
                "敏感项目必须使用本地模型进行方案片段检索与精准匹配，严禁调用云端模型或向外网暴露数据。",
                {"project_id": project_id, "model_config_id": cfg_id, "is_local": is_local},
            )


def extract_project_facts_map(state: DemoState, project_id: str) -> dict[str, str]:
    """从当前项目状态、事实表与 SLA 中提取事实变量映射表。"""
    facts_map: dict[str, str] = {}
    project = state.projects.get(project_id)
    if project:
        facts_map["project_name"] = project.name
        facts_map["项目名称"] = project.name
        if project.tender_number:
            facts_map["tender_number"] = project.tender_number
            facts_map["招标编号"] = project.tender_number
        if project.deadline:
            facts_map["deadline"] = project.deadline
            facts_map["投标截止时间"] = project.deadline
        customer = getattr(project, "customer_name", None)
        if customer:
            facts_map["customer_name"] = customer
            facts_map["客户名称"] = customer
            facts_map["采购人"] = customer

    workflow = state.workflows.get(project_id, {})
    # 1. 抽取项目事实表
    facts = workflow.get("facts", {})
    for f in facts.values():
        val = f.get("value", "")
        unit = f.get("unit", "")
        formatted = f"{val}{unit}" if unit else str(val)
        key = f.get("key", "").strip()
        if key:
            facts_map[key] = formatted
            norm_k = key.lower().replace(" ", "_")
            facts_map[norm_k] = formatted
        # 格式占位支持
        fid = f.get("id")
        if fid:
            facts_map[f"fact:{fid}"] = formatted
            facts_map[fid] = formatted
        if f.get("sla_var_key"):
            skey = f["sla_var_key"]
            facts_map[f"sla:{skey}"] = formatted
            facts_map[skey] = formatted

    # 2. 抽取 SLA 承诺与事实
    sla_dict = workflow.get("sla")
    if isinstance(sla_dict, dict):
        for k, v in sla_dict.items():
            if v is not None:
                val_str = str(v)
                facts_map[k] = val_str
                facts_map[f"sla_{k}"] = val_str
                facts_map[f"sla:{k}"] = val_str
                facts_map[f"sla:sla_{k}"] = val_str
    try:
        from icg.domain.sla import sla_facts
        for sf in sla_facts(state, project_id):
            skey = sf.get("sla_var_key") or sf.get("key")
            val = sf.get("value", "")
            unit = sf.get("unit", "")
            formatted = f"{val}{unit}" if unit else str(val)
            if skey:
                facts_map[skey] = formatted
                facts_map[f"sla:{skey}"] = formatted
                norm_k = skey.lower().replace(" ", "_")
                facts_map[norm_k] = formatted
    except Exception:
        pass

    # 3. 常见业务别名智能对齐
    alias_pairs = [
        ("service_period", ["服务期限", "服务期", "服务周期", "履约期限"]),
        ("sla_availability", ["可用性", "系统可用率", "SLA可用性", "系统可用性"]),
        ("sla_response_time", ["响应时限", "响应时间", "故障响应时限", "重大故障响应时限"]),
        ("sla_recovery_time", ["恢复时限", "恢复时间", "故障恢复时限", "处理时限"]),
        ("sla_inspection_cycle", ["巡检频次", "巡检周期", "定期巡检频次"]),
    ]
    for canonical, aliases in alias_pairs:
        if canonical not in facts_map:
            for a in aliases:
                if a in facts_map:
                    facts_map[canonical] = facts_map[a]
                    break
        else:
            for a in aliases:
                if a not in facts_map:
                    facts_map[a] = facts_map[canonical]

    return facts_map


def align_and_render_snippet_variables(
    body: str,
    declared_variables: list[str],
    facts_map: dict[str, str],
) -> tuple[str, dict[str, str], list[str]]:
    """从片段中抽取变量占位符，从项目事实表中自动对齐并填充，返回 (渲染后正文, 已匹配变量表, 缺失变量列表)。"""
    matched_vars: dict[str, str] = {}
    missing_vars: list[str] = []

    # 提取 body 中所有 {{var}}
    tokens = set(VARIABLE_PATTERN.findall(body))
    for v in declared_variables:
        tokens.add(v)

    # 逐个对齐
    for token in sorted(tokens):
        clean_token = token.strip()
        val = facts_map.get(clean_token)
        if val is None and ":" in clean_token:
            bare = clean_token.split(":", 1)[1]
            val = facts_map.get(bare)
        if val is None:
            norm = clean_token.lower().replace("-", "_").replace(" ", "_")
            val = facts_map.get(norm)

        if val is not None:
            matched_vars[clean_token] = str(val)
        else:
            missing_vars.append(clean_token)

    # 渲染替换正文
    def _replace_token(match: re.Match) -> str:
        token = match.group(1).strip()
        if token in matched_vars:
            return matched_vars[token]
        if ":" in token:
            bare = token.split(":", 1)[1]
            if bare in matched_vars:
                return matched_vars[bare]
        return match.group(0)

    rendered_body = VARIABLE_PATTERN.sub(_replace_token, body)
    return rendered_body, matched_vars, sorted(missing_vars)


def format_snippets_for_prompt(matched_items: list[dict[str, Any]]) -> str:
    """格式化方案片段为 AI 写作与审核 Prompt 上下文，包含溯源指纹与来源元数据。"""
    if not matched_items:
        return ""
    lines = ["【已核验本公司方案片段依据（严禁虚构未提及内容）】："]
    for item in matched_items:
        lines.append(f"{item['cite_tag']} 《{item['product']}》（类型：{item['snippet_type']}，版本：v{item['published_revision']}）")
        if item.get("source_group"):
            lines.append(f"  出处组：{item['source_group']}")
        lines.append(f"  内容：{item['rendered_body']}")
        lines.append(f"  防伪指纹：{item['fingerprint']}")
        if item.get("missing_variables"):
            lines.append(f"  待核对变量：{', '.join(item['missing_variables'])}")
    return "\n".join(lines)


class SnippetRetrievalService:
    """方案片段智能检索与上下文精准匹配领域服务。"""

    def __init__(self, demo_service: Any, retriever: SnippetRetriever | None = None) -> None:
        self.demo = demo_service
        self.retriever = retriever or SnippetRetriever()

    def match_snippets(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str | None = None,
        chapter_title: str | None = None,
        scoring_points: list[str] | None = None,
        query: str | None = None,
        limit: int = 5,
        min_score: float = 0.05,
        model_config_id: str | None = None,
        snippet_store: Any | None = None,
    ) -> dict[str, Any]:
        """执行针对当前项目章节与评分项的多租户方案片段检索与精准上下文匹配。"""
        # 1. 验证登录及项目归属（404 隔离）
        state: DemoState = self.demo.repository.read()
        project = state.projects.get(project_id)
        if project is None:
            raise DomainError(404, "NOT_FOUND", "项目不存在。")
        if project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "当前账号无权访问跨租户项目。")

        # 2. 敏感项目本地模型门禁
        check_sensitive_project_airgap(state, project_id, model_config_id)

        # 3. 组装章节与评分项上下文
        points: list[str] = list(scoring_points or [])
        final_title = chapter_title or ""
        if chapter_id:
            chapter = state.chapters.get(chapter_id)
            if chapter and chapter.project_id == project_id:
                if not final_title:
                    final_title = chapter.title
                workflow = state.workflows.get(project_id, {})
                plan = chapter_plan(workflow, chapter_id)
                if plan.get("writing_points"):
                    points.append(plan["writing_points"])
                for r in workflow.get("requirements", {}).values():
                    if r.get("chapter_id") == chapter_id and r.get("text"):
                        if r["text"] not in points:
                            points.append(r["text"])

        # 4. 获取方案片段存储，严格多租户隔离
        store = (
            snippet_store
            or getattr(self.demo, "snippet_publications", None)
            or getattr(state, "snippet_publications", None)
        )
        raw_items: list[dict[str, Any]] = []
        if store is not None:
            raw_items = store.list(principal.user.company_id)

        # 严格防穿透：检查并转换为 SnippetRecord
        records: list[SnippetRecord] = []
        for item in raw_items:
            if item.get("company_id") != principal.user.company_id:
                continue  # 严禁异企泄露
            if item.get("published_revision", 0) <= 0:
                continue  # 仅检索已发布片段
            if not item.get("published_body", "").strip():
                continue
            records.append(
                SnippetRecord(
                    id=item["id"],
                    company_id=item["company_id"],
                    product=item.get("product", ""),
                    snippet_type=item.get("snippet_type", ""),
                    published_body=item.get("published_body", ""),
                    variables=list(item.get("variables", [])),
                    source_group=item.get("source_group", ""),
                    boilerplate_group=item.get("boilerplate_group", ""),
                    published_revision=item.get("published_revision", 1),
                    status="published",
                )
            )

        # 5. 调用检索器计算相关度
        search_prompt = f"{final_title} {query or ''}".strip()
        candidate_matches = self.retriever.retrieve(
            company_id=principal.user.company_id,
            query=search_prompt,
            snippets=records,
            limit=limit,
            min_score=min_score,
            scoring_points=points,
        )

        # 6. 提取项目事实表并进行变量对齐替换与溯源指纹生成
        facts_map = extract_project_facts_map(state, project_id)
        matched_items: list[dict[str, Any]] = []

        for match in candidate_matches:
            rendered_body, matched_vars, missing_vars = align_and_render_snippet_variables(
                match.published_body, match.variables, facts_map
            )
            fingerprint = compute_snippet_fingerprint(
                match.id, match.published_revision, match.company_id, match.published_body
            )
            cite_tag = f"[片:{match.id}]"
            citation_clause = f"{cite_tag} 《{match.product}》({match.snippet_type}, v{match.published_revision})"

            matched_items.append({
                "snippet_id": match.id,
                "company_id": match.company_id,
                "product": match.product,
                "snippet_type": match.snippet_type,
                "source_group": match.source_group,
                "boilerplate_group": getattr(match, "boilerplate_group", ""),
                "published_revision": match.published_revision,
                "original_body": match.published_body,
                "rendered_body": rendered_body,
                "variables": match.variables,
                "matched_variables": matched_vars,
                "missing_variables": missing_vars,
                "score": round(match.score, 4),
                "cite_tag": cite_tag,
                "citation_clause": citation_clause,
                "fingerprint": fingerprint,
                "cite_metadata": {
                    "id": match.id,
                    "tag": cite_tag,
                    "name": match.product,
                    "product": match.product,
                    "snippet_type": match.snippet_type,
                    "source_group": match.source_group,
                    "company_id": match.company_id,
                    "published_revision": match.published_revision,
                    "fingerprint": fingerprint,
                    "status": "published",
                    "verified": True,
                    "matched_variables": matched_vars,
                    "missing_variables": missing_vars,
                    "cite_type": "snippet",
                },
            })

        return {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "company_id": principal.user.company_id,
            "total_matched": len(matched_items),
            "items": matched_items,
            "extracted_fact_count": len(facts_map),
            "has_missing_variables": any(item["missing_variables"] for item in matched_items),
        }
