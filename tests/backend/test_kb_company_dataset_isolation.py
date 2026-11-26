# 为什么有这个文件：验收 ISSUE-052 各公司双库数据集按 company_id 隔离、禁止混用。
# 它解决什么问题：证明 dataset 全名绑定 ${company_id}::，两家公司 ensure 后互不引用。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app
from icg.domain.knowledge_base import dataset_full_name
from test_reference_flow import login


def test_dataset_full_names_are_per_company():
    assert dataset_full_name("co-aaa11111", "history") == "co-aaa11111::icg-history"
    assert dataset_full_name("co-bbb22222", "materials") == "co-bbb22222::icg-material"
    assert dataset_full_name("co-aaa11111", "history") != dataset_full_name("co-bbb22222", "history")


@pytest.fixture()
def fake():
    return FakeRagflowV1()


@pytest.fixture()
def client(fake):
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as test_client:
        yield test_client


def test_two_companies_ensure_separate_history_and_material_datasets(client: TestClient, fake: FakeRagflowV1):
    platform = login(client, "platform-admin")
    a = client.post("/api/v1/companies", headers=platform, json={
        "name": "双库隔离甲", "admin_username": "kb-iso-a", "admin_name": "甲管",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    })
    b = client.post("/api/v1/companies", headers=platform, json={
        "name": "双库隔离乙", "admin_username": "kb-iso-b", "admin_name": "乙管",
        "admin_password": "Init_Pass_2026", "must_change_password": False,
    })
    assert a.status_code == 201 and b.status_code == 201, (a.text, b.text)
    cid_a = a.json()["company"]["id"]
    cid_b = b.json()["company"]["id"]

    headers_a = {"Authorization": "Bearer " + client.post(
        "/api/v1/auth/login", json={"username": "kb-iso-a", "password": "Init_Pass_2026"}).json()["access_token"]}
    headers_b = {"Authorization": "Bearer " + client.post(
        "/api/v1/auth/login", json={"username": "kb-iso-b", "password": "Init_Pass_2026"}).json()["access_token"]}

    # 先部署管道，再 ensure（与现网 kb-admin 用法一致）
    assert client.post("/api/v1/kb-admin/pipelines/deploy", headers=headers_a, json={}).status_code == 200
    assert client.post("/api/v1/kb-admin/pipelines/deploy", headers=headers_b, json={}).status_code == 200

    ids_a: dict[str, str] = {}
    ids_b: dict[str, str] = {}
    for kind in ("history", "materials"):
        ea = client.post(f"/api/v1/kb-admin/datasets/{kind}/ensure", headers=headers_a, json={})
        eb = client.post(f"/api/v1/kb-admin/datasets/{kind}/ensure", headers=headers_b, json={})
        assert ea.status_code == 200, ea.text
        assert eb.status_code == 200, eb.text
        body_a, body_b = ea.json(), eb.json()
        ids_a[kind] = body_a["dataset_id"]
        ids_b[kind] = body_b["dataset_id"]
        assert fake.datasets[ids_a[kind]]["name"] == dataset_full_name(cid_a, kind)
        assert fake.datasets[ids_b[kind]]["name"] == dataset_full_name(cid_b, kind)

    assert ids_a["history"] != ids_b["history"]
    assert ids_a["materials"] != ids_b["materials"]
    assert set(ids_a.values()).isdisjoint(set(ids_b.values()))
