# 为什么有这个文件：验证智能对话助手答案卡与意图分流（APP-M2-T181）。
# 它解决什么问题：
# 1. 验证意图类别 × 知识库开关 4 种组合表格驱动测试；
# 2. 验证知识库关闭时本项目数据依然直出，而公司资料直查跳过并置 library_query_skipped=True；
# 3. 验证身份证号码（18位）自动脱敏掩码为 110101********1234；
# 4. 验证答案卡插入门禁：本项目数据一律 can_insert=False，仅已确认且未过期的公司资料可 can_insert=True；
# 5. 验证受限资料权限过滤与跨公司租户隔离。

import pytest

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.answer_card import (
    AnswerCardService,
    classify_query_intent,
    mask_id_card,
    mask_sensitive_payload,
    resolve_assistant_query_route,
)
from icg_demo.domain import DemoService, Principal
from icg_demo.ports import ParserProvider
from icg_demo.workflow import WorkflowService


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


@pytest.fixture
def test_setup():
    state = seed_state()
    project = state.projects["alpha-project"]
    project.deadline = "2026-12-31T17:00:00+08:00"

    # 初始化 alpha 项目工作流数据
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
            "req-002": {
                "id": "req-002",
                "text": "服务期要求：本项目服务期限为12个月。",
                "category": "商务",
                "status": "pending",
                "response": "12个月",
                "unit": "月",
                "source": {"file_id": "file-1", "page": 5},
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
        "conflicts": {
            "服务期限": {
                "key": "服务期限",
                "choices": [
                    {"value": "12个月", "page": 5},
                    {"value": "24个月", "page": 18},
                ],
            }
        },
        "checks": {
            "chk-001": {
                "id": "chk-001",
                "passed": False,
                "issues": [
                    {"code": "FACT_MISMATCH", "severity": "high", "message": "服务期限前后不一致"}
                ],
            }
        },
        "candidates": {},
        "exports": {},
        "parse_confirmed": True,
        "plan_confirmed": True,
    })

    # 初始化公司资料库
    state.library.update({
        # 有效已确认证书（含真实 18 位身份证）
        "lib-cert-valid": {
            "id": "lib-cert-valid",
            "company_id": "alpha",
            "name": "张三 Oracle OCP 认证",
            "type": "person_cert",
            "content": "持证人张三，身份证号：110101199003071234，持有 Oracle OCP 认证，专业数据库运维工程师。",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        # 未确认证书
        "lib-cert-pending": {
            "id": "lib-cert-pending",
            "company_id": "alpha",
            "name": "李四 PMP 认证",
            "type": "person_cert",
            "content": "持证人李四，身份证号：110101199205105678，持有 PMP 证书。",
            "status": "pending",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
        # 已过期证书（早于 project.deadline 2026-12-31）
        "lib-cert-expired": {
            "id": "lib-cert-expired",
            "company_id": "alpha",
            "name": "王五 软考高级网络规划设计师",
            "type": "person_cert",
            "content": "持证人王五，身份证号：110101198808129999，持有软考高级证书。",
            "status": "confirmed",
            "valid_until": "2025-06-30",
            "is_restricted": False,
            "revision": 1,
        },
        # 受限资质文件
        "lib-qual-restricted": {
            "id": "lib-qual-restricted",
            "company_id": "alpha",
            "name": "甲公司涉密资质认证",
            "type": "qualification",
            "content": "甲公司持有涉密信息系统集成乙级资质。",
            "status": "confirmed",
            "valid_until": "2028-12-31",
            "is_restricted": True,
            "revision": 1,
        },
        # 乙公司资料（用于跨租户隔离验证）
        "lib-beta-cert": {
            "id": "lib-beta-cert",
            "company_id": "beta",
            "name": "乙公司专属资质",
            "type": "qualification",
            "content": "乙公司独有资质",
            "status": "confirmed",
            "valid_until": "2027-12-31",
            "is_restricted": False,
            "revision": 1,
        },
    })

    repo = MemoryRepository(state)
    demo = DemoService(repo, None)
    workflow_svc = WorkflowService(demo, DummyParser())
    answer_svc = AnswerCardService(demo)

    principal_editor = Principal(state.accounts["alpha-editor"], "session-alpha-editor")
    principal_admin = Principal(state.accounts["alpha-company-admin"], "session-alpha-admin")
    principal_beta = Principal(state.accounts["beta-editor"], "session-beta-editor")

    return {
        "state": state,
        "project": project,
        "answer_svc": answer_svc,
        "workflow_svc": workflow_svc,
        "principal_editor": principal_editor,
        "principal_admin": principal_admin,
        "principal_beta": principal_beta,
    }


# ============================================================================
# 1. 意图类别 × 知识库开关 4 种组合表格驱动测试
# ============================================================================

@pytest.mark.parametrize("query,kb_enabled,expected_route,expected_skipped,expected_has_card,expected_can_insert,expected_notice_sub", [
    # 组合 1：项目类意图 + 知识库开启 -> 正常直查答案卡，can_insert=False
    ("请问本项目投标保证金是多少？", True, "direct_query", False, True, False, None),
    # 组合 2：项目类意图 + 知识库关闭 -> 依然直查答案卡，can_insert=False，标注来自本项目结构化数据
    ("请问本项目投标保证金是多少？", False, "direct_query", False, True, False, "知识库已关闭，本卡来自本项目结构化数据"),
    # 组合 3：公司类意图 + 知识库开启 -> 正常直查答案卡，合法已确认证书 can_insert=True
    ("张三有哪些Oracle证书？", True, "direct_query", False, True, True, None),
    # 组合 4：公司类意图 + 知识库关闭 -> 跳过直查并记录 skipped=True，无答案卡，提示知识库已关闭
    ("张三有哪些Oracle证书？", False, "no_retrieval", True, False, False, "知识库已关闭，未查询公司资料库"),
    # 对照组 5：常规提问（无直查意图） + 知识库开启 -> 知识库检索
    ("请问如何撰写数据库高可用方案？", True, "kb_retrieval", False, False, False, None),
    # 对照组 6：常规提问（无直查意图） + 知识库关闭 -> 无检索问答
    ("请问如何撰写数据库高可用方案？", False, "no_retrieval", False, False, False, None),
])
def test_intent_category_and_kb_switch_matrix(test_setup, query, kb_enabled, expected_route,
                                              expected_skipped, expected_has_card, expected_can_insert,
                                              expected_notice_sub):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    reply = svc.process_query(principal, project.id, query, knowledge_base_enabled=kb_enabled)

    assert reply["query_route"] == expected_route
    assert reply["library_query_skipped"] is expected_skipped

    if expected_has_card:
        card = reply["answer_card"]
        assert card is not None
        assert card["query_route"] == "direct_query"
        assert card["can_insert"] is expected_can_insert
        assert len(card["records"]) > 0
    else:
        assert reply["answer_card"] is None

    if expected_notice_sub:
        assert reply["notice"] is not None
        assert expected_notice_sub in reply["notice"]
        if reply["answer_card"]:
            assert expected_notice_sub in (reply["answer_card"].get("notice") or "")


# ============================================================================
# 2. 知识库关闭时本项目数据正常直出与公司资料 skipped=True 标示
# ============================================================================

def test_kb_disabled_project_data_available_and_library_skipped(test_setup):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    # 1. 问项目事实（服务期限）：即使知识库关闭，仍然返回项目事实答案卡
    fact_reply = svc.process_query(principal, project.id, "本项目服务期限是多久？", knowledge_base_enabled=False)
    assert fact_reply["query_route"] == "direct_query"
    assert fact_reply["library_query_skipped"] is False
    assert fact_reply["answer_card"] is not None
    assert fact_reply["answer_card"]["direct_query_domain"] == "project_fact"
    assert fact_reply["answer_card"]["can_insert"] is False
    assert "知识库已关闭，本卡来自本项目结构化数据" in fact_reply["answer_card"]["notice"]

    # 2. 问企业资质：知识库关闭时，必须跳过资料库查询，标记 library_query_skipped=True，不返回答案卡
    qual_reply = svc.process_query(principal, project.id, "公司有哪些企业资质？", knowledge_base_enabled=False)
    assert qual_reply["query_route"] == "no_retrieval"
    assert qual_reply["library_query_skipped"] is True
    assert qual_reply["answer_card"] is None
    assert "知识库已关闭，未查询公司资料库" in qual_reply["notice"]


# ============================================================================
# 3. 敏感信息（身份证号）脱敏掩码验证
# ============================================================================

def test_id_card_masking_function():
    raw_text = "工程师张三（身份证：110101199003071234）持有OCP证书，李四身份证为44030119851212888X。"
    masked = mask_id_card(raw_text)
    assert "110101199003071234" not in masked
    assert "44030119851212888X" not in masked
    assert "110101********1234" in masked
    assert "440301********888X" in masked

    # 结构化递归脱敏
    payload = {
        "person": {"name": "张三", "id_number": "110101199003071234"},
        "history": ["持证人110101199003071234参加培训"],
    }
    masked_payload = mask_sensitive_payload(payload)
    assert masked_payload["person"]["id_number"] == "110101********1234"
    assert "110101********1234" in masked_payload["history"][0]


def test_id_card_masking_in_answer_card(test_setup):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    reply = svc.process_query(principal, project.id, "查询张三人员证书", knowledge_base_enabled=True)
    card = reply["answer_card"]
    assert card is not None

    # 验证答案卡内容中绝对不包含明文身份证号
    card_str = str(card)
    assert "110101199003071234" not in card_str
    assert "110101********1234" in card_str


# ============================================================================
# 4. can_insert 门禁与防篡改规则
# ============================================================================

def test_can_insert_gates_for_project_and_company_records(test_setup):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    # 规则 1：本项目结构化数据（招标要求、项目事实、检查结果）永远 can_insert=False
    req_reply = svc.process_query(principal, project.id, "查询招标要求投标保证金", knowledge_base_enabled=True)
    req_card = req_reply["answer_card"]
    assert req_card["can_insert"] is False
    assert req_card["insert_disabled_reason"] == "本项目数据不插入正文"

    chk_reply = svc.process_query(principal, project.id, "检查结果有哪些阻断项？", knowledge_base_enabled=True)
    chk_card = chk_reply["answer_card"]
    assert chk_card["can_insert"] is False
    assert chk_card["insert_disabled_reason"] == "本项目数据不插入正文"

    # 规则 2：公司资料库中的不同状态门禁
    # 查询人员证书，同时召回了张三（有效已确认）、李四（未确认）和王五（已过期）
    cert_reply = svc.process_query(principal, project.id, "查询人员证书列表", knowledge_base_enabled=True)
    cert_card = cert_reply["answer_card"]
    records = {r["name"]: r for r in cert_card["records"]}

    # 张三（已确认且有效）：can_insert=True
    assert "张三 Oracle OCP 认证" in records
    zhangsan = records["张三 Oracle OCP 认证"]
    assert zhangsan["can_insert"] is True
    assert zhangsan["confirm_status"] == "confirmed"
    assert zhangsan["validity_status"] == "valid"

    # 李四（未确认）：can_insert=False，注明“未确认”
    assert "李四 PMP 认证" in records
    lisi = records["李四 PMP 认证"]
    assert lisi["can_insert"] is False
    assert lisi["insert_disabled_reason"] == "未确认"

    # 王五（已过期）：can_insert=False，注明“已过期”
    assert "王五 软考高级网络规划设计师" in records
    wangwu = records["王五 软考高级网络规划设计师"]
    assert wangwu["can_insert"] is False
    assert wangwu["insert_disabled_reason"] == "已过期"


# ============================================================================
# 5. 项目事实抽取冲突展示
# ============================================================================

def test_project_fact_conflict_display(test_setup):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    reply = svc.process_query(principal, project.id, "查询项目事实服务期限", knowledge_base_enabled=True)
    card = reply["answer_card"]
    assert card is not None
    assert card["direct_query_domain"] == "project_fact"

    records = card["records"]
    service_period = next((r for r in records if r["key"] == "服务期限"), None)
    assert service_period is not None

    # 有冲突时，标“有冲突，待项目负责人选定”，并并列显示冲突取值和页码
    assert service_period["has_conflict"] is True
    assert service_period["status_label"] == "有冲突，待项目负责人选定"
    assert len(service_period["conflict_choices"]) == 2
    assert service_period["conflict_choices"][0]["value"] == "12个月"
    assert service_period["conflict_choices"][0]["page"] == 5
    assert service_period["conflict_choices"][1]["value"] == "24个月"
    assert service_period["conflict_choices"][1]["page"] == 18


# ============================================================================
# 6. 受限资料与跨公司隔离
# ============================================================================

def test_restricted_evidence_and_cross_company_isolation(test_setup):
    svc: AnswerCardService = test_setup["answer_svc"]
    principal_editor = test_setup["principal_editor"]
    principal_admin = test_setup["principal_admin"]
    principal_beta = test_setup["principal_beta"]
    project = test_setup["project"]

    # 1. 普通编写人（未获授权）查询资质：不出现受限资质，且不泄露其存在
    editor_reply = svc.process_query(principal_editor, project.id, "查询甲公司企业资质", knowledge_base_enabled=True)
    editor_card = editor_reply["answer_card"]
    assert editor_card is not None
    assert not any("涉密资质" in r["name"] for r in editor_card["records"])

    # 2. 公司管理员查询资质：可见受限资质
    admin_reply = svc.process_query(principal_admin, project.id, "查询甲公司企业资质", knowledge_base_enabled=True)
    admin_card = admin_reply["answer_card"]
    assert admin_card is not None
    assert any("涉密资质" in r["name"] for r in admin_card["records"])

    # 3. 乙公司人员绝对查不到甲公司的任何资料卡
    with pytest.raises(Exception):
        # 乙公司访问甲公司项目，抛出 404 NOT_FOUND 阻止
        svc.process_query(principal_beta, project.id, "查询人员证书", knowledge_base_enabled=True)


# ============================================================================
# 7. WorkflowService 对接验证
# ============================================================================

def test_workflow_service_assistant_query_delegation(test_setup):
    wf_svc: WorkflowService = test_setup["workflow_svc"]
    principal = test_setup["principal_editor"]
    project = test_setup["project"]

    reply = wf_svc.assistant_query(principal, project.id, "本项目投标保证金是多少？", knowledge_base_enabled=False)
    assert reply["query_route"] == "direct_query"
    assert reply["answer_card"] is not None
    assert reply["answer_card"]["can_insert"] is False
