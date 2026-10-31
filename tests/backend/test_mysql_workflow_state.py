# 为什么有这个文件：用真实 MySQL 核对业务状态跨仓储实例（等同另一个进程或重启后）完整可见（ISSUE-040、ISSUE-041）。
# 它解决什么问题：项目工作流（文件、条款、事实、检查、导出、分册定稿、人工处理队列）、新建账号、资料库、
# 企业设置、字典与方案片段原先只在进程内存里；这里证明它们已写入 demo_state_entry，且并发写同一条目会被乐观锁拦下。

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from icg_demo.domain import DomainError
from icg_demo.main import create_app
from test_reference_flow import ProjectFlow, login

pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]


def _upgrade() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", "upgrade", "head"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_project_workflow_and_main_path_survive_a_new_repository():
    _upgrade()
    with TestClient(create_app()) as first:
        flow = ProjectFlow(first).ready()
        technical = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
        flow.commit(technical["id"], "技术正文：每月巡检。业绩见【待补：同类业绩】。")
        flow.write(f"/chapters/{technical['id']}/loop/recheck", {})
        flow.cross_reviewed("business")
        flow.write("/volumes/business/finalize", {})
        check = flow.write("/checks", {"volume": "business"})["check"]
        before = flow.state()
        repository = first.app.state.service.repository
        with repository.engine.connect() as connection:
            scopes = set(connection.execute(
                text("SELECT scope FROM demo_state_entry WHERE scope = 'workflow' AND entry_id = :id"), {"id": flow.id},
            ).scalars().all())
        assert scopes == {"workflow"}

    with TestClient(create_app()) as second:
        headers = login(second)
        after = second.get(f"{flow.path}/workspace", headers=headers).json()
        assert after["revision"] == before["revision"]
        assert after["parse_confirmed"] is True
        assert [r["id"] for r in after["requirements"]] == [r["id"] for r in before["requirements"]]
        assert [f["id"] for f in after["files"]] == [f["id"] for f in before["files"]]
        assert any(c["id"] == check["id"] for c in after["checks"])
        assert after["human_queue_pending"] == 1
        volumes = {v["volume_id"]: v for v in second.get(flow.path + "/volumes", headers=headers).json()["volumes"]}
        assert volumes["business"]["is_finalized"] is True
        assert volumes["business"]["cross_review"]["status"] == "approved"
        original = second.get(f"{flow.path}/files/{before['files'][0]['id']}", headers=headers)
        assert original.status_code == 200, original.text


def test_accounts_library_and_service_stores_survive_a_new_repository():
    _upgrade()
    suffix = uuid4().hex[:8]
    with TestClient(create_app()) as first:
        flow = ProjectFlow(first)
        item = flow.library(name=f"合成持久化资质-{suffix}")
        admin = login(first, "alpha-company-admin")
        users = first.get("/api/v1/users", headers=admin)
        assert users.status_code == 200, users.text
        created = first.post("/api/v1/users", headers={**admin, "Idempotency-Key": str(uuid4())}, json={
            "username": f"persist-{suffix}", "name": "持久化编写人", "company_id": "alpha", "role": "bid_writer",
            "password": "Persist#2026x"})
        assert created.status_code in (200, 201), created.text
        settings = first.patch("/api/v1/companies/alpha/settings", headers=admin, json={"dup_min_chars": 12})
        assert settings.status_code == 200, settings.text

    with TestClient(create_app()) as second:
        manager = login(second)
        library = second.get("/api/v1/library", headers=manager).json()
        assert any(entry["id"] == item["id"] for entry in library["items"])
        admin = login(second, "alpha-company-admin")
        listed = second.get("/api/v1/users", headers=admin).json()
        assert any(u["id"] == f"persist-{suffix}" for u in listed["items"]), listed
        assert second.get("/api/v1/companies/alpha/settings", headers=admin).json()["dup_min_chars"] == 12


def test_concurrent_write_to_same_entry_is_rejected():
    _upgrade()
    with TestClient(create_app()) as first, TestClient(create_app()) as second:
        flow = ProjectFlow(first)
        repo_a = first.app.state.service.repository
        repo_b = second.app.state.service.repository
        repo_a.read(); repo_b.read()
        repo_b.transaction(lambda state: state.workflows.setdefault(flow.id, {}).update({"probe": "b"}))

        stale = {}

        def write_a(state):
            stale["seen"] = state.workflows.get(flow.id, {}).get("probe")
            state.workflows.setdefault(flow.id, {})["probe"] = "a"

        repo_a.transaction(write_a)
        assert stale["seen"] == "b"  # 每个事务开始时都读到了另一实例的最新写入
        assert repo_b.read().workflows[flow.id]["probe"] == "a"

        # 模拟“读到旧版本后另一实例抢先写入”：直接把库里 rev 往前推，本实例的写入必须失败
        with repo_a.engine.begin() as connection:
            connection.execute(text("UPDATE demo_state_entry SET rev = rev + 5 WHERE scope='workflow' AND entry_id=:id"),
                               {"id": flow.id})
        store = repo_a._entries
        key = ("workflow", flow.id)
        rev, body = store.cache[key]

        def forced(state):
            state.workflows[flow.id]["probe"] = "c"
            store.cache[key] = (rev, body)  # 让写入沿用旧 rev

        original_load = store.load
        store.load = lambda connection, state, remember: []
        try:
            with pytest.raises(DomainError) as conflict:
                repo_a.transaction(forced)
        finally:
            store.load = original_load
        assert conflict.value.code == "VERSION_CONFLICT"
