# 为什么有这个文件：验证 BE-M0-T19 对齐数据字典 bid_project 的 demo_project 结构与接口兼容性。
# 它解决什么问题：确保 Project 领域模型、MySQL 迁移脚本、数据表快照与 v1/旧版接口在保留历史数据的前提下，
# 统一支持 tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived 及 A 组系统审计字段。

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import DemoState, DomainError, Project
from icg_demo.database import _project_snapshot, _save_projects
from icg_demo.main import create_app


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_VERSION_0011 = ROOT / "backend" / "bid-core" / "alembic" / "versions" / "0011_bid_project_alignment.py"


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def login(client, account="alpha-manager"):
    result = client.post("/api/demo/login", json={"account_id": account})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_project_domain_model_defaults_and_properties():
    # 1. 验证向后兼容初始化（只提供 id, name, company_id）
    project = Project(id="p-001", name="测试对齐项目", company_id="alpha")
    assert project.id == "p-001"
    assert project.name == "测试对齐项目"
    assert project.company_id == "alpha"
    assert project.revision == 1
    assert project.tender_number == ""
    assert project.deadline == ""
    assert project.sensitive is False
    assert project.is_sensitive is False

    # 2. 验证新增对齐字段默认值
    assert project.tender_type == "comprehensive"
    assert project.budget_amount_cents is None or project.budget_amount_cents == 0
    assert project.deadline_at is None
    assert project.security_level == "internal"
    assert project.industry == "it"
    assert project.is_archived is False
    assert project.created_by in ("", None)
    assert project.created_at is None
    assert project.updated_by in ("", None)
    assert project.updated_at is None
    assert project.record_version == 1
    assert project.is_deleted is False

    # 3. 验证 is_sensitive 别名属性联动
    project.sensitive = True
    assert project.is_sensitive is True


def test_project_snapshot_and_database_persistence():
    state = DemoState()
    proj = Project(
        id="p-snapshot-01",
        name="快照测试",
        company_id="alpha",
        revision=2,
        tender_number="TB-999",
        deadline="2026-12-31",
        sensitive=True,
        tender_type="technical",
        budget_amount_cents=50000000,
        deadline_at=1798732800.0,
        security_level="confidential",
        industry="energy",
        is_archived=False,
        created_by="alpha-manager",
        created_at=1760000000.0,
        updated_by="alpha-manager",
        updated_at=1760001000.0,
        record_version=2,
        is_deleted=False,
    )
    state.projects[proj.id] = proj

    # 验证快照元组包含全部 18 列
    snapshot = _project_snapshot(state)
    assert proj.id in snapshot
    snap_tuple = snapshot[proj.id]
    assert len(snap_tuple) == 18
    assert snap_tuple[0] == "快照测试"
    assert snap_tuple[1] == "alpha"
    assert snap_tuple[2] == 2
    assert snap_tuple[3] == "TB-999"
    assert snap_tuple[4] == "2026-12-31"
    assert snap_tuple[5] is True
    assert snap_tuple[6] == "technical"
    assert snap_tuple[7] == 50000000
    assert snap_tuple[8] == 1798732800.0
    assert snap_tuple[9] == "confidential"
    assert snap_tuple[10] == "energy"
    assert snap_tuple[11] is False
    assert snap_tuple[12] == "alpha-manager"
    assert snap_tuple[13] == 1760000000.0
    assert snap_tuple[14] == "alpha-manager"
    assert snap_tuple[15] == 1760001000.0
    assert snap_tuple[16] == 2
    assert snap_tuple[17] is False

    # 验证 _save_projects 对 18 元组与旧 6 元组的兼容解构
    mock_connection = MagicMock()
    mock_connection.execute.return_value.rowcount = 1

    # 新版 18 元组保存
    _save_projects(
        connection=mock_connection,
        before_projects={},
        after_projects=snapshot,
        before_teams={},
        after_teams={},
        loaded_project_ids=set(),
    )
    assert mock_connection.execute.called

    # 旧版 6 元组保存（兼容旧结构调用）
    mock_connection.reset_mock()
    legacy_snapshot = {
        "legacy-01": ("旧项目", "alpha", 1, "TB-001", "2026-10-01", False)
    }
    _save_projects(
        connection=mock_connection,
        before_projects={},
        after_projects=legacy_snapshot,
        before_teams={},
        after_teams={},
        loaded_project_ids=set(),
    )
    assert mock_connection.execute.called


def test_alembic_migration_0011_file_structure():
    assert ALEMBIC_VERSION_0011.exists(), f"Migration file missing: {ALEMBIC_VERSION_0011}"
    spec = spec_from_file_location("migration_0011", str(ALEMBIC_VERSION_0011))
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision.startswith("0011")
    assert migration.down_revision.startswith("0010")
    assert hasattr(migration, "upgrade")
    assert hasattr(migration, "downgrade")


def test_api_v1_and_legacy_projects_endpoints(client):
    headers = login(client, "alpha-manager")

    # 1. POST /api/projects 创建新项目
    create_res = client.post("/api/projects", headers=headers, json={"name": "新对齐招标项目"})
    assert create_res.status_code == 200, create_res.text
    created = create_res.json()
    project_id = created["id"]
    assert created["name"] == "新对齐招标项目"
    assert created["company_id"] == "alpha"
    assert created["tender_type"] == "comprehensive"
    assert created["budget_amount_cents"] is None or created["budget_amount_cents"] == 0
    assert created["security_level"] == "internal"
    assert created["industry"] == "it"
    assert created["is_archived"] is False
    assert created["created_by"] == "alpha-manager"
    assert created["record_version"] == 1
    assert created["is_deleted"] is False

    # 2. GET /api/v1/projects 列表查询包含新字段
    v1_list_res = client.get("/api/v1/projects", headers=headers)
    assert v1_list_res.status_code == 200, v1_list_res.text
    v1_projects = v1_list_res.json()["projects"]
    match = next(p for p in v1_projects if p["id"] == project_id)
    assert match["name"] == "新对齐招标项目"
    assert match["tender_type"] == "comprehensive"
    assert match["security_level"] == "internal"
    assert match["industry"] == "it"

    # 3. GET /api/v1/projects/{project_id} 详情查询
    v1_detail_res = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert v1_detail_res.status_code == 200, v1_detail_res.text
    v1_detail = v1_detail_res.json()
    assert v1_detail["id"] == project_id
    assert v1_detail["tender_type"] == "comprehensive"
    assert v1_detail["budget_amount_cents"] is None or v1_detail["budget_amount_cents"] == 0

    # 4. GET /api/projects/{project_id} 兼容查询
    legacy_detail_res = client.get(f"/api/projects/{project_id}", headers=headers)
    assert legacy_detail_res.status_code == 200, legacy_detail_res.text
    legacy_detail = legacy_detail_res.json()
    assert legacy_detail["id"] == project_id
    assert legacy_detail["tender_type"] == "comprehensive"

    # 5. GET /api/projects 兼容列表查询
    legacy_list_res = client.get("/api/projects", headers=headers)
    assert legacy_list_res.status_code == 200, legacy_list_res.text
    legacy_projects = legacy_list_res.json()["projects"]
    assert any(p["id"] == project_id for p in legacy_projects)


def test_project_company_isolation_and_deleted_filtering(client):
    alpha_headers = login(client, "alpha-manager")
    create_res = client.post("/api/projects", headers=alpha_headers, json={"name": "Alpha 隔离项目"})
    assert create_res.status_code == 200
    project_id = create_res.json()["id"]

    # Beta 公司用户尝试访问
    beta_headers = login(client, "beta-manager")

    # 1. GET /api/v1/projects 中不应包含 Alpha 公司的项目
    beta_list_res = client.get("/api/v1/projects", headers=beta_headers)
    assert beta_list_res.status_code == 200
    beta_projects = beta_list_res.json()["projects"]
    assert all(p["id"] != project_id for p in beta_projects)

    # 2. GET /api/v1/projects/{id} 跨公司访问应返回 404
    cross_v1_res = client.get(f"/api/v1/projects/{project_id}", headers=beta_headers)
    assert cross_v1_res.status_code == 404, cross_v1_res.text

    # 3. GET /api/projects/{id} 跨公司访问应返回 404
    cross_legacy_res = client.get(f"/api/projects/{project_id}", headers=beta_headers)
    assert cross_legacy_res.status_code == 404, cross_legacy_res.text

    # 4. 软删除测试：is_deleted=True 的项目应被排除并返回 404
    app = client.app
    service = app.state.service

    def mark_deleted(state):
        state.projects[project_id].is_deleted = True

    service.repository.transaction(mark_deleted)

    # 确认列表与详情均无法访问软删除项目
    alpha_list_res = client.get("/api/v1/projects", headers=alpha_headers)
    assert all(p["id"] != project_id for p in alpha_list_res.json()["projects"])

    deleted_detail_res = client.get(f"/api/v1/projects/{project_id}", headers=alpha_headers)
    assert deleted_detail_res.status_code == 404
