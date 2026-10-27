# 为什么有这个文件：覆盖前后端异步任务中心联调契约（INT-TASK-CENTER-GLUE / APP-M2-T021）。
# 它解决什么问题：
# 1. 验证非演示模式（VITE_DEMO=0）下长任务创建、demo_job 持久化写入、状态置为 pending/running；
# 2. 验证 SSE 流式推流 /api/v1/jobs/{id}/events、Last-Event-ID 断点续传与平滑轮询降级 GET /api/v1/jobs/{id}；
# 3. 验证 allowedActions 状态流转与角色权限门禁（进行中 cancel、失败/取消 retry，只读与非负责人 403 拦截，终态冲突 409 拦截）；
# 4. 验证多租户企业空间强隔离（跨公司访问长任务严格 404，任务列表按公司隔离）。

import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from icg_demo.domain import iso_time
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
            "writing_points": "长任务联调合成要点",
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


def parse_sse_events(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        item, data_lines = {}, []
        for line in block.splitlines():
            if line.startswith("id: "):
                item["id"] = line[4:]
            elif line.startswith("event: "):
                item["event"] = line[7:]
            elif line.startswith("data: "):
                data_lines.append(line[6:])
        if data_lines:
            item["data"] = json.loads("".join(data_lines))
        events.append(item)
    return events


def test_long_task_creation_and_demo_job_persistence(client):
    """1. 验证长任务创建：分配 job_id，写入 demo_job 表，状态 pending/queued，返回 202 与 Location。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-job-{uuid4().hex[:8]}"
    resp = client.post(
        START_ALPHA,
        headers={**headers, "Idempotency-Key": key, "If-Match": "1"},
        json={"chapter_ids": [CHAPTER_ALPHA]},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    job_id = body["id"]

    assert body["status"] == "queued"
    assert body["recoverable"] is True
    assert body["progress"] == 0
    assert body["error"] is None
    assert body["allowed_actions"] == ["cancel"]
    assert body["allowedActions"] == ["cancel"]
    assert resp.headers["Location"] == f"/api/v1/jobs/{job_id}"

    # 验证 demo_job 仓储持久化记录已创建
    repo = client.app.state.service.repository
    job_record = repo.read_job(job_id)
    assert job_record is not None
    assert job_record["id"] == job_id
    assert job_record["project_id"] == PROJECT_ALPHA
    assert job_record["status"] in ("pending", "queued")
    assert job_record["progress"] == 0


def test_job_sse_events_streaming_and_resume(client):
    """2. 验证 SSE 实时事件流与 Last-Event-ID 断点续传。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-sse-{uuid4().hex[:8]}"
    accepted = client.post(
        START_ALPHA,
        headers={**headers, "Idempotency-Key": key, "If-Match": "1"},
        json={},
    ).json()
    job_id = accepted["id"]

    # 客户端建立 SSE 推流连接
    stream_resp = client.get(f"/api/v1/jobs/{job_id}/events", headers=headers)
    assert stream_resp.status_code == 200
    assert stream_resp.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(stream_resp.text)
    assert len(events) >= 4
    event_types = [e["event"] for e in events]
    assert "job.status_changed" in event_types
    assert "job.progress" in event_types
    assert "job.completed" in event_types

    # 验证 Last-Event-ID 断点续传机制：只推送更大 seq 的事件
    mid_event_id = f"{job_id}:2"
    resumed = client.get(
        f"/api/v1/jobs/{job_id}/events",
        headers={**headers, "Last-Event-ID": mid_event_id},
    )
    assert resumed.status_code == 200
    resumed_events = parse_sse_events(resumed.text)
    for evt in resumed_events:
        seq = int(evt["id"].split(":")[-1])
        assert seq > 2


def test_job_polling_and_terminal_completion(client):
    """3. 验证降级 HTTP 轮询 GET /api/v1/jobs/{job_id} 与完成终态、仓储同步。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-poll-{uuid4().hex[:8]}"
    start_body = client.post(
        START_ALPHA,
        headers={**headers, "Idempotency-Key": key, "If-Match": "1"},
        json={},
    ).json()
    job_id = start_body["id"]

    # 执行轮询查询
    poll_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert poll_resp.status_code == 200
    job = poll_resp.json()
    assert job["id"] == job_id
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["completed_at"] is not None
    assert job["error"] is None
    assert job["allowed_actions"] == []
    assert job["allowedActions"] == []

    # 验证 demo_job 仓储同步记录置为 completed
    repo = client.app.state.service.repository
    persisted = repo.read_job(job_id)
    assert persisted is not None
    assert persisted["status"] == "completed"
    assert persisted["progress"] == 100


def test_job_cancel_action_and_permissions(client):
    """4. 验证长任务取消：进行中可取消、只读角色 403 拦截、终态 409 拦截。"""
    headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-cancel-{uuid4().hex[:8]}"
    job_id = client.post(
        START_ALPHA,
        headers={**headers, "Idempotency-Key": key, "If-Match": "1"},
        json={},
    ).json()["id"]

    # 只读角色尝试取消长任务 -> 403 拦截
    viewer_headers = login(client, "alpha-viewer")
    viewer_cancel = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**viewer_headers, "Idempotency-Key": f"cancel-v-{uuid4().hex[:8]}"},
    )
    assert viewer_cancel.status_code == 403
    assert viewer_cancel.json()["code"] == "PROJECT_WRITER_REQUIRED"

    # 项目负责人取消排队中长任务 -> 200 成功
    cancel_key = f"cancel-{uuid4().hex[:8]}"
    cancel_resp = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**headers, "Idempotency-Key": cancel_key},
    )
    assert cancel_resp.status_code == 200
    cancelled_job = cancel_resp.json()
    assert cancelled_job["status"] == "cancelled"
    assert cancelled_job["progress"] == 100
    assert cancelled_job["allowed_actions"] == ["retry"]
    assert cancelled_job["allowedActions"] == ["retry"]

    # 仓储 demo_job 状态同步为 cancelled
    repo = client.app.state.service.repository
    persisted = repo.read_job(job_id)
    assert persisted["status"] == "cancelled"

    # 对已终态任务再次取消 -> 409 冲突拦截
    conflict_cancel = client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**headers, "Idempotency-Key": f"cancel-again-{uuid4().hex[:8]}"},
    )
    assert conflict_cancel.status_code == 409
    assert conflict_cancel.json()["code"] == "VERSION_CONFLICT"


def test_job_retry_action_and_permissions(client):
    """5. 验证失败与取消任务重试：负责人与管理员可重试，只读与编写人 403 拦截，非终态 409 拦截。"""
    manager_headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-retry-{uuid4().hex[:8]}"
    job_id = client.post(
        START_ALPHA,
        headers={**manager_headers, "Idempotency-Key": key, "If-Match": "1"},
        json={},
    ).json()["id"]

    # 先将任务取消至终态
    client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**manager_headers, "Idempotency-Key": f"c-{uuid4().hex[:8]}"},
    )

    # 1. 只读角色尝试重试 -> 403 拦截
    viewer_headers = login(client, "alpha-viewer")
    viewer_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**viewer_headers, "Idempotency-Key": f"ret-v-{uuid4().hex[:8]}"},
    )
    assert viewer_retry.status_code == 403
    assert viewer_retry.json()["code"] == "PROJECT_LEAD_REQUIRED"

    # 2. 普通编写人（非项目负责人）尝试重试 -> 403 拦截
    editor_headers = login(client, "alpha-editor")
    editor_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**editor_headers, "Idempotency-Key": f"ret-e-{uuid4().hex[:8]}"},
    )
    assert editor_retry.status_code == 403
    assert editor_retry.json()["code"] == "PROJECT_LEAD_REQUIRED"

    # 3. 项目负责人重试已取消任务 -> 200 成功，重置为 queued
    retry_key = f"ret-m-{uuid4().hex[:8]}"
    retry_resp = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**manager_headers, "Idempotency-Key": retry_key},
    )
    assert retry_resp.status_code == 200
    retried_job = retry_resp.json()
    assert retried_job["status"] == "queued"
    assert retried_job["progress"] == 0
    assert retried_job["allowed_actions"] == ["cancel"]
    assert retried_job["allowedActions"] == ["cancel"]

    # 验证 demo_job 仓储状态已重置为 pending
    repo = client.app.state.service.repository
    persisted = repo.read_job(job_id)
    assert persisted["status"] == "pending"
    assert persisted["progress"] == 0

    # 验证幂等重放
    replay_resp = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**manager_headers, "Idempotency-Key": retry_key},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.headers["Idempotent-Replayed"] == "true"
    assert replay_resp.json()["id"] == job_id

    # 4. 对处于排队中（非终态）的任务触发重试 -> 409 VERSION_CONFLICT 拦截
    conflict_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**manager_headers, "Idempotency-Key": f"ret-conf-{uuid4().hex[:8]}"},
    )
    assert conflict_retry.status_code == 409
    assert conflict_retry.json()["code"] == "VERSION_CONFLICT"

    # 5. 公司管理员（alpha-company-admin）在加入项目后拥有重试权限
    def add_admin_to_team(state):
        state.project_teams[PROJECT_ALPHA]["members"]["alpha-company-admin"] = {
            "user_id": "alpha-company-admin",
            "project_role": "lead",
            "volumes": ["technical", "business"],
        }
    repo.transaction(add_admin_to_team)

    admin_headers = login(client, "alpha-company-admin")
    # 再次取消后让管理员重试
    client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers={**manager_headers, "Idempotency-Key": f"c2-{uuid4().hex[:8]}"},
    )
    admin_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        headers={**admin_headers, "Idempotency-Key": f"ret-adm-{uuid4().hex[:8]}"},
    )
    assert admin_retry.status_code == 200
    assert admin_retry.json()["status"] == "queued"


def test_tenant_and_multi_company_strong_isolation(client):
    """6. 验证多租户企业空间强隔离：跨公司访问长任务严格 404，任务列表按公司隔离。"""
    alpha_headers = login(client, "alpha-manager")
    confirm_chapter(client)

    key = f"glue-iso-{uuid4().hex[:8]}"
    alpha_job_id = client.post(
        START_ALPHA,
        headers={**alpha_headers, "Idempotency-Key": key, "If-Match": "1"},
        json={},
    ).json()["id"]

    # 乙公司用户尝试访问甲公司的任务
    beta_headers = login(client, "beta-manager")

    # 查询长任务详情 -> 严格 404 NOT_FOUND（防嗅探与信息泄露）
    get_res = client.get(f"/api/v1/jobs/{alpha_job_id}", headers=beta_headers)
    assert get_res.status_code == 404
    assert get_res.json()["code"] == "NOT_FOUND"

    # 订阅 SSE 事件流 -> 严格 404 NOT_FOUND
    sse_res = client.get(f"/api/v1/jobs/{alpha_job_id}/events", headers=beta_headers)
    assert sse_res.status_code == 404
    assert sse_res.json()["code"] == "NOT_FOUND"

    # 尝试取消 -> 严格 404 NOT_FOUND
    cancel_res = client.post(
        f"/api/v1/jobs/{alpha_job_id}/cancel",
        headers={**beta_headers, "Idempotency-Key": f"iso-c-{uuid4().hex[:8]}"},
    )
    assert cancel_res.status_code == 404
    assert cancel_res.json()["code"] == "NOT_FOUND"

    # 尝试重试 -> 严格 404 NOT_FOUND
    retry_res = client.post(
        f"/api/v1/jobs/{alpha_job_id}/retry",
        headers={**beta_headers, "Idempotency-Key": f"iso-r-{uuid4().hex[:8]}"},
    )
    assert retry_res.status_code == 404
    assert retry_res.json()["code"] == "NOT_FOUND"

    # 查看乙公司任务列表 -> 绝对不包含甲公司的任务
    beta_jobs_list = client.get("/api/v1/jobs", headers=beta_headers).json()["jobs"]
    assert alpha_job_id not in {j["id"] for j in beta_jobs_list}


def test_persisted_demo_job_transparent_adaptation(client):
    """7. 验证 demo_job 仓储中外部长任务透明适配为 JobStatus 与事件推流。"""
    repo = client.app.state.service.repository
    ext_job_id = f"job-ext-{uuid4().hex[:8]}"

    # 向 demo_job 写入一条外部章节生成长任务
    repo.save_job({
        "id": ext_job_id,
        "job_type": "generate_chapter",
        "project_id": PROJECT_ALPHA,
        "status": "pending",
        "progress": 20,
        "step_name": "组装上下文提示词中",
        "created_by": "alpha-manager",
    })

    headers = login(client, "alpha-manager")

    # 本公司有权用户查询 -> 透明适配成功
    resp = client.get(f"/api/v1/jobs/{ext_job_id}", headers=headers)
    assert resp.status_code == 200
    job = resp.json()
    assert job["id"] == ext_job_id
    assert job["status"] in ("completed", "running")
    assert job["recoverable"] is True
    assert "allowed_actions" in job

    # 验证 SSE 也可无缝推流
    sse_resp = client.get(f"/api/v1/jobs/{ext_job_id}/events", headers=headers)
    assert sse_resp.status_code == 200
    assert sse_resp.headers["content-type"].startswith("text/event-stream")
