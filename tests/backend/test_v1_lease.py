# 为什么有这个文件：证明编辑权的取得、续期和释放已经接到 /api/v1。
# 它解决什么问题：避免新路由改掉 120 秒租约、接管规则，或让旧验证页失去原入口。

import json

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DemoService, iso_time
from icg_demo.main import create_app
from test_demo import CHAPTER, MutableClock, acquire, login
from test_error_idempotency import SPEC, implemented_contract

V1_LOCK = f"/api/v1/chapters/{CHAPTER}/lock"
V1_LOCK_PATH = "/api/v1/chapters/{chapter_id}/lock"


@pytest.fixture
def clock():
    return MutableClock()


@pytest.fixture
def client(clock):
    with TestClient(create_app(clock=clock)) as actual_client:
        yield actual_client


def test_v1_lease_uses_the_same_rules_and_error_body(client, clock):
    editor = login(client)
    acquired = client.post(V1_LOCK, headers=editor, json={})
    assert acquired.status_code == 200, acquired.text
    body = acquired.json()
    assert body["owner_id"]
    assert body["expires_at"] == iso_time(clock.value + DemoService.LEASE_SECONDS)
    token = body["lease_token"]

    clock.value += 30
    renewed = client.post(V1_LOCK + "/renew", headers=editor, json={"lease_token": token})
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["lease_token"] == token
    assert renewed.json()["expires_at"] == iso_time(clock.value + DemoService.LEASE_SECONDS)

    other = login(client)
    held = client.post(V1_LOCK, headers=other, json={})
    assert held.status_code == 423
    assert set(held.json()) == {"code", "message", "details", "traceId"}
    assert held.json()["code"] == "LOCK_HELD"
    assert held.json()["traceId"] == held.headers["X-Request-ID"]

    manager = login(client, "alpha-manager")
    missing_reason = client.post(V1_LOCK, headers=manager, json={})
    assert missing_reason.status_code == 409
    assert missing_reason.json()["code"] == "TAKEOVER_REASON_REQUIRED"
    takeover = client.post(V1_LOCK, headers=manager, json={"takeover_reason": "负责人接管本节"})
    assert takeover.status_code == 200, takeover.text
    assert takeover.json()["lease_token"] != token

    stale = client.post(V1_LOCK + "/renew", headers=editor, json={"lease_token": token})
    assert stale.status_code == 423
    assert stale.json()["code"] == "LOCK_LOST"

    released = client.post(
        V1_LOCK + "/release", headers=manager, json={"lease_token": takeover.json()["lease_token"]})
    assert released.status_code == 200
    assert released.json() == {"released": True}


def test_editor_cannot_take_over_on_v1(client):
    manager, editor = login(client, "alpha-manager"), login(client)
    client.post(V1_LOCK, headers=manager, json={})
    refused = client.post(V1_LOCK, headers=editor, json={"takeover_reason": "编写人越权接管"})
    assert refused.status_code == 403
    assert refused.json()["code"] == "FORBIDDEN"
    assert "error" not in refused.json()


def test_legacy_lock_routes_remain_for_the_demo_page(client):
    headers = login(client)
    token = acquire(client, headers)
    renewed = client.post(f"/api/chapters/{CHAPTER}/lock/renew", headers=headers, json={"lease_token": token})
    assert renewed.status_code == 200
    assert "error" not in renewed.json()
    assert "traceId" not in renewed.json()


def test_openapi_exports_the_v1_lease_routes():
    schema = create_app().openapi()
    for suffix in ("", "/renew", "/release"):
        operation = schema["paths"][V1_LOCK_PATH + suffix]["post"]
        assert operation["operationId"]
        for response in operation["responses"].values():
            ref = response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
            assert not ref.endswith("/ErrorResponse")
    stored = json.loads(SPEC.read_text(encoding="utf-8"))
    assert implemented_contract(stored) == schema
