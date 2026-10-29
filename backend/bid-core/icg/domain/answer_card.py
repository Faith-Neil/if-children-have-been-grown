# 为什么有这个文件：实现智能对话助手的结构化直查、意图分流与答案卡装配（APP-M2-T181）。
# 它解决什么问题：
# 1. 意图分流：根据用户问题精准识别直查意图（本项目数据类与本公司资料类），分流 direct_query、kb_retrieval 与 no_retrieval；
# 2. 知识库开关联动：知识库关闭时本项目结构化数据依然直查（注“本卡来自本项目结构化数据”），公司资料直查跳过并置 library_query_skipped=True，普通问答走无检索；
# 3. 敏感信息自动掩码：身份证号一律脱敏为 110101********1234；
# 4. 答案卡防篡改与插入门禁：本项目结构化数据卡一律 can_insert=False，仅已确认且未过期的公司资料卡可标记 can_insert=True。

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .domain import Chapter, DemoState, DomainError, Lease, Principal, Project, iso_time, new_id
from .generation_context import evidence_expired, project_facts


DIRECT_QUERY_INTENT_VERSION = 1

ID_CARD_REGEX = re.compile(r"(?<![0-9A-Za-z])([1-9]\d{5})(?:\d{8})(\d{3}[0-9Xx])(?![0-9A-Za-z])")


def mask_id_card(text: str) -> str:
    """对文本中的 18 位身份证号码进行脱敏掩码，中间 8 位出生年月日替换为星号。"""
    if not isinstance(text, str):
        return text
    return ID_CARD_REGEX.sub(r"\1********\2", text)


def mask_sensitive_payload(data: Any) -> Any:
    """递归遍历字典/列表，对所有身份证号进行脱敏掩码。"""
    if isinstance(data, str):
        return mask_id_card(data)
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if isinstance(k, str) and any(key in k.lower() for key in ("id_card", "id_number", "identity_card")):
                if isinstance(v, str):
                    v = mask_id_card(v)
            masked[k] = mask_sensitive_payload(v)
        return masked
    if isinstance(data, list):
        return [mask_sensitive_payload(item) for item in data]
    return data


@dataclass(frozen=True)
class IntentMatch:
    matched: bool
    category: str | None  # "project" | "company" | None
    domain: str | None    # answer_card_domain
    intent: str | None    # 意图名称
    intent_version: int = DIRECT_QUERY_INTENT_VERSION


# 平台设置 direct_query_intents 词表规则（带版本号 DIRECT_QUERY_INTENT_VERSION = 1）
COMPANY_INTENT_RULES: list[tuple[str, str, list[str]]] = [
    ("person_cert", "人员证书直查", [
        "人员", "员工", "证书", "持证", "工程师", "项目经理", "架构师", "建造师",
        "张三", "李四", "王五", "软考", "pmp", "ocp", "oracle", "安全员", "消控证"
    ]),
    ("qualification", "企业资质直查", [
        "企业资质", "资质", "iso", "cmmi", "高新", "体系认证", "信息安全认证", "三甲", "安防"
    ]),
    ("contract", "企业业绩直查", [
        "业绩", "合同", "历史项目", "同类项目", "案例", "签约", "同类业绩"
    ]),
    ("sla", "SLA时限直查", [
        "sla", "响应时限", "恢复时限", "到达现场", "到场时限", "服务等级", "故障响应", "服务承诺"
    ]),
]

PROJECT_INTENT_RULES: list[tuple[str, str, list[str]]] = [
    ("tender_slice", "招标文件切片检索", [
        "招标文件切片", "招标文件检索", "检索招标文件", "条款检索", "查招标文件", "招标文件原文"
    ]),
    ("tender_requirement", "招标要求直查", [
        "招标要求", "投标保证金", "保证金", "开标时间", "星号条款", "★", "废标条款", "评分项要求", "付款方式"
    ]),
    ("project_fact", "项目事实直查", [
        "项目事实", "服务期限", "服务期多久", "最高限价", "限价", "建设单位", "交付地点", "采购人", "项目金额"
    ]),
    ("response_matrix", "响应矩阵直查", [
        "响应矩阵", "偏离表", "未分配章节", "应答状态", "评分项分配"
    ]),
    ("check_result", "检查结果直查", [
        "检查结果", "阻断项", "合规问题", "未覆盖评分项", "合规检查", "最近检查"
    ]),
]


def classify_query_intent(query: str) -> IntentMatch:
    """根据查询词与实体规则识别直查意图。"""
    query_lower = query.lower()
    # 优先匹配本项目数据类直查意图
    for domain, intent, keywords in PROJECT_INTENT_RULES:
        if any(kw in query_lower for kw in keywords):
            return IntentMatch(matched=True, category="project", domain=domain, intent=intent)
    # 匹配本公司资料类直查意图
    for domain, intent, keywords in COMPANY_INTENT_RULES:
        if any(kw in query_lower for kw in keywords):
            return IntentMatch(matched=True, category="company", domain=domain, intent=intent)
    return IntentMatch(matched=False, category=None, domain=None, intent=None)


@dataclass
class RouteDecision:
    query: str
    query_route: str               # "direct_query" | "kb_retrieval" | "no_retrieval"
    intent_category: str | None    # "project" | "company" | None
    domain: str | None             # answer_card_domain
    intent: str | None
    intent_version: int
    kb_enabled: bool
    library_query_skipped: bool
    notice: str | None = None


def resolve_assistant_query_route(query: str, knowledge_base_enabled: bool = True) -> RouteDecision:
    """
    裁决对话助手取数路径：
    1. direct_query: 命中直查意图；
       - 项目类：无论知识库开启与否均可直查；关闭时注“知识库已关闭，本卡来自本项目结构化数据”
       - 公司类：开启时直查；关闭时跳过检索（library_query_skipped=True，转为 no_retrieval，注“知识库已关闭，未查询公司资料库”）
    2. kb_retrieval: 未命中直查意图且知识库开启
    3. no_retrieval: 未命中直查意图且知识库关闭（常规回答，不检索）
    """
    match = classify_query_intent(query)
    if not match.matched:
        if knowledge_base_enabled:
            return RouteDecision(
                query=query,
                query_route="kb_retrieval",
                intent_category=None,
                domain=None,
                intent=None,
                intent_version=DIRECT_QUERY_INTENT_VERSION,
                kb_enabled=knowledge_base_enabled,
                library_query_skipped=False,
                notice=None,
            )
        else:
            return RouteDecision(
                query=query,
                query_route="no_retrieval",
                intent_category=None,
                domain=None,
                intent=None,
                intent_version=DIRECT_QUERY_INTENT_VERSION,
                kb_enabled=knowledge_base_enabled,
                library_query_skipped=False,
                notice=None,
            )

    # 命中本项目结构化数据直查意图
    if match.category == "project":
        notice = None if knowledge_base_enabled else "知识库已关闭，本卡来自本项目结构化数据"
        return RouteDecision(
            query=query,
            query_route="direct_query",
            intent_category="project",
            domain=match.domain,
            intent=match.intent,
            intent_version=match.intent_version,
            kb_enabled=knowledge_base_enabled,
            library_query_skipped=False,
            notice=notice,
        )

    # 命中本公司资料类直查意图
    if knowledge_base_enabled:
        return RouteDecision(
            query=query,
            query_route="direct_query",
            intent_category="company",
            domain=match.domain,
            intent=match.intent,
            intent_version=match.intent_version,
            kb_enabled=knowledge_base_enabled,
            library_query_skipped=False,
            notice=None,
        )
    else:
        return RouteDecision(
            query=query,
            query_route="no_retrieval",
            intent_category="company",
            domain=match.domain,
            intent=match.intent,
            intent_version=match.intent_version,
            kb_enabled=knowledge_base_enabled,
            library_query_skipped=True,
            notice="知识库已关闭，未查询公司资料库",
        )


@dataclass
class AnswerCard:
    title: str
    direct_query_domain: str
    direct_query_intent: str
    direct_query_intent_version: int
    query_route: str
    kb_enabled: bool
    library_query_skipped: bool
    source: str
    records: list[dict[str, Any]]
    total_count: int
    can_insert: bool
    insert_disabled_reason: str
    source_type: str = "company_library"
    notice: str | None = None
    disclaimer: str = "系统直查 · 未经模型改写"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "direct_query_domain": self.direct_query_domain,
            "direct_query_intent": self.direct_query_intent,
            "direct_query_intent_version": self.direct_query_intent_version,
            "query_route": self.query_route,
            "kb_enabled": self.kb_enabled,
            "library_query_skipped": self.library_query_skipped,
            "source": self.source,
            "source_type": self.source_type,
            "notice": self.notice,
            "records": self.records,
            "total_count": self.total_count,
            "can_insert": self.can_insert,
            "insert_disabled_reason": self.insert_disabled_reason,
            "disclaimer": self.disclaimer,
        }


class AnswerCardService:
    """负责根据意图与权限装配结构化直查答案卡。"""

    def __init__(self, demo_service: Any):
        self.demo = demo_service

    def process_query(self, principal: Principal, project_id: str, query: str,
                      knowledge_base_enabled: bool = True) -> dict[str, Any]:
        """
        处理对话助手用户提问：
        1. 裁决路由与开关联动
        2. 若为直查意图且可查，装配答案卡（敏感信息脱敏、插入门禁）
        3. 返回统一结构的助手响应
        """
        route = resolve_assistant_query_route(query, knowledge_base_enabled)

        card_dict = None
        fallback_to_general = False
        final_query_route = route.query_route
        final_notice = route.notice
        library_query_skipped = route.library_query_skipped

        if route.query_route == "direct_query":
            card = self.assemble_answer_card(principal, project_id, query, route)
            if card is None or len(card.records) == 0:
                # 直查未命中！触发优雅降级与常规回答回退，绝不编造虚假卡片
                fallback_to_general = True
                card_dict = None
                if route.intent_category == "project":
                    # 本项目数据未命中
                    if knowledge_base_enabled:
                        final_query_route = "kb_retrieval"
                        final_notice = "本项目结构化数据中未查询到对应条目，已转入常规助手解答"
                    else:
                        final_query_route = "no_retrieval"
                        final_notice = "本项目结构化数据中未查询到对应条目，已转入常规助手解答。知识库已关闭，未查询公司资料库"
                else:
                    # 本公司资料未命中
                    if knowledge_base_enabled:
                        final_query_route = "kb_retrieval"
                        final_notice = "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答"
                    else:
                        final_query_route = "no_retrieval"
                        library_query_skipped = True
                        final_notice = "知识库已关闭，未查询公司资料库"
            else:
                card_dict = card.to_dict()
                final_notice = card.notice
        else:
            final_query_route = route.query_route
            final_notice = route.notice
            # 常驻说明一致性：在常规回复中如遇知识库关闭，一律携带常驻说明“知识库已关闭，未查询公司资料库”
            if not knowledge_base_enabled and final_query_route == "no_retrieval":
                if not final_notice:
                    final_notice = "知识库已关闭，未查询公司资料库"
                elif "知识库已关闭，未查询公司资料库" not in final_notice:
                    final_notice = f"{final_notice}。知识库已关闭，未查询公司资料库"

        return {
            "query": query,
            "query_route": final_query_route,
            "intent_category": route.intent_category,
            "direct_query_domain": route.domain,
            "direct_query_intent": route.intent,
            "direct_query_intent_version": route.intent_version,
            "kb_enabled": route.kb_enabled,
            "library_query_skipped": library_query_skipped,
            "fallback_to_general": fallback_to_general,
            "notice": final_notice,
            "answer_card": card_dict,
        }

    def assemble_answer_card(self, principal: Principal, project_id: str, query: str,
                             route: RouteDecision) -> AnswerCard:
        state: DemoState = self.demo.repository.read()
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

        workflow = state.workflows.get(project_id, {})
        domain = route.domain or "project_fact"

        if route.intent_category == "project":
            return self._assemble_project_card(state, project, workflow, domain, route, query, principal=principal)
        else:
            return self._assemble_company_card(state, principal, project, domain, route, query)

    def _assemble_project_card(self, state: DemoState, project: Project, workflow: dict[str, Any],
                               domain: str, route: RouteDecision, query: str,
                               principal: Principal | None = None) -> AnswerCard:
        records: list[dict[str, Any]] = []
        source_label = "本项目结构化数据"

        if domain == "tender_slice":
            source_label = "本项目招标文件"
            title = f"招标文件检索 · {route.intent}"
            search_service = getattr(self.demo, "tender_retrieval", None)
            if search_service is None:
                from icg.infra.tender_retrieval import TenderRetrievalService
                search_service = TenderRetrievalService(self.demo)
                self.demo.tender_retrieval = search_service
            if principal is not None:
                search_res = search_service.search(principal, project.id, query)
                records = [s.to_dict() for s in search_res.slices]
                notice = search_res.notice
            else:
                records = []
                notice = "招标文件检索服务未就绪"
            masked_records = mask_sensitive_payload(records)
            return AnswerCard(
                title=title,
                direct_query_domain=domain,
                direct_query_intent=route.intent or "招标文件检索",
                direct_query_intent_version=route.intent_version,
                query_route=route.query_route,
                kb_enabled=route.kb_enabled,
                library_query_skipped=route.library_query_skipped,
                source=source_label,
                source_type="tender_document",
                records=masked_records,
                total_count=len(masked_records),
                can_insert=False,
                insert_disabled_reason="本项目招标文件切片不提供直接插入正文，可一键注入章节Prompt上下文作为依据或以变量引用改写",
                notice=notice,
                disclaimer="系统直查 · 招标文件原文切片",
            )

        if domain == "tender_requirement":
            source_label = "本项目招标文件"
            raw_reqs = list(workflow.get("requirements", {}).values())
            # 过滤已被替代的条目
            active_reqs = [r for r in raw_reqs if r.get("status") != "superseded"]

            # 根据查询词做针对性实体过滤与相关性排序
            target_words = [w for w in ("保证金", "投标保证金", "星号", "★", "开标时间", "开标", "服务期", "废标", "付款方式") if w in query]
            if target_words:
                filtered_reqs = [r for r in active_reqs if any(w in (r.get("text") or "") for w in target_words)]
            else:
                filtered_reqs = active_reqs

            for req in filtered_reqs[:10]:
                text = req.get("text", "")
                is_star = "★" in text or req.get("is_star")
                importance = "star" if is_star else ("void" if "废标" in text else "normal")
                records.append({
                    "id": req.get("id"),
                    "category": req.get("category", "技术"),
                    "importance": importance,
                    "title": text,
                    "value": req.get("response") or "【待补】",
                    "unit": req.get("unit", ""),
                    "confirm_status": "confirmed" if req.get("status") == "confirmed" else "pending",
                    "status_label": "已确认" if req.get("status") == "confirmed" else "待确认",
                    "page": req.get("source", {}).get("page"),
                })
            title = f"招标要求 · {route.intent}"

        elif domain == "project_fact":
            source_label = "本项目项目事实表"
            facts = project_facts(state, project.id)
            conflicts = workflow.get("conflicts", {})

            # 针对特定事实键的实体过滤
            specific_fact_keywords = ("服务期限", "服务期", "最高限价", "限价", "建设单位", "交付地点", "采购人", "项目金额")
            query_fact_keywords = [w for w in specific_fact_keywords if w in query]

            if query_fact_keywords:
                matched_facts = [
                    f for f in facts
                    if any(w in (f.get("label", "") + f.get("key", "")) for w in query_fact_keywords)
                ]
            else:
                matched_facts = facts

            def fact_score(f: dict) -> int:
                label = f.get("label", "") + f.get("key", "")
                return sum(1 for w in query_fact_keywords if w in label)

            sorted_facts = sorted(matched_facts, key=fact_score, reverse=True)

            for fact in sorted_facts[:10]:
                fact_key = fact.get("key", "")
                conflict_entry = conflicts.get(fact_key)
                if conflict_entry:
                    status = "conflict"
                    status_label = "有冲突，待项目负责人选定"
                    conflict_choices = conflict_entry.get("choices", [])
                else:
                    status = fact.get("status", "confirmed")
                    status_label = "已确认" if status == "confirmed" else "待确认"
                    conflict_choices = []

                records.append({
                    "id": fact.get("id"),
                    "key": fact_key,
                    "label": fact.get("label", fact_key),
                    "value": fact.get("value", ""),
                    "unit": fact.get("unit", ""),
                    "source_type": fact.get("source_type", "parsed"),
                    "confirm_status": status,
                    "status_label": status_label,
                    "has_conflict": bool(conflict_entry),
                    "conflict_choices": conflict_choices,
                })
            title = f"项目事实 · {route.intent}"

        elif domain == "response_matrix":
            source_label = "本项目响应矩阵"
            reqs = list(workflow.get("requirements", {}).values())
            assigned_count = sum(1 for r in reqs if r.get("chapter_id"))
            records.append({
                "total_requirements": len(reqs),
                "assigned_chapters": assigned_count,
                "unassigned_count": len(reqs) - assigned_count,
                "deviation_count": 0,
            })
            title = "响应矩阵 · 当前汇总"

        elif domain == "check_result":
            source_label = "本项目检查结果"
            checks = list(workflow.get("checks", {}).values())
            latest_check = checks[-1] if checks else None
            if latest_check:
                records.append({
                    "check_id": latest_check.get("id"),
                    "passed": latest_check.get("passed", False),
                    "issue_count": len(latest_check.get("issues", [])),
                    "issues": latest_check.get("issues", [])[:5],
                })
            else:
                records.append({
                    "check_id": None,
                    "passed": True,
                    "issue_count": 0,
                    "issues": [],
                    "note": "尚未执行项目合规检查",
                })
            title = "检查结果 · 最近合规检查"

        else:
            title = f"本项目数据 · {domain}"

        # 敏感信息脱敏掩码
        masked_records = mask_sensitive_payload(records)

        # 本项目结构化数据卡门禁：一律不可直接插入正文
        return AnswerCard(
            title=title,
            direct_query_domain=domain,
            direct_query_intent=route.intent or "结构化直查",
            direct_query_intent_version=route.intent_version,
            query_route=route.query_route,
            kb_enabled=route.kb_enabled,
            library_query_skipped=route.library_query_skipped,
            source=source_label,
            source_type="project_data",
            records=masked_records,
            total_count=len(masked_records),
            can_insert=False,
            insert_disabled_reason="本项目数据不插入正文",
            notice=route.notice,
            disclaimer="系统直查 · 未经模型改写",
        )

    def _assemble_company_card(self, state: DemoState, principal: Principal, project: Project,
                               domain: str, route: RouteDecision, query: str) -> AnswerCard:
        from .workflow import WorkflowService

        records: list[dict[str, Any]] = []
        source_label = "本公司资料库"

        if domain == "sla":
            source_label = "本公司SLA服务承诺"
            workflow = state.workflows.get(project.id, {})
            template_id = workflow.get("sla")
            templates = list(state.sla_templates.values())
            company_templates = [tmpl for tmpl in templates if tmpl.get("company_id") == principal.user.company_id]

            target_levels = [lvl for lvl in ("一级", "二级", "三级", "四级", "五级", "特级") if lvl in query]

            for tmpl in company_templates:
                levels = tmpl.get("levels", [])
                if target_levels:
                    matched_levels = [l for l in levels if any(lvl in str(l) for lvl in target_levels)]
                    if not matched_levels:
                        continue
                else:
                    matched_levels = levels

                records.append({
                    "id": tmpl.get("id"),
                    "template_name": tmpl.get("name"),
                    "fault_levels": matched_levels,
                    "confirm_status": "confirmed",
                    "status_label": "已确认",
                    "can_insert": True,
                    "insert_disabled_reason": "",
                })
            title = "SLA服务承诺 · 响应时限"
        else:
            raw_library = [item for item in state.library.values()
                           if item.get("company_id") == principal.user.company_id]

            query_lower = query.lower()
            # 常见人名或查询指定人名
            target_persons = [p for p in ("张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "陈十一") if p in query]
            name_matches = re.findall(r"(?:查询|请问)?([一-龥]{2,3})(?:有哪些|有何|的|持有|证书|人员)", query)
            for m in name_matches:
                if m not in ("人员", "公司", "证书", "资质", "业绩", "项目", "合同", "哪些", "我们", "请问"):
                    if m not in target_persons:
                        target_persons.append(m)

            # 证书名称关键词
            target_certs = [c for c in ("oracle", "ocp", "pmp", "cisp", "软考", "建造师", "消控证", "安全员", "cissp", "itil", "togaf") if c in query_lower]
            # 资质名称关键词
            target_quals = [q for q in ("iso", "cmmi", "高新", "体系认证", "信息安全认证", "三甲", "安防", "涉密") if q in query_lower]
            # 业绩关键词
            target_contracts = [w for w in ("同类业绩", "三甲", "医院", "银行", "高校", "教育", "交通", "政务", "涉密") if w in query]

            for item in raw_library:
                # 权限隔离：受限资料仅有权人员可见，无权人员不出现亦不提示存在
                if item.get("is_restricted") and not WorkflowService._restricted_allowed(state, principal, item):
                    continue

                item_type = item.get("type", "")
                item_name = item.get("name", "")
                item_content = item.get("content", "")
                item_text = (item_name + " " + item_content).lower()

                # 匹配领域类型与具体实体
                is_match = False
                if domain in ("person", "person_cert"):
                    type_ok = item_type in ("person", "cert", "person_cert", "credential") or any(
                        w in item_name or w in item_content for w in ("张三", "李四", "王五", "证书", "工程师", "ocp", "pmp")
                    )
                    if type_ok:
                        person_ok = (not target_persons) or any(p in item_name or p in item_content for p in target_persons)
                        cert_ok = (not target_certs) or any(c in item_text for c in target_certs)
                        if person_ok and cert_ok:
                            is_match = True
                elif domain == "qualification":
                    type_ok = item_type in ("qualification", "cert", "enterprise_cert") or any(
                        w in item_name or w in item_content for w in ("资质", "iso", "cmmi", "认证")
                    )
                    if type_ok:
                        qual_ok = (not target_quals) or any(q in item_text for q in target_quals)
                        if qual_ok:
                            is_match = True
                elif domain == "contract":
                    type_ok = item_type in ("contract", "project", "performance") or any(
                        w in item_name or w in item_content for w in ("业绩", "合同", "案例")
                    )
                    if type_ok:
                        contract_ok = (not target_contracts) or any(c in (item_name + " " + item_content) for c in target_contracts)
                        if contract_ok:
                            is_match = True
                else:
                    is_match = True

                if not is_match:
                    continue

                # 插入门禁与状态判断
                status = item.get("status", "pending")
                is_confirmed = status == "confirmed"
                is_expired = evidence_expired(item, project.deadline)

                if not is_confirmed:
                    can_insert = False
                    insert_disabled_reason = "未确认"
                    validity_status = "unconfirmed"
                elif is_expired:
                    can_insert = False
                    insert_disabled_reason = "已过期"
                    validity_status = "expired"
                else:
                    can_insert = True
                    insert_disabled_reason = ""
                    validity_status = "valid"

                records.append({
                    "id": item.get("id"),
                    "name": item_name,
                    "type": item_type,
                    "content": item_content,
                    "valid_until": item.get("valid_until") or item.get("valid_to"),
                    "confirm_status": status,
                    "status_label": "已确认" if is_confirmed else "待确认",
                    "validity_status": validity_status,
                    "can_insert": can_insert,
                    "insert_disabled_reason": insert_disabled_reason,
                })

            title = f"本公司资料 · {route.intent}"

        # 敏感信息脱敏掩码
        masked_records = mask_sensitive_payload(records)

        # 只要存在可插入的有效已确认记录，卡片整体即标记为支持插入
        card_can_insert = any(r.get("can_insert", False) for r in masked_records)
        card_disabled_reason = "" if card_can_insert else (
            masked_records[0].get("insert_disabled_reason") if masked_records else "暂无记录"
        )

        return AnswerCard(
            title=title,
            direct_query_domain=domain,
            direct_query_intent=route.intent or "结构化直查",
            direct_query_intent_version=route.intent_version,
            query_route=route.query_route,
            kb_enabled=route.kb_enabled,
            library_query_skipped=route.library_query_skipped,
            source=source_label,
            source_type="company_library",
            records=masked_records,
            total_count=len(masked_records),
            can_insert=card_can_insert,
            insert_disabled_reason=card_disabled_reason,
            notice=route.notice,
            disclaimer="系统直查 · 未经模型改写",
        )

    def insert_answer_card(
        self,
        principal: Principal,
        project_id: str,
        chapter_id: str,
        card_data: dict[str, Any] | AnswerCard,
        lease_token: str,
        item_id: str | None = None,
        insert_mode: str = "append",
        target_paragraph: str | None = None,
    ) -> dict[str, Any]:
        """
        落地 APP-M2-T183 插入为引用后台服务与流程：
        门禁 1（编辑锁守卫）：验证调用方持有目标章节的有效编辑租约（若无租约或租约过期，抛出 409/423 LOCK_LOST）
        门禁 2（卡片类型与资格拦截）：
          - 仅 source_type="company_library" 且 can_insert=True 的合格资料卡允许执行插入
          - 本项目数据卡（source_type="project_data"）严格禁止插入（抛出 403 FORBIDDEN）
          - 已过期（400 EVIDENCE_EXPIRED）、受限无权（403 FORBIDDEN）或未通过确认（400 EVIDENCE_NOT_USABLE）严格禁止插入
        门禁 3（引用标记与正文写入）：将资料内容格式化为带溯源标识的引用节点（[证:ID]），写入目标段落，正文 revision 自增
        门禁 4（增量复查标记）：插入完成后，章节状态触发“增量复查中”（incremental_check_status="pending"，章节状态“人工已处理”），生成版本历史变更记录
        """
        if hasattr(card_data, "to_dict"):
            card_dict = card_data.to_dict()
        else:
            card_dict = dict(card_data)

        # 门禁 2 前置校验：卡片类型与全局插入资格
        source_type = card_dict.get("source_type")
        if not source_type:
            domain = card_dict.get("direct_query_domain", "")
            if domain in ("tender_requirement", "project_fact", "response_matrix", "check_result"):
                source_type = "project_data"
            else:
                source_type = "company_library"

        if source_type == "project_data" or source_type != "company_library":
            raise DomainError(403, "FORBIDDEN", "本项目结构化数据卡禁止插入正文。")

        if not card_dict.get("can_insert", True):
            reason = card_dict.get("insert_disabled_reason", "")
            if "过期" in reason:
                raise DomainError(409, "EVIDENCE_EXPIRED", f"资料已过期，不可作为引用插入正文：{reason}")
            else:
                raise DomainError(409, "EVIDENCE_NOT_USABLE", f"资料不可引用，无法插入正文：{reason}")

        from .workflow import WorkflowService

        def operation(state: DemoState) -> dict[str, Any]:
            project = state.projects.get(project_id)
            if project is None or project.company_id != principal.user.company_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

            chapter = state.chapters.get(chapter_id)
            if chapter is None or chapter.project_id != project_id:
                raise DomainError(404, "NOT_FOUND", "未找到有权访问的章节。")

            # 角色权限校验：当前用户必须有该章节写权限
            from .project_access import require_chapter
            require_chapter(state, principal, chapter)

            # 门禁 1：验证独占编辑锁
            lease = chapter.lock
            now = self.demo._now()
            if (lease is None or lease.expires_at <= now
                    or lease.token != lease_token
                    or lease.owner_id != principal.user.id
                    or lease.session_token != principal.session_token):
                raise DomainError(423, "LOCK_LOST", "编辑权已失效，请重新取得编辑权后再操作。")

            # 门禁 2 深入校验：核查资料库记录实体的真实有效性
            target_item_id = item_id
            records = card_dict.get("records", [])
            if not target_item_id and records:
                target_item_id = records[0].get("id")

            domain = card_dict.get("direct_query_domain", "")
            item = None

            if domain == "sla":
                workflow = state.workflows.get(project_id, {})
                tmpl_id = target_item_id or workflow.get("sla")
                tmpl = state.sla_templates.get(tmpl_id) if tmpl_id else None
                if not tmpl:
                    for t in state.sla_templates.values():
                        if t.get("company_id") == principal.user.company_id:
                            tmpl = t
                            break
                if not tmpl or tmpl.get("company_id") != principal.user.company_id:
                    raise DomainError(404, "NOT_FOUND", "未找到对应的 SLA 服务承诺。")
                item = tmpl
                target_item_id = tmpl.get("id")
            else:
                if not target_item_id:
                    raise DomainError(409, "EVIDENCE_NOT_USABLE", "缺少资料记录ID，无法插入正文。")
                item = state.library.get(target_item_id)
                if not item or item.get("company_id") != principal.user.company_id:
                    raise DomainError(404, "NOT_FOUND", "未找到对应的资料记录。")

                if item.get("is_restricted") and not WorkflowService._restricted_allowed(state, principal, item):
                    raise DomainError(403, "FORBIDDEN", "无权访问受限资料，无法插入正文。")

                if item.get("status") != "confirmed":
                    raise DomainError(409, "EVIDENCE_NOT_USABLE", "资料未确认，不可作为引用插入正文。")

                if evidence_expired(item, project.deadline):
                    raise DomainError(409, "EVIDENCE_EXPIRED", "资料已过期，不可作为引用插入正文。")

            # 门禁 3：格式化引用节点与写入正文
            cite_tag = f"[证:{target_item_id}]"
            item_name = item.get("name") or item.get("template_name") or ""
            item_content = item.get("content", "")
            valid_until = item.get("valid_until") or item.get("valid_to") or ""

            if domain in ("person", "person_cert"):
                text = f"{item_content}（有效期至 {valid_until}）" if valid_until else item_content
            elif domain == "qualification":
                text = f"公司持有{item_name}（有效期至 {valid_until}）。" if valid_until else f"公司持有{item_name}。"
            elif domain == "contract":
                text = f"公司具备同类业绩：{item_name}（{item_content}）。"
            elif domain == "sla":
                levels = item.get("levels", [])
                lvl_str = "；".join(f"{l.get('level')}响应时限 {l.get('response_minutes')} 分钟" for l in levels[:2])
                text = f"公司提供 SLA 服务承诺：{item_name}（{lvl_str}）。"
            else:
                text = f"{item_name}：{item_content}"

            inserted_text = f"{cite_tag} {text}"

            old_content = chapter.content
            if insert_mode == "replace" and target_paragraph and target_paragraph in old_content:
                new_content = old_content.replace(target_paragraph, inserted_text, 1)
            elif insert_mode == "append" and target_paragraph and target_paragraph in old_content:
                idx = old_content.find(target_paragraph) + len(target_paragraph)
                new_content = old_content[:idx] + "\n" + inserted_text + old_content[idx:]
            else:
                if old_content.endswith("\n"):
                    new_content = old_content + inserted_text + "\n"
                else:
                    new_content = old_content + "\n" + inserted_text

            from .system_chapters import refuse_manual_edit
            refuse_manual_edit(state, chapter)
            chapter.content = new_content
            chapter.revision += 1
            state.projects[chapter.project_id].revision += 1

            citation = {
                "id": new_id("cite"),
                "source_type": "company_library",
                "item_id": target_item_id,
                "revision": item.get("revision", 1),
                "name": item_name,
                "tag": cite_tag,
                "cite_text": inserted_text,
                "basis": item_content,
                "created_at": iso_time(self.demo._now()),
                "actor_id": principal.user.id,
            }

            # 门禁 4：增量复查标记与版本历史变更
            version_entry = {
                "revision": chapter.revision,
                "content": chapter.content,
                "actor_id": principal.user.id,
                "actor_name": principal.user.name,
                "created_at": iso_time(self.demo._now()),
                "version_origin": "assistant_edit",
                "edit_mode": "insert_answer_card",
                "citation": citation,
                "incremental_check_status": "pending",
            }
            chapter.versions.append(version_entry)
            chapter.incremental_check_status = "pending"

            workflow = state.workflows.setdefault(project_id, {})
            chapter_status_map = workflow.setdefault("chapter_statuses", {})
            chapter_status_map[chapter.id] = "人工已处理"

            incremental_checks = workflow.setdefault("incremental_checks", {})
            incremental_checks[chapter.id] = {
                "chapter_id": chapter.id,
                "revision": chapter.revision,
                "status": "pending",
                "source_type": "证据",
                "operation_type": "insert_answer_card",
                "citation_id": citation["id"],
                "triggered_at": iso_time(self.demo._now()),
            }

            chapter.drafts.pop(principal.user.id, None)
            self.demo._audit(state, principal, chapter, "answer_card.insert", {
                "item_id": target_item_id,
                "revision": chapter.revision,
            })

            return {
                "chapter_id": chapter.id,
                "revision": chapter.revision,
                "content": chapter.content,
                "inserted_text": inserted_text,
                "citation": citation,
                "incremental_check_status": "pending",
                "chapter_status": "人工已处理",
            }

        return self.demo.repository.transaction(operation)

    def general_chat(
        self,
        principal: Principal,
        project_id: str,
        query: str,
        knowledge_base_enabled: bool = True,
        chapter_id: str | None = None,
        history: list[dict[str, str]] | None = None,
        chapter_title: str | None = None,
        selected_text: str | None = None,
        scene: str | None = None,
        lease_token: str | None = None,
        injected_tender_clauses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        落地 APP-M2-T179 自由问答（只“复制”与安全隔离）核心业务服务：
        门禁 1（禁止写入正文）：响应中 can_insert 恒定为 False，不返回写入或段落替换操作，action="copy_only"；
        门禁 2（知识库关闭常驻说明）：当 knowledge_base_enabled=False 时，严格禁止外呼 RAGFlow 检索公司库，
               并在回答中保持常驻说明“知识库已关闭，未查询公司资料库”，绝不编造虚假的公司资质或业绩数据；
        门禁 3（敏感项目模型隔离）：若当前项目为敏感项目（sensitive=True 或 is_sensitive=True），
               必须强制使用本地模型运行时；企图绑定或调用云端模型时，严格触发 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
        门禁 4（只读角色提问拦截）：只读角色（group_admin、viewer、auditor、platform_admin）尝试发起自由提问时，
               统一拦截拒绝（抛出 403 FORBIDDEN）。
        """
        # 若指定了编辑台选中文本、显式场景或注入条款，转由 EditorAIContextService 进行深度上下文联动
        if chapter_id and (selected_text is not None or scene is not None or injected_tender_clauses is not None):
            return self.demo.chat_editor_context(
                principal=principal,
                project_id=project_id,
                query=query,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                selected_text=selected_text,
                scene=scene,
                lease_token=lease_token,
                knowledge_base_enabled=knowledge_base_enabled,
                history=history,
                injected_tender_clauses=injected_tender_clauses,
            )

        # 门禁 4：只读角色提问前置拦截
        from .project_access import ROLE_NORMALIZATION_MAP, READONLY_SYSTEM_ROLES

        norm_role = ROLE_NORMALIZATION_MAP.get(principal.user.role, principal.user.role)
        if norm_role in READONLY_SYSTEM_ROLES:
            raise DomainError(403, "FORBIDDEN", "只读角色不可使用智能助手提问。")

        state: DemoState = self.demo.repository.read()
        project = state.projects.get(project_id)
        if project is None or project.company_id != principal.user.company_id:
            raise DomainError(404, "NOT_FOUND", "未找到有权访问的项目。")

        # 检查项目级只读分工
        team = state.project_teams.get(project_id, {})
        members = team.get("members", {})
        user_member = members.get(principal.user.id)
        if user_member and user_member.get("project_role") == "viewer":
            raise DomainError(403, "FORBIDDEN", "项目只读成员不可使用智能助手提问。")

        # 门禁 3：敏感项目模型隔离强校验
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

        # 收集上下文材料（章节、事实等）
        context_summary: dict[str, Any] = {
            "project_id": project.id,
            "project_name": project.name,
        }
        chapter = None
        if chapter_id:
            chapter = state.chapters.get(chapter_id)
            if chapter and chapter.project_id == project_id:
                context_summary["chapter_id"] = chapter.id
                context_summary["chapter_title"] = chapter.title
                context_summary["chapter_volume"] = chapter.volume

        # 检查是否命中直查意图（若命中且有卡片，支持返回直查卡；但 root 响应仍恒定 copy_only）
        route = resolve_assistant_query_route(query, knowledge_base_enabled)
        answer_card_payload = None
        if route.query_route == "direct_query":
            card = self.assemble_answer_card(principal, project_id, query, route)
            if card and len(card.records) > 0:
                answer_card_payload = card.to_dict()

        # 门禁 2：知识库关闭常驻说明与检索拦截
        citations: list[dict[str, Any]] = []
        if not knowledge_base_enabled:
            # 严格禁止外呼 RAGFlow 检索公司库！
            query_route = "no_retrieval"
            library_query_skipped = True
            notice = "知识库已关闭，未查询公司资料库"
            citations = []
        else:
            query_route = "kb_retrieval" if not answer_card_payload else "direct_query"
            library_query_skipped = False
            notice = None
            # 知识库开启时：按需从证据服务检索候选切片
            if hasattr(self.demo, "evidence_service") and self.demo.evidence_service:
                try:
                    candidates = self.demo.evidence_service.search(project.company_id, query)
                    for c in (candidates or [])[:5]:
                        citations.append({
                            "id": getattr(c, "id", str(c)),
                            "name": getattr(c, "name", "资料片段"),
                            "type": getattr(c, "record_type", "snippet"),
                            "source_type": "company_library",
                        })
                except Exception:
                    citations = []

        # 调用模型生成回答
        provider = self.demo.resolve_model_provider(state, project.id)
        system_prompt = (
            "你是一名专业的投标文件编写智能助手。当前处于自由问答模式，请针对用户的提问提供严谨、专业、合规的解答。\n"
            "原则要求：\n"
            "1. 本回答仅供参考与复制，不能直接作为正式章节内容插入；\n"
            "2. 若知识库未开启或未检索到公司资料，严禁自行捏造虚假的公司资质编号、人员身份或业绩合同。"
        )

        user_content_parts = [f"用户提问：{query}"]
        if not knowledge_base_enabled:
            user_content_parts.append("【系统提示】：知识库已关闭，未查询公司资料库。请基于通用知识和已知项目上下文回答。")
        elif citations:
            cite_desc = "；".join(f"[{c['id']}] {c['name']}" for c in citations)
            user_content_parts.append(f"【参考证据】：{cite_desc}")

        if chapter:
            user_content_parts.append(f"【当前章节】：{chapter.title}（{chapter.volume}）")

        user_content = "\n".join(user_content_parts)

        try:
            if provider is not None and hasattr(provider, "suggest"):
                raw_reply = provider.suggest(system_prompt, user_content)
                if not isinstance(raw_reply, str):
                    raw_reply = str(raw_reply)
            else:
                raw_reply = f"关于“{query}”，建议结合本项目实际需求与招标文件条款进行编制与核对。"
        except DomainError:
            raise
        except Exception as error:
            raise DomainError(502, "MODEL_UNAVAILABLE", "智能助手回答服务暂时不可用，请稍后重试。") from error

        # 确保门禁 2 语义完整：若知识库关闭，回答中保持常驻说明“知识库已关闭，未查询公司资料库”
        if not knowledge_base_enabled:
            if "知识库已关闭" not in raw_reply:
                reply = f"{raw_reply}\n\n（说明：知识库已关闭，未查询公司资料库）"
            else:
                reply = raw_reply
        else:
            reply = raw_reply

        # 门禁 1（禁止写入正文）：can_insert 恒定为 False，action="copy_only"
        return {
            "query": query,
            "reply": reply,
            "query_route": query_route,
            "kb_enabled": knowledge_base_enabled,
            "library_query_skipped": library_query_skipped,
            "notice": notice,
            "can_insert": False,
            "insert_disabled_reason": "自由问答仅供参考与复制，不可直接插入正文",
            "action": "copy_only",
            "citations": citations,
            "context_summary": context_summary,
            "answer_card": answer_card_payload,
        }

    ask_assistant = general_chat

    def search_tender_slices(
        self,
        principal: Principal,
        project_id: str,
        query: str,
        enabled: bool | None = None,
        top_k: int = 10,
        clause_type: str | None = None,
    ) -> dict[str, Any]:
        search_service = getattr(self.demo, "tender_retrieval", None)
        if search_service is None:
            from icg.infra.tender_retrieval import TenderRetrievalService
            search_service = TenderRetrievalService(self.demo)
            self.demo.tender_retrieval = search_service
        return search_service.search(
            principal=principal,
            project_id=project_id,
            query=query,
            enabled=enabled,
            top_k=top_k,
            clause_type=clause_type,
        ).to_dict()

    def editor_context_chat(
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
        return self.demo.chat_editor_context(
            principal=principal,
            project_id=project_id,
            query=query,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            selected_text=selected_text,
            scene=scene,
            lease_token=lease_token,
            knowledge_base_enabled=knowledge_base_enabled,
            history=history,
            injected_tender_clauses=injected_tender_clauses,
        )
