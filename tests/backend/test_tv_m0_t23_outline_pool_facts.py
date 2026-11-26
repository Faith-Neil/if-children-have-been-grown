# 为什么有这个文件：验证 TV-M0-T23 目录编辑“未挂载池（Unassigned Pool）”防丢、确认 409 门禁、自动归入兜底节与全局项目事实表闭环。
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_technical_sources import _docx


def _login(client: TestClient, username: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": "X_2026"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_parsed_project(client: TestClient, headers: dict[str, str]) -> tuple[str, dict]:
    created = client.post(
        "/api/v1/projects",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"name": "目录防丢与事实表测试项目", "volume_mode": "technical_only"},
    )
    assert created.status_code in (200, 201), created.text
    data = created.json()
    pid = (data.get("project") or data)["id"]
    ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=headers).json()

    tender_text = (
        "采购人：星河市财政局\n"
        "项目名称：核心业务数据库维保服务\n"
        "服务期：2年\n"
        "服务方案中应包含数据库的日常巡检、故障应急响应、备份恢复演练等。\n"
    )
    docx_bytes = _docx(tender_text)
    up = client.post(
        f"/api/v1/projects/{pid}/files",
        headers={**headers, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
        json={"filename": "招标.docx", "content_base64": __import__("base64").b64encode(docx_bytes).decode()},
    )
    assert up.status_code in (200, 201), up.text
    ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{pid}/parse",
        headers={**headers, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=headers).json()
    return pid, ws


def test_deleting_chapter_moves_points_to_unassigned_pool_and_blocks_silent_confirm():
    with TestClient(create_app()) as client:
        mgr = _login(client, "alpha-manager")
        pid, ws = _create_parsed_project(client, mgr)
        outline = ws["technical_outline"]
        chapter_id = outline["chapter_id"]
        headings = outline["headings"]
        leaves = [h for h in headings if h.get("requirement_ids") or h.get("requirement_id")]
        assert len(leaves) >= 2

        dropped = leaves[-1]
        dropped_rids = dropped.get("requirement_ids") or [dropped["requirement_id"]]
        kept_headings = [h for h in headings if h is not dropped]

        saved = client.post(
            f"/api/v1/projects/{pid}/plan",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "scope": "technical",
                "chapters": [{"id": chapter_id, "title": outline["title"], "volume": "technical", "fact_ids": [], "writing_points": ""}],
                "outline_title": outline["title"],
                "outline_headings": [
                    {
                        "level": h["level"],
                        "title": h["title"],
                        "requirement_id": h.get("requirement_id"),
                        "task_id": h.get("task_id"),
                        "requirement_ids": h.get("requirement_ids") or ([] if not h.get("requirement_id") else [h["requirement_id"]]),
                    }
                    for h in kept_headings
                ],
                "confirm_outline": False,
            },
        )
        assert saved.status_code == 200, saved.text
        ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=mgr).json()

        pool = ws["technical_outline"]["unassigned_requirements"]
        pool_ids = [item["requirement_id"] for item in pool]
        for rid in dropped_rids:
            assert rid in pool_ids
        # 被删章节的孤儿任务必须同步移除，不在覆盖视图残留幽灵行
        active_task_rids = {rid for t in ws["response_tasks"] for rid in t["requirement_ids"]}
        for rid in dropped_rids:
            assert rid not in active_task_rids

        # 未处理未挂载池时直接确认目录 -> 409 拦截并附带未挂载列表
        blocked = client.post(
            f"/api/v1/projects/{pid}/plan",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "scope": "technical",
                "chapters": [{"id": chapter_id, "title": outline["title"], "volume": "technical", "fact_ids": [], "writing_points": ""}],
                "confirm_outline": True,
            },
        )
        assert blocked.status_code == 409
        body = blocked.json()
        assert body["code"] == "MATRIX_MAPPING_MISSING"
        assert len(body["details"]["unassigned_requirements"]) >= 1

        # 一键自动归入「其他服务承诺」并确认 -> 200，未挂载池清零
        auto_ok = client.post(
            f"/api/v1/projects/{pid}/plan",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "scope": "technical",
                "chapters": [{"id": chapter_id, "title": outline["title"], "volume": "technical", "fact_ids": [], "writing_points": ""}],
                "confirm_outline": True,
                "auto_mount_unassigned": True,
            },
        )
        assert auto_ok.status_code == 200, auto_ok.text
        ws_after = client.get(f"/api/v1/projects/{pid}/workspace", headers=mgr).json()
        assert ws_after["plan_confirmed"] is True
        assert ws_after["technical_outline"]["unassigned_requirements"] == []
        assert any(h["title"] == "其他服务承诺" for h in ws_after["technical_outline"]["headings"])


def test_global_fact_sheet_update_freeze_and_readonly_403():
    with TestClient(create_app()) as client:
        mgr = _login(client, "alpha-manager")
        pid, ws = _create_parsed_project(client, mgr)

        # 加入只读成员
        team = ws["team"]
        members = [
            {"user_id": m["user_id"], "project_role": m["project_role"], "volumes": m.get("volumes") or ["technical"]}
            for m in team["members"]
        ] + [{"user_id": "alpha-viewer", "project_role": "readonly", "volumes": ["technical"]}]
        add_ro = client.put(
            f"/api/v1/projects/{pid}/team",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "members": members,
                "volumes": [{"volume": v["volume"], "owner_id": v.get("owner_id")} for v in team["volumes"]],
                "assembly_owner_id": team.get("assembly_owner_id"),
                "reason": "添加只读验收成员",
            },
        )
        assert add_ro.status_code == 200, add_ro.text
        ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=mgr).json()

        # 只读成员修改全局事实表 -> 403
        viewer = _login(client, "alpha-viewer")
        ro_resp = client.put(
            f"/api/v1/projects/{pid}/global-fact-sheet",
            headers={**viewer, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={"warranty_period": "3年", "target_models": ["Model-X800"]},
        )
        assert ro_resp.status_code == 403

        # 项目负责人更新全局事实表并确认目录冻结快照
        upd = client.put(
            f"/api/v1/projects/{pid}/global-fact-sheet",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "client_name": "星河市财政局",
                "service_period": "2年",
                "warranty_period": "3年免费质保",
                "sla_response": "7×24小时，15分钟响应，2小时到场",
                "project_manager": "张工",
                "target_models": ["OceanBase-X800", "OceanBase-S200"],
            },
        )
        assert upd.status_code == 200, upd.text
        ws = client.get(f"/api/v1/projects/{pid}/workspace", headers=mgr).json()
        sheet = ws["global_fact_sheet"]
        assert sheet["warranty_period"] == "3年免费质保"
        assert sheet["target_models"] == ["OceanBase-X800", "OceanBase-S200"]
        assert sheet["frozen_at"] is None

        chapter_id = ws["technical_outline"]["chapter_id"]
        confirmed = client.post(
            f"/api/v1/projects/{pid}/plan",
            headers={**mgr, "If-Match": str(ws["revision"]), "Idempotency-Key": str(uuid4())},
            json={
                "scope": "technical",
                "chapters": [{"id": chapter_id, "title": "服务方案", "volume": "technical", "fact_ids": [], "writing_points": ""}],
                "confirm_outline": True,
            },
        )
        assert confirmed.status_code == 200, confirmed.text
        ws_frozen = client.get(f"/api/v1/projects/{pid}/workspace", headers=mgr).json()
        assert ws_frozen["global_fact_sheet"]["frozen_at"] is not None
