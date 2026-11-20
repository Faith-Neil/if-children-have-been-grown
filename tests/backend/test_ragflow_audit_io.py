from __future__ import annotations

import json

import pytest

from fake_ragflow import MODE_BUSINESS_ERROR, MODE_CHUNKS, MODE_TIMEOUT
from icg.domain.parsing import ParsedDocument
from icg.domain.tender_remote import RemoteOutcome, RemoteTenderParser
from icg.infra.ragflow_client import (
    RagflowBusinessError,
    RagflowRetrievalClient,
    RagflowTimeoutError,
)

SYNTHETIC_KEY = "synthetic-ragflow-key"
SYNTHETIC_QUESTION = "巡检要求"
SYNTHETIC_DATASET_IDS = ["syntheticdataset0001"]


def _lines(folder) -> list[dict]:
    path = folder / "ragflow-io.jsonl"
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _client(fake_ragflow) -> RagflowRetrievalClient:
    return RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
        timeout_seconds=5.0,
    )


def test_retrieval_appends_ragflow_io_when_audit_dir_set(fake_ragflow, tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    fake_ragflow.mode = MODE_CHUNKS
    result = _client(fake_ragflow).retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)

    assert result.total == 1
    rows = _lines(tmp_path)
    blob = (tmp_path / "ragflow-io.jsonl").read_text(encoding="utf-8")
    request = next(row for row in rows if row["kind"] == "request" and row["url"].endswith("/api/v1/retrieval"))
    response = next(row for row in rows if row["kind"] == "response" and row["url"].endswith("/api/v1/retrieval"))
    assert request["json"]["question"] == SYNTHETIC_QUESTION
    assert request["json"]["dataset_ids"] == SYNTHETIC_DATASET_IDS
    assert response["status"] == 200
    assert SYNTHETIC_KEY not in blob


def test_retrieval_error_still_appends_ragflow_io(fake_ragflow, tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    fake_ragflow.mode = MODE_BUSINESS_ERROR
    with pytest.raises(RagflowBusinessError):
        _client(fake_ragflow).retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)

    blob = (tmp_path / "ragflow-io.jsonl").read_text(encoding="utf-8")
    assert SYNTHETIC_QUESTION in blob
    assert SYNTHETIC_KEY not in blob


def test_retrieval_timeout_records_error(fake_ragflow, tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    fake_ragflow.mode = MODE_TIMEOUT
    fake_ragflow.hold_responses()
    client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key=SYNTHETIC_KEY,
        timeout_seconds=0.2,
    )
    try:
        with pytest.raises(RagflowTimeoutError):
            client.retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)
    finally:
        fake_ragflow.release_responses()

    rows = _lines(tmp_path)
    assert any(row["kind"] == "error" and row["error"] == "timeout" for row in rows)
    assert SYNTHETIC_KEY not in (tmp_path / "ragflow-io.jsonl").read_text(encoding="utf-8")


def test_deepdoc_parse_http_appends_ragflow_io(fake_ragflow, tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    assert _client(fake_ragflow).trigger_parse("ds-1", ["doc-1"]) is True
    rows = _lines(tmp_path)
    request = next(row for row in rows if row["kind"] == "request" and row["url"].endswith("/chunks"))
    assert request["json"]["document_ids"] == ["doc-1"]
    assert SYNTHETIC_KEY not in (tmp_path / "ragflow-io.jsonl").read_text(encoding="utf-8")


def test_deepdoc_submit_appends_submit_start(tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))

    class Document:
        id = "doc-1"

    class Client:
        def upload_file(self, dataset_id, filename, data, content_type):
            return Document()

        def trigger_parse(self, dataset_id, document_ids):
            return True

    parser = RemoteTenderParser(object())
    parser.client = lambda company_id: Client()
    parser.ensure_dataset = lambda client, company_id: "ds-1"
    parser.poll = lambda company_id, remote, budget=None: RemoteOutcome(
        "done",
        document=ParsedDocument(pages=["甲"], pagination="ragflow_deepdoc_positions", warnings=["经 RAGFlow DeepDOC"]),
    )
    outcome = parser.submit("alpha", "scan.pdf", b"%PDF-1.4 probe")

    assert outcome.state == "done"
    rows = _lines(tmp_path)
    started = next(row for row in rows if row["kind"] == "submit_start")
    assert started["company_id"] == "alpha"
    assert started["filename"] == "scan.pdf"
    assert started["bytes"] == len(b"%PDF-1.4 probe")


def test_audit_dir_unset_writes_nothing(fake_ragflow, tmp_path, monkeypatch):
    monkeypatch.delenv("ICG_AUDIT_IO_DIR", raising=False)
    fake_ragflow.mode = MODE_CHUNKS
    _client(fake_ragflow).retrieve(SYNTHETIC_QUESTION, SYNTHETIC_DATASET_IDS)
    assert not (tmp_path / "ragflow-io.jsonl").exists()
