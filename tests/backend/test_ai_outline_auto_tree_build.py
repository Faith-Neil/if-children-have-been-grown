# 为什么有这个文件：独立测试招标文件解析驱动的大纲树自动规划构建引擎（AI-OUTLINE-AUTO-TREE-BUILD）。
# 它解决什么问题：
# 1. 结构化大纲树自动衍生：验证卷（Volume 0级）-> 章/编（Part/Chapter 1级）-> 节（Section 2级）多层级标准编号（第一卷、第一章、1.1、1.1.1）；
# 2. 矩阵条款多维度自动对齐：验证商务资质、技术架构、实施SLA、安全合规、偏离表精准对齐至对应卷与叶子节，实现 100% 零遗漏映射；
# 3. 评分要点与写作指引生成：验证叶子章节自动挂接真实条款 ID（bound_requirement_ids）、评分分值、星号（★）及废标标记，生成结构化写作要点（writing_points）；
# 4. 条款防编造白名单校验：验证传入虚构或不存在的条款 ID 时严格拦截并抛出 422 INVALID_REQUIREMENT_REFERENCE；
# 5. 多租户强隔离门禁：验证跨租户操作直接抛出 404 NOT_FOUND；
# 6. RBAC 权限门禁：验证只读角色与项目只读成员拦截 403 FORBIDDEN；
# 7. 涉密项目本地模型门禁：验证敏感项目使用外部模型拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL，本地模型正常放行；
# 8. 预览与单事务持久化：验证 preview 模式纯内存不落盘，持久化模式原子推进章节、工作流与版本自增；
# 9. 大纲定稿锁定前置就绪检查：验证核验未映射条款、空章节与星号条款合规阻断；
# 10. HTTP API 端点集成：验证 POST /api/v1/projects/{project_id}/outline/auto-tree-build 端点契约。

from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from icg_demo.adapters import MemoryRepository, seed_state
from icg.domain.domain import Chapter, DemoService, DomainError, Principal, iso_time, new_id
from icg.domain.outline_auto_tree import (
    AutoTreeBuildEngine,
    check_tree_finalization_readiness,
    classify_requirement_clause,
    to_chinese_num,
    format_volume_info,
    format_chapter_info,
    format_section_info,
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
        return "云端模型建议"


@pytest.fixture
def test_env():
    state = seed_state()
    repo = MemoryRepository()
    repo.transaction(lambda s: s.__dict__.update(state.__dict__))
    demo = DemoService(repo, MockLocalModelProvider())
    demo.outline_service = OutlinePlanService(demo)

    # 预置全面的解析需求矩阵（包含五大核心类别与星号、废标条款）
    def init_wf(s):
        wf = s.workflows.setdefault("alpha-project", {})
        wf["parse_confirmed"] = True
        wf["requirements"] = {
            "req-biz-01": {
                "id": "req-biz-01",
                "clause": "投标人须具备有效营业执照及法定代表人身份证明",
                "category": "commercial",
                "volume": "business",
                "score": 3.0,
                "scoring_criteria": "资质证件齐全合规得3分",
                "status": "confirmed",
            },
            "req-biz-02": {
                "id": "req-biz-02",
                "clause": "投标人需提供经第三方审计的财务报告，未提供作废标处理",
                "category": "finance",
                "volume": "business",
                "score": 2.0,
                "disqualified": True,
                "scoring_criteria": "财务状况良好且审计合规得2分",
                "status": "confirmed",
            },
            "req-biz-03": {
                "id": "req-biz-03",
                "clause": "投标人具备CMMI3及以上或ISO9001认证证书",
                "category": "qualification",
                "volume": "business",
                "score": 5.0,
                "scoring_criteria": "具备认证得5分",
                "status": "confirmed",
            },
            "req-biz-04": {
                "id": "req-biz-04",
                "clause": "商务条款实质性偏离说明表",
                "category": "deviation",
                "volume": "business",
                "score": None,
                "status": "confirmed",
            },
            "req-tech-01": {
                "id": "req-tech-01",
                "clause": "系统整体采用微服务与容器化高可用拓扑架构",
                "category": "technical",
                "volume": "technical",
                "score": 10.0,
                "scoring_criteria": "架构设计先进且可扩展性强得满分",
                "status": "confirmed",
            },
            "req-tech-02": {
                "id": "req-tech-02",
                "clause": "★核心数据库主从双活容灾切换时间小于30秒",
                "category": "technical",
                "volume": "technical",
                "score": 10.0,
                "mandatory": True,
                "asterisk": True,
                "scoring_criteria": "双活高可用指标达成得10分，未达成得0分",
                "status": "confirmed",
            },
            "req-tech-03": {
                "id": "req-tech-03",
                "clause": "实施交付团队核心骨干不少于8人，项目经理具备PMP证书",
                "category": "service",
                "volume": "technical",
                "score": 6.0,
                "scoring_criteria": "团队资质齐备且经验丰富得6分",
                "status": "confirmed",
            },
            "req-tech-04": {
                "id": "req-tech-04",
                "clause": "提供7x24小时全天候运维巡检与故障应急服务承诺(SLA)",
                "category": "sla",
                "volume": "technical",
                "score": 4.0,
                "scoring_criteria": "服务承诺满足并优于要求得4分",
                "status": "confirmed",
            },
            "req-tech-05": {
                "id": "req-tech-05",
                "clause": "系统满足国家网络安全等级保护三级测评要求",
                "category": "security",
                "volume": "technical",
                "score": 5.0,
                "scoring_criteria": "等保三级证明有效得5分",
                "status": "confirmed",
            },
            "req-tech-06": {
                "id": "req-tech-06",
                "clause": "技术规格及参数逐条偏离说明表",
                "category": "deviation",
                "volume": "technical",
                "score": None,
                "status": "confirmed",
            },
        }

    repo.transaction(init_wf)
    return {
        "demo": demo,
        "repo": repo,
        "service": demo.outline_service,
        "principals": {
            "manager": Principal(state.accounts["alpha-manager"], "tok-alpha-manager"),
            "editor": Principal(state.accounts["alpha-editor"], "tok-alpha-editor"),
            "viewer": Principal(state.accounts["alpha-viewer"], "tok-alpha-viewer"),
            "outsider": Principal(state.accounts["beta-editor"], "tok-beta-editor"),
        },
    }


def test_chinese_numbering_utilities():
    """验证中文数字生成与编号格式化工具。"""
    assert to_chinese_num(1) == "一"
    assert to_chinese_num(2) == "二"
    assert to_chinese_num(10) == "十"
    assert to_chinese_num(12) == "十二"
    assert to_chinese_num(20) == "二十"
    assert to_chinese_num(25) == "二十五"

    c_vol, full_vol = format_volume_info("business", 1)
    assert c_vol == "第一卷"
    assert full_vol == "第一卷 商务标"

    c_ch, sec_num, full_ch = format_chapter_info(1, "投标人商务资质与综合实力")
    assert c_ch == "第一章"
    assert sec_num == "1.0"
    assert full_ch == "第一章 投标人商务资质与综合实力"

    sec_no, full_sec = format_section_info(1, 2, "财务审计报告与资产纳税证明")
    assert sec_no == "1.1" or sec_no == "1.2"
    assert "财务审计报告" in full_sec


def test_clause_categorization_and_volume_alignment():
    """验证需求条款分类与分册对齐逻辑。"""
    vol, major, sub = classify_requirement_clause({
        "category": "finance",
        "clause": "经审计的财务报表与纳税申报证明",
    })
    assert vol == "business"
    assert major == "qualification"
    assert sub == "financial_audit"

    vol, major, sub = classify_requirement_clause({
        "category": "security",
        "clause": "数据加密存储与应急容灾备份",
    })
    assert vol == "technical"
    assert major == "security"
    assert sub == "security_emergency"

    vol, major, sub = classify_requirement_clause({
        "category": "deviation",
        "clause": "商务条款实质性偏离表",
    })
    assert vol == "business"
    assert major == "deviation"
    assert sub == "deviation_table"


def test_auto_tree_build_structure_and_numbering(test_env):
    """验证大纲树自动推导的多层级层次结构与规范编号。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    # 执行自动大纲树构建（持久化）
    res = service.auto_build_outline_tree(
        project_id="alpha-project",
        principal=principal,
    )

    assert res["project_id"] == "alpha-project"
    assert res["total_volumes"] == 2
    assert res["mapped_requirements_count"] == 10
    assert res["unmapped_requirements_count"] == 0

    # 1. 验证卷节点（Level 0）
    volumes = res["volumes"]
    assert len(volumes) == 2
    biz_vol = next(v for v in volumes if v["volume"] == "business")
    tech_vol = next(v for v in volumes if v["volume"] == "technical")

    assert biz_vol["chinese_num"] == "第一卷"
    assert biz_vol["title"] == "第一卷 商务标"
    assert biz_vol["level"] == 0

    assert tech_vol["chinese_num"] == "第二卷"
    assert tech_vol["title"] == "第二卷 技术标"
    assert tech_vol["level"] == 0

    # 2. 验证章/编节点（Level 1）
    biz_parts = biz_vol["children"]
    assert len(biz_parts) >= 2
    assert biz_parts[0]["chinese_num"] == "第一章"
    assert biz_parts[0]["section_number"] == "1.0"
    assert biz_parts[0]["level"] == 1

    # 3. 验证节节点（Level 2 叶子节点）
    leaf_chapters = res["leaf_chapters"]
    assert len(leaf_chapters) >= 8

    # 验证商务节与条款绑定
    fin_sec = next(c for c in leaf_chapters if "财务审计" in c["title"])
    assert fin_sec["volume"] == "business"
    assert fin_sec["level"] == 2
    assert fin_sec["section_number"] == "1.2"
    assert "req-biz-02" in fin_sec["bound_requirement_ids"]
    assert fin_sec["has_disqualified"] is True
    assert fin_sec["is_mandatory"] is True

    # 验证技术节与★条款绑定
    ha_sec = next(c for c in leaf_chapters if "高可用" in c["title"] or "双活" in c["title"])
    assert ha_sec["volume"] == "technical"
    assert "req-tech-02" in ha_sec["bound_requirement_ids"]
    assert ha_sec["has_asterisk"] is True
    assert ha_sec["is_mandatory"] is True

    # 验证结构化 writing_points
    assert len(ha_sec["writing_points"]) > 0
    assert "【★关键星号项·必须实质响应】" in ha_sec["writing_points"]
    assert "建议目标字数" in ha_sec["writing_points"]
    assert ha_sec["target_length"] >= 800


def test_anti_hallucination_clause_verification(test_env):
    """验证条款防编造门禁：传入不存在的虚构条款 ID 严格抛出 422。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    # 尝试绑定虚构条款 ID
    with pytest.raises(DomainError) as exc_info:
        service.auto_build_outline_tree(
            project_id="alpha-project",
            principal=principal,
            options={
                "custom_mappings": {
                    "1.1": ["req-fake-nonexistent-clause-999"]
                }
            },
        )

    assert exc_info.value.status == 422
    assert exc_info.value.code == "INVALID_REQUIREMENT_REFERENCE"
    assert "req-fake-nonexistent-clause-999" in str(exc_info.value.message)


def test_multi_tenant_isolation(test_env):
    """验证多租户隔离门禁：跨租户操作直接抛出 404 NOT_FOUND。"""
    service = test_env["service"]
    outsider = test_env["principals"]["outsider"]  # 属于 beta 公司

    with pytest.raises(DomainError) as exc_info:
        service.auto_build_outline_tree(
            project_id="alpha-project",
            principal=outsider,
        )

    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_rbac_role_gate(test_env):
    """验证 RBAC 权限门禁：系统只读角色或项目只读成员拦截 403 FORBIDDEN。"""
    service = test_env["service"]
    viewer = test_env["principals"]["viewer"]  # alpha-viewer (只读账号)

    with pytest.raises(DomainError) as exc_info:
        service.auto_build_outline_tree(
            project_id="alpha-project",
            principal=viewer,
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_sensitive_project_local_model_gate(test_env):
    """验证涉密项目本地模型门禁：敏感项目调用外部云端模型时抛出 403。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    # 标记项目为敏感项目，并配置云端模型
    def mark_sensitive(s):
        s.projects["alpha-project"].sensitive = True

    test_env["repo"].transaction(mark_sensitive)
    test_env["demo"].model_provider = MockCloudModelProvider()

    with pytest.raises(DomainError) as exc_info:
        service.auto_build_outline_tree(
            project_id="alpha-project",
            principal=principal,
            options={"use_ai_model": True},
        )

    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 切换回本地模型后成功放行
    test_env["demo"].model_provider = MockLocalModelProvider()
    res = service.auto_build_outline_tree(
        project_id="alpha-project",
        principal=principal,
        options={"use_ai_model": True, "preview": True},
    )
    assert res["project_id"] == "alpha-project"
    assert res["preview"] is True


def test_preview_mode_preserves_state(test_env):
    """验证 preview=True 模式下纯内存推导，不修改持久化仓库。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    before_state = test_env["repo"].read()
    before_rev = before_state.projects["alpha-project"].revision
    before_ch_count = len([c for c in before_state.chapters.values() if c.project_id == "alpha-project"])

    res = service.auto_build_outline_tree(
        project_id="alpha-project",
        principal=principal,
        options={"preview": True},
    )

    assert res["preview"] is True
    assert res["total_volumes"] == 2
    assert len(res["leaf_chapters"]) > 0

    after_state = test_env["repo"].read()
    assert after_state.projects["alpha-project"].revision == before_rev
    assert len([c for c in after_state.chapters.values() if c.project_id == "alpha-project"]) == before_ch_count


def test_persistence_mode_atomic_updates(test_env):
    """验证持久化模式下原子更新章节、工作流、需求映射与版本自增。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    res = service.auto_build_outline_tree(
        project_id="alpha-project",
        principal=principal,
        options={"preview": False},
    )

    assert res["preview"] is False
    assert res["project_revision"] > 1
    assert res["outline_revision"] >= 1

    # 读取持久化仓库进行核验
    state = test_env["repo"].read()
    wf = state.workflows["alpha-project"]

    # 1. 验证需求矩阵全量映射且无遗漏
    for req in wf["requirements"].values():
        assert req.get("chapter_id") is not None
        assert req["chapter_id"] in state.chapters

    # 2. 验证 chapter_order 正确维护
    assert len(wf["chapter_order"]) == len(res["leaf_chapters"])
    for cid in wf["chapter_order"]:
        assert cid in state.chapters

    # 3. 验证 outline_plans 元数据已落盘
    for leaf in res["leaf_chapters"]:
        cid = leaf["id"]
        assert cid in wf["outline_plans"]
        plan = wf["outline_plans"][cid]
        assert plan["section_number"] == leaf["section_number"]
        assert plan["level"] == 2
        assert len(plan["writing_points"]) > 0

    # 4. 验证 writing_plan 同步就绪
    for leaf in res["leaf_chapters"]:
        cid = leaf["id"]
        assert cid in wf["writing_plan"]["chapters"]
        wp = wf["writing_plan"]["chapters"][cid]
        assert wp["target_length"] == leaf["target_length"]


def test_outline_finalization_readiness_check(test_env):
    """验证大纲定稿就绪检查（零未映射条款、空章节与星号条款门禁）。"""
    service = test_env["service"]
    principal = test_env["principals"]["manager"]

    # 1. 执行自动构建树
    service.auto_build_outline_tree(project_id="alpha-project", principal=principal)
    state = test_env["repo"].read()

    # 此时章节无正文且大纲未人工确认，readiness 应为 False
    readiness = check_tree_finalization_readiness(state, "alpha-project", "technical")
    assert readiness["ready"] is False
    assert readiness["unmapped_requirements_count"] == 0  # 条款已全部映射
    assert len(readiness["empty_chapters"]) > 0  # 但章节内容为空

    # 2. 模拟填充正文并确认方案
    def fill_and_confirm(s):
        s.workflows["alpha-project"]["plan_confirmed"] = True
        for ch in s.chapters.values():
            if ch.project_id == "alpha-project":
                ch.content = "本章节编写正文，完全实质性响应招标文件条款要求。"

    test_env["repo"].transaction(fill_and_confirm)
    state = test_env["repo"].read()

    # 填充正文后，定稿就绪检查应变为 True
    readiness_after = check_tree_finalization_readiness(state, "alpha-project", "technical")
    assert readiness_after["ready"] is True
    assert readiness_after["unmapped_requirements_count"] == 0
    assert len(readiness_after["empty_chapters"]) == 0
    assert len(readiness_after["pending_chapters"]) == 0


def test_http_api_auto_tree_build(test_env):
    """验证 HTTP API 端点 POST /api/v1/projects/{project_id}/outline/auto-tree-build 集成。"""
    app = FastAPI()
    workflow = WorkflowService(test_env["demo"], DummyParser())
    current_user = lambda: test_env["principals"]["manager"]
    include_workflow_routes(app, test_env["demo"], current_user, DummyParser())

    client = TestClient(app)
    response = client.post(
        "/api/v1/projects/alpha-project/outline/auto-tree-build",
        json={"preview": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "alpha-project"
    assert data["total_volumes"] == 2
    assert data["mapped_requirements_count"] == 10
    assert len(data["leaf_chapters"]) >= 8
    assert "volumes" in data
