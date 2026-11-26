# 为什么有这个文件：真机验收发现模型配置密钥解密失败（SECRET_KEY_UNAVAILABLE）时，
# resolve_model_provider 的异常被 except Exception 静默吞掉，解析/目录/生成全部降级为规则与模板，
# 但工作区毫无提示——违反“诚实记录降级”红线。
# 它解决什么问题：锁定新语义——配置类失败必须显式落盘 technical_model_error；
# 安全类 DomainError（敏感项目模型硬约束）必须继续向上抛，不得吞掉。
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from icg.domain.domain import DomainError
from icg_demo.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


def _parse(client, headers, monkeypatch, side_effect):
    from uuid import uuid4

    from test_technical_sources import _docx, _project, _upload

    service = client.app.state.service

    def broken(*args, **kwargs):
        raise side_effect

    monkeypatch.setattr(service, "resolve_model_provider", broken)
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx("服务方案中应包含数据库巡检。"))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    return client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    ), project_id


def test_config_failure_is_surfaced_not_swallowed(client, monkeypatch):
    from test_reference_flow import login

    headers = login(client)
    resp, project_id = _parse(client, headers, monkeypatch, ValueError("InvalidToken: 密钥解密失败"))
    # 配置类失败不阻断解析（规则兜底仍有业务价值），但必须显式落盘原因
    assert resp.status_code == 200, resp.text
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert "technical_model_error" in ws
    assert "InvalidToken" in ws["technical_model_error"]
    # 诚实降级：目录来源必须是 rule 而不是伪装成模型编排
    assert ws.get("outline_source") in ("", "rule")


def test_healthy_resolution_clears_error(client, monkeypatch):
    from test_reference_flow import login

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            return '{"who":"","what":"","period":"","sla":"","format_order":[],"items":[]}'

    headers = login(client)
    service = client.app.state.service
    monkeypatch.setattr(service, "resolve_model_provider", lambda *a, **k: Local())

    from uuid import uuid4

    from test_technical_sources import _docx, _project, _upload

    project_id, revision = _project(client, headers)
    _upload(client, headers, project_id, revision, "招标.docx", content=_docx("服务方案中应包含数据库巡检。"))
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    resp = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert resp.status_code == 200, resp.text
    ws = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    assert ws.get("technical_model_error") in (None, "")


def test_sensitive_security_domain_error_propagates(client, monkeypatch):
    from test_reference_flow import login

    headers = login(client)
    resp, _pid = _parse(
        client, headers, monkeypatch,
        DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型。"),
    )
    # 安全类硬错误不得被吞：必须按其语义拒绝，而不是静默降级继续解析
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"
