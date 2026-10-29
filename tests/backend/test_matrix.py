# 为什么有这个文件：验证响应矩阵（PRD v1.8 §5.3.1，APP-M2-T112～T117）。
# 它解决什么问题：响应方式与偏离口径同源；星号条款不能偏离；风险与状态分开；批量匹配只给候选不挂接；
# 分流由负责人确认；Excel 可直接打开；只读成员看得到改不了。

from uuid import uuid4

from icg.infra.xlsx import read_xlsx_rows
from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _row(flow, volume="technical"):
    return next(r for r in flow.state()["requirements"] if r["volume"] == volume)


def _matrix(flow):
    resp = flow.client.get(f"{flow.path}/matrix", headers=flow.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_matrix_lists_response_type_risk_and_suggested_volume(client):
    flow = ProjectFlow(client).ready()
    data = _matrix(flow)
    assert data["stats"]["total"] == len(flow.state()["requirements"]) and data["stats"]["coverage"] == 100
    star = next(i for i in data["items"] if i["critical"])
    assert star["response_type"] is None and "routing_pending" in star["risk_flags"]
    assert {i["suggested_volume"] for i in data["items"]} <= {"technical", "business"}


def test_response_type_maps_to_deviation_and_star_rows_are_blocked_not_hidden(client):
    flow = ProjectFlow(client).ready()
    star = next(r for r in flow.state()["requirements"] if "★" in r["text"])
    error = flow.write("/requirements/" + star["id"], {"response_type": "not_applicable", "reason": "x"}, "PATCH", expected=409)
    assert "不能标为不适用" in error["message"]
    # 做不到的星号条款可以如实登记偏离：列为阻断项，检查不通过
    flow.write("/requirements/" + star["id"], {"response_type": "deviate", "deviation_reason": "暂不能每月巡检"}, "PATCH")
    item = next(i for i in _matrix(flow)["items"] if i["id"] == star["id"])
    assert "star_deviation" in item["risk_flags"]
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert any(i["severity"] in ("blocker", "blocking") for i in check["issues"]) and not check["passed"]
    ok = flow.write("/requirements/" + star["id"], {"response_type": "exceed"}, "PATCH")["requirement"]
    assert ok["deviation_type"] == "positive"
    other = _row(flow, "business")
    missing = flow.write("/requirements/" + other["id"], {"response_type": "deviate"}, "PATCH", expected=422)
    assert missing["code"] == "REASON_REQUIRED"
    flow.write("/requirements/" + other["id"], {"response_type": "deviate", "deviation_reason": "资质证书年审中"}, "PATCH")
    item = next(i for i in _matrix(flow)["items"] if i["id"] == other["id"])
    assert item["response_label"] == "偏离" and item["deviation_label"] == "负偏离"


def test_evidence_invalid_is_a_risk_not_a_status(client):
    flow = ProjectFlow(client).ready()
    business = _row(flow, "business")
    item = next(i for i in _matrix(flow)["items"] if i["id"] == business["id"])
    assert item["evidence"] and item["evidence"][0]["usable"] and "evidence_invalid" not in item["risk_flags"]
    library = client.get("/api/v1/library", headers=flow.headers).json()
    evidence_id = item["evidence"][0]["id"]
    client.patch(f"/api/v1/library/{evidence_id}", json={"valid_until": "2026-01-01", "status": "confirmed", "reason": "改有效期"},
                 headers={**flow.headers, "If-Match": str(library["revision"]), "Idempotency-Key": str(uuid4())})
    item = next(i for i in _matrix(flow)["items"] if i["id"] == business["id"])
    assert "evidence_invalid" in item["risk_flags"] and item["status"] == "confirmed"


def test_batch_match_returns_candidates_without_attaching(client):
    flow = ProjectFlow(client).ready()
    flow.library(name="合成企业资质（第二份）", content="仅供测试：有效企业资质证明已核对。")
    flow.library(name="2024 某银行投标书", type="history", content="企业资质证明详见附件。", status="pending")
    row = _row(flow, "business")
    before = row["evidence_ids"]
    resp = client.post(f"{flow.path}/matrix/match", json={"requirement_ids": [row["id"]]}, headers=flow.headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()["results"][0]
    assert result["structured"] and all("attachable" in c and c["basis"] for c in result["structured"])
    assert all(c["type"] == "history" for c in result["history_reference"])
    assert not any(c.get("type") == "history" for c in result["structured"])
    assert next(r for r in flow.state()["requirements"] if r["id"] == row["id"])["evidence_ids"] == before


def test_routing_confirmation_is_lead_only_and_recorded(client):
    flow = ProjectFlow(client).ready()
    row = _row(flow)
    writer = {**login(client, "alpha-editor"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    denied = client.post(f"{flow.path}/matrix/routing", json={"rows": [{"id": row["id"], "volume": "technical"}]}, headers=writer)
    assert denied.status_code == 403
    flow.write("/matrix/routing", {"rows": [{"id": row["id"], "volume": "technical", "is_cross_volume": True}]})
    item = next(i for i in _matrix(flow)["items"] if i["id"] == row["id"])
    assert item["volume_confirmed_at"] and item["is_cross_volume"] and "routing_pending" not in item["risk_flags"]


def test_matrix_excel_and_readonly_access(client):
    flow = ProjectFlow(client).ready()
    resp = client.get(f"{flow.path}/matrix.xlsx", headers=flow.headers)
    assert resp.status_code == 200 and resp.content[:2] == b"PK"
    rows = read_xlsx_rows(resp.content)
    assert rows[0][0].startswith("响应矩阵") and rows[3][:3] == ["序号", "要求原文", "页码"]
    assert len(rows) - 4 == len(flow.state()["requirements"])
    viewer = login(client, "alpha-viewer")
    assert client.get(f"{flow.path}/matrix", headers=viewer).status_code == 200
    assert client.get(f"{flow.path}/matrix", headers=login(client, "beta-manager")).status_code == 404
    row = _row(flow)
    resp = client.patch(f"{flow.path}/requirements/{row['id']}", json={"assignee_id": "alpha-viewer"},
                        headers={**flow.headers, "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())})
    assert resp.status_code == 422 and resp.json()["code"] == "ASSIGNEE_NOT_WRITABLE"
