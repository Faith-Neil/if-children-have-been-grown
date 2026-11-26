# 为什么有这个文件：在技术方案单节检索前执行「检索意图拆解与多路 Query 生成」（TV-M0-T25）。
# 它解决什么问题：直接拿干巴巴的章节标题同时去搜历史标书和资料库，既搜不出产品特定型号的原生能力，也捞不到故障报错案例；
# 这里基于「章节面包屑 + 挂载评分点 + 全局目标产品型号」生成面向历史库（搜写法）与资料三子库（搜产品参数/运维SOP/故障预案）
# 的差异化 Query 及 RAGFlow metadata_condition 过滤条件；真实本地模型可用时支持结构化拆解，超时或离线毫秒级回落确定性规则。

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

SECTION_TYPE_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("架构", "总体", "设计"), "technical_architecture"),
    (("安全", "保密", "加密", "等保"), "data_security"),
    (("网络", "防火墙", "链路"), "network_security"),
    (("部署", "安装", "上线", "割切", "迁移"), "deployment"),
    (("实施", "进度", "计划", "交付"), "implementation"),
    (("培训", "移交", "知识转移"), "training"),
    (("应急", "故障", "抢修", "宕机", "恢复", "切换", "演练"), "emergency_plan"),
    (("质量", "验收", "考核"), "quality_assurance"),
    (("团队", "人员", "驻场", "组织"), "project_team"),
    (("巡检", "运维", "维保", "监控", "值守", "备份", "补丁", "优化", "SLA", "服务"), "operation_maintenance"),
)

QUERY_PLAN_SYSTEM = (
    "你是招投标知识库检索规划器。根据待写章节路径、挂载评分要点和目标产品型号，输出严格 JSON（不要思考过程和解释）："
    '{"section_type":"operation_maintenance","tender_query":"…","history_queries":["…"],'
    '"product_queries":["…"],"manual_queries":["…"],"fault_case_queries":["…"]}。'
    "规则：1. 严禁把招标原文整句照抄进 query，每条 query 用 3～6 个高区分度专业词（不超过 50 字），且必须保留目标型号与核心业务/技术锚点词（如 Oracle、数据库维保），严禁泛化成「高可用架构设计」这类无锚点抽象词；"
    "2. history_queries 偏宏观方案架构与服务话术；"
    "3. product_queries 聚焦目标型号的原生功能、冗余架构与技术指标；"
    "4. manual_queries 聚焦标准操作 SOP、巡检周期与升级回滚步骤；"
    "5. fault_case_queries 聚焦典型故障场景、根因定位与应急处置闭环。"
)


@dataclass
class SectionQueryPlan:
    section_type: str
    tender_query: str
    history_queries: list[str] = field(default_factory=list)
    product_queries: list[str] = field(default_factory=list)
    manual_queries: list[str] = field(default_factory=list)
    fault_case_queries: list[str] = field(default_factory=list)
    history_metadata_condition: dict[str, Any] | None = None
    product_metadata_condition: dict[str, Any] | None = None
    manual_metadata_condition: dict[str, Any] | None = None
    fault_metadata_condition: dict[str, Any] | None = None
    source: str = "rule"


# 核心业务/技术锚点词表：从章节语境扫描命中后固定进检索 query，防止模型泛化丢失行业锚点。
_DOMAIN_VOCAB = (
    "数据库", "维保", "运维", "一体机", "DBA", "Oracle", "巡检", "备份", "容灾", "集群",
    "中间件", "操作系统", "虚拟化", "云平台", "网络", "安全", "存储", "灾备", "监控",
)


def _scan_domain_anchors(*texts: str) -> list[str]:
    blob = " ".join(str(t or "") for t in texts)
    return [w for w in _DOMAIN_VOCAB if w in blob][:3]


def infer_section_type(title: str, points: list[str] | None = None) -> str:
    blob = f"{title or ''} {' '.join(points or [])}"
    for keywords, sec_type in SECTION_TYPE_HINTS:
        if any(kw in blob for kw in keywords):
            return sec_type
    return "operation_maintenance"


def _pin_anchor_terms(queries: list[str], anchors: list[str]) -> list[str]:
    """模型/规则拆解的 query 若丢失核心业务/技术锚点词（型号、行业词），确定性补齐。
    真机实证：30B 模型把 history query 泛化成"高可用架构设计"导致可复用文档分数跌破阈值。"""
    pinned: list[str] = []
    for q in queries or []:
        text = str(q or "").strip()
        missing = [a for a in anchors if a and a not in text]
        if missing and text:
            text = f"{' '.join(missing[:2])} {text}".strip()
        pinned.append(text[:80])
    return pinned


def _anchor_terms(target_models: list[str] | None, workflow_project_words: list[str] | None = None) -> list[str]:
    """核心锚点词：目标型号 token + 项目业务词（数据库/维保/一体机/DBA/运维等行业词）。"""
    anchors: list[str] = []
    for m in (target_models or [])[:2]:
        token = str(m).strip()
        if token:
            anchors.append(token)
    for w in (workflow_project_words or [])[:3]:
        if w and w not in anchors:
            anchors.append(w)
    return anchors[:4]


def _clean_phrase(text: str, limit: int = 24) -> str:
    cleaned = re.sub(r"^[★\d.\s、．（）()]+", "", str(text or "").strip())
    cleaned = re.sub(r"[，,。；;：:！!？?|｜]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:limit]


def _build_metadata_conditions(
    section_type: str, target_models: list[str],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    # 历史标书的排他（not_reusable / buyer_requirement）由检索回收后应用侧确定性执行
    # （technical_rag._filter_history_hits）：真机实测 RAGFlow 1.0 负向算子 not is 行为不可靠
    # （缺字段文档被误排、命中不一致），安全底线类过滤不得依赖检索端。此处不再下发负向条件。
    history_cond: dict[str, Any] = {"logic": "and", "conditions": []}

    clean_models = [str(m).strip() for m in target_models if str(m).strip()]
    if not clean_models:
        return history_cond, None, None, None

    if len(clean_models) == 1:
        m = clean_models[0]
        prod_cond: dict[str, Any] | None = {
            "logic": "and",
            "conditions": [{"name": "model", "comparison_operator": "is", "value": m}],
        }
        fault_cond: dict[str, Any] | None = {
            "logic": "and",
            "conditions": [{"name": "product_model", "comparison_operator": "is", "value": m}],
        }
    else:
        prod_cond = {
            "logic": "or",
            "conditions": [{"name": "model", "comparison_operator": "is", "value": m} for m in clean_models[:5]],
        }
        fault_cond = {
            "logic": "or",
            "conditions": [{"name": "product_model", "comparison_operator": "is", "value": m} for m in clean_models[:5]],
        }
    return history_cond, prod_cond, None, fault_cond


def _rule_plan(
    title: str,
    *,
    breadcrumb: str = "",
    points: list[str] | None = None,
    target_models: list[str] | None = None,
) -> SectionQueryPlan:
    from icg.domain.technical_rag import section_query

    pts = [_clean_phrase(p, 22) for p in (points or []) if _clean_phrase(p, 22)][:3]
    models = [str(m).strip() for m in (target_models or []) if str(m).strip()][:3]
    sec_type = infer_section_type(f"{breadcrumb} {title}", pts)
    base_q = section_query(title, points=pts[:2])
    model_prefix = " ".join(models[:2])

    history_q = " ".join(part for part in [title, *pts[:2], "技术服务方案 实施步骤"] if part).strip()[:80]
    product_q = " ".join(part for part in [model_prefix, title, pts[0] if pts else "", "技术参数 高可用 原生能力"] if part).strip()[:80]
    manual_q = " ".join(part for part in [model_prefix, title, *pts[:2], "操作流程 巡检规范 SOP"] if part).strip()[:80]
    fault_q = " ".join(part for part in [model_prefix, title, pts[0] if pts else "", "故障排查 根因定位 应急处置"] if part).strip()[:80]
    tender_q = " ".join(part for part in [base_q, "服务期限 响应要求 考核违约"] if part).strip()[:80]

    h_cond, p_cond, m_cond, f_cond = _build_metadata_conditions(sec_type, models)
    return SectionQueryPlan(
        section_type=sec_type,
        tender_query=tender_q or base_q,
        history_queries=[history_q or base_q],
        product_queries=[product_q or base_q],
        manual_queries=[manual_q or base_q],
        fault_case_queries=[fault_q or base_q],
        history_metadata_condition=h_cond,
        product_metadata_condition=p_cond,
        manual_metadata_condition=m_cond,
        fault_metadata_condition=f_cond,
        source="rule",
    )


def _parse_json_obj(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            fenced = parts[1]
            text = fenced[4:] if fenced.startswith("json") else fenced
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        obj = json.loads(text[start:end + 1])
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _list_of_queries(raw: Any, fallback: list[str]) -> list[str]:
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()[:80]]
    if isinstance(raw, list):
        kept = [str(item).strip()[:80] for item in raw if str(item or "").strip()]
        if kept:
            return kept[:2]
    return fallback


def plan_section_queries(
    title: str,
    *,
    breadcrumb: str = "",
    points: list[str] | None = None,
    target_models: list[str] | None = None,
    model: Any = None,
    use_llm: bool | None = None,
) -> SectionQueryPlan:
    """拆解单节多库检索计划。默认对真实 OpenAICompatibleModelProvider 启用轻量模型拆解，替身/单测自动走规则拆解。"""
    fallback = _rule_plan(title, breadcrumb=breadcrumb, points=points, target_models=target_models)
    if use_llm is None:
        from icg.infra.openai_model import OpenAICompatibleModelProvider
        use_llm = isinstance(model, OpenAICompatibleModelProvider)
    if not use_llm or model is None or not callable(getattr(model, "suggest", None)):
        return fallback

    from icg.infra.openai_model import EXTRACT_CALL, call_with_profile

    pts = [_clean_phrase(p, 30) for p in (points or []) if _clean_phrase(p, 30)][:4]
    models = [str(m).strip() for m in (target_models or []) if str(m).strip()][:5]
    user_prompt = "\n".join([
        f"章节路径：{breadcrumb or title}",
        f"当前小节：{title}",
        "挂载要点：" + ("；".join(pts) if pts else "（无）"),
        "目标产品型号：" + ("、".join(models) if models else "（未指定）"),
    ])
    try:
        raw = call_with_profile(model.suggest, QUERY_PLAN_SYSTEM, user_prompt, profile=EXTRACT_CALL)
        parsed = _parse_json_obj(str(raw or ""))
    except Exception:
        return fallback
    if not parsed:
        return fallback

    sec_type = str(parsed.get("section_type") or fallback.section_type).strip() or fallback.section_type
    h_cond, p_cond, m_cond, f_cond = _build_metadata_conditions(sec_type, models)
    # 锚点固定：型号 token + 语境领域词，缺失即补齐（真机实证模型会把 query 泛化成无锚点抽象词）
    anchors = _anchor_terms(models) + _scan_domain_anchors(breadcrumb, title, " ".join(points or []))
    return SectionQueryPlan(
        section_type=sec_type,
        tender_query=str(parsed.get("tender_query") or fallback.tender_query).strip()[:80] or fallback.tender_query,
        history_queries=_pin_anchor_terms(_list_of_queries(parsed.get("history_queries"), fallback.history_queries), anchors),
        product_queries=_list_of_queries(parsed.get("product_queries"), fallback.product_queries),
        manual_queries=_list_of_queries(parsed.get("manual_queries"), fallback.manual_queries),
        fault_case_queries=_list_of_queries(parsed.get("fault_case_queries"), fallback.fault_case_queries),
        history_metadata_condition=h_cond,
        product_metadata_condition=p_cond,
        manual_metadata_condition=m_cond,
        fault_metadata_condition=f_cond,
        source="model",
    )
