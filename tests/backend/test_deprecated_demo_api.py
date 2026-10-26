# 为什么有这个文件：验证 /api/demo 弃用生命周期治理与 RFC 8594 Sunset 响应头（落实用户 2026-10-26 拍板 B4）。
# 它解决什么问题：
# 1. 验证 GET /api/demo/accounts 与 POST /api/demo/login 在 OpenAPI 契约中显式声明 deprecated: true；
# 2. 验证 /api/demo/* 端点在正常与异常响应中均下发 Deprecation: true 与 Sunset: Sun, 15 Nov 2026 00:00:00 GMT；
# 3. 验证 /api/v1 正式业务端点绝不下发 Deprecation 与 Sunset 响应头；
# 4. 验证全站错误体严格遵循统一规范格式 {code, message, details, traceId}；
# 5. 同时兼容并覆盖 icg_demo.main 与新迁移的 icg.app.main 双应用装配实例。

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app as create_demo_app
try:
    from icg.app.main import create_app as create_icg_app
except ImportError:
    create_icg_app = None


EXPECTED_SUNSET_HEADER = "Sun, 15 Nov 2026 00:00:00 GMT"
EXPECTED_SUNSET_DATETIME = datetime(2026, 11, 15, 0, 0, 0, tzinfo=timezone.utc)

APP_FACTORIES = [create_demo_app]
if create_icg_app is not None:
    APP_FACTORIES.append(create_icg_app)


@pytest.fixture(params=APP_FACTORIES, ids=[f.__module__ for f in APP_FACTORIES])
def app_instance(request):
    return request.param()


@pytest.fixture
def client(app_instance):
    return TestClient(app_instance)


def test_openapi_demo_routes_deprecated_metadata(app_instance):
    """契约验证：OpenAPI schema 中 /api/demo/accounts 与 /api/demo/login 必须包含 deprecated: true。"""
    schema = app_instance.openapi()
    paths = schema.get("paths", {})

    assert "/api/demo/accounts" in paths, "必须保留 /api/demo/accounts 兼容路由"
    accounts_op = paths["/api/demo/accounts"].get("get", {})
    assert accounts_op.get("deprecated") is True, "/api/demo/accounts 必须显式声明 deprecated=True"

    assert "/api/demo/login" in paths, "必须保留 /api/demo/login 兼容路由"
    login_op = paths["/api/demo/login"].get("post", {})
    assert login_op.get("deprecated") is True, "/api/demo/login 必须显式声明 deprecated=True"


def test_demo_accounts_success_returns_sunset_and_deprecation(client):
    """运行时验证：GET /api/demo/accounts 成功时返回 Sunset 与 Deprecation 响应头。"""
    resp = client.get("/api/demo/accounts")
    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
    assert resp.headers.get("Sunset") == EXPECTED_SUNSET_HEADER
    assert resp.headers.get("X-Request-ID") is not None

    # 校验 RFC 8594 / RFC 7231 日期解析
    parsed_date = parsedate_to_datetime(resp.headers["Sunset"])
    assert parsed_date == EXPECTED_SUNSET_DATETIME


def test_demo_login_success_returns_sunset_and_deprecation(client):
    """运行时验证：POST /api/demo/login 成功时返回 Sunset 与 Deprecation 响应头。"""
    resp = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
    assert resp.headers.get("Sunset") == EXPECTED_SUNSET_HEADER
    assert resp.headers.get("X-Request-ID") is not None

    data = resp.json()
    assert "access_token" in data
    assert "user" in data


def test_demo_routes_error_responses_contain_sunset_and_deprecation(client, monkeypatch):
    """运行时验证：/api/demo 触发错误时（如 422 字段校验或 403 生产禁用），依然下发 Sunset 与 Deprecation 头。"""
    # 422 验证错误
    resp_422 = client.post("/api/demo/login", json={"account_id": 99999})
    assert resp_422.status_code == 422
    assert resp_422.headers.get("Deprecation") == "true"
    assert resp_422.headers.get("Sunset") == EXPECTED_SUNSET_HEADER
    err_422 = resp_422.json()
    assert err_422["code"] == "VALIDATION_ERROR"
    assert "traceId" in err_422
    assert "message" in err_422
    assert "details" in err_422

    # 403 生产门禁拦截
    monkeypatch.setenv("ICG_ALLOW_DEMO_LOGIN", "0")
    resp_403 = client.post("/api/demo/login", json={"account_id": "alpha-manager"})
    assert resp_403.status_code == 403
    assert resp_403.headers.get("Deprecation") == "true"
    assert resp_403.headers.get("Sunset") == EXPECTED_SUNSET_HEADER
    err_403 = resp_403.json()
    assert err_403["code"] == "FORBIDDEN"
    assert "traceId" in err_403


def test_v1_endpoints_do_not_contain_demo_deprecation_headers(client):
    """隔离验证：/api/v1 正式业务端点绝不应携带 /api/demo 的 Deprecation 与 Sunset 响应头。"""
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 401
    assert "Deprecation" not in resp.headers
    assert "Sunset" not in resp.headers
    assert resp.headers.get("X-Request-ID") is not None

    err = resp.json()
    assert err["code"] == "UNAUTHENTICATED"
    assert "traceId" in err
    assert "message" in err
    assert "details" in err
