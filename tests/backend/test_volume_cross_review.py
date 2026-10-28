# 为什么有这个文件：验证 APP-M2-T144 分册交叉复核、定稿快照与解锁失效（PRD v1.8 §2.3、§4.2、§5.8.5）。
# 它解决什么问题：
# 1. 复核人不能是本分册编写人，只有被指定的人能确认，退回须写原因；
# 2. 未复核、复核后正文改动、仍有待人工问题时都不能定稿；
# 3. 定稿后后台拒绝取得编辑权和处理队列问题（不只靠页面禁用）；
# 4. 解锁须写原因，复核作废，旧检查过期；本册负责人可定稿本册。

from uuid import uuid4

from test_reference_flow import ProjectFlow, client, login  # noqa: F401


def _post(flow, path, data, account="alpha-manager"):
    headers = {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    return flow.client.post(flow.path + path, json=data, headers=headers)


def _technical(flow):
    return next(c for c in flow.state()["chapters"] if c["volume"] == "technical")


def test_reviewer_rules(client):
    flow = ProjectFlow(client).ready()
    editor_as_reviewer = _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-manager"})
    assert editor_as_reviewer.status_code == 409 and editor_as_reviewer.json()["code"] == "CROSS_REVIEWER_IS_EDITOR"
    readonly = _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-viewer"})
    assert readonly.status_code == 422
    by_writer = _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-editor"}, "alpha-editor")
    assert by_writer.status_code == 403 and by_writer.json()["code"] == "VOLUME_OWNER_REQUIRED"

    assert _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-editor"}).status_code == 200
    stranger = _post(flow, "/volumes/technical/cross-review/confirm", {"decision": "approved"})
    assert stranger.status_code == 403 and stranger.json()["code"] == "CROSS_REVIEWER_REQUIRED"
    no_note = _post(flow, "/volumes/technical/cross-review/confirm", {"decision": "returned"}, "alpha-editor")
    assert no_note.status_code == 422
    returned = _post(flow, "/volumes/technical/cross-review/confirm",
                     {"decision": "returned", "note": "第二节巡检频次与事实表不一致"}, "alpha-editor")
    assert returned.status_code == 200 and returned.json()["cross_review"]["status"] == "returned"
    blocked = _post(flow, "/volumes/technical/finalize", {})
    assert blocked.status_code == 409 and blocked.json()["code"] == "CROSS_REVIEW_REQUIRED"


def test_finalize_requires_review_on_current_content(client):
    flow = ProjectFlow(client).ready()
    missing = _post(flow, "/volumes/technical/finalize", {})
    assert missing.status_code == 409 and missing.json()["code"] == "CROSS_REVIEW_REQUIRED"

    flow.cross_reviewed("technical")
    flow.commit(_technical(flow)["id"], "技术正文验收标记：复核后又改了一句。")
    status = client.get(flow.path + "/volumes/technical", headers=flow.headers).json()
    assert status["cross_review"]["status"] == "approved" and status["cross_review"]["stale"] is True
    stale = _post(flow, "/volumes/technical/finalize", {})
    assert stale.status_code == 409 and stale.json()["details"]["status"] == "stale"

    flow.cross_reviewed("technical")
    done = _post(flow, "/volumes/technical/finalize", {})
    assert done.status_code == 200, done.text
    assert done.json()["volume"]["snapshot"][0]["chapter_id"] == _technical(flow)["id"]
    assert done.json()["volume"]["cross_reviewer_id"] == "alpha-editor"


def test_pending_human_issues_block_finalize(client):
    flow = ProjectFlow(client).ready()
    chapter_id = _technical(flow)["id"]
    flow.commit(chapter_id, "技术正文：每月巡检，业绩见【待补：同类业绩】。")
    assert _post(flow, f"/chapters/{chapter_id}/loop/recheck", {}).status_code == 200
    flow.cross_reviewed("technical")
    blocked = _post(flow, "/volumes/technical/finalize", {})
    assert blocked.status_code == 409 and blocked.json()["code"] == "HUMAN_ISSUES_PENDING"
    assert blocked.json()["details"]["chapter_ids"] == [chapter_id]
    listed = client.get(flow.path + "/volumes", headers=flow.headers).json()["volumes"]
    assert next(v for v in listed if v["volume_id"] == "technical")["pending_human_issues"] == 1


def test_finalized_volume_is_read_only_in_backend_and_unlock_invalidates(client):
    flow = ProjectFlow(client).ready()
    check = flow.write("/checks", {"volume": "all"})["check"]
    flow.cross_reviewed("technical")
    assert _post(flow, "/volumes/technical/finalize", {"check_id": check["id"]}).status_code == 200

    chapter_id = _technical(flow)["id"]
    lock = client.post(f"/api/chapters/{chapter_id}/lock", headers=flow.headers, json={})
    assert lock.status_code == 409 and lock.json()["code"] == "VOLUME_FINALIZED"
    recheck = _post(flow, f"/chapters/{chapter_id}/loop/recheck", {})
    assert recheck.status_code == 409 and recheck.json()["code"] == "VOLUME_FINALIZED"
    assert _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-editor"}).json()["code"] == "VOLUME_FINALIZED"

    unlocked = _post(flow, "/volumes/technical/unlock", {"reason": "澄清补遗调整巡检频次"})
    assert unlocked.status_code == 200
    state = flow.state()
    assert next(c for c in state["checks"] if c["id"] == check["id"])["status"] == "stale"
    status = client.get(flow.path + "/volumes/technical", headers=flow.headers).json()
    assert status["cross_review"]["status"] == "none"
    assert any(h["action"] == "voided_by_unlock" for h in status["cross_review"]["history"])
    assert client.post(f"/api/chapters/{chapter_id}/lock", headers=flow.headers, json={}).status_code == 200


def test_volume_owner_can_finalize_own_volume(client):
    flow = ProjectFlow(client).ready()
    flow.write("/team", {"members": [
        {"user_id": "alpha-manager", "project_role": "lead", "volumes": ["technical", "business"]},
        {"user_id": "alpha-editor", "project_role": "writer", "volumes": ["technical", "business"]},
        {"user_id": "alpha-tech", "project_role": "writer", "volumes": ["technical"]}],
        "volumes": [{"volume": "technical", "owner_id": "alpha-editor"}, {"volume": "business", "owner_id": "alpha-manager"}],
        "assembly_owner_id": "alpha-manager"}, "PUT")
    owner_reviews_self = _post(flow, "/volumes/technical/cross-review", {"reviewer_id": "alpha-editor"}, "alpha-editor")
    assert owner_reviews_self.json()["code"] == "CROSS_REVIEWER_IS_EDITOR"
    flow.cross_reviewed("technical", reviewer="alpha-tech", assigner="alpha-editor")
    done = _post(flow, "/volumes/technical/finalize", {}, "alpha-editor")
    assert done.status_code == 200, done.text
    other_volume = _post(flow, "/volumes/business/finalize", {}, "alpha-editor")
    assert other_volume.status_code == 403
