# 为什么有这个文件：确认模型抽取不在 MemoryRepository 全局锁内执行。
# 它解决什么问题：解析线程长时间占 RLock 时 login 会连续超时；事务外预跑后锁内只写结果。

from __future__ import annotations

import json
import threading

import pytest
from fastapi.testclient import TestClient

from icg.domain.technical_model_extract import extract_with_model
from icg.infra.memory_repository import MemoryRepository
from icg_demo.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as actual:
        yield actual


class _LockProbeModel:
    is_real_model = True
    is_local = True
    model = "qwen-test"
    base_url = "http://127.0.0.1:11434"

    def __init__(self, memory: MemoryRepository):
        self.memory = memory
        self.other_thread_got_lock = []

    def suggest(self, system, user):
        got = {"ok": False}

        def probe():
            # 另一线程：若本线程正占着事务锁，这里会阻塞；短超时失败则说明锁被占。
            acquired = self.memory._lock.acquire(timeout=0.05)
            got["ok"] = bool(acquired)
            if acquired:
                self.memory._lock.release()

        worker = threading.Thread(target=probe)
        worker.start()
        worker.join(timeout=1)
        self.other_thread_got_lock.append(got["ok"])
        return json.dumps({
            "who": "探针业主",
            "what": "运维",
            "period": "",
            "sla": "",
            "format_order": [],
            "items": [{"role": "response_mount", "text": "巡检服务", "quote": "巡检", "kind": "scoring"}],
        }, ensure_ascii=False)


def test_extract_with_model_runs_while_memory_lock_is_free():
    memory = MemoryRepository()
    probe = _LockProbeModel(memory)
    payload = extract_with_model(["提供巡检服务"], probe)
    assert payload["items"]
    assert probe.other_thread_got_lock == [True]


def test_held_transaction_blocks_other_thread_from_lock():
    memory = MemoryRepository()
    probe = _LockProbeModel(memory)

    def inside(state):
        extract_with_model(["提供巡检服务"], probe)
        return True

    memory.transaction(inside)
    assert probe.other_thread_got_lock == [False]


def test_parse_extract_is_not_inside_repository_transaction(client, monkeypatch):
    """重庆中烟：EXTRACT 若仍在 _write 事务里，login 会跟 RLock 排队。"""
    import json
    from uuid import uuid4

    from test_reference_flow import login
    from test_technical_sources import _docx, _project, _upload

    service = client.app.state.service
    repo = service.repository
    lock = getattr(repo, "_lock", None) or getattr(getattr(repo, "_memory", None), "_lock", None)
    seen = {"txn": False, "in_txn": [], "lock_free": []}
    orig_txn = repo.transaction

    def wrapped_txn(operation):
        seen["txn"] = True
        try:
            return orig_txn(operation)
        finally:
            seen["txn"] = False

    monkeypatch.setattr(repo, "transaction", wrapped_txn)

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"

        def suggest(self, system, user):
            seen["in_txn"].append(bool(seen.get("txn")))
            if lock is not None:
                got = lock.acquire(timeout=0.05)
                seen["lock_free"].append(bool(got))
                if got:
                    lock.release()
            if "目录" in (system or "") or "mount_ids" in (system or ""):
                return json.dumps([
                    {"level": 1, "title": "运维保障与巡检", "mount_ids": []},
                ], ensure_ascii=False)
            return json.dumps({
                "who": "", "what": "", "period": "", "sla": "",
                "format_order": [],
                "items": [{"role": "response_mount", "text": "巡检服务",
                           "quote": "巡检", "kind": "scoring"}],
            }, ensure_ascii=False)

    monkeypatch.setattr(service, "resolve_model_provider", lambda *args, **kwargs: Local())
    headers = login(client)
    project_id, revision = _project(client, headers)
    uploaded = _upload(client, headers, project_id, revision, "招标.docx", content=_docx("服务方案中应包含数据库巡检。"))
    assert uploaded.status_code == 200, uploaded.text
    workspace = client.get(f"/api/v1/projects/{project_id}/workspace", headers=headers).json()
    parsed = client.post(
        f"/api/v1/projects/{project_id}/parse",
        headers={**headers, "If-Match": str(workspace["revision"]), "Idempotency-Key": str(uuid4())},
        json={},
    )
    assert parsed.status_code == 200, parsed.text
    assert seen["in_txn"], "模型 suggest 应被解析调用"
    assert all(flag is False for flag in seen["in_txn"])
    assert seen["lock_free"]
    assert all(flag is True for flag in seen["lock_free"])
