# 为什么有这个文件：验证导出批次的原子生成与历史快照（APP-M2-T202，PRD v1.8 §5.9.1 规则 13、异常，§5.9.3）。
# 它解决什么问题：两册与合标清单同一批次号、绑定同一次检查与定稿；任一册生成失败整批作废、不留可下载文件且不动正文；
# 旧批次在正文改动后标“已过期”，仍能下载当时生成的原文件，下载时照常重核权限。

from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest

from test_merge_checklist import _headers, _submission
from test_reference_flow import client, login  # noqa: F401


def _docx_text(data: bytes) -> str:
    return ZipFile(BytesIO(data)).read("word/document.xml").decode("utf-8")


def test_submission_batch_shares_one_number_and_binds_check_and_finalized_volumes(client):
    flow, check, export = _submission(client)
    assert export["status"] == "valid" and export["export_status"] == "completed"
    batch = export["batch_no"]
    assert batch.startswith("S") and batch.endswith("-001") and len(batch) == len("S20261029-001")
    assert {v["batch_no"] for v in export["volumes"]} == {batch}
    assert all(v["docx_sha256"] and v["size_bytes"] > 0 and "blob" not in v for v in export["volumes"])
    assert export["check_id"] == check["id"] and export["merge_checklist"]["check_id"] == check["id"]
    bound = export["bound_volumes"]
    assert set(bound) == {"technical", "business"}
    assert all(b["is_finalized"] and b["finalized_at"] and b["snapshot_sha256"] for b in bound.values())
    for volume in export["volumes"]:
        resp = client.get(volume["download_url"], headers=flow.headers)
        assert resp.status_code == 200 and resp.content[:2] == b"PK"
        assert resp.headers["X-ICG-Export-Status"] == "valid" and resp.headers["X-ICG-Export-Batch"] == batch
        import hashlib
        assert hashlib.sha256(resp.content).hexdigest() == volume["docx_sha256"]
    # 第二次内部稿：内部稿另有编号序列
    internal = flow.write("/exports", {"check_id": check["id"], "kind": "internal", "volume": "all"})["export"]
    assert internal["batch_no"].startswith("I") and internal["batch_no"].endswith("-001")


def test_one_failing_volume_fails_the_whole_batch_without_partial_files(client):
    flow = _ready_for_submission(client)
    check = flow.state()["checks"][-1]
    before = {c["id"]: (c["content"], c["revision"]) for c in flow.state()["chapters"]}
    workflow = client.app.state.workflow
    from icg.domain.export_batch import _render

    def broken(volume, document, filename):
        if volume == "business":
            raise RuntimeError("template missing")
        return _render(volume, document, filename)

    workflow.export_renderer = broken
    try:
        resp = client.post(f"{flow.path}/exports", json={"check_id": check["id"], "kind": "submission", "volume": "all"},
                           headers=_headers(flow))
    finally:
        workflow.export_renderer = None
    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert body["code"] == "EXPORT_FAILED" and "商务分册生成失败" in body["message"] and "整体作废" in body["message"]
    state = flow.state()
    failed = next(e for e in state["exports"] if e["id"] == body["details"]["export_id"])
    assert failed["status"] == "failed" and failed["volumes"] == [] and failed["failed_volume"] == "business"
    assert failed["batch_no"] == body["details"]["batch_no"] and not failed.get("merge_checklist")
    assert not any(e["kind"] == "submission" and e["status"] == "valid" for e in state["exports"])
    assert {c["id"]: (c["content"], c["revision"]) for c in state["chapters"]} == before
    assert all(v["is_finalized"] for v in state.get("volumes", {}).values()) if state.get("volumes") else True
    job = state["jobs"][-1] if isinstance(state["jobs"], list) else None
    if job:
        assert job["status"] == "failed" and job["error"]["code"] == "EXPORT_FAILED"
    # 失败批次没有可下载文件
    for volume in ("technical", "business"):
        assert client.get(f"{flow.path}/exports/{failed['id']}/{volume}", headers=flow.headers).status_code == 404
    # 修复后重新导出成功，序号顺延（失败批次也占号）
    retry = client.post(f"{flow.path}/exports", json={"check_id": check["id"], "kind": "submission", "volume": "all"},
                        headers=_headers(flow))
    assert retry.status_code == 200, retry.text
    assert retry.json()["export"]["batch_no"].endswith("-002")


def test_old_batch_stays_downloadable_as_the_original_file_after_content_changes(client):
    flow, check, export = _submission(client)
    technical = next(v for v in export["volumes"] if v["volume"] == "technical")
    original = client.get(technical["download_url"], headers=flow.headers).content
    unlock = client.post(f"{flow.path}/volumes/technical/unlock", json={"reason": "补充驻场方案"}, headers=_headers(flow))
    assert unlock.status_code == 200, unlock.text
    chapter = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
    flow.commit(chapter["id"], chapter["content"] + "\n新增：补充驻场方案段落。")
    listed = next(e for e in flow.state()["exports"] if e["id"] == export["id"])
    assert listed["status"] == "stale"
    resp = client.get(technical["download_url"], headers=flow.headers)
    assert resp.status_code == 200 and resp.headers["X-ICG-Export-Status"] == "stale"
    assert resp.content == original and "补充驻场方案段落" not in _docx_text(resp.content)
    # 过期后照常重核权限：递交版仍只限项目负责人
    assert client.get(technical["download_url"], headers=login(client, "alpha-editor")).status_code == 403
    assert client.get(technical["download_url"], headers=login(client, "beta-manager")).status_code == 404


def _ready_for_submission(client):
    from test_reference_flow import ProjectFlow
    flow = ProjectFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    assert check["passed"], check["issues"]
    for volume in ("technical", "business"):
        flow.cross_reviewed(volume)
        resp = client.post(f"{flow.path}/volumes/{volume}/finalize", json={"check_id": check["id"]}, headers=_headers(flow))
        assert resp.status_code == 200, resp.text
    return flow


@pytest.mark.parametrize("kind", ["submission", "internal"])
def test_batch_number_survives_idempotent_replay(client, kind):
    flow = _ready_for_submission(client)
    check = flow.state()["checks"][-1]
    key = str(uuid4())
    headers = {**login(client, "alpha-manager"), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": key}
    first = client.post(f"{flow.path}/exports", json={"check_id": check["id"], "kind": kind, "volume": "all"}, headers=headers)
    again = client.post(f"{flow.path}/exports", json={"check_id": check["id"], "kind": kind, "volume": "all"}, headers=headers)
    assert first.status_code == again.status_code == 200, (first.text, again.text)
    assert first.json()["export"]["batch_no"] == again.json()["export"]["batch_no"]
    assert len([e for e in flow.state()["exports"] if e["kind"] == kind]) == 1
