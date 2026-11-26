# 为什么有这个文件：model-io 审计须区分 DEVIATION 与 SECTION 调用。

from __future__ import annotations

import json
import os
from pathlib import Path

from icg.infra.openai_model import AuditIoLabel, _audit_model_io


def test_audit_io_records_label(tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    with AuditIoLabel("DEVIATION"):
        _audit_model_io("request", {"url": "http://127.0.0.1:9", "model": "stub"})
    with AuditIoLabel("SECTION"):
        _audit_model_io("request", {"url": "http://127.0.0.1:9", "model": "stub"})
    lines = Path(tmp_path, "model-io.jsonl").read_text(encoding="utf-8").strip().splitlines()
    labels = [json.loads(line).get("label") for line in lines]
    assert labels == ["DEVIATION", "SECTION"]