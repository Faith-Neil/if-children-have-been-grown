# 为什么有这个文件：验证条款 PATCH 挂证据时拒绝过期、缺协议和受限资料。
# 它解决什么问题：避免历史标书和未确认之外，过期、仅供参考、缺协议或无权的受限资料仍能挂上。

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import Account
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def _row(flow):
    return flow.state()["requirements"][0]


def _mount(flow, evidence_id, expected=200):
    return flow.write("/requirements/" + _row(flow)["id"], {"evidence_ids": [evidence_id]}, "PATCH", expected)


def _set_role(client, role):
    repository = client.app.state.workflow.demo.repository

    def operation(state):
        current = state.accounts["alpha-manager"]
        state.accounts["alpha-manager"] = Account(current.id, current.name, current.company_id, role)
        return None

    repository.transaction(operation)


def test_library_exposes_is_restricted_and_rejects_the_old_name(client):
    flow = ProjectFlow(client).reviewed()
    item = flow.library(source_tier="own", is_restricted=False, is_long_term=False, valid_to="2027-12-31")
    assert item["is_restricted"] is False
    assert item["source_tier"] == "own"
    assert "restricted" not in item
    library = client.get("/api/v1/library", headers=flow.headers).json()
    rejected = client.post("/api/v1/library", json={
        "name": "旧字段", "type": "qualification", "content": "合成内容。", "restricted": True,
    }, headers={**flow.headers, "If-Match": str(library["revision"]), "Idempotency-Key": str(uuid4())})
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "VALIDATION_ERROR"


def test_expired_evidence_is_rejected_on_mount_unless_long_term(client):
    flow = ProjectFlow(client).reviewed()
    expired = flow.library(valid_to="2026-01-01", is_long_term=False, status="confirmed")
    error = _mount(flow, expired["id"], 409)
    assert error["code"] == "EVIDENCE_EXPIRED"
    covered = flow.library(valid_until="2026-01-01", status="confirmed")
    assert _mount(flow, covered["id"], 409)["code"] == "EVIDENCE_EXPIRED"
    lasting = flow.library(valid_to="2026-01-01", is_long_term=True, status="confirmed")
    assert _mount(flow, lasting["id"])["requirement"]["evidence_ids"] == [lasting["id"]]


def test_reference_and_partner_without_agreement_are_distinctly_unusable(client):
    flow = ProjectFlow(client).reviewed()
    reference = flow.library(source_tier="reference", status="confirmed")
    reference_error = _mount(flow, reference["id"], 409)
    assert reference_error["code"] == "EVIDENCE_NOT_USABLE"
    assert "仅供参考" in reference_error["message"]
    partner = flow.library(source_tier="partner", partner_entity_id="partner-synth", status="confirmed")
    missing = _mount(flow, partner["id"], 409)
    assert missing["code"] == "EVIDENCE_NOT_USABLE"
    assert "缺协议" in missing["message"]
    assert missing["message"] != reference_error["message"]
    flow.write("", {"project_partners": [{
        "partner_entity_id": "partner-synth", "agreement_attachment_id": None,
    }]}, "PATCH")
    assert _mount(flow, partner["id"], 409)["message"] == missing["message"]
    flow.write("", {"project_partners": [{
        "partner_entity_id": "partner-synth", "agreement_attachment_id": "agreement-synth",
    }]}, "PATCH")
    assert _mount(flow, partner["id"])["requirement"]["evidence_ids"] == [partner["id"]]


def test_restricted_evidence_requires_admin_or_acl(client):
    flow = ProjectFlow(client).reviewed()
    hidden = flow.library(is_restricted=True, status="confirmed", acl_user_ids=[])
    denied = _mount(flow, hidden["id"], 403)
    assert denied["code"] == "FORBIDDEN"
    assert denied["code"] != "MATRIX_RESPONSE_FORBIDDEN"
    assert "受限" in denied["message"]
    allowed = flow.library(is_restricted=True, status="confirmed", acl_user_ids=["alpha-manager"])
    assert _mount(flow, allowed["id"])["requirement"]["evidence_ids"] == [allowed["id"]]
    for role in ("company_admin", "data_admin"):
        _set_role(client, role)
        again = flow.library(is_restricted=True, status="confirmed", acl_user_ids=[])
        assert _mount(flow, again["id"])["requirement"]["evidence_ids"] == [again["id"]]
        _set_role(client, "manager")
