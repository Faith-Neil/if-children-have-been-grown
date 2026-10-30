# 为什么有这个文件：APP-M2-T260 口令登录的验收测试（PRD v1.8 §5.12.1 验收①～④⑦⑧）。
# 它解决什么问题：证明须改密由后端拦截、停用公司不能登录、失败提示不暴露账号是否存在、
# 密码规则按公司安全设置执行、锁定到期自动解锁，以及退出登录让令牌失效。

from dataclasses import replace

from fastapi.testclient import TestClient

from test_reference_flow import client, login  # noqa: F401

GENERIC = "账号或密码错误，请核实后重试。"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_writer(client: TestClient, username: str, password: str = "Init_Pass_2026") -> None:
    admin = login(client, "alpha-company-admin")
    created = client.post("/api/v1/users", headers=admin, json={
        "username": username, "name": "合成编写人", "company_id": "alpha", "role": "bid_writer", "password": password})
    assert created.status_code in (200, 201), created.text
    assert created.json()["must_change_password"] is True


def test_new_account_must_change_password_before_any_business_call(client: TestClient):
    _create_writer(client, "t260-new-writer")
    first = client.post("/api/v1/auth/login", json={"username": "t260-new-writer", "password": "Init_Pass_2026"})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["must_change_password"] is True
    policy_keys = ("min_length", "min_char_classes", "char_classes", "scope")
    assert {k: body["password_policy"][k] for k in policy_keys} == {
        "min_length": 8, "min_char_classes": 3, "char_classes": ["大写字母", "小写字母", "数字", "符号"], "scope": "company"}
    headers = _bearer(body["access_token"])

    # 改密前直接调业务接口被拒（后端判定，不靠页面跳转）
    for method, path in (("get", "/api/v1/projects"), ("get", "/api/v1/session"), ("get", "/api/v1/library")):
        refused = getattr(client, method)(path, headers=headers)
        assert refused.status_code == 403, (path, refused.text)
        assert refused.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    policy = client.get("/api/v1/auth/password-policy", headers=headers)
    assert policy.status_code == 200 and policy.json()["must_change_password"] is True

    wrong_old = client.post("/api/v1/auth/password", headers=headers,
                            json={"old_password": "Not_The_Pass_1", "new_password": "Brand_New_2026"})
    assert wrong_old.status_code == 422 and wrong_old.json()["code"] == "OLD_PASSWORD_INCORRECT"
    weak = client.post("/api/v1/auth/password", headers=headers,
                       json={"old_password": "Init_Pass_2026", "new_password": "short1"})
    assert weak.status_code == 422 and weak.json()["code"] == "PASSWORD_WEAK"
    problems = weak.json()["details"]["problems"]
    assert any("至少 8 位" in p for p in problems) and any("缺少大写字母、符号" in p for p in problems)
    same = client.post("/api/v1/auth/password", headers=headers,
                       json={"old_password": "Init_Pass_2026", "new_password": "Init_Pass_2026"})
    assert same.status_code == 422 and "不能与当前密码相同" in same.json()["details"]["problems"]

    changed = client.post("/api/v1/auth/password", headers=headers,
                          json={"old_password": "Init_Pass_2026", "new_password": "Brand_New_2026"})
    assert changed.status_code == 200, changed.text
    assert changed.json() == {"success": True, "must_change_password": False}
    assert client.get("/api/v1/projects", headers=headers).status_code == 200

    again = client.post("/api/v1/auth/login", json={"username": "t260-new-writer", "password": "Brand_New_2026"})
    assert again.status_code == 200 and again.json()["must_change_password"] is False
    audit = client.app.state.service.repository.read().audit
    assert any(e.get("action") == "user.change_password" and e.get("user_id") == "t260-new-writer" and e.get("forced")
               for e in audit)


def test_reset_password_forces_change_and_editing_the_user_keeps_the_flag(client: TestClient):
    _create_writer(client, "t260-reset-writer")
    admin = login(client, "alpha-company-admin")
    edited = client.patch("/api/v1/users/t260-reset-writer", headers=admin, json={"display_name": "改了昵称"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["must_change_password"] is True  # 修改资料不能顺带清掉须改密

    reset = client.post("/api/v1/users/t260-reset-writer/reset-password", headers=admin,
                        json={"new_password": "Reset_Pass_2026"})
    assert reset.status_code == 200, reset.text
    logged = client.post("/api/v1/auth/login", json={"username": "t260-reset-writer", "password": "Reset_Pass_2026"})
    assert logged.json()["must_change_password"] is True
    refused = client.get("/api/v1/projects", headers=_bearer(logged.json()["access_token"]))
    assert refused.status_code == 403 and refused.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_failure_messages_do_not_reveal_whether_the_account_exists(client: TestClient):
    _create_writer(client, "t260-disabled-writer")
    admin = login(client, "alpha-company-admin")
    disabled = client.patch("/api/v1/users/t260-disabled-writer", headers=admin, json={"status": "disabled"})
    assert disabled.status_code == 200, disabled.text

    attempts = [
        {"username": "no-such-account-t260", "password": "Whatever_2026"},
        {"username": "alpha-manager", "password": "Wrong_Pass_2026"},
        {"username": "t260-disabled-writer", "password": "Init_Pass_2026"},
    ]
    bodies = []
    for payload in attempts:
        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 401, res.text
        bodies.append((res.json()["code"], res.json()["message"]))
    assert bodies == [("INVALID_CREDENTIALS", GENERIC)] * 3
    reasons = {e.get("reason") for e in client.app.state.service.repository.read().audit
               if e.get("action") == "user.login_failed"}
    assert {"unknown_account", "wrong_password", "account_disabled"} <= reasons


def test_company_password_policy_applies_on_next_change_only(client: TestClient):
    admin = login(client, "alpha-company-admin")
    stricter = client.patch("/api/v1/companies/alpha/settings", headers=admin,
                            json={"password_min_length": 12, "password_min_char_classes": 4})
    assert stricter.status_code == 200, stricter.text
    loose = client.patch("/api/v1/companies/alpha/settings", headers=admin, json={"password_min_length": 6})
    assert loose.status_code == 422  # 低于平台默认的保存被服务端拒绝（验收⑧）

    # 已有账号仍可用原密码登录（验收⑦）
    assert client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"}).status_code == 200

    weak_for_company = client.post("/api/v1/users", headers=admin, json={
        "username": "t260-strict-writer", "name": "合成", "company_id": "alpha", "role": "bid_writer",
        "password": "Only_Three1"})
    assert weak_for_company.status_code == 422
    assert weak_for_company.json()["details"]["policy"]["min_length"] == 12
    ok = client.post("/api/v1/users", headers=admin, json={
        "username": "t260-strict-writer", "name": "合成", "company_id": "alpha", "role": "bid_writer",
        "password": "Four_Classes_2026"})
    assert ok.status_code in (200, 201), ok.text

    # 平台级账号按平台默认（8 位 3 类）
    platform = client.post("/api/v1/auth/login", json={"username": "admin", "password": "X_2026"}).json()
    policy = client.get("/api/v1/auth/password-policy", headers=_bearer(platform["access_token"])).json()
    assert policy["scope"] == "platform" and policy["min_length"] == 8 and policy["min_char_classes"] == 3


def test_disabled_company_cannot_log_in_and_sessions_end(client: TestClient):
    manager_headers = login(client, "alpha-manager")
    company_admin = login(client, "alpha-company-admin")
    platform = login(client, "admin")

    listed = client.get("/api/v1/companies", headers=platform)
    assert listed.status_code == 200, listed.text
    alpha = next(c for c in listed.json()["items"] if c["id"] == "alpha")
    assert alpha["status"] == "active" and alpha["user_count"] > 0 and listed.json()["can_change_status"] is True
    own = client.get("/api/v1/companies", headers=company_admin).json()
    assert [c["id"] for c in own["items"]] == ["alpha"] and own["can_change_status"] is False
    assert client.get("/api/v1/companies", headers=login(client, "alpha-editor")).status_code == 403

    forbidden = client.post("/api/v1/companies/alpha/status", headers=company_admin, json={"status": "disabled",
                                                                                            "confirm_name": alpha["name"]})
    assert forbidden.status_code == 403
    unconfirmed = client.post("/api/v1/companies/alpha/status", headers=platform, json={"status": "disabled"})
    assert unconfirmed.status_code == 422 and unconfirmed.json()["code"] == "CONFIRMATION_REQUIRED"
    assert client.post("/api/v1/companies/nowhere/status", headers=platform,
                       json={"status": "active"}).status_code == 404

    disabled = client.post("/api/v1/companies/alpha/status", headers=platform,
                           json={"status": "disabled", "confirm_name": alpha["name"]})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"

    assert client.get("/api/v1/projects", headers=manager_headers).status_code == 401
    refused = client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"})
    assert refused.status_code == 403 and refused.json()["code"] == "COMPANY_DISABLED"
    wrong = client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "Wrong_2026x"})
    assert wrong.status_code == 401 and wrong.json()["message"] == GENERIC  # 密码不对时不透露公司状态
    assert client.post("/api/v1/auth/login", json={"username": "beta-manager", "password": "X_2026"}).status_code == 200

    enabled = client.post("/api/v1/companies/alpha/status", headers=platform, json={"status": "active"})
    assert enabled.status_code == 200 and enabled.json()["status"] == "active"
    assert client.post("/api/v1/auth/login", json={"username": "alpha-manager", "password": "X_2026"}).status_code == 200
    actions = [e["action"] for e in client.app.state.service.repository.read().audit if e.get("company_id") == "alpha"]
    assert actions[-2:] == ["company.disable", "company.enable"]


def test_lock_expires_after_lock_minutes(client: TestClient):
    for i in range(5):
        client.post("/api/v1/auth/login", json={"username": "alpha-viewer", "password": f"Wrong_{i}_2026"})
    locked = client.post("/api/v1/auth/login", json={"username": "alpha-viewer", "password": "X_2026"})
    assert locked.status_code == 423 and "分钟后重试" in locked.json()["message"]

    repository = client.app.state.service.repository

    def age_lock(state):
        account = state.accounts["alpha-viewer"]
        state.accounts["alpha-viewer"] = replace(account, locked_at=account.locked_at - 16 * 60)

    repository.transaction(age_lock)
    unlocked = client.post("/api/v1/auth/login", json={"username": "alpha-viewer", "password": "X_2026"})
    assert unlocked.status_code == 200, unlocked.text
    account = repository.read().accounts["alpha-viewer"]
    assert account.is_locked is False and account.failed_login_attempts == 0 and account.locked_at is None
    assert any(e.get("action") == "user.unlock" and e.get("reason") == "lock_expired" for e in repository.read().audit)


def test_logout_revokes_the_token_and_branding_is_public(client: TestClient):
    headers = login(client)
    out = client.post("/api/v1/auth/logout", headers=headers)
    assert out.status_code == 200 and out.json() == {"success": True}
    assert client.get("/api/v1/projects", headers=headers).status_code == 401

    branding = client.get("/api/v1/branding")
    assert branding.status_code == 200
    assert branding.json() == {"product_name": "智能投标系统", "logo_horizontal_url": None}
