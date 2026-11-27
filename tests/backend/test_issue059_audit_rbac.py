# 为什么有这个文件：登记 ISSUE-059(b) 审计日志越权（CWE-862）修复的复现与回归。
# 它解决什么问题：审计日志含登录失败原因、锁定与敏感操作痕迹；
# 普通成员一律 403，公司管理员仅本公司且跨公司查询参数拒绝，平台管理员可全局/指定公司。

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg_demo.main import create_app
from test_demo import login


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_member_forbidden_from_audit_logs(client):
    """普通成员（member）一律 403：修复前仅被强制限定本公司，仍能读本公司审计日志。"""
    for account in ("alpha-editor", "alpha-manager", "alpha-viewer", "beta-editor"):
        headers = login(client, account)
        res = client.get("/api/v1/audit-logs", headers=headers)
        assert res.status_code == 403, f"{account} 应被拒绝: {res.status_code}"
        assert res.json()["code"] == "FORBIDDEN"


def test_company_admin_reads_own_company_audit_logs(client):
    headers = login(client, "alpha-company-admin")
    res = client.get("/api/v1/audit-logs", headers=headers)
    assert res.status_code == 200, res.text
    assert all(row.get("company_id") in (None, "alpha") for row in res.json()["items"])

    # 显式指定本公司也允许
    own = client.get("/api/v1/audit-logs?company_id=alpha", headers=headers)
    assert own.status_code == 200, own.text


def test_company_admin_cross_company_param_rejected(client):
    headers = login(client, "alpha-company-admin")
    cross = client.get("/api/v1/audit-logs?company_id=beta", headers=headers)
    assert cross.status_code == 403
    assert cross.json()["code"] == "FORBIDDEN"


def test_platform_admin_reads_global_and_specific_company(client):
    platform = login(client, "admin")
    global_rows = client.get("/api/v1/audit-logs", headers=platform)
    assert global_rows.status_code == 200, global_rows.text
    assert global_rows.json()["total"] >= 1

    scoped = client.get("/api/v1/audit-logs?company_id=alpha", headers=platform)
    assert scoped.status_code == 200, scoped.text
    assert all(row.get("company_id") in (None, "alpha") for row in scoped.json()["items"])


def test_platform_admin_role_account_global_access(client):
    """platform_admin 角色账号（非 admin 超级账号）也可全局调阅。"""
    headers = login(client, "platform-admin")
    res = client.get("/api/v1/audit-logs", headers=headers)
    assert res.status_code == 200, res.text
