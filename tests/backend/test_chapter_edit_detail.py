# 为什么有这个文件：验证编辑台章节详情读取与段落结构接口（BE-CHAPTER-EDIT-DETAIL）。
# 它解决什么问题：
# 1. 验证 GET /api/v1/projects/{project_id}/chapters/{chapter_id} 接口契约：
#    返回 id, project_id, title, chapter_number, outline_type, is_mandatory, locked_by, lock_expires_at, revision, paragraphs；
# 2. 验证持锁/非持锁状态感知（结合 ChapterLock 与 ProjectLock）；
# 3. 验证项目涉密隔离与八角色权限（只读角色 viewer/guest 只能 GET 读取，不可写）；
# 4. 验证不存在章节 404、跨项目隔离 404 与跨公司租户隔离 404。

import json
import pytest
from fastapi.testclient import TestClient

from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import DemoState, DomainError, Principal, iso_time
from icg_demo.main import create_app
from test_reference_flow import client, login


def test_get_chapter_edit_detail_success(client: TestClient):
    """验证正常获取章节详情，返回完备的元数据与段落结构。"""
    headers = login(client, "alpha-manager")

    res = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["id"] == "alpha-tech"
    assert data["project_id"] == "alpha-project"
    assert data["title"] == "技术方案"
    assert "chapter_number" in data
    assert data["outline_type"] in ("specialized", "general", "system")
    assert isinstance(data["is_mandatory"], bool)
    assert data["locked_by"] is None
    assert data["lock_expires_at"] is None
    assert isinstance(data["revision"], int)
    assert isinstance(data["paragraphs"], list)


def test_get_chapter_edit_detail_paragraphs_and_citations(client: TestClient):
    """验证章节正文切分为带编号段落，并精准关联引用（citations）与时间戳。"""
    headers = login(client, "alpha-manager")
    app = client.app
    workflow = app.state.workflow

    # 1. 设置带多段落正文与关联引用
    def setup_data(state: DemoState):
        ch = state.chapters["alpha-tech"]
        ch.content = "第一段：本项目技术方案设计架构概述。\n\n第二段：高可用集群部署与服务承诺[证:cert-01]。"
        ch.revision = 2
        ch.versions = [
            {"revision": 1, "content": "第一段", "created_at": "2026-10-21T10:00:00Z"},
            {
                "revision": 2,
                "content": ch.content,
                "created_at": "2026-10-21T11:00:00Z",
                "citation": {
                    "id": "cert-01",
                    "name": "CMMI5级认证",
                    "tag": "[证]",
                    "cite_text": "CMMI5级认证证书",
                },
            },
        ]
        wf = state.workflows.setdefault("alpha-project", {})
        wf["requirements"] = {
            "req-01": {
                "id": "req-01",
                "chapter_id": "alpha-tech",
                "clause": "★投标人须具备CMMI5级认证",
                "volume": "technical",
                "mandatory": True,
                "evidence_ids": ["cert-01"],
            }
        }
        state.library["cert-01"] = {
            "id": "cert-01",
            "name": "CMMI5级认证",
            "company_id": "company-alpha",
            "status": "confirmed",
            "revision": 1,
        }

    workflow.repository.transaction(setup_data)

    res = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    # 验证星号硬性门禁标记识别
    assert data["is_mandatory"] is True
    assert data["revision"] == 2

    # 验证段落切分与引用
    paragraphs = data["paragraphs"]
    assert len(paragraphs) == 2

    p1 = paragraphs[0]
    assert p1["order"] == 1
    assert "第一段" in p1["text"]
    assert p1["id"] == "alpha-tech-p1"
    assert p1["created_at"] == "2026-10-21T10:00:00Z"
    assert p1["updated_at"] == "2026-10-21T11:00:00Z"

    p2 = paragraphs[1]
    assert p2["order"] == 2
    assert "第二段" in p2["text"]
    assert p2["id"] == "alpha-tech-p2"
    assert len(p2["citations"]) >= 1
    assert any(c["id"] == "cert-01" for c in p2["citations"])


def test_unauthenticated_returns_401(client: TestClient):
    """未登录或 Token 缺失时拦截 401 UNAUTHENTICATED。"""
    res = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech")
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert "traceId" in body


def test_non_existent_chapter_and_project_returns_404(client: TestClient):
    """章节不存在或项目不存在时返回 404 NOT_FOUND。"""
    headers = login(client, "alpha-manager")

    # 章节不存在
    res_chap = client.get("/api/v1/projects/alpha-project/chapters/non-existent-chapter", headers=headers)
    assert res_chap.status_code == 404
    assert res_chap.json()["code"] == "NOT_FOUND"

    # 项目不存在
    res_proj = client.get("/api/v1/projects/non-existent-project/chapters/alpha-tech", headers=headers)
    assert res_proj.status_code == 404
    assert res_proj.json()["code"] == "NOT_FOUND"


def test_cross_project_and_company_isolation(client: TestClient):
    """跨项目访问或跨公司越权访问严格隔离拦截 404。"""
    alpha_headers = login(client, "alpha-manager")

    # 1. 章节属于 beta-project，企图通过 alpha-project 路径调阅
    res_cross_proj = client.get("/api/v1/projects/alpha-project/chapters/beta-tech", headers=alpha_headers)
    assert res_cross_proj.status_code == 404
    assert res_cross_proj.json()["code"] == "NOT_FOUND"

    # 2. 公司 Alpha 账号调阅公司 Beta 的项目
    res_cross_comp = client.get("/api/v1/projects/beta-project/chapters/beta-tech", headers=alpha_headers)
    assert res_cross_comp.status_code == 404
    assert res_cross_comp.json()["code"] == "NOT_FOUND"


def test_lock_status_sensing_unlocked_and_locked(client: TestClient):
    """验证持锁人元数据正确感知：未锁 -> 持锁展示 owner_id 与 expires_at -> 释放后置空。"""
    headers = login(client, "alpha-editor")

    # 1. 初始状态：未持锁
    res1 = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["locked_by"] is None
    assert res1.json()["lock_expires_at"] is None

    # 2. 获取编辑锁
    lock_res = client.post("/api/v1/chapters/alpha-tech/lock", headers=headers, json={"takeover_reason": None})
    assert lock_res.status_code == 200, lock_res.text
    lease_data = lock_res.json()
    lease_token = lease_data["lease_token"]

    # 3. 持锁状态下：正确展示 locked_by 与 lock_expires_at
    res2 = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res2.status_code == 200
    detail2 = res2.json()
    assert detail2["locked_by"] == "alpha-editor"
    assert detail2["lock_expires_at"] is not None

    # 4. 释放编辑锁
    rel_res = client.post("/api/v1/chapters/alpha-tech/lock/release", headers=headers, json={"lease_token": lease_token})
    assert rel_res.status_code == 200

    # 5. 释放后重新读取：锁信息恢复为 None
    res3 = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res3.status_code == 200
    assert res3.json()["locked_by"] is None
    assert res3.json()["lock_expires_at"] is None


def test_eight_roles_read_only_viewer_can_get_but_cannot_write(client: TestClient):
    """验证只读角色（viewer）只能 GET 读取章节详情，不可执行写操作（如加锁）。"""
    viewer_headers = login(client, "alpha-viewer")

    # 1. 只读角色正常调阅详情 (GET 200 OK)
    res = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=viewer_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id"] == "alpha-tech"
    assert data["can_edit"] is False
    assert data["permissions"]["edit"] is False

    # 2. 只读角色试图取得编辑锁 -> 403 FORBIDDEN 拦截
    lock_attempt = client.post("/api/v1/chapters/alpha-tech/lock", headers=viewer_headers, json={"takeover_reason": None})
    assert lock_attempt.status_code == 403
    assert lock_attempt.json()["code"] == "FORBIDDEN"


def test_stored_structured_paragraphs_takes_precedence(client: TestClient):
    """验证若存储中已持久化结构化段落，优先使用存储的段落数据。"""
    headers = login(client, "alpha-manager")
    workflow = client.app.state.workflow

    custom_paras = [
        {
            "id": "p-custom-101",
            "order": 1,
            "text": "存储的自定义第一段落",
            "citations": [{"id": "c-1", "name": "引用1"}],
            "created_at": "2026-10-21T08:00:00Z",
            "updated_at": "2026-10-21T08:30:00Z",
        }
    ]

    def set_custom(state: DemoState):
        wf = state.workflows.setdefault("alpha-project", {})
        cp = wf.setdefault("chapter_paragraphs", {})
        cp["alpha-tech"] = custom_paras

    workflow.repository.transaction(set_custom)

    res = client.get("/api/v1/projects/alpha-project/chapters/alpha-tech", headers=headers)
    assert res.status_code == 200
    paras = res.json()["paragraphs"]
    assert len(paras) == 1
    assert paras[0]["id"] == "p-custom-101"
    assert paras[0]["text"] == "存储的自定义第一段落"
    assert paras[0]["citations"][0]["id"] == "c-1"
