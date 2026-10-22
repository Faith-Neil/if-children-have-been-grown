# 为什么有这个文件：证明单章导出记下当时的检查、版本和输入摘要。
# 它解决什么问题：来源变了以后，旧文件不能再被当成当前有效结果。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import CHAPTER, MutableClock, acquire, login


@pytest.fixture
def client():
    with TestClient(create_app(clock=MutableClock())) as actual_client:
        yield actual_client


def test_export_names_the_bound_check_version_and_input(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    from test_demo import checked_export

    checked, exported = checked_export(client, headers, lease)
    assert exported["check_id"] == checked["id"]
    assert exported["revision"] >= 1
    assert exported["content_hash"]
    assert exported["input_fingerprint"]
    assert exported["excludes_drafts"] is True
    assert "stale" not in exported
    download = client.get(exported["download_url"], headers=headers)
    assert download.status_code == 200


def test_input_change_retires_the_old_chapter_export(client):
    headers = login(client, "alpha-manager")
    lease = acquire(client, headers)
    from test_demo import checked_export

    checked, exported = checked_export(client, headers, lease)
    library = client.get("/api/v1/library", headers=headers)
    assert library.status_code == 200, library.text
    created = client.post(
        "/api/v1/library",
        headers={**headers, "If-Match": str(library.json()["revision"]), "Idempotency-Key": str(uuid4())},
        json={"name": "合成企业资质", "type": "qualification", "content": "仅供测试：有效企业资质已核对。",
              "valid_until": "2027-12-31", "status": "confirmed"},
    )
    assert created.status_code == 200, created.text
    refused = client.post(
        f"/api/chapters/{CHAPTER}/exports", headers=headers, json={"check_id": checked["id"]})
    assert refused.status_code == 409
    assert (refused.json().get("code") or refused.json().get("error", {}).get("code")) == "CHECK_STALE"
    download = client.get(exported["download_url"], headers=headers)
    assert download.status_code == 409
    assert (download.json().get("code") or download.json().get("error", {}).get("code")) == "EXPORT_STALE"
    assert "stale" not in exported
