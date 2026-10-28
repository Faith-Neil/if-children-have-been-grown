
def _seed_lead_and_project(service):
    pwd_hash, salt = hash_password("Lead_pass_2026")
    target_user = Account(
        id="transfer-target-lead",
        name="待交接项目经理",
        company_id="alpha",
        role="project_lead",
        _DEMO_ONLY=False,
        password_hash=pwd_hash,
        salt=salt,
        display_name="待交接经理",
        status="active",
    )
    project = Project(
        id="project-alpha-active-1",
        name="Alpha 智慧政务在投标段",
        company_id="alpha",
        is_archived=False,
    )
    team = initial_team("transfer-target-lead")
    def _seed(state):
        state.accounts["transfer-target-lead"] = target_user
        state.projects[project.id] = project
        state.project_teams[project.id] = team
    service.repository.transaction(_seed)
# 为什么有这个文件：前后端契约联调工单 INT-USER-TRANSFER-RBAC-GLUE 专属端到端集成测试。
# 它解决什么问题：
# 1. 验证非演示模式（VITE_DEMO=0）下用户列表调阅与密码哈希严格脱敏（GET /api/v1/users）；
# 2. 验证 Q28 密码强度策略（最少8位且至少含3类字符，不足拦截 422 PASSWORD_WEAK）；
# 3. 验证核心业务红线：对负责在投项目的用户直接停用严格拦截 409 USER_TRANSFER_REQUIRED 并返回未结清清单；
# 4. 验证传入有效 successor_user_id 后原子完成名下在投项目负责人平滑交接并成功停用；
# 5. 验证多租户强隔离（跨公司访问 404 NOT_FOUND）与 RBAC 权限隔离（非管理员写操作拦截 403 FORBIDDEN）。

import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import Account, Project
from icg.domain.auth_service import hash_password
from icg.domain.project_access import initial_team
from test_reference_flow import client


@pytest.fixture
def auth_tokens(client: TestClient):
    """为不同测试角色创建账号与认证 Token。"""
    service = client.app.state.service

    # 1. 超级管理员登录 Token
    super_admin_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"})
    assert super_admin_res.status_code == 200
    super_admin_token = super_admin_res.json()["access_token"]

    # 2. Alpha 企业管理员账号
    alpha_pass_hash, alpha_salt = hash_password("Alpha_admin_2026")
    alpha_admin_user = Account(
        id="formal-alpha-admin",
        name="Alpha 企业管理员",
        company_id="alpha",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=alpha_pass_hash,
        salt=alpha_salt,
        display_name="Alpha 企管",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-alpha-admin", alpha_admin_user))
    alpha_login = client.post("/api/v1/auth/login", json={"username": "formal-alpha-admin", "password": "Alpha_admin_2026"})
    assert alpha_login.status_code == 200
    alpha_admin_token = alpha_login.json()["access_token"]

    # 3. Alpha 投标编写人账号（普通非管理员角色）
    writer_pass_hash, writer_salt = hash_password("Alpha_writer_2026")
    alpha_writer_user = Account(
        id="formal-alpha-writer",
        name="Alpha 标书编写人",
        company_id="alpha",
        role="bid_writer",
        _DEMO_ONLY=False,
        password_hash=writer_pass_hash,
        salt=writer_salt,
        display_name="Alpha 标书编写人",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-alpha-writer", alpha_writer_user))
    writer_login = client.post("/api/v1/auth/login", json={"username": "formal-alpha-writer", "password": "Alpha_writer_2026"})
    assert writer_login.status_code == 200
    alpha_writer_token = writer_login.json()["access_token"]

    # 4. Beta 企业管理员账号
    beta_pass_hash, beta_salt = hash_password("Beta_admin_2026")
    beta_admin_user = Account(
        id="formal-beta-admin",
        name="Beta 企业管理员",
        company_id="beta",
        role="company_admin",
        _DEMO_ONLY=False,
        password_hash=beta_pass_hash,
        salt=beta_salt,
        display_name="Beta 企管",
    )
    service.repository.transaction(lambda state: state.accounts.__setitem__("formal-beta-admin", beta_admin_user))
    beta_login = client.post("/api/v1/auth/login", json={"username": "formal-beta-admin", "password": "Beta_admin_2026"})
    assert beta_login.status_code == 200
    beta_admin_token = beta_login.json()["access_token"]

    return {
        "super_admin": super_admin_token,
        "alpha_admin": alpha_admin_token,
        "alpha_writer": alpha_writer_token,
        "beta_admin": beta_admin_token,
    }


def test_unauthenticated_user_api_blocked_401(client: TestClient):
    """验证未提供 Token 访问用户管理接口统一拦截 401 UNAUTHENTICATED。"""
    res_get = client.get("/api/v1/users")
    assert res_get.status_code == 401
    assert res_get.json()["code"] == "UNAUTHENTICATED"

    res_post = client.post("/api/v1/users", json={"username": "test_u", "name": "测试"})
    assert res_post.status_code == 401
    assert res_post.json()["code"] == "UNAUTHENTICATED"


def test_user_list_retrieval_and_sanitization(client: TestClient, auth_tokens):
    """验证 admin 跨企业与企管本企业用户调阅，且密码哈希与盐严格脱敏绝不泄露。"""
    # 1. 超级管理员可查全平台用户
    admin_headers = {"Authorization": f"Bearer {auth_tokens['super_admin']}"}
    res_all = client.get("/api/v1/users", headers=admin_headers)
    assert res_all.status_code == 200, res_all.text
    data_all = res_all.json()
    assert data_all["total"] >= 10
    companies = {u["company_id"] for u in data_all["items"]}
    assert "alpha" in companies
    assert "beta" in companies

    # 严格脱敏断言
    for u in data_all["items"]:
        assert "password_hash" not in u
        assert "salt" not in u
        assert "password" not in u

    # 2. Alpha 企管查询严格限定在 Alpha 公司内
    alpha_headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}
    res_alpha = client.get("/api/v1/users", headers=alpha_headers)
    assert res_alpha.status_code == 200, res_alpha.text
    data_alpha = res_alpha.json()
    for u in data_alpha["items"]:
        assert u["company_id"] == "alpha"
        assert "password_hash" not in u
        assert "salt" not in u


def test_password_strength_validation_422(client: TestClient, auth_tokens):
    """验证创建用户时 Q28 密码强度策略核验（不足 8 位或少于 3 类字符拦截 422 PASSWORD_WEAK）。"""
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 密码过短（< 8 位）
    res_short = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "user_short_pwd",
            "name": "短密码用户",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "Ab1!",  # 4位
        },
    )
    assert res_short.status_code == 422, res_short.text
    err = res_short.json()
    assert err["code"] == "PASSWORD_WEAK"
    assert "低于平台下限 8 位" in err["message"]

    # 2. 密码字符种类不足（只有小写字母，< 3 类）
    res_simple = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "user_simple_pwd",
            "name": "简单密码用户",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "onlylowercasepassword",
        },
    )
    assert res_simple.status_code == 422, res_simple.text
    err_simple = res_simple.json()
    assert err_simple["code"] == "PASSWORD_WEAK"
    assert "至少需包含" in err_simple["message"]

    # 3. 合法强密码创建成功（>= 8 位且包含大写、小写、数字、特殊符号中的三类）
    res_valid = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "user_strong_pwd",
            "name": "强密码用户",
            "company_id": "alpha",
            "role": "project_lead",
            "password": "Strong_Pass_2026",
            "display_name": "强密码项目经理",
        },
    )
    assert res_valid.status_code == 201, res_valid.text
    u = res_valid.json()
    assert u["id"] == "user_strong_pwd"
    assert u["company_id"] == "alpha"
    assert u["status"] == "active"
    assert "password_hash" not in u


def test_deactivation_without_transfer_blocked_409(client: TestClient, auth_tokens):
    """验证核心业务红线：对负责在投项目的用户直接发起停用，严格拦截 409 USER_TRANSFER_REQUIRED 并返回未结清资产。"""
    service = client.app.state.service
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 创建待停用用户 transfer-target-lead 及在投项目
    _seed_lead_and_project(service)

    # 3. 直接尝试停用该用户（未提供 successor_user_id）
    res_deactivate = client.patch(
        "/api/v1/users/transfer-target-lead",
        headers=headers,
        json={"status": "disabled"},
    )
    assert res_deactivate.status_code == 409, res_deactivate.text
    err = res_deactivate.json()
    assert err["code"] == "USER_TRANSFER_REQUIRED"
    assert "停用前必须转交名下资产" in err["message"]
    untransferred = err["details"]["untransferred_projects"]
    assert len(untransferred) >= 1
    assert any(p["project_id"] == "project-alpha-active-1" for p in untransferred)


def test_deactivation_with_successor_transfer_success(client: TestClient, auth_tokens):
    """验证停用时传入有效 successor_user_id，成功执行平滑交接并将账号停用。"""
    service = client.app.state.service
    headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}

    # 1. 确保待停用用户有项目
    _seed_lead_and_project(service)
    assert "transfer-target-lead" in service.repository.read().accounts
    assert "project-alpha-active-1" in service.repository.read().projects

    # 2. 发起附带 successor_user_id 的停用请求
    res = client.patch(
        "/api/v1/users/transfer-target-lead",
        headers=headers,
        json={
            "status": "disabled",
            "successor_user_id": "formal-alpha-admin",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "disabled"

    # 3. 验证项目负责人已平滑转交给 formal-alpha-admin
    team = service.repository.read().project_teams["project-alpha-active-1"]
    assert team["assembly_owner_id"] == "formal-alpha-admin"
    assert team["members"]["formal-alpha-admin"]["project_role"] == "lead"
    assert "transfer-target-lead" not in team["members"]

    # 4. 验证交接留痕
    handoffs = team.get("handoffs", [])
    assert len(handoffs) >= 1
    last_handoff = handoffs[-1]
    assert last_handoff["from_user_id"] == "transfer-target-lead"
    assert last_handoff["to_user_id"] == "formal-alpha-admin"


def test_tenant_and_rbac_isolation(client: TestClient, auth_tokens):
    """验证多租户强隔离（跨企业 404 NOT_FOUND）与 RBAC 权限隔离（非管理员写操作 403 FORBIDDEN）。"""
    alpha_admin_headers = {"Authorization": f"Bearer {auth_tokens['alpha_admin']}"}
    alpha_writer_headers = {"Authorization": f"Bearer {auth_tokens['alpha_writer']}"}

    # 1. 跨企业修改用户拦截 404 NOT_FOUND（防嗅探）
    res_cross = client.patch(
        "/api/v1/users/formal-beta-admin",
        headers=alpha_admin_headers,
        json={"name": "尝试越权修改"},
    )
    assert res_cross.status_code == 404, res_cross.text
    assert res_cross.json()["code"] == "NOT_FOUND"

    # 2. 跨企业指定交接接收人拦截 422 INVALID_SUCCESSOR
    res_cross_successor = client.post(
        "/api/v1/users/formal-alpha-admin/transfer",
        headers=alpha_admin_headers,
        json={"successor_user_id": "formal-beta-admin"},
    )
    assert res_cross_successor.status_code == 422, res_cross_successor.text
    assert res_cross_successor.json()["code"] == "VALIDATION_ERROR"

    # 3. 同企业内非管理员角色（投标编写人）尝试新增用户拦截 403 FORBIDDEN
    res_writer_create = client.post(
        "/api/v1/users",
        headers=alpha_writer_headers,
        json={
            "username": "writer_forbidden_user",
            "name": "非法新建",
            "company_id": "alpha",
            "role": "bid_writer",
            "password": "Password_2026!",
        },
    )
    assert res_writer_create.status_code == 403, res_writer_create.text
    assert res_writer_create.json()["code"] == "FORBIDDEN"

    # 4. 非管理员尝试修改用户拦截 403 FORBIDDEN
    res_writer_update = client.patch(
        "/api/v1/users/formal-alpha-admin",
        headers=alpha_writer_headers,
        json={"name": "非法更新"},
    )
    assert res_writer_update.status_code == 403, res_writer_update.text
    assert res_writer_update.json()["code"] == "FORBIDDEN"
