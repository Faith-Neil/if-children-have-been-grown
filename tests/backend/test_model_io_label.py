# 为什么有这个文件：model-io 审计须区分 DEVIATION 与 SECTION 调用。

from __future__ import annotations

import json
import os
from pathlib import Path

from icg.infra.openai_model import AuditIoLabel, _audit_model_io


def test_tree_suggest_audits_label_and_model(tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    from icg.domain.technical_chapter_tree import build_chapter_tree

    class Local:
        is_real_model = True
        is_local = True
        base_url = "http://127.0.0.1:11434"
        model = "qwen-test"

        def suggest(self, system, user, profile=None):
            _audit_model_io("request", {"model": self.model, "url": "http://127.0.0.1:9"})
            return "[]"

    tasks = [{
        "task_id": "t1",
        "theme": "运维保障",
        "title": "运维保障",
        "requirement_ids": ["r1"],
        "response_points": ["数据库巡检"],
        "constraint_ids": [],
        "rejection_requirement_ids": [],
    }]
    workflow = {"requirements": {
        "r1": {"id": "r1", "text": "数据库巡检", "section_kind": "scoring", "technical_clause": True},
    }}
    build_chapter_tree(tasks, workflow, model=Local())
    lines = [json.loads(line) for line in Path(tmp_path, "model-io.jsonl").read_text(encoding="utf-8").splitlines()]
    assert lines[0]["label"] == "TREE"
    assert lines[0]["model"] == "qwen-test"


def test_audit_io_records_label(tmp_path, monkeypatch):
    monkeypatch.setenv("ICG_AUDIT_IO_DIR", str(tmp_path))
    with AuditIoLabel("DEVIATION"):
        _audit_model_io("request", {"url": "http://127.0.0.1:9", "model": "stub"})
    with AuditIoLabel("SECTION"):
        _audit_model_io("request", {"url": "http://127.0.0.1:9", "model": "stub"})
    lines = Path(tmp_path, "model-io.jsonl").read_text(encoding="utf-8").strip().splitlines()
    labels = [json.loads(line).get("label") for line in lines]
    assert labels == ["DEVIATION", "SECTION"]