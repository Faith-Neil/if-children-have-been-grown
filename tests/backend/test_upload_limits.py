# 为什么有这个文件：验证全应用统一的上传上限（默认 100MB，ICG_MAX_UPLOAD_MB 可调）、二进制直传通道与原件文件存储。
# 它解决什么问题：真实扫描件几十 MB；原件不能再塞进业务状态 JSON（MySQL 单包上限），超限必须在读完之前就拒绝。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.domain.upload_limits import max_upload_bytes
from icg_demo.main import create_app
from test_reference_flow import TENDER, ProjectFlow, client, login  # noqa: F401


def _raw_headers(flow):
    return {**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4()),
            "Content-Type": "application/octet-stream"}


def test_default_limit_is_100mb(monkeypatch):
    monkeypatch.delenv("ICG_MAX_UPLOAD_MB", raising=False)
    assert max_upload_bytes() == 100 * 1024 * 1024


def test_raw_tender_upload_stores_original_outside_state_and_parses(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_BLOB_DIR", str(tmp_path))
    flow = ProjectFlow(client)
    resp = client.post(f"{flow.path}/files/raw", params={"filename": "合成招标.txt"}, content=TENDER.encode(),
                       headers=_raw_headers(flow))
    assert resp.status_code == 200, resp.text
    file_id = resp.json()["file"]["id"]
    assert "blob" not in resp.json()["file"] and "content" not in resp.json()["file"]
    stored = list(tmp_path.rglob("*"))
    assert any(p.is_file() and p.read_bytes() == TENDER.encode() for p in stored)
    state = client.app.state.service.repository.read()
    record = state.workflows[flow.id]["files"][file_id]
    assert "content" not in record and record["blob"] == record["sha256"]
    original = client.get(f"{flow.path}/files/{file_id}", headers=flow.headers)
    assert original.status_code == 200 and original.content == TENDER.encode()
    flow.write("/parse", {})
    assert flow.state()["files"][0]["status"] == "parsed" and flow.state()["requirements"]


def test_oversize_upload_rejected_on_both_channels(client, monkeypatch):
    monkeypatch.setenv("ICG_MAX_UPLOAD_MB", "1")
    flow = ProjectFlow(client)
    big = b"x" * (1024 * 1024 + 1)
    raw = client.post(f"{flow.path}/files/raw", params={"filename": "大.txt"}, content=big, headers=_raw_headers(flow))
    assert raw.status_code == 413 and raw.json()["code"] == "FILE_SIZE_LIMIT" and "1MB" in raw.json()["message"]
    import base64
    js = flow.write("/files", {"filename": "大.txt", "content_base64": base64.b64encode(big).decode()}, expected=413)
    assert js["code"] == "FILE_SIZE_LIMIT"
    ok = client.post(f"{flow.path}/files/raw", params={"filename": "小.txt"}, content=TENDER.encode(), headers=_raw_headers(flow))
    assert ok.status_code == 200, ok.text


def test_kb_raw_upload_uses_same_limit(monkeypatch):
    fake = FakeRagflowV1()
    app = create_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as test_client:
        headers = {**login(test_client, "alpha-data-admin"), "Content-Type": "application/octet-stream"}
        resp = test_client.post("/api/v1/kb-admin/datasets/history/documents/raw",
                                params={"filename": "2024投标书.docx", "content_type": "application/msword"},
                                content=b"history bid body", headers=headers)
        assert resp.status_code == 200, resp.text
        assert any(d["name"] == "2024投标书.docx" for d in fake.documents.values())
        monkeypatch.setenv("ICG_MAX_UPLOAD_MB", "1")
        too_big = test_client.post("/api/v1/kb-admin/datasets/history/documents/raw", params={"filename": "大.docx"},
                                   content=b"x" * (1024 * 1024 + 10), headers=headers)
        assert too_big.status_code == 413
