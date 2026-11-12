# 为什么有这个文件：确认模型抽取不在 MemoryRepository 全局锁内执行。
# 它解决什么问题：解析线程长时间占 RLock 时 login 会连续超时；事务外预跑后锁内只写结果。

from __future__ import annotations

import json
import threading

from icg.domain.technical_model_extract import extract_with_model
from icg.infra.memory_repository import MemoryRepository


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
