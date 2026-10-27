# 为什么有这个文件：独立测试大纲评分项分值权重加权与章节优先级智能排序引擎（AI-OUTLINE-SCORE-WEIGHT-CALC）。
# 它解决什么问题：
# 1. 分值权重精确计算：测试基于真实招标文件评分条款的分值累加、全标权重比与分册内权重比；
# 2. 综合优先级与智能队列：测试一票否决红线（bonus 100）、★关键必保（bonus 60）、高分值（bonus 30）、中分值（bonus 15）梯度加权与排序；
# 3. 严格防编造与依据可追溯：测试分值严格源自真实解析条款，分值为零/缺失时的除零鲁棒性；
# 4. 自动大纲树构建深度集成：测试 auto_build_outline_tree 正确回写分值权重与推荐编写序列至工作流与大纲元数据；
# 5. 多租户强隔离门禁：验证跨租户操作严密拦截并抛出 404 NOT_FOUND；
# 6. RBAC 权限门禁：验证只读角色及项目只读成员拦截 403 FORBIDDEN；
# 7. 涉密项目本地模型门禁：验证涉密项目使用云端外部模型拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
# 8. HTTP API 端点集成：验证 POST /score-weights 与 GET /recommended-order 端点契约。

from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.domain import Chapter, DemoService, DomainError, Principal, iso_time, new_id
from icg.domain.outline_auto_tree import (
    AutoTreeBuildEngine,
    calculate_score_weights_and_priorities,
)
from icg.domain.outline_service import OutlinePlanService
from icg.domain.ports import ModelProvider, ParserProvider
from icg.domain.workflow import WorkflowService
from icg.api.workflow import include_workflow_routes


class DummyParser(ParserProvider):
    def parse(self, filename: str, content: bytes) -> dict:
        return {"title": "测试文件", "pagination": "none", "pages": [], "warnings": []}


class MockLocalModelProvider(ModelProvider):
    name = "mock-local-qwen"
    is_real_model = True
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return "本地模型结构化大纲优化建议"


class MockCloudModelProvider(ModelProvider):
    name = "mock-cloud-model"
    is_real_model = True
    is_local = False

    def suggest(self, instruction: str, content: str) -> str:
        return "云端外部模型建议"


@pytest.fixture
def test_env():
    state = seed_state()
    repo = MemoryRepository()
    repo.transaction(lambda s: s.__dict__.update(state.__dict__))
    demo = DemoService(repo, MockLocalModelProvider())
    demo.outline_service = OutlinePlanService(demo)

    # 预置包含真实评分项的解析需求矩阵
    def init_wf(s):
        wf = s.workflows.setdefault("alpha-project", {})
        wf["parse_confirmed"] = True
        wf["requirements"] = {
            "req-biz-01": {
                "id": "req-biz-01",
                "clause": "投标人须具备有效营业执照及法定代表人身份证明",
                "category": "commercial",
                "volume": "business",
                "score": 5.0,
                "scoring_criteria": "资质证件齐全合规得5分",
                "status": "confirmed",
            },
            "req-biz-02": {
                "id": "req-biz-02",
                "clause": "投标人近三年审计报告财务状况良好，资产负债率不高于60%",
                "category": "commercial",
                "volume": "business",
                "score": 15.0,
                "scoring_criteria": "财务状况优良得15分",
                "status": "confirmed",
            },
            "req-tech-01": {
                "id": "req-tech-01",
                "clause": "系统总体技术拓扑与微服务分布式架构方案",
                "category": "technical",
                "volume": "technical",
                "score": 30.0,
                "scoring_criteria": "架构设计先进合理得30分",
                "status": "confirmed",
            },
            "req-tech-02": {
                "id": "req-tech-02",
                "clause": "★ 系统须提供跨机房高可用双活容灾方案，RPO=0，RTO<30s",
                "category": "technical",
                "volume": "technical",
                "mandatory": True,
                "asterisk": True,
                "score": 20.0,
                "scoring_criteria": "具备双活容灾且满足指标得20分，不满足不得分",
                "status": "confirmed",
            },
            "req-tech-03": {
                "id": "req-tech-03",
                "clause": "核心系统不满足国家等保三级认证者一票否决废标",
                "category": "security",
                "volume": "technical",
                "disqualified": True,
                "score": 0.0,
                "scoring_criteria": "必须提供等保三级证书，未提供直接废标",
                "status": "confirmed",
            },
            "req-serv-01": {
                "id": "req-serv-01",
                "clause": "提供7x24小时本地化驻场运维服务，响应时间不超过15分钟",
                "category": "service",
                "volume": "technical",
                "score": 10.0,
                "scoring_criteria": "符合SLA服务保障承诺得10分",
                "status": "confirmed",
            },
        }

    repo.transaction(init_wf)
    return {
        "repo": repo,
        "demo": demo,
        "service": demo.outline_service,
        "principals": {
            "manager": Principal(state.accounts["alpha-manager"], "tok-alpha-manager"),
            "editor": Principal(state.accounts["alpha-editor"], "tok-alpha-editor"),
            "viewer": Principal(state.accounts["alpha-viewer"], "tok-alpha-viewer"),
            "auditor": Principal(state.accounts["alpha-auditor"], "tok-alpha-auditor"),
            "outsider": Principal(state.accounts["beta-editor"], "tok-beta-editor"),
        },
    }


# ==================== 1. 独立算法单元测试 ====================

def test_calculate_score_weights_and_priorities_standalone():
    """测试分值权重与综合优先级排序独立计算算法。"""
    leaves = [
        {
            "id": "ch-tech-arch",
            "section_number": "1.1",
            "title": "系统总体架构设计",
            "volume": "technical",
            "scoring_rows": [{"id": "r1", "score": 30.0}],
            "has_asterisk": False,
            "has_disqualified": False,
        },
        {
            "id": "ch-tech-sec",
            "section_number": "1.2",
            "title": "关键安全防护方案",
            "volume": "technical",
            "scoring_rows": [{"id": "r2", "score": 20.0}],
            "has_asterisk": True,
            "has_disqualified": False,
        },
        {
            "id": "ch-tech-disq",
            "section_number": "1.3",
            "title": "等保三级合规声明",
            "volume": "technical",
            "scoring_rows": [{"id": "r3", "score": 0.0}],
            "has_asterisk": False,
            "has_disqualified": True,
        },
        {
            "id": "ch-biz-audit",
            "section_number": "2.1",
            "title": "财务审计证明",
            "volume": "business",
            "scoring_rows": [{"id": "r4", "score": 15.0}],
            "has_asterisk": False,
            "has_disqualified": False,
        },
        {
            "id": "ch-biz-reg",
            "section_number": "2.2",
            "title": "营业执照证明",
            "volume": "business",
            "scoring_rows": [{"id": "r5", "score": 5.0}],
            "has_asterisk": False,
            "has_disqualified": False,
        },
        {
            "id": "ch-biz-supp",
            "section_number": "2.3",
            "title": "其他辅助证明",
            "volume": "business",
            "scoring_rows": [],
            "has_asterisk": False,
            "has_disqualified": False,
        },
    ]

    summary, recommended_order = calculate_score_weights_and_priorities(leaves)

    # 1. 总分验证：30 + 20 + 0 + 15 + 5 + 0 = 70.0
    assert summary["grand_total_score"] == 70.0
    assert summary["volume_scores"]["technical"] == 50.0
    assert summary["volume_scores"]["business"] == 20.0
    assert summary["volume_weights"]["technical"] == round(50.0 / 70.0, 4)
    assert summary["volume_weights"]["business"] == round(20.0 / 70.0, 4)

    # 2. 优先级判定与加权得分验证：
    # ch-tech-disq: 废标项 (bonus 100) -> priority: critical, priority_score: 100.0
    disq_leaf = next(c for c in leaves if c["id"] == "ch-tech-disq")
    assert disq_leaf["priority"] == "critical"
    assert disq_leaf["priority_score"] == 100.0
    assert "废标" in disq_leaf["priority_reason"]

    # ch-tech-sec: ★星号项 (bonus 60 + 20) -> priority: critical, priority_score: 80.0
    sec_leaf = next(c for c in leaves if c["id"] == "ch-tech-sec")
    assert sec_leaf["priority"] == "critical"
    assert sec_leaf["priority_score"] == 80.0
    assert "★" in sec_leaf["priority_reason"]

    # ch-tech-arch: 高分值项 (30分 >= 15分, bonus 30 + 30) -> priority: high, priority_score: 60.0
    arch_leaf = next(c for c in leaves if c["id"] == "ch-tech-arch")
    assert arch_leaf["priority"] == "high"
    assert arch_leaf["priority_score"] == 60.0
    assert arch_leaf["score_weight"] == round(30.0 / 70.0, 4)
    assert arch_leaf["volume_score_weight"] == round(30.0 / 50.0, 4)

    # ch-biz-audit: 高分值项 (15分, bonus 30 + 15) -> priority: high, priority_score: 45.0
    audit_leaf = next(c for c in leaves if c["id"] == "ch-biz-audit")
    assert audit_leaf["priority"] == "high"
    assert audit_leaf["priority_score"] == 45.0

    # ch-biz-reg: 中分值项 (5分, bonus 15 + 5) -> priority: medium, priority_score: 20.0
    reg_leaf = next(c for c in leaves if c["id"] == "ch-biz-reg")
    assert reg_leaf["priority"] == "medium"
    assert reg_leaf["priority_score"] == 20.0

    # ch-biz-supp: 支撑项 (0分) -> priority: low, priority_score: 0.0
    supp_leaf = next(c for c in leaves if c["id"] == "ch-biz-supp")
    assert supp_leaf["priority"] == "low"
    assert supp_leaf["priority_score"] == 0.0

    # 3. 推荐执行队列次序验证：
    # 严格按照 -priority_score 降序：
    expected_order_ids = [
        "ch-tech-disq",  # 100.0
        "ch-tech-sec",   # 80.0
        "ch-tech-arch",  # 60.0
        "ch-biz-audit",  # 45.0
        "ch-biz-reg",    # 20.0
        "ch-biz-supp",   # 0.0
    ]
    actual_order_ids = [item["chapter_id"] for item in recommended_order]
    assert actual_order_ids == expected_order_ids
    assert recommended_order[0]["order"] == 1
    assert recommended_order[0]["suggested_action"] != ""


def test_zero_division_and_malformed_score_resilience():
    """测试全部条款分值为0、空值或非数字时的除零保护与鲁棒性。"""
    leaves = [
        {
            "id": "c1",
            "section_number": "1.1",
            "title": "测试零分章节",
            "volume": "technical",
            "scoring_rows": [{"id": "r1", "score": None}, {"id": "r2", "score": "invalid"}],
            "has_asterisk": False,
            "has_disqualified": False,
        },
        {
            "id": "c2",
            "section_number": "1.2",
            "title": "测试星号零分章节",
            "volume": "technical",
            "scoring_rows": [{"id": "r3", "score": 0}],
            "has_asterisk": True,
            "has_disqualified": False,
        },
    ]

    summary, order = calculate_score_weights_and_priorities(leaves)
    assert summary["grand_total_score"] == 0.0
    assert summary["volume_scores"]["technical"] == 0.0
    assert summary["volume_weights"]["technical"] == 0.0

    # c2 即使得分为 0，因含有星号仍应获得 critical 优先级和 60.0 priority_score
    c2_order = next(item for item in order if item["chapter_id"] == "c2")
    assert c2_order["priority"] == "critical"
    assert c2_order["priority_score"] == 60.0

    c1_order = next(item for item in order if item["chapter_id"] == "c1")
    assert c1_order["priority"] == "low"
    assert c1_order["priority_score"] == 0.0


# ==================== 2. 服务层与大纲树集成测试 ====================

def test_auto_build_outline_tree_incorporates_score_weights(test_env):
    """测试自动大纲树推导引擎内建分值权重加权与排序队列。"""
    repo, demo = test_env["repo"], test_env["demo"]
    pm = test_env["principals"]["manager"]

    result = demo.outline_service.auto_build_outline_tree(
        project_id="alpha-project",
        principal=pm,
    )

    # 1. 验证返回的大纲结果包含分值权重摘要与推荐队列
    assert "score_weights_summary" in result
    summary = result["score_weights_summary"]
    # 总分：5 (biz) + 15 (biz) + 30 (tech) + 20 (tech) + 0 (tech) + 10 (tech) = 80.0
    assert summary["grand_total_score"] == 80.0
    assert summary["volume_scores"]["business"] == 20.0
    assert summary["volume_scores"]["technical"] == 60.0
    assert summary["critical_chapters_count"] >= 2  # 包含 ★ 和 废标 章节

    assert "recommended_writing_order" in result
    order = result["recommended_writing_order"]
    assert len(order) == len(result["leaf_chapters"])

    # 推荐次序第一位应为废标条款章节（priority_score >= 100）
    first_item = order[0]
    assert first_item["priority"] == "critical"
    assert first_item["priority_score"] >= 100.0

    # 2. 验证工作流与大纲方案元数据正确持久化
    state = repo.read()
    wf = state.workflows["alpha-project"]
    assert "score_weights_summary" in wf
    assert "recommended_writing_order" in wf

    outline_plans = wf["outline_plans"]
    for ch_id, plan in outline_plans.items():
        assert "score_weight" in plan
        assert "volume_score_weight" in plan
        assert "priority" in plan
        assert "priority_score" in plan
        assert "suggested_action" in plan


def test_calculate_outline_score_weights_service(test_env):
    """测试单独触发的大纲分值权重计算服务接口。"""
    demo = test_env["demo"]
    pm = test_env["principals"]["manager"]

    # 先构建大纲树
    demo.outline_service.auto_build_outline_tree("alpha-project", pm)

    # 显式调用 calculate_outline_score_weights
    calc_res = demo.outline_service.calculate_outline_score_weights("alpha-project", pm)
    assert calc_res["project_id"] == "alpha-project"
    assert "score_weights_summary" in calc_res
    assert "recommended_writing_order" in calc_res
    assert calc_res["chapters_count"] > 0

    # 测试通过 get_recommended_writing_order 读取
    order_res = demo.outline_service.get_recommended_writing_order("alpha-project", pm)
    assert order_res["project_id"] == "alpha-project"
    assert len(order_res["recommended_writing_order"]) == calc_res["chapters_count"]


# ==================== 3. 安全、隔离与门禁测试 ====================

def test_multi_tenant_isolation(test_env):
    """测试跨租户访问大纲分值计算与排序队列时抛出 404 NOT_FOUND。"""
    demo = test_env["demo"]
    outsider = test_env["principals"]["outsider"]

    # 计算分值权重隔离
    with pytest.raises(DomainError) as exc_calc:
        demo.outline_service.calculate_outline_score_weights("alpha-project", outsider)
    assert exc_calc.value.status == 404
    assert exc_calc.value.code == "NOT_FOUND"

    # 获取推荐编写队列隔离
    with pytest.raises(DomainError) as exc_order:
        demo.outline_service.get_recommended_writing_order("alpha-project", outsider)
    assert exc_order.value.status == 404
    assert exc_order.value.code == "NOT_FOUND"


def test_rbac_readonly_forbidden(test_env):
    """测试只读系统角色和项目只读成员无权执行分值权重计算。"""
    demo = test_env["demo"]
    auditor = test_env["principals"]["auditor"]
    viewer = test_env["principals"]["viewer"]

    with pytest.raises(DomainError) as exc_auditor:
        demo.outline_service.calculate_outline_score_weights("alpha-project", auditor)
    assert exc_auditor.value.status == 403
    assert exc_auditor.value.code == "FORBIDDEN"

    with pytest.raises(DomainError) as exc_viewer:
        demo.outline_service.calculate_outline_score_weights("alpha-project", viewer)
    assert exc_viewer.value.status == 403
    assert exc_viewer.value.code == "FORBIDDEN"


def test_sensitive_project_local_model_gate(test_env):
    """测试涉密项目调用外部云端大模型规划时硬门禁拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    repo, demo = test_env["repo"], test_env["demo"]
    pm = test_env["principals"]["manager"]

    # 将 alpha-project 标记为涉密项目
    def mark_sensitive(s):
        s.projects["alpha-project"].sensitive = True
    repo.transaction(mark_sensitive)

    # 替换为外部云端模型 provider
    demo.model_provider = MockCloudModelProvider()

    with pytest.raises(DomainError) as exc:
        demo.outline_service.calculate_outline_score_weights(
            "alpha-project",
            pm,
            options={"use_ai_model": True},
        )
    assert exc.value.status == 403
    assert exc.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 换回本地模型 provider 则放行
    demo.model_provider = MockLocalModelProvider()
    res = demo.outline_service.calculate_outline_score_weights(
        "alpha-project",
        pm,
        options={"use_ai_model": True},
    )
    assert res["project_id"] == "alpha-project"


# ==================== 4. FastAPI HTTP 端点集成测试 ====================

def test_http_api_endpoints(test_env):
    """测试 FastAPI 端点 POST /outline/score-weights 与 GET /outline/recommended-order。"""
    demo = test_env["demo"]
    pm = test_env["principals"]["manager"]

    # 构建并启动测试 App
    app = FastAPI()
    include_workflow_routes(
        application=app,
        service=demo,
        current_user=lambda: pm,
        parser=DummyParser(),
    )
    client = TestClient(app)

    # 1. 先调用自动构建大纲
    res_build = client.post("/api/v1/projects/alpha-project/outline/auto-tree-build", json={})
    assert res_build.status_code == 200
    build_json = res_build.json()
    assert "score_weights_summary" in build_json
    assert "recommended_writing_order" in build_json

    # 2. 调用 POST /outline/score-weights
    res_weights = client.post("/api/v1/projects/alpha-project/outline/score-weights", json={})
    assert res_weights.status_code == 200
    weights_json = res_weights.json()
    assert weights_json["project_id"] == "alpha-project"
    assert "score_weights_summary" in weights_json
    assert "recommended_writing_order" in weights_json
    assert weights_json["score_weights_summary"]["grand_total_score"] == 80.0

    # 3. 调用 GET /outline/recommended-order
    res_order = client.get("/api/v1/projects/alpha-project/outline/recommended-order")
    assert res_order.status_code == 200
    order_json = res_order.json()
    assert order_json["project_id"] == "alpha-project"
    assert len(order_json["recommended_writing_order"]) > 0
    assert order_json["recommended_writing_order"][0]["priority"] == "critical"
