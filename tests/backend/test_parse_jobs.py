# 为什么有这个文件：验证招标解析后台任务与任务事件流（APP-M2-T020 / PRD v1.8 §5.12.4、§5.2.1）。
# 它解决什么问题：启动即返回 202 与任务；后台按原解析流程执行并写进度事件；RAGFlow 仍在识别时反复取回直到完成或等满上限；
# 事件流在任务进行中保持连接并推送新事件；取消、重试、权限与重复启动行为如实。

import threading
import time
from uuid import uuid4

import pytest

from test_reference_flow import TENDER, ProjectFlow, client, login  # noqa: F401


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setenv("ICG_PARSE_JOB_POLL_SECONDS", "0.05")
    monkeypatch.setenv("ICG_SSE_HOLD_SECONDS", "5")


def _uploaded(client):
    flow = ProjectFlow(client)
    flow.write("", {"tender_number": "SYNTH-001", "deadline": "2026-12-31T17:00:00+08:00"}, "PATCH")
    flow.upload(TENDER.encode())
    return flow


def _start(flow, account="alpha-manager", expected=200):
    headers = {**login(flow.client, account), "If-Match": str(flow.state()["revision"]), "Idempotency-Key": str(uuid4())}
    return flow.client.post(f"{flow.path}/parse/jobs", json={}, headers=headers)


def _wait(flow, job_id, statuses=("completed", "failed", "cancelled"), timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = flow.client.get(f"/api/v1/jobs/{job_id}", headers=flow.headers).json()
        if job["status"] in statuses:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach {statuses}: {job}")


def test_parse_job_runs_in_background_and_reports_events(client):
    flow = _uploaded(client)
    started = _start(flow)
    assert started.status_code == 202, started.text
    body = started.json()
    assert started.headers["Location"] == f"/api/v1/jobs/{body['id']}"
    assert body["type"] == "parse" and body["status"] in ("queued", "running", "completed")

    job = _wait(flow, body["id"])
    assert job["status"] == "completed", job
    assert "条款" in job["message"] and job["progress"] == 100 and job["allowedActions"] == []
    kinds = [e["type"] for e in job["events"]]
    assert kinds[0] == "job.status_changed" and kinds[-1] == "job.completed"
    assert [e["seq"] for e in job["events"]] == list(range(1, len(kinds) + 1))
    assert flow.state()["requirements"], "解析结果已写入项目"

    listed = [j for j in client.get("/api/v1/jobs", headers=flow.headers).json()["jobs"] if j["project_id"] == flow.id]
    assert [j["type"] for j in listed].count("parse") == 1  # 后台任务代表这次解析，内部调用不重复列出
    assert next(j for j in listed if j["id"] == body["id"])["status"] == "completed"

    stream = client.get(f"/api/v1/jobs/{body['id']}/events", headers={**flow.headers, "Last-Event-ID": f"{body['id']}:1"})
    assert stream.status_code == 200 and stream.headers["content-type"].startswith("text/event-stream")
    assert f"id: {body['id']}:1\n" not in stream.text and f"id: {body['id']}:2\n" in stream.text
    assert "event: job.completed" in stream.text


def test_outer_parse_stays_listed_after_inner_sync_job_is_dropped(client):
    """工作区能看到运行中的解析时，任务列表也要能看到；丢掉同步记录不能带走外层任务。"""
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    gate = threading.Event()
    entered = threading.Event()
    original = runner._parse_once

    def blocked(principal, project_id, payload, *args):
        entered.set()
        assert gate.wait(timeout=20), "parse was not released"
        return original(principal, project_id, payload)

    runner._parse_once = blocked
    try:
        started = _start(flow)
        assert started.status_code == 202, started.text
        job_id = started.json()["id"]
        assert entered.wait(timeout=10), "parse did not reach the background call"

        def parse_ids(jobs):
            return {job["id"] for job in jobs if job["id"] == job_id}

        assert job_id in parse_ids(flow.state()["jobs"])
        listed = client.get("/api/v1/jobs", headers=flow.headers)
        assert listed.status_code == 200, listed.text
        assert job_id in parse_ids(listed.json()["jobs"])

        runner.repository.transaction(lambda state: state.jobs.pop(job_id, None))
        assert job_id in parse_ids(flow.state()["jobs"])
        listed = client.get("/api/v1/jobs", headers=flow.headers)
        assert listed.status_code == 200, listed.text
        row = next(job for job in listed.json()["jobs"] if job["id"] == job_id)
        assert row["status"] == "running" and row["recoverable"] is False and row["type"] == "parse"

        admin = client.get("/api/v1/jobs", headers=login(client, "platform-admin"))
        assert admin.status_code == 200, admin.text
        assert job_id in {job["id"] for job in admin.json()["jobs"]}

        inner_id = "job-inner-sync-only"
        def plant(state):
            state.jobs[inner_id] = {
                "id": inner_id, "project_id": flow.id, "type": "parse", "status": "completed",
                "progress": 100, "message": "同步解析记录", "created_at": "2026-11-12T00:00:00+00:00",
                "completed_at": "2026-11-12T00:00:00+00:00", "error": None, "recoverable": False,
            }

        runner.repository.transaction(plant)
        runner._drop_inner_job({"job": {"id": inner_id}})
        runner._drop_inner_job({"job": {"id": job_id}})
        listed_ids = {job["id"] for job in client.get("/api/v1/jobs", headers=flow.headers).json()["jobs"]}
        assert inner_id not in listed_ids
        assert job_id in listed_ids
    finally:
        gate.set()


def test_remote_parse_is_fetched_repeatedly_and_the_stream_stays_open(client, monkeypatch):
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    calls = {"n": 0}
    original = runner._pending_files

    def pending(project_id, payload):
        calls["n"] += 1
        return ["file-remote"] if calls["n"] <= 3 else original(project_id, payload)

    monkeypatch.setattr(runner, "_pending_files", pending)
    body = _start(flow).json()
    with client.stream("GET", f"/api/v1/jobs/{body['id']}/events", headers=flow.headers) as response:
        text = "".join(response.iter_text())
    assert "RAGFlow 正在识别 1 份文件" in text
    assert text.rstrip().endswith("}") and "event: job.completed" in text  # 连接保持到任务结束
    job = _wait(flow, body["id"])
    assert job["status"] == "completed" and calls["n"] >= 4
    progress = [e["payload"]["message"] for e in job["events"] if e["type"] == "job.progress"]
    assert sum("第" in m and "次取回" in m for m in progress) == 3


def test_waiting_too_long_fails_then_retry_continues(client, monkeypatch):
    monkeypatch.setenv("ICG_PARSE_JOB_MAX_WAIT_SECONDS", "1")
    flow = _uploaded(client)
    repository = client.app.state.service.repository
    updates = []
    monkeypatch.setattr(repository, "mode", "mysql", raising=False)
    monkeypatch.setattr(repository, "save_job", lambda data, **kwargs: True)
    monkeypatch.setattr(repository, "update_job_progress",
                        lambda job_id, progress, **kwargs: updates.append({"id": job_id, "progress": progress, **kwargs}) or True)
    runner = client.app.state.parse_job_runner
    original = runner._pending_files
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    body = _start(flow).json()
    failed = _wait(flow, body["id"])
    assert failed["status"] == "failed" and failed["error"]["code"] == "PARSER_UNAVAILABLE"
    assert failed["allowedActions"] == ["retry"] and failed["events"][-1]["type"] == "job.failed"
    assert any(row["id"] == body["id"] and row.get("status") == "failed" for row in updates)

    monkeypatch.setattr(runner, "_pending_files", original)
    retried = client.post(f"/api/v1/jobs/{body['id']}/retry", headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert retried.status_code == 200, retried.text
    assert _wait(flow, body["id"])["status"] == "completed"
    assert any(row["id"] == body["id"] and row.get("status") == "completed" and row["progress"] == 100 for row in updates)


def test_cancel_stops_the_job_and_duplicate_start_returns_the_running_job(client, monkeypatch):
    flow = _uploaded(client)
    repository = client.app.state.service.repository
    updates = []
    monkeypatch.setattr(repository, "mode", "mysql", raising=False)
    monkeypatch.setattr(repository, "save_job", lambda data, **kwargs: True)
    monkeypatch.setattr(repository, "update_job_progress",
                        lambda job_id, progress, **kwargs: updates.append({"id": job_id, "progress": progress, **kwargs}) or True)
    runner = client.app.state.parse_job_runner
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    first = _start(flow).json()
    _wait(flow, first["id"], statuses=("running",))
    again = _start(flow)
    assert again.status_code == 202 and again.json()["id"] == first["id"]
    cancelled = client.post(f"/api/v1/jobs/{first['id']}/cancel", headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    time.sleep(0.3)
    job = client.get(f"/api/v1/jobs/{first['id']}", headers=flow.headers).json()
    assert job["status"] == "cancelled" and job["events"][-1]["type"] == "job.cancelled"
    assert any(row["id"] == first["id"] and row.get("status") == "cancelled" for row in updates)


def test_parse_job_permissions(client):
    flow = _uploaded(client)
    viewer = _start(flow, "alpha-viewer")
    assert viewer.status_code == 403
    beta = _start(flow, "beta-manager")
    assert beta.status_code == 404
    no_match = client.post(f"{flow.path}/parse/jobs", json={}, headers={**flow.headers, "Idempotency-Key": str(uuid4())})
    assert no_match.status_code == 428 and no_match.json()["code"] == "IF_MATCH_REQUIRED"
    job = _start(flow).json()
    assert client.get(f"/api/v1/jobs/{job['id']}", headers=login(client, "beta-manager")).status_code == 404
    _wait(flow, job["id"])


def test_orphan_running_parse_job_is_failed_so_restart_can_reparse(client, monkeypatch):
    """进程崩溃后遗留的 running 任务：再次 start 应收口并开新任务，而不是永远返回僵尸。"""
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    monkeypatch.setattr(runner, "_pending_files", lambda project_id, payload: ["file-remote"])
    original = runner._parse_once
    entered = threading.Event()
    release = threading.Event()
    block_first = {"active": True}

    def controlled_parse(principal, project_id, payload, job_id=None, on_outline_ready=None):
        if block_first["active"]:
            block_first["active"] = False
            entered.set()
            assert release.wait(timeout=10), "orphan parse was not released"
            raise RuntimeError("synthetic orphan parse thread")
        return original(principal, project_id, payload, job_id, on_outline_ready)

    monkeypatch.setattr(runner, "_parse_once", controlled_parse)
    first = _start(flow).json()
    assert entered.wait(timeout=10), "parse did not reach the background call"
    _wait(flow, first["id"], statuses=("running",))
    with runner._lock:
        runner._running.discard(first["id"])  # 模拟进程/线程丢失
    again = _start(flow)
    release.set()
    assert again.status_code == 202, again.text
    body = again.json()
    assert body["id"] != first["id"]
    orphan = client.get(f"/api/v1/jobs/{first['id']}", headers=flow.headers).json()
    assert orphan["status"] == "failed"
    assert orphan["error"]["code"] == "PARSER_INTERRUPTED"
    client.post(f"/api/v1/jobs/{body['id']}/cancel", headers={**flow.headers, "Idempotency-Key": str(uuid4())})


def test_fail_orphans_on_wire_marks_stale_running_jobs(client):
    flow = _uploaded(client)
    runner = client.app.state.parse_job_runner
    now = "2026-11-12T00:00:00+08:00"
    stale_id = "job-stale-orphan"

    def plant(state):
        job = {"id": stale_id, "project_id": flow.id, "type": "parse", "status": "running", "progress": 5,
               "message": "后台任务处理中", "created_at": now, "completed_at": None, "error": None,
               "events": [], "recoverable": True, "live": True, "created_by": "alpha-manager",
               "file_ids": None, "service": "auto"}
        state.recoverable_jobs[stale_id] = job
        state.jobs[stale_id] = {
            key: job.get(key) for key in ("id", "project_id", "type", "status", "progress", "message",
                                          "created_at", "completed_at", "error")
        } | {"recoverable": False}

    runner.repository.transaction(plant)
    assert runner.fail_orphans() >= 1
    orphan = client.get(f"/api/v1/jobs/{stale_id}", headers=flow.headers).json()
    assert orphan["status"] == "failed" and orphan["error"]["code"] == "PARSER_INTERRUPTED"


def _technical_job(client, model):
    from test_reference_flow import login
    from test_technical_sources import _docx, _project, _upload

    service = client.app.state.service
    monkeypatch = _technical_job.monkeypatch
    monkeypatch.setattr(service, "resolve_model_provider", lambda *args, **kwargs: model)
    headers = login(client)
    project_id, revision = _project(client, headers)
    uploaded = _upload(
        client, headers, project_id, revision, "招标.docx",
        content=_docx("服务方案中应包含数据库巡检。"),
    )
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    started = client.post(
        f"/api/v1/projects/{project_id}/parse/jobs",
        json={},
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
    )
    assert started.status_code == 202, started.text
    job = _wait_project(client, headers, started.json()["id"])
    state = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    return job, state


def _wait_project(client, headers, job_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
        if job["status"] in ("completed", "failed", "cancelled"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish: {job}")


def _skeleton_json(user: str, title: str = "运维保障与巡检") -> str:
    """两阶段契约阶段一（ISSUE-060）：章节骨架。单个一级章即叶子，编号 deterministic 为 1。"""
    import json as _json
    return _json.dumps({"nodes": [{"level": 1, "title": title}]}, ensure_ascii=False)


def _mounts_json(user: str) -> str:
    """两阶段契约阶段二：把提示里的全部 T/S 编号挂到叶子 1；refs 必须真实来自提示。"""
    import json as _json
    import re as _re
    refs = []
    for ref in _re.findall(r"[TS]-\d+(?:-\d+)?", user or ""):
        if ref not in refs:
            refs.append(ref)
    return _json.dumps({"mounts": [{"node": "1", "refs": refs or ["T-01"]}]}, ensure_ascii=False)


def _outline_tree_json(user: str, title: str = "运维保障与巡检") -> str:
    """兼容旧单次拟目录契约的合成返回；新两阶段流程用 _skeleton_json/_mounts_json。"""
    import json as _json
    import re as _re
    refs = []
    for ref in _re.findall(r"[TS]-\d+(?:-\d+)?", user or ""):
        if ref not in refs:
            refs.append(ref)
    return _json.dumps({"nodes": [{"level": 1, "title": title, "points": [
        {"text": "数据库巡检", "refs": refs or ["T-01"]}
    ]}]}, ensure_ascii=False)


def _is_tree_prompt(system: str) -> bool:
    return (
        "设计章节目录骨架" in system      # 两阶段阶段一（ISSUE-060）
        or "挂载响应要点" in system       # 两阶段阶段二
        or "编排技术服务方案目录" in system  # 旧单次契约（遗留路径）
        or "你在为技术服务方案拟目录" in system
    )


def _tree_reply(system: str, user: str, title: str = "运维保障与巡检") -> str:
    if "设计章节目录骨架" in system:
        return _skeleton_json(user, title=title)
    if "挂载响应要点" in system:
        return _mounts_json(user)
    return _outline_tree_json(user, title=title)


class _StageModel:
    is_real_model = True
    is_local = True
    base_url = "http://127.0.0.1:11434"
    messages: list[str] = []

    def __init__(self, repository):
        self.repository = repository
        self.messages = []

    def suggest(self, system, user):
        for job in self.repository.read().recoverable_jobs.values():
            if job.get("type") == "parse" and job.get("status") == "running":
                self.messages.append(job.get("message") or "")
        system = system or ""
        if _is_tree_prompt(system):
            return _tree_reply(system, user)
        if "response_mount" in system:
            return '{"items":[{"role":"response_mount","text":"数据库巡检","quote":"数据库巡检","kind":"scoring"}]}'
        return "按招标要求写巡检步骤。"


class _TimeoutModel:
    is_real_model = True
    is_local = True
    base_url = "http://127.0.0.1:11434"

    def suggest(self, system, user):
        from icg.infra.openai_model import RetryableModelError
        system = system or ""
        if "你在读一份招标文件" in system or _is_tree_prompt(system) or "response_mount" in system:
            raise RetryableModelError("timeout")
        return "按招标要求写巡检步骤。"


def test_stage_message_names_extract_after_deepdoc_and_tree():
    from icg.domain.tender_orchestrator import parse_stage_message

    assert parse_stage_message("extract", recognized=True) == "DeepDoc 已完成，正在抽取条款。"
    chunk = parse_stage_message("extract", recognized=True, index=2, total=9)
    assert chunk == "DeepDoc 已完成，正在抽取条款（第 2/9 块）。"
    assert parse_stage_message("tree") == "正在编排目录。"
    assert "DeepDoc" not in parse_stage_message("extract")


def test_extract_and_tree_stages_replace_the_running_message(client, monkeypatch):
    _technical_job.monkeypatch = monkeypatch
    model = _StageModel(client.app.state.service.repository)
    job, _state = _technical_job(client, model)
    assert job["status"] == "completed", job
    assert job.get("error") in (None, {})
    progress = [event["payload"]["message"] for event in job["events"] if event["type"] == "job.progress"]
    assert any("正在抽取条款" in message for message in progress)
    assert any("编排目录" in message for message in progress)
    assert any("正在抽取条款" in message for message in model.messages)
    assert any("编排目录" in message for message in model.messages)


def test_job_completes_once_outline_is_ready_while_matrix_retrieval_still_runs(client, monkeypatch):
    """抽取完、目录落库后作业就是 completed 100%；矩阵历史检索在后面慢慢跑，不能让作业停在 92%。"""
    _technical_job.monkeypatch = monkeypatch
    service = client.app.state.service
    original = service.knowledge_base.search
    entered = threading.Event()
    gate = threading.Event()

    def slow_matrix_search(company_id, query, *args, **kwargs):
        if kwargs.get("kinds") == {"history", "materials"}:
            entered.set()
            assert gate.wait(timeout=30), "matrix retrieval was not released"
        return original(company_id, query, *args, **kwargs)

    monkeypatch.setattr(service.knowledge_base, "search", slow_matrix_search)
    try:
        job, state = _technical_job(client, _StageModel(service.repository))
        assert entered.is_set(), "matrix retrieval never started"
        assert not gate.is_set()
        assert job["status"] == "completed" and job["progress"] == 100, job
        assert job["events"][-1]["type"] == "job.completed"
        assert state["technical_outline"]["headings"]
        assert state["parse_confirmed"] is True
    finally:
        gate.set()


def test_extract_mass_timeout_completes_degraded_not_clean(client, monkeypatch):
    _technical_job.monkeypatch = monkeypatch
    job, state = _technical_job(client, _TimeoutModel())
    assert job["status"] == "completed", job
    assert job["error"]["code"] == "EXTRACT_DEGRADED"
    assert "降质" in job["message"]
    assert "解析完成：" not in job["message"]
    completed = job["events"][-1]
    assert completed["type"] == "job.completed"
    assert completed["payload"]["error"] == "EXTRACT_DEGRADED"
    assert state["extract_degraded"] is True
    assert state["extract_timeout_count"] >= 1
    if state.get("technical_outline"):
        # 模型超时失败不再写 rule_fallback 兜底树：可见目录保持规则草稿，失败状态独立上浮。
        assert state["technical_outline"]["outline_source"] in ("rule", "rule_fallback")
        assert state["tree_model_failed"] is True


class _TreeModel(_StageModel):
    """抽取正常；编目录时返回给定内容或抛错，并记下 TREE 请求次数。"""

    def __init__(self, repository, tree):
        super().__init__(repository)
        self.tree = tree
        self.tree_calls = 0
        self.entered = threading.Event()
        self.gate = threading.Event()
        self.gate.set()

    def suggest(self, system, user):
        if not _is_tree_prompt(system or ""):
            return super().suggest(system, user)
        self.tree_calls += 1
        self.entered.set()
        assert self.gate.wait(timeout=30), "TREE was not released"
        if isinstance(self.tree, Exception):
            raise self.tree
        if self.tree is SINGLE_QUOTED_TREE:
            return _tree_reply(system or "", user, title="数据库巡检服务")
        return self.tree


SINGLE_QUOTED_TREE = (
    "[{'level': 1, 'title': '运维保障', 'mount_ids': []},"
    " {'level': 2, 'title': '数据库巡检服务', 'mount_ids': ['m1']}]"
)


def test_usable_model_schedules_tree_and_rule_draft_is_labelled_while_it_runs(client, monkeypatch):
    """有可用本地模型时必须发 TREE；TREE 返回前目录只是规则草稿，工作区要说明原因，不能像已定稿的规则目录。"""
    _technical_job.monkeypatch = monkeypatch
    service = client.app.state.service
    model = _TreeModel(service.repository, SINGLE_QUOTED_TREE)
    model.gate.clear()
    seen: dict = {}

    def watch():
        assert model.entered.wait(timeout=30), "TREE was never requested"
        workflow = service.repository.read().workflows
        project_id = next(pid for pid, wf in workflow.items() if wf.get("technical_outline"))
        seen.update(workflow[project_id])
        model.gate.set()

    watcher = threading.Thread(target=watch)
    watcher.start()
    try:
        job, state = _technical_job(client, model)
    finally:
        model.gate.set()
        watcher.join(timeout=30)
    # ISSUE-060 两阶段契约：阶段一骨架 + 阶段二挂载，恰好两次 TREE 调用。
    assert model.tree_calls == 2
    assert seen["outline_source"] != "model"
    assert "正在编排" in seen["outline_reason"]
    assert "正在编排" in seen["technical_outline"]["outline_reason"]
    assert job["status"] == "completed" and job.get("error") in (None, {}), job
    assert state["outline_source"] == "model"
    assert state["technical_outline"]["outline_source"] == "model"
    assert state["outline_reason"] == ""
    assert "数据库巡检服务" in [item["title"] for item in state["technical_outline"]["headings"]]


def test_tree_timeout_keeps_rule_draft_with_explicit_failure(client, monkeypatch):
    """真实适配器超时（ISSUE-060）：绝不静默写通用规则目录冒充成功——可见目录保持解析期规则草稿，
    tree_model_failed/原因/错误链上浮，前端凭此给「重新生成目录」入口。"""
    from icg.infra.openai_model import RetryableModelError

    _technical_job.monkeypatch = monkeypatch
    model = _TreeModel(client.app.state.service.repository, RetryableModelError("timeout"))
    job, state = _technical_job(client, model)
    assert model.tree_calls >= 1
    assert job["status"] == "completed" and job["error"]["code"] == "TREE_MODEL_FAILED", job
    # 可见目录仍是解析期规则草稿（rule），失败状态独立成字段，不伪装成可用模型目录。
    assert state["outline_source"] == "rule"
    assert state["tree_model_failed"] is True
    assert "超时" in state["outline_reason"]
    assert "重新生成目录" in state["outline_reason"]
    assert "超时" in state["technical_outline"]["outline_reason"]
    # 真实适配器 RetryableModelError('timeout') 必须被识别为超时并落错误链（持久化在 workflow JSON）。
    workflow = client.app.state.service.repository.read().workflows[
        state.get("project", {}).get("id") or next(iter(client.app.state.service.repository.read().workflows))]
    assert workflow["outline_model_error"]["timeout"] is True
    assert workflow["outline_model_error"]["stage"] == "skeleton"
    # 规则草稿目录仍然可见可用（未被清空、未被通用模板覆盖）。
    assert state["technical_outline"]["headings"]


def test_health_exposes_effective_model(client):
    health = client.get("/health").json()
    assert health["model"] in ("mock", "real")
    assert health["effective_model"] in ("mock", "real", "company_real")
    assert "effective_model" in health
