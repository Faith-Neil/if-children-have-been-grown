# 为什么有这个文件：用真实 MySQL 核对项目聚合能不能跨进程看见，以及失败时会不会留下行。
# 它解决什么问题：整份演示状态不能再当作一条记录写入；章节仍留在进程内存里。

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from icg_demo.domain import DomainError, Project
from icg_demo.main import create_app


pytestmark = pytest.mark.mysql

ROOT = Path(__file__).resolve().parents[2]
WORKER_DIR = Path(__file__).resolve().parent


def _process(action: str, payload: dict) -> dict:
    if str(WORKER_DIR) not in sys.path:
        sys.path.insert(0, str(WORKER_DIR))
    from mysql_worker import run_action
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=run_action, args=(action, payload, queue))
    process.start()
    process.join(60)
    assert process.exitcode == 0, process.exitcode
    return queue.get(timeout=5)


def _upgrade() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/bid-core/alembic.ini", "upgrade", "head"],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_created_project_is_visible_to_another_process_without_its_chapters():
    _upgrade()
    created = _process("create_project", {"name": "合成跨进程项目"})
    assert created["ok"], created
    project_id = created["body"]["id"]
    seen = _process("read_project", {"project_id": project_id})
    assert seen["ok"], seen
    match = next(item for item in seen["listed"] if item["id"] == project_id)
    assert match["name"] == "合成跨进程项目"
    assert match["company_id"] == "alpha"
    project = seen["workspace"]["project"]
    assert project["revision"] == 1
    assert project["sensitive"] is False
    assert project["tender_number"] == ""
    assert project["deadline"] == ""
    lead = next(item for item in seen["team"]["members"] if item["user_id"] == "alpha-manager")
    assert lead["project_role"] == "lead"
    assert seen["team"]["revision"] == 1
    assert seen["chapters"] == []
    assert seen["workspace"]["chapters"] == []
    seed = _process("read_project", {"project_id": "alpha-project"})
    assert seed["ok"], seed
    assert any(chapter["id"] == "alpha-tech" for chapter in seed["chapters"])
    repository = create_app().state.service.repository
    with repository.engine.connect() as connection:
        stored = set(connection.execute(text("SELECT id FROM demo_project")).scalars().all())
    assert project_id in stored
    assert "alpha-project" not in stored


def test_failed_project_write_leaves_no_row_and_no_memory():
    _upgrade()
    repository = create_app().state.service.repository
    project_id = "project-rollback-" + uuid4().hex
    before_ids = set(repository.read().projects)

    def operation(state):
        state.projects[project_id] = Project(project_id, "不应留下的合成项目", "alpha")
        state.project_teams[project_id] = {
            "members": {}, "owners": {}, "assembly_owner_id": None, "handoffs": [],
        }
        raise RuntimeError("synthetic failure")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        repository.transaction(operation)
    assert project_id not in repository.read().projects
    assert set(repository.read().projects) == before_ids
    with repository.engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM demo_project WHERE id = :id"),
            {"id": project_id},
        ).scalar()
    assert count == 0


def test_stale_project_revision_does_not_overwrite():
    _upgrade()
    created = _process("create_project", {"name": "合成版本项目"})
    assert created["ok"], created
    project_id = created["body"]["id"]
    repository = create_app().state.service.repository

    def operation(state):
        state.projects[project_id].name = "被挡住的名称"
        with repository.engine.begin() as connection:
            connection.execute(
                text("UPDATE demo_project SET revision = 99 WHERE id = :id"),
                {"id": project_id},
            )
        return "changed"

    with pytest.raises(DomainError) as caught:
        repository.transaction(operation)
    assert caught.value.code == "REVISION_CONFLICT"
    assert repository.read().projects[project_id].name == "合成版本项目"
    with repository.engine.connect() as connection:
        row = connection.execute(
            text("SELECT name, revision FROM demo_project WHERE id = :id"),
            {"id": project_id},
        ).one()
    assert row.name == "合成版本项目"
    assert row.revision == 99
