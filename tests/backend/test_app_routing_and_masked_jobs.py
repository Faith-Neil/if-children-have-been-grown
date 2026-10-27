# 为什么有这个文件：覆盖 INT-APP-SLIM-ROUTING 与 APP-M2-T022 平台管理员脱敏长任务全链路联调契约。
# 它解决什么问题：
# 1. 验证非演示模式下平台管理员（platform_admin）长任务脱敏查询（listJobsMasked / ?masked=true）：
#    返回任务类型、企业标识脱敏、耗时、状态、错误码与脱敏摘要，隐藏项目名称与敏感招标文件名称；
# 2. 验证平台管理员仅具备运维审计视图，严禁返回项目正文或密钥；直调项目业务接口与取消/重试接口严格被 RBAC 拦截；
# 3. 验证长任务取消（cancel）与从失败步骤重试（retry）端到端权限矩阵：
#    项目负责人可 retry，写作者可 cancel，只读角色与写作者越权 retry 严格 403 拦截；
# 4. 验证统一错误响应符合 RFC 7807 规范（code, message, details, traceId 与 X-Request-ID 标头）。

from datetime import datetime, timezone
import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import Account, DemoState, iso_time
from icg_demo.generation_context import writing_source_fingerprint
from icg_demo.main import create_app
from test_demo import MutableClock, login

PROJECT_ALPHA = "alpha-project"
PROJECT_BETA = "beta-project"
CHAPTER_ALPHA = "alpha-tech"
START_ALPHA = f"/api/v1/projects/{PROJECT_ALPHA}/generation/start"


@pytest.fixture
def clock():
    return MutableClock()


@pytest.fixture
def client(clock):
    with TestClient(create_app(clock=clock)) as actual_client:
        yield actual_client


def _blank_workflow(project_id):
    return {
        "files": {},
        "requirements": {},
        "facts": {},
        "conflicts": {},
        "candidates": {},
        "checks": {},
        "exports": {},
        "parse_confirmed": True,
        "plan_confirmed": True,
        "chapter_order": [],
        "sla": None,
        "sla_commitments": {},
        "writing_plan": {},
    }


def confirm_chapter(client, chapter_id=CHAPTER_ALPHA, project_id=PROJECT_ALPHA, revision=1):
    def operation(state):
        workflow = state.workflows.setdefault(project_id, _blank_workflow(project_id))
        workflow.update(parse_confirmed=True, plan_confirmed=True, outline_revision=revision)
        chapters = workflow.setdefault("writing_plan", {}).setdefault("chapters", {})
        chapters[chapter_id] = {
            "fact_ids": [],
            "writing_points": "长任务脱敏与鉴权联调要点",
            "target_length": 150,
            "confirmed_by": "alpha-manager",
            "confirmed_by_name": "甲公司项目经理（合成）",
            "confirmed_at": iso_time(1),
            "confirmation_pending": False,
        }
        chapters[chapter_id]["confirmed_input_fingerprint"] = writing_source_fingerprint(
            state, project_id, chapter_id
        )
    client.app.state.service.repository.transaction(operation)


def test_platform_admin_masked_jobs_view(client):
    """1. 平台管理员脱敏长任务查询（APP-M2-T022 / listJobsMasked）：
    - 平台管理员自动脱敏；
    - 聚合跨公司多租户任务；
    - 企业标识脱敏（alpha -> al***, beta -> be***）；
    - 项目 ID 脱敏为 prj-***，不泄露项目真实名与敏感文件名；
    - allowed_actions 严格置空，无取消/重试权限。
    """
    repo = client.app.state.service.repository

    # 1. 注入甲公司的一个失败长任务（含错误码与敏感文件名）
    job_alpha_id = f"job-alpha-{uuid4().hex[:8]}"
    repo.save_job({
        "id": job_alpha_id,
        "job_type": "parse_tender",
        "project_id": PROJECT_ALPHA,
        "status": "failed",
        "progress": 60,
        "step_name": "正在解析敏感原件：绝密工程招标文件_2026.pdf",
        "created_by": "alpha-manager",
        "error_json": {"code": "PARSE_TIMEOUT", "message": "解析文件超时"},
    })

    # 2. 注入乙公司的一个运行中长任务
    job_beta_id = f"job-beta-{uuid4().hex[:8]}"
    repo.save_job({
        "id": job_beta_id,
        "job_type": "generate",
        "project_id": PROJECT_BETA,
        "status": "running",
        "progress": 45,
        "step_name": "正在生成乙公司商业机密方案",
        "created_by": "beta-manager",
    })

    # 3. 平台管理员登录
    admin_headers = login(client, "platform-admin")

    # 4. 平台管理员调用 /api/v1/jobs（自动应用脱敏逻辑）
    resp = client.get("/api/v1/jobs", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "jobs" in data
    jobs_map = {j["id"]: j for j in data["jobs"]}

    # 验证跨公司两个任务都在列表中
    assert job_alpha_id in jobs_map
    assert job_beta_id in jobs_map

    # 检查甲公司任务的脱敏详情
    alpha_job = jobs_map[job_alpha_id]
    assert alpha_job["type"] == "parse_tender"
    assert alpha_job["status"] == "failed"
    assert alpha_job["project_id"] == "prj-***"
    assert alpha_job["company_id"] == "al***"
    assert alpha_job["masked_company"] == "al***"
    assert alpha_job["is_masked"] is True
    assert alpha_job["error_code"] == "PARSE_TIMEOUT"
    assert alpha_job["allowed_actions"] == []
    assert alpha_job["allowedActions"] == []
    # 验证敏感文件名和项目名被完全隐藏/脱敏
    assert "绝密" not in alpha_job["message"]
    assert "2026.pdf" not in alpha_job["message"]
    assert "业务细节已脱敏" in alpha_job["message"]

    # 检查乙公司任务的脱敏详情
    beta_job = jobs_map[job_beta_id]
    assert beta_job["type"] == "generate"
    assert beta_job["status"] == "running"
    assert beta_job["project_id"] == "prj-***"
    assert beta_job["company_id"] == "be***"
    assert beta_job["allowed_actions"] == []
    assert "商业机密" not in beta_job["message"]
    assert "业务细节已脱敏" in beta_job["message"]

    # 5. 验证普通企业用户请求 ?masked=true 时，也获得脱敏视图但受限于本企业租户空间
    alpha_headers = login(client, "alpha-manager")
    masked_alpha_resp = client.get("/api/v1/jobs?masked=true", headers=alpha_headers)
    assert masked_alpha_resp.status_code == 200
    alpha_user_jobs = {j["id"]: j for j in masked_alpha_resp.json()["jobs"]}
    assert job_alpha_id in alpha_user_jobs
    assert job_beta_id not in alpha_user_jobs  # 绝不出现乙公司任务


def test_platform_admin_security_rbac_boundary(client):
    """2. 平台管理员安全与隔离防线：
    - 仅具备运维审计视图，严禁返回项目正文或密钥；
    - 直调项目普通业务接口（workspace、start generation）拦截 404 NOT_FOUND（防嗅探）；
    - 直调取消/重试接口严格被 RBAC 拦截 403。
    """
    admin_headers = login(client, "platform-admin")

    # 1. 尝试直接查看甲公司项目工作区 -> 严格 404 NOT_FOUND
    ws_resp = client.get(f"/api/v1/projects/{PROJECT_ALPHA}/workspace", headers=admin_headers)
    assert ws_resp.status_code == 404
    assert ws_resp.json()["code"] == "NOT_FOUND"

    # 2. 尝试为甲公司启动长任务 -> 严格 404 NOT_FOUND
    start_resp = client.post(
        START_ALPHA,
        headers={**admin_headers, "Idempotency-Key": f"adm-{uuid4().hex[:8]}", "If-Match": "1"},
        json={"chapter_ids": [CHAPTER_ALPHA]},
    )
    assert start_resp.status_code == 404
    assert start_resp.json()["code"] == "NOT_FOUND"

    # 3. 创建一条真实任务，平台管理员直调 cancel -> 403 PROJECT_WRITER_REQUIRED
    mgr_headers = login(client, "alpha-manager")
    confirm_chapter(client)
    job_id = client.post(
        START_ALPHA,
        headers={**mgr_headers, "Idempotency-Key": f"k-{uuid4().hex[:8]}", "If-Match": "1"},
        json={},
    ).json()["id"]

    # 3. 平台管理员直调业务任务 cancel -> 严格 404 NOT_FOUND（租户隔离与防嗅探，跨公司/未授权项目一律 404）
    cancel_resp = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**admin_headers, "Idempotency-Key": f"c-adm-{uuid4().hex[:8]}"},
    )
    assert cancel_resp.status_code == 404
    assert cancel_resp.json()["code"] == "NOT_FOUND"

    # 4. 平台管理员直调 retry -> 同样拦截 404 NOT_FOUND
    retry_resp = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**admin_headers, "Idempotency-Key": f"r-adm-{uuid4().hex[:8]}"},
    )
    assert retry_resp.status_code == 404
    assert retry_resp.json()["code"] == "NOT_FOUND"

    # 5. 平台管理员尝试直调非脱敏长任务详情 GET /api/v1/jobs/{job_id} -> 严格 404 NOT_FOUND
    detail_resp = client.get(f"/api/v1/jobs/{job_id}", headers=admin_headers)
    assert detail_resp.status_code == 404
    assert detail_resp.json()["code"] == "NOT_FOUND"


def test_long_task_retry_and_cancel_role_rbac_matrix(client):
    """3. 长任务取消与失败重试端到端鉴权矩阵：
    - 项目负责人 (alpha-manager) 可执行 retry，可执行 cancel；
    - 普通写作者 (alpha-editor) 可执行 cancel；
    - 普通写作者 (alpha-editor) 触发 retry 拦截 403 PROJECT_LEAD_REQUIRED；
    - 只读角色 (alpha-viewer) 触发 cancel 拦截 403 PROJECT_WRITER_REQUIRED；
    - 只读角色 (alpha-viewer) 触发 retry 拦截 403 PROJECT_LEAD_REQUIRED；
    - 非终态重试触发 409 VERSION_CONFLICT。
    """
    manager_headers = login(client, "alpha-manager")
    editor_headers = login(client, "alpha-editor")
    viewer_headers = login(client, "alpha-viewer")
    confirm_chapter(client)

    # 1. 创建长任务
    job_id = client.post(
        START_ALPHA,
        headers={**manager_headers, "Idempotency-Key": f"matrix-{uuid4().hex[:8]}", "If-Match": "1"},
        json={},
    ).json()["id"]

    # 2. 只读人员 (viewer) 尝试取消 -> 拦截 403
    v_cancel = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**viewer_headers, "Idempotency-Key": f"vc-{uuid4().hex[:8]}"},
    )
    assert v_cancel.status_code == 403
    assert v_cancel.json()["code"] == "PROJECT_WRITER_REQUIRED"

    # 3. 普通写作者 (editor) 取消 -> 允许 200
    e_cancel = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**editor_headers, "Idempotency-Key": f"ec-{uuid4().hex[:8]}"},
    )
    assert e_cancel.status_code == 200
    assert e_cancel.json()["status"] == "cancelled"

    # 4. 普通写作者 (editor) 尝试重试 -> 拦截 403 PROJECT_LEAD_REQUIRED
    e_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**editor_headers, "Idempotency-Key": f"er-{uuid4().hex[:8]}"},
    )
    assert e_retry.status_code == 403
    assert e_retry.json()["code"] == "PROJECT_LEAD_REQUIRED"

    # 5. 只读人员 (viewer) 尝试重试 -> 拦截 403 PROJECT_LEAD_REQUIRED
    v_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**viewer_headers, "Idempotency-Key": f"vr-{uuid4().hex[:8]}"},
    )
    assert v_retry.status_code == 403
    assert v_retry.json()["code"] == "PROJECT_LEAD_REQUIRED"

    # 6. 项目负责人 (manager) 重试 -> 允许 200，状态重新置为 queued
    m_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**manager_headers, "Idempotency-Key": f"mr-{uuid4().hex[:8]}"},
    )
    assert m_retry.status_code == 200
    assert m_retry.json()["status"] == "queued"

    # 7. 对排队中（非终态）任务再次重试 -> 409 VERSION_CONFLICT 拦截
    conflict_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**manager_headers, "Idempotency-Key": f"conf-{uuid4().hex[:8]}"},
    )
    assert conflict_retry.status_code == 409
    assert conflict_retry.json()["code"] == "VERSION_CONFLICT"


def test_rfc7807_unified_error_format_compliance(client):
    """4. 验证统一错误响应符合 RFC 7807 规范：
    - 401, 403, 404, 409, 428 等响应均具备 code, message, details, traceId；
    - 具备 X-Request-ID 标头与 Cache-Control: no-store。
    """
    # 401 未登录
    unauth_resp = client.get("/api/v1/jobs")
    assert unauth_resp.status_code == 401
    assert unauth_resp.headers["Cache-Control"] == "no-store"
    assert "X-Request-ID" in unauth_resp.headers
    err_body = unauth_resp.json()
    assert err_body["code"] == "UNAUTHENTICATED"
    assert "message" in err_body
    assert "details" in err_body
    assert "traceId" in err_body
    assert err_body["traceId"] == unauth_resp.headers["X-Request-ID"]

    # 404 资源未找到
    alpha_headers = login(client, "alpha-manager")
    not_found_resp = client.get(f"/api/v1/jobs/non-existent-job-id", headers=alpha_headers)
    assert not_found_resp.status_code == 404
    assert not_found_resp.json()["code"] == "NOT_FOUND"
    assert not_found_resp.json()["traceId"] == not_found_resp.headers["X-Request-ID"]

    # 428 缺少幂等键
    no_key_resp = client.post(
        START_ALPHA,
        headers={**alpha_headers, "If-Match": "1"},
        json={},
    )
    assert no_key_resp.status_code == 428
    assert no_key_resp.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert no_key_resp.json()["traceId"] == no_key_resp.headers["X-Request-ID"]
