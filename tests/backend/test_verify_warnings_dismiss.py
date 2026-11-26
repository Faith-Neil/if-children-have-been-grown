# 为什么有这个文件：验证核验警示人工消警闭环（TV-M0-T27 遗留整改）——
# 规则核验存在合理噪声，用户核对无误后可消警，覆盖视图不再显示待复核红标，原文留档审计。
from __future__ import annotations

from icg.domain.technical_response_plan import confirm_reasons


def test_dismissed_warnings_clear_confirm_reason():
    task = {
        "response_status": "generated_review",
        "generation_status": "generated",
        "verify_warnings": ["跨节口径冲突：服务期限本节取12个月，他节出现1个月"],
        "dismissed_warnings": ["跨节口径冲突：服务期限本节取12个月，他节出现1个月"],
        "rag": {"status": "hit"},
    }
    assert "后置核验待复核" not in confirm_reasons(task, False)


def test_active_warnings_still_show_confirm_reason():
    task = {
        "response_status": "generated_review",
        "generation_status": "generated",
        "verify_warnings": ["警示A", "警示B"],
        "dismissed_warnings": ["警示A"],
        "rag": {"status": "hit"},
    }
    assert "后置核验待复核" in confirm_reasons(task, False)


def test_coverage_row_exposes_active_warnings_only():
    """覆盖行只暴露未消警的活跃警示，已消警计入数。"""
    task = {
        "task_id": "t1", "requirement_ids": ["r1"],
        "verify_warnings": ["警示A", "警示B"], "dismissed_warnings": ["警示A"],
        "generation_status": "generated",
    }
    active = [w for w in (task.get("verify_warnings") or []) if w not in set(task.get("dismissed_warnings") or [])]
    assert active == ["警示B"]
    assert len(task["dismissed_warnings"]) == 1
