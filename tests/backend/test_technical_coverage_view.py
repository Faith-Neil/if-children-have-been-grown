# 为什么有这个文件：核对覆盖视图（即矩阵）的检索摘要、人工确认原因、单节重试与人工确认接口。
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg.domain.technical_rag import rag_summary
from icg.domain.technical_response_plan import confirm_reasons
from icg_demo.main import create_app
from test_generation_session import _finish, _frames, _ready, _start
from test_reference_flow import login


@pytest.fixture()
def client():
    with TestClient(create_app()) as actual:
        yield actual


def test_rag_summary_status_follows_hits_and_errors():
    assert rag_summary({"history_searched": True, "history_hits": 2, "top": [{"name": "a"}] * 5})["status"] == "hit"
    assert len(rag_summary({"history_hits": 1, "top": [{"name": "a"}] * 5})["top"]) == 3
    assert rag_summary({"history_searched": True, "material_searched": True})["status"] == "empty"
    assert rag_summary({"skip_reason": "ReadTimeout"})["status"] == "failed"
    assert rag_summary({})["status"] == "skipped"


def test_confirm_reasons():
    assert confirm_reasons({"generation_status": "failed"}, False) == ["生成失败"]
    assert confirm_reasons({"generation_status": "pending"}, True) == []
    generated = {"generation_status": "generated", "response_status": "needs_confirm", "rag": {"status": "empty"},
                 "constraint_check": {"missing": ["R-01"]}}
    assert confirm_reasons(generated, True) == ["知识库无依据", "废标约束待核", "质量八条未达标"]
    assert confirm_reasons({**generated, "response_status": "confirmed"}, True) == []


def _generate(client):
    headers, project_id, workspace, model = _ready(client)
    responses: list = []
    worker = _start(client, headers, project_id, workspace, responses)
    assert model.started.wait(10)
    model.gate.set()
    events = _frames(_finish(worker, responses).text)
    assert events[-1]["event"] == "volume.done"
    return headers, project_id, events


def test_generated_rows_carry_rag_and_confirm_flow(client):
    headers, project_id, events = _generate(client)
    generated = [item for item in events if item["event"] == "task.patched" and item.get("generation_status") == "generated"]
    assert generated and all(item["rag"]["status"] in ("hit", "empty", "skipped", "failed") for item in generated)
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    rows = workspace["coverage_rows"]
    assert workspace["tender_digest"]["tech"] or workspace["tender_digest"]["scoring"]
    row = rows[0]
    assert row["rag"]["query"] and row["retryable"] is True and row["digest_id"]
    assert "知识库无依据" in row["confirm_reasons"]

    path = f"/api/v1/projects/{project_id}/technical-tasks/{row['task_id']}/confirm"
    confirmed = client.post(path, json={}, headers={**headers, "If-Match": str(workspace["revision"]),
                                                     "Idempotency-Key": str(uuid4())})
    assert confirmed.status_code == 200, confirmed.text
    after = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    mine = [item for item in after["coverage_rows"] if item["task_id"] == row["task_id"]]
    assert all(item["confirm_reasons"] == [] and item["confirmed_at"] for item in mine)
    assert all(item["response_status"] == "confirmed" for item in mine)

    missing = client.post(f"/api/v1/projects/{project_id}/technical-tasks/nope/confirm", json={},
                          headers={**headers, "If-Match": str(after["revision"]), "Idempotency-Key": str(uuid4())})
    assert missing.status_code == 404


def test_readonly_project_member_cannot_confirm(client):
    headers, project_id, _events = _generate(client)
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    team = client.put(f"/api/v1/projects/{project_id}/team", headers={
        **headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())}, json={
        "members": [{"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical"]},
                    {"user_id": "alpha-editor", "project_role": "readonly", "volumes": ["technical"]}],
        "volumes": [{"volume": "technical", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-manager"})
    assert team.status_code == 200, team.text
    reader = login(client, "alpha-editor")
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=reader).json()
    task_id = workspace["coverage_rows"][0]["task_id"]
    denied = client.post(f"/api/v1/projects/{project_id}/technical-tasks/{task_id}/confirm", json={}, headers={
        **reader, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())})
    assert denied.status_code == 403, denied.text
    retry = client.post(f"/api/v1/projects/{project_id}/technical-volume/stream", json={
        "section": workspace["coverage_rows"][0]["outline_title"]}, headers={
        **reader, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())})
    assert retry.status_code == 403, retry.text


def test_writer_without_chapter_edit_cannot_confirm(client):
    headers, project_id, _events = _generate(client)
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    team = client.put(f"/api/v1/projects/{project_id}/team", headers={
        **headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())}, json={
        "members": [{"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical"]},
                    {"user_id": "alpha-editor", "project_role": "writer", "volumes": []}],
        "volumes": [{"volume": "technical", "owner_id": "alpha-manager"}], "assembly_owner_id": "alpha-manager"})
    assert team.status_code == 200, team.text
    writer = login(client, "alpha-editor")
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=writer).json()
    task_id = workspace["coverage_rows"][0]["task_id"]
    denied = client.post(f"/api/v1/projects/{project_id}/technical-tasks/{task_id}/confirm", json={}, headers={
        **writer, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())})
    assert denied.status_code == 403, denied.text
