# 为什么有这个文件：验证真实片段服务在重复并发和回执提交失败时只产生一致结果。
# 它解决什么问题：避免同一操作重复创建或发布，以及失败后留下没有回执的资料。
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest

from icg_demo.domain import Principal
from test_reference_flow import client, login


CLEAN = {"product": "合成巡检", "snippet_type": "solution", "variables": [],
         "source_group": "synthetic", "boilerplate_group": "", "draft_body": "合成正文。"}


def principal(client):
    token = login(client)["Authorization"].removeprefix("Bearer ")
    return Principal(client.app.state.service.repository.read().accounts["alpha-manager"], token)


@pytest.mark.parametrize("different_payload", [False, True])
def test_concurrent_key_mutates_once_and_replays_or_rejects(client, monkeypatch, different_payload):
    actor = principal(client)
    service = client.app.state.snippet_publication_service
    store = service.store
    entered, release, second_started, duplicate_mutation = Event(), Event(), Event(), Event()
    lock = Lock()
    counters = {"writers": 0, "mutations": 0}
    original_create, original_writer = store.create, service._writer

    def checked_writer(user):
        original_writer(user)
        with lock:
            counters["writers"] += 1
            if counters["writers"] == 2:
                second_started.set()

    def gated_create(*args):
        with lock:
            counters["mutations"] += 1
            if counters["mutations"] > 1:
                duplicate_mutation.set()
        entered.set()
        assert release.wait(10), "controlled mutation was not released"
        return original_create(*args)

    monkeypatch.setattr(service, "_writer", checked_writer)
    monkeypatch.setattr(store, "create", gated_create)
    key = "concurrent-synthetic-review-key"
    body_two = {**CLEAN, "draft_body": "另一份合成正文。"} if different_payload else dict(CLEAN)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.create, actor, dict(CLEAN), key, None)
        assert entered.wait(10)
        second = pool.submit(service.create, actor, body_two, key, None)
        try:
            assert second_started.wait(10)
            assert not duplicate_mutation.wait(0.4), "same key entered a second mutation before receipt commit"
        finally:
            release.set()
        result = first.result(timeout=10)
        if different_payload:
            with pytest.raises(Exception) as failed:
                second.result(timeout=10)
            assert failed.value.code == "IDEMPOTENCY_CONFLICT"
        else:
            assert second.result(timeout=10) == result
    assert counters["mutations"] == 1
    assert len(store.snapshot()["records"]) == 1
    assert len(service.repository.read().workflow_receipts) == 1


def test_failed_receipt_commit_rolls_back_separate_snippet_store(client, monkeypatch):
    actor = principal(client)
    service = client.app.state.snippet_publication_service
    before = service.store.snapshot()
    receipts = service.repository.read().workflow_receipts

    def failed_commit(operation):
        # 实际执行回调后模拟存储提交失败；回执状态不提交。
        snapshot = service.repository.read()
        result = operation(snapshot)
        if snapshot.workflow_receipts != receipts:
            raise RuntimeError("synthetic receipt commit failure")
        return result

    monkeypatch.setattr(service.repository, "transaction", failed_commit)
    with pytest.raises(RuntimeError, match="synthetic receipt"):
        service.create(actor, dict(CLEAN), "failed-synthetic-review-key", None)
    assert service.store.snapshot() == before
    assert service.repository.read().workflow_receipts == receipts
