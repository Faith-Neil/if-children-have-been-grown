# 为什么有这个文件：用真实 MySQL 核对 Wave 11 新增的工作流状态能跨仓储实例（等同另一个进程）看见。
# 它解决什么问题：分册定稿与交叉复核、人工处理队列原先只在进程内存里，重启后会丢；这里证明它们已写入 demo_project_workflow_state。

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

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


def test_finalize_review_and_human_queue_survive_a_new_repository():
    _upgrade()
    with TestClient(create_app()) as first:
        flow = ProjectFlow(first).ready()
        technical = next(c for c in flow.state()["chapters"] if c["volume"] == "technical")
        flow.commit(technical["id"], "技术正文：每月巡检。业绩见【待补：同类业绩】。")
        flow.write(f"/chapters/{technical['id']}/loop/recheck", {})
        flow.cross_reviewed("business")
        flow.write("/volumes/business/finalize", {})
        project_path = flow.path
        project_id = flow.id
        repository = first.app.state.service.repository
        with repository.engine.connect() as connection:
            stored = connection.execute(
                text("SELECT project_id FROM demo_project_workflow_state WHERE project_id = :id"), {"id": project_id},
            ).scalars().all()
        assert stored == [project_id]

    with TestClient(create_app()) as second:
        headers = login(second)
        volumes = second.get(project_path + "/volumes", headers=headers)
        assert volumes.status_code == 200, volumes.text
        by_id = {v["volume_id"]: v for v in volumes.json()["volumes"]}
        assert by_id["business"]["is_finalized"] is True
        assert by_id["business"]["cross_review"]["status"] == "approved"
        assert by_id["technical"]["pending_human_issues"] == 1
        queue = second.get(project_path + "/human-queue", headers=headers)
        assert queue.status_code == 200, queue.text
        assert queue.json()["summary"]["pending"] == 1
