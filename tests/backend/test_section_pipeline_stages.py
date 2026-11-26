# 为什么有这个文件：PR-C 每节编排阶段机（检索→偏离→写正文）。
# 它解决什么问题：禁止偏离 JSON 落盘后静默停住；取消策略与迁移表可单测。

from __future__ import annotations

import pytest

from icg.domain.technical_section_stages import (
    STAGE_CANCEL_RESUME,
    STAGE_LABELS,
    advance_section_stage,
    forbid_silent_deviate_only,
    is_terminal_stage,
    stage_progress_message,
)


def test_stage_transition_table():
    assert advance_section_stage(None) == "retrieve"
    assert advance_section_stage("retrieve") == "deviate"
    assert advance_section_stage("deviate") == "write_section"
    assert advance_section_stage("write_section") is None
    with pytest.raises(ValueError):
        advance_section_stage("unknown")


def test_deviate_must_not_end_pipeline_silently():
    forbid_silent_deviate_only("write_section")
    forbid_silent_deviate_only("failed", reason="偏离判定失败")
    with pytest.raises(AssertionError):
        forbid_silent_deviate_only("deviate")
    with pytest.raises(AssertionError):
        forbid_silent_deviate_only("deviate", reason="")


def test_terminal_stages_and_cancel_resume_policy():
    assert is_terminal_stage("done")
    assert is_terminal_stage("failed")
    assert is_terminal_stage("cancelled")
    assert not is_terminal_stage("deviate")
    assert "重新点生成" in STAGE_CANCEL_RESUME
    assert "retrieve" in STAGE_CANCEL_RESUME


def test_job_message_shows_stage_and_title():
    tally = {"done": 1, "total": 4, "failed": 0}
    assert "检索" in stage_progress_message(tally, stage="retrieve", title="健康检查")
    assert "偏离" in stage_progress_message(tally, stage="deviate", title="健康检查")
    assert "写正文" in stage_progress_message(tally, stage="write_section", title="健康检查")
    assert stage_progress_message(tally, stage=None, title=None) == "已完成 1/4 节"
    assert STAGE_LABELS["deviate"] == "判偏离"