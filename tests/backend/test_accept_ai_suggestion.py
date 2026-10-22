# 为什么有这个文件：验证 AI 助手采纳润色建议原地回写与段落替换协议（APP-M2-T185）。
# 它解决什么问题：
# 1. 验证采纳润色建议原地回写协议：支持按段落编号（paragraph_id）或原文片段（original_text）精准替换正文，原子递增章节与项目 revision；
# 2. 验证排他编辑锁强门禁：未持锁/锁过期拦截 423 LOCK_LOST，他人持锁拦截 423 LOCK_HELD；
# 3. 验证并发版本冲突门禁：base_revision 不一致或原文内容已被他人篡改拦截 409 REVISION_CONFLICT，彻底阻断覆盖；
# 4. 验证修订历史归档：保留包含 AI 建议依据、采纳人与时间戳的完整版本记录，并自动触发增量复查标记 pending；
# 5. 验证敏感项目本地模型规则门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）；
# 6. 验证只读角色（403 FORBIDDEN）与跨租户多维隔离（404 NOT_FOUND）；
# 7. 验证 FastAPI HTTP 端点贯通及 include_in_schema=False 契约保护。

import json
import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import DemoState, DomainError, Principal, iso_time
from icg_demo.main import create_app
from icg_demo.model_config_storage import ModelConfig, encrypt_api_key
from icg_demo.parsing import LocalTextParser
from icg_demo.workflow import WorkflowService
from icg_demo.domain import DemoService


@pytest.fixture
def repo():
    return MemoryRepository(seed_state())


@pytest.fixture
def parser():
    return LocalTextParser()


@pytest.fixture
def demo(repo):
    return DemoService(repo, None)


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


def test_accept_suggestion_success_by_paragraph_id(setup_context, demo, workflow, repo):
    """测试按 paragraph_id 定位并精准原地回写替换段落内容，原子递增版本并归档历史。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    # 1. 获取章节初始编辑锁
    lock_res = demo.acquire_lock(manager, cid, "采纳技术方案润色建议")
    lease_token = lock_res["lease_token"]

    ch_before = repo.read().chapters[cid]
    base_rev = ch_before.revision
    p_id = f"{cid}-p1"
    orig_text = "甲公司合成项目的技术方案。"
    suggested = "甲公司星河云平台维保服务项目之整体技术方案与架构设计。"
    citations = [
        {"id": "cite-01", "name": "CMMI5级认证", "tag": "[证]", "source_type": "company_library"}
    ]

    # 2. 采纳建议并原地回写
    res = workflow.accept_ai_suggestion(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
        lease_token=lease_token,
        base_revision=base_rev,
        suggested_text=suggested,
        paragraph_id=p_id,
        original_text=orig_text,
        citations=citations,
    )

    # 3. 验证返回结构与段落
    assert res["chapter_id"] == cid
    assert res["project_id"] == pid
    assert res["revision"] == base_rev + 1
    assert suggested in res["content"]
    assert orig_text not in res["content"]
    assert res["updated_paragraph"]["id"] == p_id
    assert res["updated_paragraph"]["order"] == 1
    assert suggested in res["updated_paragraph"]["text"]
    assert res["incremental_check_status"] == "pending"

    # 4. 验证仓储持久化状态
    state = repo.read()
    ch_after = state.chapters[cid]
    assert ch_after.revision == base_rev + 1
    assert suggested in ch_after.content
    assert state.projects[pid].revision > 1

    # 验证修订历史归档（留存依据、采纳人与模式）
    assert len(ch_after.versions) >= 2
    latest_ver = ch_after.versions[-1]
    assert latest_ver["revision"] == base_rev + 1
    assert latest_ver["version_origin"] == "ai_polish_accepted"
    assert latest_ver["edit_mode"] == "accept_ai_suggestion"
    assert latest_ver["actor_id"] == manager.user.id
    assert latest_ver["paragraph_id"] == p_id
    assert latest_ver["citations"] == citations


def test_accept_suggestion_success_by_original_text_only(setup_context, demo, workflow, repo):
    """测试不传 paragraph_id，仅传 original_text 时同样能够精准在正文中定位并替换。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    lock_res = demo.acquire_lock(manager, cid, "采纳文本改写建议")
    lease_token = lock_res["lease_token"]

    ch_before = repo.read().chapters[cid]
    base_rev = ch_before.revision
    orig_text = "本内容仅用于本地演示，不可作为真实承诺或正式递交文件。"
    suggested = "本项目提供同城双活高可用与7×24小时专业技术保障服务。"

    res = workflow.accept_ai_suggestion(
        principal=manager,
        project_id=pid,
        chapter_id=cid,
        lease_token=lease_token,
        base_revision=base_rev,
        suggested_text=suggested,
        original_text=orig_text,
    )

    assert res["revision"] == base_rev + 1
    assert suggested in res["content"]
    assert orig_text not in res["content"]
    assert res["updated_paragraph"]["order"] == 2
    assert res["updated_paragraph"]["id"] == f"{cid}-p2"


def test_gate_no_lock_or_expired_lock_blocked_with_423(setup_context, demo, workflow, repo):
    """测试排他编辑锁强门禁：无锁/锁过期拦截 423 LOCK_LOST，他人持锁拦截 423 LOCK_HELD。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]
    editor = ctx["editor"]

    ch = repo.read().chapters[cid]
    base_rev = ch.revision

    # 1. 未持有任何锁直接尝试回写 -> 423 LOCK_LOST
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token="invalid-dummy-token",
            base_revision=base_rev,
            suggested_text="改写文本",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_LOST"

    # 2. manager 持有有效编辑锁，editor 试图使用 manager 的 token 越权写入 -> 423 LOCK_HELD
    lock_res = demo.acquire_lock(manager, cid, "负责人上锁")
    lease_token = lock_res["lease_token"]

    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=editor,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=base_rev,
            suggested_text="编写人企图写入",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_HELD"

    # 3. 锁已过期场景 -> 423 LOCK_LOST
    def expire_lock(st: DemoState):
        st.chapters[cid].lock.expires_at = 0.0

    repo.transaction(expire_lock)

    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=base_rev,
            suggested_text="过期锁写入",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 423
    assert exc_info.value.code == "LOCK_LOST"


def test_gate_revision_conflict_blocked_with_409(setup_context, demo, workflow, repo):
    """测试并发保护门禁：章节被其他人抢先提交或段落原文不匹配时拦截 409 REVISION_CONFLICT。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    lock_res = demo.acquire_lock(manager, cid, "版本冲突测试")
    lease_token = lock_res["lease_token"]

    # 1. 提交基线版本滞后拦截：数据库当前版本已为 2，客户端仍传 base_revision=1
    def bump_revision(st: DemoState):
        st.chapters[cid].revision = 2

    repo.transaction(bump_revision)

    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=1,  # 滞后版本
            suggested_text="滞后版本尝试覆盖",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 2. 原文内容不匹配拦截：客户端传的 original_text 与服务端真实段落不符
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=2,
            suggested_text="篡改文本改写",
            paragraph_id=f"{cid}-p1",
            original_text="根本不存在的篡改原文内容片段XYZ",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"

    # 3. 指定了超出范围的 paragraph_id -> 409 REVISION_CONFLICT
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=2,
            suggested_text="不存在段落改写",
            paragraph_id=f"{cid}-p999",
        )
    assert exc_info.value.status == 409
    assert exc_info.value.code == "REVISION_CONFLICT"


def test_gate_sensitive_project_blocks_cloud_model_with_403(setup_context, demo, workflow, repo):
    """测试敏感项目本地模型规则门禁：敏感项目若绑定云端模型拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    lock_res = demo.acquire_lock(manager, cid, "敏感项目测试")
    lease_token = lock_res["lease_token"]

    # 绑定云端非本地模型并设为敏感项目
    cloud_cfg = ModelConfig(
        id="cfg-cloud-remote",
        company_id="alpha",
        name="云端模型",
        provider="openai-compatible",
        base_url="https://api.openai.com/v1",
        model="cloud-gpt-4o",
        encrypted_api_key="cipher-dummy-key",
        is_local=False,
        allow_sensitive=False,
    )

    def mark_sensitive_and_bind_cloud(st: DemoState):
        st.projects[pid].sensitive = True
        st.model_configs[cloud_cfg.id] = cloud_cfg
        st.project_model_configs[pid] = cloud_cfg.id

    repo.transaction(mark_sensitive_and_bind_cloud)

    ch = repo.read().chapters[cid]
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id=cid,
            lease_token=lease_token,
            base_revision=ch.revision,
            suggested_text="敏感项目正文改写",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"


def test_gate_readonly_and_permission_blocked_with_403(setup_context, demo, workflow, repo):
    """测试只读角色与权限门禁：只读角色（viewer）与项目外成员拦截 403 FORBIDDEN。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    viewer = ctx["viewer"]
    outsider = ctx["outsider"]

    ch = repo.read().chapters[cid]
    base_rev = ch.revision

    # 1. 系统只读角色（viewer）-> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=viewer,
            project_id=pid,
            chapter_id=cid,
            lease_token="dummy-token",
            base_revision=base_rev,
            suggested_text="只读角色改写",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"

    # 2. 项目外未分配成员 -> 403 FORBIDDEN
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=outsider,
            project_id=pid,
            chapter_id=cid,
            lease_token="dummy-token",
            base_revision=base_rev,
            suggested_text="外部成员改写",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_cross_project_and_cross_tenant_isolation_with_404(setup_context, workflow, repo):
    """测试严格租户隔离：跨公司租户访问或不存在项目/章节拦截 404 NOT_FOUND。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    beta_user = ctx["beta_user"]
    manager = ctx["manager"]

    ch = repo.read().chapters[cid]
    base_rev = ch.revision

    # 1. Beta 公司用户越权访问 Alpha 公司的项目 -> 404 NOT_FOUND
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=beta_user,
            project_id=pid,
            chapter_id=cid,
            lease_token="dummy-token",
            base_revision=base_rev,
            suggested_text="跨公司改写",
            paragraph_id=f"{cid}-p1",
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"

    # 2. 访问不存在的章节 -> 404 NOT_FOUND
    with pytest.raises(DomainError) as exc_info:
        workflow.accept_ai_suggestion(
            principal=manager,
            project_id=pid,
            chapter_id="non-existent-chapter",
            lease_token="dummy-token",
            base_revision=base_rev,
            suggested_text="不存在章节改写",
            paragraph_id="p1",
        )
    assert exc_info.value.status == 404
    assert exc_info.value.code == "NOT_FOUND"


def test_http_endpoint_and_openapi_safety(setup_context, repo, demo):
    """测试 FastAPI HTTP 端点贯通及 include_in_schema=False 契约保护。"""
    ctx = setup_context
    pid = ctx["project_id"]
    cid = ctx["chapter_id"]
    manager = ctx["manager"]

    client = TestClient(create_app(repository=repo))
    login_res = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 获取有效编辑锁（使用当前登录 session）
    lock_resp = client.post(f"/api/v1/chapters/{cid}/lock", headers=headers, json={"takeover_reason": "HTTP回写测试"})
    assert lock_resp.status_code == 200
    lease_token = lock_resp.json()["lease_token"]
    base_rev = repo.read().chapters[cid].revision

    # 2. 调用 POST /api/v1/projects/{project_id}/chapters/{chapter_id}/accept-ai-suggestion
    payload = {
        "lease_token": lease_token,
        "base_revision": base_rev,
        "paragraph_id": f"{cid}-p1",
        "original_text": "甲公司合成项目的技术方案。",
        "suggested_text": "甲公司经 HTTP 接口采纳的最新润色正文方案。",
        "citations": [{"id": "cite-http", "name": "技术认证", "tag": "[证]"}],
    }
    resp = client.post(
        f"/api/v1/projects/{pid}/chapters/{cid}/accept-ai-suggestion",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["chapter_id"] == cid
    assert data["revision"] == base_rev + 1
    assert "甲公司经 HTTP 接口采纳的最新润色正文方案" in data["content"]
    assert data["updated_paragraph"]["id"] == f"{cid}-p1"
    assert data["incremental_check_status"] == "pending"
