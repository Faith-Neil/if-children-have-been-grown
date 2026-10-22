# 为什么有这个文件：自动化测试 AI-COMPLIANCE-CROSS-CHECK 合规检查依据交叉核验与差距诊断服务。
# 它解决什么问题：
# 1. 验证段落强声明与依据交叉核验：充分证据支撑（高置信度）、佐证仅为一般描述缺乏量化数据（中置信度差距诊断）；
# 2. 验证与招标文件条款比对，正文负偏离（如时限劣于招标要求）强阻断（零置信度、block）；
# 3. 验证未标注证据（无依据支撑）、证据过期与缺失合作协议的合规拦截；
# 4. 验证涉密项目本地模型门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）、多租户与权限隔离（404/403）；
# 5. 验证 FastAPI HTTP 端点、增量复查状态联动与 OpenAPI 契约安全保护。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import DemoService, DemoState, DomainError, Principal
from icg_demo.main import create_app
from icg_demo.model_config_storage import ModelConfig
from icg_demo.parsing import LocalTextParser
from icg_demo.workflow import WorkflowService


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def demo(repo):
    return DemoService(repo, None)


@pytest.fixture
def parser():
    return LocalTextParser()


@pytest.fixture
def workflow(demo, parser):
    return WorkflowService(demo, parser)


@pytest.fixture
def setup_context(repo, demo):
    def seed_sessions(st: DemoState):
        st.sessions.update({
            "token-manager": "alpha-manager",
            "token-editor": "alpha-editor",
            "token-viewer": "alpha-viewer",
            "token-outsider": "alpha-outsider-manager",
            "token-beta": "beta-editor",
        })
    repo.transaction(seed_sessions)

    state = repo.read()
    pid = "alpha-project"
    cid = "alpha-tech"
    manager = Principal(state.accounts["alpha-manager"], "token-manager")
    editor = Principal(state.accounts["alpha-editor"], "token-editor")
    viewer = Principal(state.accounts["alpha-viewer"], "token-viewer")
    outsider = Principal(state.accounts["alpha-outsider-manager"], "token-outsider")
    beta_user = Principal(state.accounts["beta-editor"], "token-beta")

    return {
        "project_id": pid,
        "chapter_id": cid,
        "manager": manager,
        "editor": editor,
        "viewer": viewer,
        "outsider": outsider,
        "beta_user": beta_user,
    }


def test_cross_check_high_confidence_with_full_evidence(setup_context, workflow, repo):
    """测试正文做高可用承诺且佐证资料中包含确切公章/指标数据，评定为高置信度与合规通过。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    # 准备充分证据与招标文件要求
    evidence_id = "cite-full-sla"
    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = (
            "第一章 平台整体高可用服务方案。\n\n"
            "本方案承诺业务系统可用性达到 99.99% 的高可用 SLA 指标，"
            f"依托双活多活容灾体系确保系统不中断运行 [证:{evidence_id}]。\n\n"
            "第二章 组织与交付团队。"
        )
        ch.citations = [{
            "id": evidence_id,
            "name": "99.99%高可用评测报告及公章SLA承诺",
            "content": "第三方国家级测评机构认证报告，经严格长周期压力测试，确认本系统可用性达到 99.99%，并附带投标主体公章承诺。",
            "status": "confirmed",
            "is_expired": False,
        }]
        wf = st.workflows.setdefault(pid, {})
        wf.setdefault("candidates", {})[evidence_id] = {
            "id": evidence_id,
            "name": "99.99%高可用评测报告及公章SLA承诺",
            "content": "第三方国家级测评机构认证报告，经严格长周期压力测试，确认本系统可用性达到 99.99%，并附带投标主体公章承诺。",
            "status": "confirmed",
            "is_expired": False,
            "agreement_present": True,
        }
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    assert res["compliance_status"] == "compliant"
    assert res["overall_confidence"] >= 0.85
    assert res["total_claims"] >= 1
    assert res["verified_claims"] >= 1
    assert len(res["findings"]) >= 1

    finding = res["findings"][0]
    assert finding.claim_type == "sla_metric"
    assert "99.99%" in finding.claim_text
    assert finding.confidence_level == "high"
    assert finding.confidence_score >= 0.85
    assert finding.risk_level == "info"
    assert "严格相符" in finding.gap_description or "有确切" in finding.gap_description

    # 验证章节增量复查状态联动
    ch_after = repo.read().chapters[cid]
    assert ch_after.incremental_check_status == "passed"


def test_cross_check_medium_confidence_gap_general_description_only(setup_context, workflow, repo):
    """测试正文做高额数值承诺，但佐证中仅包含一般架构描述，精准诊断出数据支撑差距（中置信度与警告）。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    evidence_id = "cite-vague-desc"
    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = (
            "第一章 平台整体高可用服务方案。\n\n"
            "本方案承诺业务系统可用性达到 99.99% 的高可用标准，"
            f"依托双活多活容灾体系确保系统不中断运行 [证:{evidence_id}]。"
        )
        ch.citations = [{
            "id": evidence_id,
            "name": "平台高可用架构白皮书",
            "content": "本方案采用业界成熟的主备冗余与负载均衡架构设计，能够有效防范单点故障，保障业务系统平稳可靠运行。",
            "status": "confirmed",
            "is_expired": False,
        }]
        wf = st.workflows.setdefault(pid, {})
        wf.setdefault("candidates", {})[evidence_id] = {
            "id": evidence_id,
            "name": "平台高可用架构白皮书",
            "content": "本方案采用业界成熟的主备冗余与负载均衡架构设计，能够有效防范单点故障，保障业务系统平稳可靠运行。",
            "status": "confirmed",
            "is_expired": False,
            "agreement_present": True,
        }
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    assert res["compliance_status"] == "warning"
    assert res["warning_claims"] >= 1

    finding = res["findings"][0]
    assert finding.confidence_level == "medium"
    assert finding.confidence_score == 0.55
    assert finding.risk_level == "warning"
    assert "一般性架构或运维文字描述" in finding.gap_description
    assert "缺少明确的【99.99%】量化指标测评报告" in finding.gap_description
    assert "补充上传" in finding.suggestion

    ch_after = repo.read().chapters[cid]
    assert ch_after.incremental_check_status == "warning"


def test_cross_check_negative_deviation_blocked_with_zero_confidence(setup_context, workflow, repo):
    """测试正文承诺劣于招标文件硬性条款（如响应时间 30分钟 vs 招标要求 15分钟），判为负偏离并阻断（0置信度）。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = (
            "运维响应方案：我司承诺在接到故障报修后 30分钟以内到达现场 实施紧急处置与排障。"
        )
        wf = st.workflows.setdefault(pid, {})
        wf["requirements"] = [{
            "id": "req-resp-01",
            "clause_number": "3.2.1",
            "requirement": "发生紧急故障时，投标人必须在 15分钟 以内到达现场进行抢修，超出时限扣除履约保证金并追究责任。",
            "type": "technical",
        }]
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    assert res["compliance_status"] == "non_compliant"
    assert res["unsupported_claims"] >= 1

    finding = res["findings"][0]
    assert finding.claim_type == "sla_metric"
    assert finding.confidence_level == "unsupported"
    assert finding.confidence_score == 0.0
    assert finding.risk_level == "block"
    assert "负偏离废标风险" in finding.gap_description
    assert "15 分钟" in finding.suggestion

    ch_after = repo.read().chapters[cid]
    assert ch_after.incremental_check_status == "failed"


def test_cross_check_unsupported_claim_without_evidence(setup_context, workflow, repo):
    """测试正文陈述强承诺（资质或人员能力）但未添加任何依据标记，诊断为无依据支撑。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = (
            "项目交付保障：我方项目实施团队持有 PMP 证书，且具备 10 年以上相关开发经验。"
        )
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    assert len(res["findings"]) >= 1
    for f in res["findings"]:
        assert f.evidence_status == "missing"
        assert f.risk_level == "warning"
        assert f.confidence_level in ("low", "unsupported")
        assert "未" in f.gap_description


def test_cross_check_expired_or_invalid_evidence_blocked(setup_context, workflow, repo):
    """测试引用已过期依据或缺少合作协议的依据，严格触发阻断（置信度 0.0）。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    eid_expired = "cite-exp-01"
    eid_no_agree = "cite-no-agree-02"

    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = (
            f"我方持有 CMMI5 认证证书 [证:{eid_expired}]，"
            f"同时由合作伙伴提供驻场保障承诺 [证:{eid_no_agree}]。"
        )
        wf = st.workflows.setdefault(pid, {})
        wf.setdefault("candidates", {})[eid_expired] = {
            "id": eid_expired,
            "name": "过期CMMI5认证",
            "content": "CMMI 5级评估证书",
            "status": "expired",
            "is_expired": True,
            "agreement_present": True,
        }
        wf["candidates"][eid_no_agree] = {
            "id": eid_no_agree,
            "name": "合作伙伴驻场承诺",
            "content": "承诺提供驻场保障服务",
            "status": "confirmed",
            "is_expired": False,
            "source_tier": "partner",
            "agreement_present": False,  # 缺合作协议
        }
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    assert res["compliance_status"] == "non_compliant"
    block_findings = [f for f in res["findings"] if f.risk_level == "block"]
    assert len(block_findings) >= 2
    for bf in block_findings:
        assert bf.confidence_score == 0.0
        assert bf.confidence_level == "unsupported"


def test_gate_sensitive_project_blocks_cloud_model(setup_context, workflow, repo):
    """测试涉密项目调用合规核验服务时，若绑定云端非本地模型，强拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    cloud_cfg = ModelConfig(
        id="cfg-cloud-comp",
        company_id="alpha",
        name="云端通用大模型",
        provider="openai-compatible",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        encrypted_api_key="cipher-dummy",
        is_local=False,
        allow_sensitive=False,
    )

    def mark_sensitive_and_bind_cloud(st: DemoState):
        st.projects[pid].sensitive = True
        st.model_configs[cloud_cfg.id] = cloud_cfg
        st.project_model_configs[pid] = cloud_cfg.id
    repo.transaction(mark_sensitive_and_bind_cloud)

    with pytest.raises(DomainError) as exc_info:
        workflow.compliance_cross_check(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_cross_tenant_and_permission_isolation(setup_context, workflow):
    """测试跨租户访问拦截 404 NOT_FOUND，非项目成员拦截 403 FORBIDDEN。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    outsider = ctx["outsider"]
    beta_user = ctx["beta_user"]

    # 1. 跨公司租户拦截 404
    with pytest.raises(DomainError) as exc_info:
        workflow.compliance_cross_check(
            principal=beta_user,
            project_id=pid,
            chapter_id=cid,
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 2. 非项目成员拦截 403
    with pytest.raises(DomainError) as exc_info:
        workflow.compliance_cross_check(
            principal=outsider,
            project_id=pid,
            chapter_id=cid,
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_http_endpoint_and_openapi_safety(setup_context, repo):
    """测试 FastAPI HTTP POST /api/v1/projects/{pid}/chapters/{cid}/compliance-cross-check 贯通及 include_in_schema=False 契约保护。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]

    client = TestClient(create_app(repository=repo))
    login_res = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 准备测试段落
    def seed_content(st: DemoState):
        ch = st.chapters[cid]
        ch.content = "第一章 概述。\n\n本章节承诺提供 7×24小时 全天候技术支持保障。"
    repo.transaction(seed_content)

    # 2. 调用 POST 接口
    resp = client.post(
        f"/api/v1/projects/{pid}/chapters/{cid}/compliance-cross-check",
        headers=headers,
        json={"strict_mode": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapter_id"] == cid
    assert data["project_id"] == pid
    assert "total_claims" in data
    assert "findings" in data
    assert "checks_summary" in data

    # 3. 校验 OpenAPI 规范中不泄露非冻结内部路由（include_in_schema=False）
    schema = create_app().openapi()
    endpoint_path = "/api/v1/projects/{project_id}/chapters/{chapter_id}/compliance-cross-check"
    assert endpoint_path not in schema.get("paths", {})


def test_incremental_check_status_and_checks_integration(setup_context, workflow, repo):
    """测试核验结果完整沉淀至 workflow['incremental_checks']，以及阻断项生成合法 CheckIssue。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    def seed_data(st: DemoState):
        ch = st.chapters[cid]
        ch.content = "本章节承诺业务可用性 99.99% [证:cite-missing-id]。"
    repo.transaction(seed_data)

    res = workflow.compliance_cross_check(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
    )

    wf = repo.read().workflows.get(pid, {})
    inc_checks = wf.get("incremental_checks", [])
    assert len(inc_checks) >= 1
    latest_check = inc_checks[-1]
    assert latest_check["chapter_id"] == cid
    assert latest_check["status"] in ("warning", "non_compliant")
    assert "findings" in latest_check
    assert res["checks_summary"]["issues_count"] >= 1

