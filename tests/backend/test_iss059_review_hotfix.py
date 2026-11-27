# 为什么有这个文件：登记 ISSUE-059 Devin Review 后端热修（第二轮）的复现与回归。
# 它解决什么问题：
# 1. Critical 6：知识库重建产生新文档 ID 后，历史标书新分块必须完整重跑去实体化，严禁沿用旧「已脱敏」状态直接可检索；
# 2. 技术卷最后一节进度落库失败时正文不得提交；完成状态落库失败时不得发布 volume.done、不得声称完成；
# 3. /health 在 persistent=true 时必须真探活 MySQL（SELECT 1），不可达返回 503 且 healthy=false。

from __future__ import annotations

import base64
import threading
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from fake_ragflow_v1 import FakeRagflowV1
from icg.app.main import create_app as create_icg_app
from icg.domain.knowledge_base import KnowledgeBaseService, read_index
from icg_demo.main import create_app as create_demo_app
from test_generation_session import _active_session, _chapter, _finish, _frames, _ready, _start, _wait_status
from test_reference_flow import login

ADMIN = "alpha-data-admin"

# 二进制 PDF 原件：字节层从未脱敏，脱敏只能发生在解析后的分块层（deferred_chunk_scrub 路径）。
SENSITIVE_TEXT = (
    "采购人：合成市第一商业银行\n"
    "项目名称：核心系统运维项目\n"
    "\n"
    "本项目为合成市第一商业银行提供核心系统运维服务，合同金额 500万元整。\n"
)


def _pdf_payload() -> str:
    return base64.b64encode(b"%PDF-1.4\n" + SENSITIVE_TEXT.encode("utf-8")).decode()


@pytest.fixture()
def kb_client():
    fake = FakeRagflowV1()
    app = create_icg_app()
    kb = app.state.service.knowledge_base
    kb._client_factory = lambda state, company_id: fake.client()
    kb.background = False
    with TestClient(app) as client:
        yield client, fake


def _upload_sensitive_history(client, fake):
    admin = login(client, ADMIN)
    ensured = client.post("/api/v1/kb-admin/datasets/history/ensure", headers=admin, json={})
    assert ensured.status_code == 200, ensured.text
    result = client.post("/api/v1/kb-admin/datasets/history/documents", headers=admin,
                         json={"filename": "合成历史标书.pdf", "content_base64": _pdf_payload(),
                               "content_type": "application/pdf",
                               "metadata": {"purchaser": "合成市第一商业银行", "project_name": "核心系统运维项目"}})
    assert result.status_code == 200, result.text
    return admin, result.json()


def _chunk_texts(fake, document_id):
    return [chunk["content"] for chunk in fake.documents[document_id]["chunks"]]


def test_rebuild_history_resets_deferred_scrub_and_rescrubs_new_document(kb_client):
    """Critical 6 复现：重建迁移的是未脱敏原件字节，新文档新分块必须重跑去实体化。"""
    client, fake = kb_client
    admin, doc = _upload_sensitive_history(client, fake)
    original_id = doc["document_id"]
    # 对照组：首次上传解析后脱敏已生效，分块不留敏感实体；且本条目的状态机已复位。
    assert doc["status"] == "synced"
    assert doc["deferred_chunk_scrub"] is False
    assert not any("合成市第一商业银行" in text for text in _chunk_texts(fake, original_id))

    old_dataset = fake.documents[original_id]["dataset_id"]
    rebuilt = client.post("/api/v1/kb-admin/datasets/history/rebuild", headers=admin)
    assert rebuilt.status_code == 200, rebuilt.text
    new_dataset = rebuilt.json()["dataset_id"]
    assert new_dataset != old_dataset and old_dataset not in fake.datasets

    migrated = fake.docs_in(new_dataset)[0]
    new_id = migrated["id"]
    assert new_id != original_id
    # 关键对照：重建后解析出的新分块来自未脱敏原件字节，此刻确实带敏感实体——
    # 若本断言不成立，下面的清洗断言就是空转。
    assert any("合成市第一商业银行" in text for text in _chunk_texts(fake, new_id))

    # 索引状态机：重建后的条目必须是 parsing + 待清洗（脱敏标记被重置，不是随迁携带的 False）。
    index = read_index(client.app.state.service.repository.read(), "alpha")
    entry = next(row for row in index["files"].values() if row.get("document_id") == new_id)
    assert entry["status"] == "parsing"
    assert entry["deferred_chunk_scrub"] is True

    # 状态同步触发解析后分块清洗：新文档的全部分块重跑去实体化后才允许进入检索。
    client.app.state.service.knowledge_base.refresh_status("alpha")
    assert not any("合成市第一商业银行" in text for text in _chunk_texts(fake, new_id)), \
        "重建后的新分块必须重新执行去实体化，严禁敏感实体直接可检索"
    assert not any("500万元" in text for text in _chunk_texts(fake, new_id))
    scrub_writes = [path for method, path, _body in fake.calls
                    if method == "PATCH" and f"/documents/{new_id}/chunks/" in path]
    assert scrub_writes, "重建后必须对新文档分块发起脱敏回写"

    index = read_index(client.app.state.service.repository.read(), "alpha")
    entry = next(row for row in index["files"].values() if row.get("document_id") == new_id)
    assert entry["status"] == "synced"
    assert entry["deferred_chunk_scrub"] is False


def test_scrub_failure_blocks_retrieval_until_retry_converges(kb_client, monkeypatch):
    """脱敏回写失败时文档严禁以 synced 进入检索；保持 parsing 待重试，清洗幂等收敛后放行。"""
    client, fake = kb_client
    admin = login(client, ADMIN)
    ensured = client.post("/api/v1/kb-admin/datasets/history/ensure", headers=admin, json={})
    assert ensured.status_code == 200, ensured.text

    real_scrub = KnowledgeBaseService._scrub_synced_history_chunks
    monkeypatch.setattr(KnowledgeBaseService, "_scrub_synced_history_chunks",
                        staticmethod(lambda *args: False))
    result = client.post("/api/v1/kb-admin/datasets/history/documents", headers=admin,
                         json={"filename": "合成历史标书.pdf", "content_base64": _pdf_payload(),
                               "content_type": "application/pdf", "metadata": {}})
    assert result.status_code == 200, result.text
    document_id = result.json()["document_id"]

    client.app.state.service.knowledge_base.refresh_status("alpha")
    index = read_index(client.app.state.service.repository.read(), "alpha")
    entry = next(row for row in index["files"].values() if row.get("document_id") == document_id)
    # 状态机：脱敏未完成严禁 synced；保持 parsing 以便下次同步重试，原因如实写在 message。
    assert entry["status"] == "parsing"
    assert entry["deferred_chunk_scrub"] is True
    assert "去实体化" in entry["message"]

    monkeypatch.setattr(KnowledgeBaseService, "_scrub_synced_history_chunks", staticmethod(real_scrub))
    client.app.state.service.knowledge_base.refresh_status("alpha")
    index = read_index(client.app.state.service.repository.read(), "alpha")
    entry = next(row for row in index["files"].values() if row.get("document_id") == document_id)
    assert entry["status"] == "synced"
    assert entry["deferred_chunk_scrub"] is False
    assert not any("合成市第一商业银行" in text for text in _chunk_texts(fake, document_id))


# ---------------------------------------------------------------- 技术卷进度/正文提交一致性

@pytest.fixture()
def generation_client():
    with TestClient(create_demo_app()) as client:
        yield client


def test_last_section_progress_failure_prevents_chapter_commit(generation_client, monkeypatch):
    """最后一节进度行同步失败：正文不得提交，任务状态一致 failed，流事件无 volume.done。"""
    headers, project_id, workspace, model = _ready(generation_client)
    chapter_id = workspace["technical_outline"]["chapter_id"]
    before = _chapter(generation_client, headers, project_id, chapter_id)["content"]
    repository = generation_client.app.state.service.repository
    original = repository.update_job_progress

    def fail_when_settled(job_id, progress, *args, **kwargs):
        # 全部小节落定（share=1 → progress 95）的最后一节进度写失败；终态落库放行以便收敛。
        if int(progress) >= 95 and kwargs.get("status") == "running":
            return False
        return original(job_id, progress, *args, **kwargs)

    monkeypatch.setattr(repository, "update_job_progress", fail_when_settled)

    model.gate.set()
    responses = []
    worker = _start(generation_client, headers, project_id, workspace, responses)
    job = _active_session(generation_client, headers, project_id)
    failed = _wait_status(generation_client, headers, job["id"], {"failed"}, timeout=20)
    assert "任务存储" in failed["message"] or "任务存储" in str(failed.get("error"))
    # 同步确认边界：最后一节进度落库未确认，正文严禁提交。
    assert _chapter(generation_client, headers, project_id, chapter_id)["content"] == before
    events = _frames(_finish(worker, responses).text)
    kinds = [event["event"] for event in events]
    assert "volume.failed" in kinds, kinds
    assert not any(event["event"] == "volume.done" for event in events)


def test_completion_persistence_failure_publishes_no_volume_done(generation_client, monkeypatch):
    """完成状态写入失败：不发布 volume.done、不声称完成；任务如实改记失败并说明正文去向。"""
    headers, project_id, workspace, model = _ready(generation_client)
    repository = generation_client.app.state.service.repository
    original = repository.update_job_progress

    def fail_completion(job_id, progress, *args, **kwargs):
        if kwargs.get("status") == "completed":
            return False
        return original(job_id, progress, *args, **kwargs)

    monkeypatch.setattr(repository, "update_job_progress", fail_completion)

    model.gate.set()
    responses = []
    worker = _start(generation_client, headers, project_id, workspace, responses)
    job = _active_session(generation_client, headers, project_id)
    failed = _wait_status(generation_client, headers, job["id"], {"failed"}, timeout=20)
    # 严禁声称完成；失败说明必须如实指出正文已经写入、由人核对，而不是假装什么都没发生。
    assert failed["status"] == "failed"
    assert "完成状态未能写入任务存储" in failed["message"]
    events = _frames(_finish(worker, responses).text)
    kinds = [event["event"] for event in events]
    assert not any(event["event"] == "volume.done" for event in events), kinds
    assert "volume.failed" in kinds
    failed_at = len(kinds) - 1 - kinds[::-1].index("volume.failed")
    assert not any(event["event"] not in ("session.live",) for event in events[failed_at + 1:]), kinds


def test_terminal_persistence_precedes_event_publish_in_happy_path(generation_client):
    """对照组：正常路径 volume.done 依然发布、任务 completed、正文写入，证明边界不改变正常语义。"""
    headers, project_id, workspace, model = _ready(generation_client)
    model.gate.set()
    responses = []
    worker = _start(generation_client, headers, project_id, workspace, responses)
    job = _active_session(generation_client, headers, project_id)
    done = _wait_status(generation_client, headers, job["id"], {"completed"}, timeout=20)
    assert done["sections"]["done"] == done["sections"]["total"] >= 1
    events = _frames(_finish(worker, responses).text)
    assert events[-1]["event"] == "volume.done"
    chapter = _chapter(generation_client, headers, project_id, workspace["technical_outline"]["chapter_id"])
    assert "本节完成" in chapter["content"]


# ---------------------------------------------------------------- 健康探针

class _FakeConnection:
    def __init__(self):
        self.probed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def exec_driver_sql(self, sql):
        self.probed.append(sql)
        assert sql == "SELECT 1"
        return object()


class _HealthyEngine:
    def __init__(self, connection):
        self._connection = connection

    def connect(self):
        return self._connection


class _BrokenEngine:
    def connect(self):
        raise RuntimeError("synthetic mysql unreachable")


class _MysqlProbeDouble:
    """包装内存仓储：mode 报告 mysql、engine 换成探针替身，其余全部委托。"""

    mode = "mysql"

    def __init__(self, inner, engine):
        self._inner = inner
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _mysql_app(engine):
    from icg.infra.memory_repository import MemoryRepository
    inner = MemoryRepository()
    return create_icg_app(repository=_MysqlProbeDouble(inner, engine))


def test_health_probes_mysql_and_stays_healthy_when_reachable():
    connection = _FakeConnection()
    with TestClient(_mysql_app(_HealthyEngine(connection))) as client:
        result = client.get("/health")
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["persistent"] is True
        assert body["healthy"] is True
        assert connection.probed == ["SELECT 1"], "persistent 模式必须对 MySQL 执行 SELECT 1 真探活"


def test_health_reports_unhealthy_and_503_when_mysql_unreachable():
    with TestClient(_mysql_app(_BrokenEngine())) as client:
        result = client.get("/health")
        assert result.status_code == 503, result.text
        body = result.json()
        assert body["persistent"] is True
        assert body["healthy"] is False


def test_health_memory_mode_is_healthy_without_probe():
    with TestClient(create_icg_app()) as client:
        result = client.get("/health")
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["persistent"] is False
        assert body["healthy"] is True
