# 为什么有这个文件：验证智能对话助手直查未命中与常规回答回退机制（APP-M2-T182，ISSUE-007，PRD v1.8 §5.11.15）。
# 它解决什么问题：
# 1. 结构化直查未命中优雅降级：当命中直查意图但在项目事实/招标文件/公司资料中查无对应条目时，
#    严禁编造虚假答案卡（answer_card 必须为 None），优雅回退为常规问答（开启KB走检索，关闭KB走自身生成）。
# 2. 回退提示语规范：
#    - 本项目结构化数据未命中且KB开启：提示“本项目结构化数据中未查询到对应条目，已转入常规助手解答”，query_route="kb_retrieval"；
#    - 本项目结构化数据未命中且KB关闭：提示“本项目结构化数据中未查询到对应条目，已转入常规助手解答。知识库已关闭，未查询公司资料库”，query_route="no_retrieval"；
#    - 本公司资料未命中且KB开启：提示“本公司资料库中未查询到对应结构化记录，已转入知识库检索解答”，query_route="kb_retrieval"；
#    - 本公司资料且KB关闭：跳过查询置 library_query_skipped=True，提示“知识库已关闭，未查询公司资料库”，query_route="no_retrieval"。
# 3. 知识库关闭常驻说明一致性：只要知识库处于关闭状态，常规问答及回退回答均常驻说明“知识库已关闭，未查询公司资料库”。
# 4. 契约防线与租户隔离：保持 143 错误码集不变，非本项目或跨租户访问严格阻止。

import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import AnswerCardService
from icg_demo.domain import DemoService, Principal
from icg_demo.ports import ParserProvider
from icg_demo.workflow import WorkflowService


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


@pytest.fixture
def fallback_setup():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"

    # 初始化 alpha 项目工作流数据：仅包含“投标保证金”要求与“服务期限”项目事实
    workflow = state.workflows.setdefault(project.id, {
        "files": {},
        "requirements": {
            "req-001": {
                "id": "req-001",
                "text": "★技术要求：投标人应缴纳投标保证金人民币20万元整。",
                "category": "商务",
                "status": "confirmed",
                "response": "20万元整",
                "unit": "万元",
                "source": {"file_id": "file-1", "page": 4},
            },
        },
        "facts": {
            "fact-001": {
                "id": "fact-001",
                "key": "服务期限",
                "value": "12个月",
                "status": "confirmed",
                "unit": "月",
                "source_type": "parsed",
            },
            "fact-002": {
                "id": "fact-002",
                "key": "最高限价",
                "value": "500万元",
                "status": "pending",
                "unit": "万元",
                "source_type": "parsed",
            },
        },
        "conflicts": {},
        "checks": {},
        "candidates": {},
        "exports": {},
        "parse_confirmed": True,
        "plan_confirmed": True,
    })

    # 初始化公司资料库：仅包含张三的 Oracle 证书
    state.library.update({
        "lib-cert-zhangsan": {
            "id": "lib-cert-zhangsan",
            "company_id": "alpha",
            "name": "张三 Oracle OCP 认证",
            "type": "person_cert",
            "content": "持证人张三，身份证号：110101199003071234，持有 Oracle OCP 认证。",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
    })

    # 初始化 SLA 模板：仅 1-4 级故障时限
    state.sla_templates["sla-alpha-standard"] = {
        "id": "sla-alpha-standard",
        "company_id": "alpha",
        "name": "标准SLA保障承诺",
        "levels": [
            {"level": "一级", "response_minutes": 15, "arrive_hours": 2, "resolve_hours": 4},
            {"level": "二级", "response_minutes": 30, "arrive_hours": 4, "resolve_hours": 8},
        ],
    }

    repo = MemoryRepository(state)
    demo = DemoService(repo, None)
    wf_svc = WorkflowService(demo, DummyParser())
    answer_svc = AnswerCardService(demo)

    principal_editor = Principal(state.accounts["alpha-editor"], "session-alpha-editor")
    principal_beta = Principal(state.accounts["beta-editor"], "session-beta-editor")

    return {
        "state": state,
        "project": project,
        "answer_svc": answer_svc,
        "workflow_svc": wf_svc,
        "principal_editor": principal_editor,
        "principal_beta": principal_beta,
    }


# ============================================================================
# 1. 本项目结构化数据未命中降级测试（知识库开 vs 关）
# ============================================================================

def test_project_fact_unhit_fallback_kb_on(fallback_setup):
    """项目事实未命中（如交付地点）且知识库开启：回退到 kb_retrieval，绝不编造虚假卡片。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "请问本项目交付地点在何处？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert reply["library_query_skipped"] is False
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in reply["notice"]


def test_project_fact_unhit_fallback_kb_off(fallback_setup):
    """项目事实未命中且知识库关闭：回退到 no_retrieval，携带常驻关闭说明，绝不编造虚假卡片。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "请问本项目交付地点在何处？", knowledge_base_enabled=False)

    assert reply["query_route"] == "no_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert reply["library_query_skipped"] is False
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in reply["notice"]
    assert "知识库已关闭，未查询公司资料库" in reply["notice"]


def test_tender_requirement_unhit_fallback(fallback_setup):
    """招标文件条款未命中（如开标时间未在要求表中）回退验证。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    # 1. 知识库开启时
    reply_on = svc.process_query(principal, project.id, "本项目开标时间是哪天？", knowledge_base_enabled=True)
    assert reply_on["query_route"] == "kb_retrieval"
    assert reply_on["fallback_to_general"] is True
    assert reply_on["answer_card"] is None
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in reply_on["notice"]

    # 2. 知识库关闭时
    reply_off = svc.process_query(principal, project.id, "本项目开标时间是哪天？", knowledge_base_enabled=False)
    assert reply_off["query_route"] == "no_retrieval"
    assert reply_off["fallback_to_general"] is True
    assert reply_off["answer_card"] is None
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in reply_off["notice"]
    assert "知识库已关闭，未查询公司资料库" in reply_off["notice"]


# ============================================================================
# 2. 本公司资料库未命中降级测试（知识库开 vs 关）
# ============================================================================

def test_company_library_person_unhit_fallback_kb_on(fallback_setup):
    """公司人员/证书未命中（查询资料库不存在的赵六）：转入知识库检索解答，绝不编造虚假卡片。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "赵六有哪些证书？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert reply["library_query_skipped"] is False
    assert "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" in reply["notice"]


def test_company_library_cert_unhit_fallback_kb_on(fallback_setup):
    """公司特定证书未命中（查询未持有的 CISP 证书）：转入知识库检索解答。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "公司是否有CISP安全认证证书？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" in reply["notice"]


def test_company_library_qualification_unhit_fallback_kb_on(fallback_setup):
    """企业资质未命中（查询未持有的 CMMI 认证）：转入知识库检索解答。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "公司有CMMI5资质认证吗？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" in reply["notice"]


def test_company_library_contract_unhit_fallback_kb_on(fallback_setup):
    """同类业绩未命中（公司无三甲医院业绩）：转入知识库检索解答。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "公司有哪些三甲医院同类业绩合同？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" in reply["notice"]


def test_company_library_sla_unhit_fallback_kb_on(fallback_setup):
    """SLA等级未命中（查询不存在的特级故障响应）：转入知识库检索解答。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "特级故障响应时限承诺是多少？", knowledge_base_enabled=True)

    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert "本公司资料库中未查询到对应结构化记录，已转入知识库检索解答" in reply["notice"]


def test_company_library_query_kb_off_skipped(fallback_setup):
    """公司资料意图在知识库关闭时：跳过查询置 library_query_skipped=True，提示常驻说明，无答案卡。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    reply = svc.process_query(principal, project.id, "赵六有哪些证书？", knowledge_base_enabled=False)

    assert reply["query_route"] == "no_retrieval"
    assert reply["library_query_skipped"] is True
    assert reply["answer_card"] is None
    assert "知识库已关闭，未查询公司资料库" in reply["notice"]


# ============================================================================
# 3. 知识库关闭常驻说明一致性与常规提问回退验证
# ============================================================================

def test_kb_disabled_persistent_notice_consistency(fallback_setup):
    """验证知识库关闭时，各类常规提问与回退问答均携带统一常驻提示。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    # 1. 常规自由提问 + 知识库关闭
    general_reply = svc.process_query(principal, project.id, "如何撰写投标方案售后服务章节？", knowledge_base_enabled=False)
    assert general_reply["query_route"] == "no_retrieval"
    assert general_reply["answer_card"] is None
    assert "知识库已关闭，未查询公司资料库" in general_reply["notice"]

    # 2. 项目事实直查未命中 + 知识库关闭
    fact_miss = svc.process_query(principal, project.id, "本项目交付地点是哪里？", knowledge_base_enabled=False)
    assert fact_miss["query_route"] == "no_retrieval"
    assert fact_miss["answer_card"] is None
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in fact_miss["notice"]
    assert "知识库已关闭，未查询公司资料库" in fact_miss["notice"]

    # 3. 公司资料直查 + 知识库关闭
    company_miss = svc.process_query(principal, project.id, "张三有哪些Oracle证书？", knowledge_base_enabled=False)
    assert company_miss["query_route"] == "no_retrieval"
    assert company_miss["library_query_skipped"] is True
    assert company_miss["answer_card"] is None
    assert "知识库已关闭，未查询公司资料库" in company_miss["notice"]


# ============================================================================
# 4. WorkflowService 委派调用验证与跨租户安全门禁
# ============================================================================

def test_workflow_service_fallback_delegation(fallback_setup):
    """验证 WorkflowService 顶层入口透传未命中回退。"""
    wf_svc: WorkflowService = fallback_setup["workflow_svc"]
    principal = fallback_setup["principal_editor"]
    project = fallback_setup["project"]

    # 验证未命中降级响应
    reply = wf_svc.assistant_query(principal, project.id, "本项目交付地点在哪？", knowledge_base_enabled=True)
    assert reply["query_route"] == "kb_retrieval"
    assert reply["fallback_to_general"] is True
    assert reply["answer_card"] is None
    assert "本项目结构化数据中未查询到对应条目，已转入常规助手解答" in reply["notice"]


def test_cross_tenant_access_rejection(fallback_setup):
    """跨租户访问项目，严格按 143 错误码集拒绝（404 NOT_FOUND）。"""
    svc: AnswerCardService = fallback_setup["answer_svc"]
    principal_beta = fallback_setup["principal_beta"]
    project = fallback_setup["project"]

    with pytest.raises(Exception) as exc_info:
        svc.process_query(principal_beta, project.id, "本项目交付地点在哪？", knowledge_base_enabled=True)
    assert "NOT_FOUND" in str(exc_info.value) or "未找到有权访问的项目" in str(exc_info.value)
