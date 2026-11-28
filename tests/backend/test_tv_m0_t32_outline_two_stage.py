# 为什么有这个文件：核对 ISSUE-060 两阶段模型目录规划——骨架+全量挂载、重试、
# 超时显式记录、无静默规则兜底、无 9 条截断/兜底倾倒。
from __future__ import annotations

import json

from icg.domain.technical_digest_outline import plan_technical_outline, error_is_timeout
from icg.infra.openai_model import ModelCallError, RetryableModelError


class FakeModel:
    is_real_model = True
    is_local = True
    base_url = ""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def suggest(self, system, user, profile=None):
        self.calls.append((system, user))
        reply = self.replies.pop(0) if self.replies else RuntimeError("exhausted")
        if isinstance(reply, Exception):
            raise reply
        return reply


def _workflow(n_tech=3):
    reqs = {}
    for index in range(1, n_tech + 1):
        rid = f"r{index}"
        reqs[rid] = {"id": rid, "text": f"技术服务要求{index}条内容", "technical_clause": True,
                     "status": "pending", "section_kind": "spec", "source": {"page": 3, "quote": f"要求{index}"}}
    return {"requirements": reqs, "technical_sidecars": {"rejection_lines": [], "format_lines": []}}


def _timeout_chain():
    inner = RetryableModelError("timeout")
    outer = ModelCallError("openai-compatible model call failed")
    outer.__cause__ = inner
    return outer


def test_timeout_exception_chain_detected():
    assert error_is_timeout(_timeout_chain()) is True
    assert error_is_timeout(TimeoutError("x")) is True
    assert error_is_timeout(RuntimeError("HTTP 503")) is False


def test_two_stage_calls_skeleton_then_mount():
    skeleton = json.dumps({"nodes": [{"level": 1, "title": "运维服务"}, {"level": 2, "title": "巡检"}]}, ensure_ascii=False)
    mounts = json.dumps({"mounts": [{"node": "1.1", "refs": ["T-01", "T-02", "T-03"]}]}, ensure_ascii=False)
    model = FakeModel([skeleton, mounts])
    workflow = _workflow()
    plan = plan_technical_outline(workflow, model)
    assert workflow["outline_source"] == "model" and workflow["tree_model_failed"] is False
    assert len(model.calls) == 2  # 恰好两阶段
    assert "骨架" in model.calls[0][1] or "技术需求清单" in model.calls[0][1]
    assert "叶子" in model.calls[1][1]  # 阶段二给骨架编号
    assert plan["validation"]["unmounted_digest_refs"] == []


def test_mount_retry_fixes_missing_refs():
    skeleton = json.dumps({"nodes": [{"level": 1, "title": "运维服务"}, {"level": 2, "title": "巡检"}]}, ensure_ascii=False)
    partial = json.dumps({"mounts": [{"node": "1.1", "refs": ["T-01"]}]}, ensure_ascii=False)
    full = json.dumps({"mounts": [{"node": "1.1", "refs": ["T-01", "T-02", "T-03"]}]}, ensure_ascii=False)
    model = FakeModel([skeleton, partial, full])
    workflow = _workflow()
    plan = plan_technical_outline(workflow, model)
    assert workflow["outline_source"] == "model"
    assert len(model.calls) == 3  # 骨架1 + 挂载2次
    assert "未挂载编号" in model.calls[2][1]  # 反馈进入重试提示


def test_model_failure_no_silent_rule_fallback():
    workflow = _workflow()
    plan = plan_technical_outline(workflow, FakeModel([RuntimeError("boom")] * 3))
    assert workflow["tree_model_failed"] is True
    assert plan["headings"] == []  # 绝不塞通用规则目录冒充成功
    assert "重试" in workflow["outline_reason"]
    assert workflow["outline_model_error"]["stage"] == "skeleton"


def test_timeout_recorded_with_real_adapter_types():
    workflow = _workflow()
    plan_technical_outline(workflow, FakeModel([_timeout_chain()] * 3))
    err = workflow["outline_model_error"]
    assert err["timeout"] is True and err["stage"] == "skeleton"
    assert "超时" in workflow["outline_reason"]
    assert any("RetryableModelError" in item for item in err["chain"])


def test_missing_refs_go_to_unassigned_pool_not_fallback_chapter():
    skeleton = json.dumps({"nodes": [
        {"level": 1, "title": "运维服务"}, {"level": 2, "title": "巡检"}, {"level": 2, "title": "备份"}
    ]}, ensure_ascii=False)
    mounts = json.dumps({"mounts": [{"node": "1.1", "refs": ["T-01", "T-02"]}]}, ensure_ascii=False)
    workflow = _workflow()
    # 3 条漏 1 条=33% 漏挂比例；MIN_MOUNT_RATIO 0.6 → 2/3=66% 接受，残余进池
    plan = plan_technical_outline(workflow, FakeModel([skeleton, mounts, mounts, mounts]))
    titles = [h["title"] for h in plan["headings"]]
    assert "其他服务承诺" not in titles
    assert plan["validation"]["unmounted_digest_refs"] == ["T-03"]


def test_no_nine_per_chapter_truncation():
    workflow = _workflow(n_tech=15)
    skeleton = json.dumps({"nodes": [{"level": 1, "title": "运维服务"}, {"level": 2, "title": "巡检"}]}, ensure_ascii=False)
    refs = [f"T-{i:02d}" for i in range(1, 16)]
    mounts = json.dumps({"mounts": [{"node": "1.1", "refs": refs}]}, ensure_ascii=False)
    plan = plan_technical_outline(workflow, FakeModel([skeleton, mounts]))
    leaf = next(h for h in plan["headings"] if h.get("points"))
    assert len(leaf["points"]) == 15  # 全部挂载，无 9 条截断


def test_no_model_falls_back_to_rule_draft():
    workflow = _workflow()
    plan = plan_technical_outline(workflow, model=None)
    assert plan["headings"]  # 无模型时规则草稿仍可用（解析期编排）
    assert workflow.get("tree_model_failed") is not True


def test_repair_json_payload_recovers_truncated_mounts_without_inventing_refs():
    from icg.domain.technical_digest_outline import repair_json_payload

    raw = '{"mounts":[{"node":"1.1","refs":["T-01","S-01-1"]},{"node":"1.2","refs":["T-02"]},{"node":"1.1","refs":["T-01'
    payload = repair_json_payload(raw)
    refs = [ref for entry in payload.get("mounts", []) for ref in entry.get("refs", [])]
    assert payload.get("mounts")
    assert "T-01" in refs and "S-01-1" in refs and "T-02" in refs
    assert all(ref.startswith(("T-", "S-")) for ref in refs)


def test_scoring_weighted_candidate_wins_and_missing_refs_are_merged_from_model_attempts():
    from icg.domain.technical_digest_outline import _merge_missing_mounts, _mount_score

    weights = {"T-01": 1.0, "T-02": 1.0, "S-60": 13.0}
    broad = {"1.1": ["T-01", "T-02"]}
    scoring = {"1.2": ["T-01", "S-60"]}
    assert _mount_score(scoring, weights) > _mount_score(broad, weights)
    merged = _merge_missing_mounts(scoring, [scoring, broad], ["T-01", "T-02", "S-60"])
    assert merged["1.2"] == ["T-01", "S-60"]
    assert merged["1.1"] == ["T-02"]


def test_mount_quality_penalizes_concentrated_high_score_dump():
    from icg.domain.technical_digest_outline import _mount_quality

    weights = {"T-01": 1.0, "T-02": 1.0, "S-60": 13.0}
    concentrated = {"1.1": ["T-01", "T-02", "S-60"]}
    balanced = {"1.1": ["T-01"], "1.2": ["T-02", "S-60"]}
    assert _mount_quality(balanced, weights) > _mount_quality(concentrated, weights)


def test_scoring_group_ref_expands_to_point_refs_before_dedup():
    from icg.domain.technical_digest_outline import _expand_refs

    index = {"S-01": ["r1", "r2"], "S-01-1": ["r1"], "S-01-2": ["r2"], "T-01": ["r3"]}
    assert _expand_refs(["S-01", "T-01"], index) == ["S-01-1", "S-01-2", "T-01"]


def test_empty_leaves_and_empty_parents_are_pruned_and_renumbered():
    from icg.domain.technical_digest_outline import prune_empty_skeleton

    skeleton = [
        {"level": 1, "title": "运维", "number": "1", "leaf": False},
        {"level": 2, "title": "巡检", "number": "1.1", "leaf": True},
        {"level": 2, "title": "空节", "number": "1.2", "leaf": True},
        {"level": 1, "title": "空章", "number": "2", "leaf": True},
    ]
    pruned, remapped = prune_empty_skeleton(skeleton, {"1.1": ["T-01"], "1.2": []})
    assert [(node["number"], node["title"], node["leaf"]) for node in pruned] == [("1", "运维", False), ("1.1", "巡检", True)]
    assert remapped == {"1.1": ["T-01"]}


def test_merged_mounts_reject_concentration_and_choose_balanced_candidate():
    from icg.domain.technical_digest_outline import _select_merged_mounts

    expected = ["T-01", "T-02", "T-03", "T-04"]
    weights = {ref: 1.0 for ref in expected}
    concentrated = {"1.1": ["T-01", "T-02", "T-03"]}
    balanced = {"1.2": ["T-01", "T-02"], "1.3": ["T-03"]}
    merged = _select_merged_mounts([concentrated, balanced], expected, weights, leaf_count=3)
    assert merged == {"1.2": ["T-01", "T-02"], "1.3": ["T-03"]}


def test_end_to_end_empty_leaf_is_not_written_as_generation_task():
    skeleton = json.dumps({"nodes": [
        {"level": 1, "title": "运维服务"}, {"level": 2, "title": "巡检"}, {"level": 2, "title": "空章节"}
    ]}, ensure_ascii=False)
    mounts = json.dumps({"mounts": [{"node": "1.1", "refs": ["T-01", "T-02", "T-03"]}]}, ensure_ascii=False)
    workflow = _workflow()
    plan = plan_technical_outline(workflow, FakeModel([skeleton, mounts]))
    titles = [node["title"] for node in plan["headings"]]
    assert "空章节" not in titles
    assert len(plan["tasks"]) == 1
    assert all(task["requirement_ids"] for task in plan["tasks"])


def test_missing_ref_merge_uses_alternative_positions_under_leaf_capacity():
    from icg.domain.technical_digest_outline import _merge_missing_mounts

    expected = [f"T-{index:02d}" for index in range(1, 7)]
    weights = {ref: 1.0 for ref in expected}
    base = {"1.1": ["T-01", "T-02"]}
    # 三组候选都提供模型位置；若只取第一个位置，T-03/T-04 都会挤进 1.1 并超过容量 3。
    candidates = [
        base,
        {"1.1": ["T-01", "T-02", "T-03", "T-04"]},
        {"1.1": ["T-01", "T-02", "T-03", "T-04"], "1.2": ["T-04"], "1.3": ["T-03"]},
    ]
    merged = _merge_missing_mounts(base, candidates, expected, weights, max_leaf_count=3)
    mounted = sorted({ref for refs in merged.values() for ref in refs})
    assert mounted == expected[:4]
    assert max(len(refs) for refs in merged.values()) <= 3
    assert any(ref in merged.get("1.2", []) or ref in merged.get("1.3", []) for ref in ("T-03", "T-04"))


def test_unmergeable_missing_refs_keep_valid_base_instead_of_failing():
    from icg.domain.technical_digest_outline import _merge_missing_mounts, _select_merged_mounts

    expected = [f"T-{index:02d}" for index in range(1, 9)]
    weights = {ref: 1.0 for ref in expected}
    base = {"1.1": ["T-01", "T-02", "T-03", "T-04"], "1.2": ["T-05", "T-06"]}
    candidates = [
        base,
        {"1.1": ["T-01", "T-02", "T-03", "T-04", "T-07"], "1.2": ["T-05", "T-06"]},
        {"1.1": ["T-01", "T-02", "T-03", "T-04", "T-08"], "1.2": ["T-05", "T-06"]},
    ]
    merged = _merge_missing_mounts(base, candidates, expected, weights, max_leaf_count=4)
    assert merged == base  # T-07/T-08 留在未挂载池，不把 1.1 推到 5 条
    selected = _select_merged_mounts(candidates, expected, weights, leaf_count=3)
    assert selected == base  # 合格的基底候选保守保留，不直接判生成失败
    assert max(len(refs) for refs in selected.values()) <= 4
    assert len({ref for refs in selected.values() for ref in refs}) == 6


def test_time_specification_prefix_is_not_stripped_as_outline_number():
    from icg.domain.technical_digest_outline import _clean_title

    assert _clean_title("7×24小时响应机制") == "7×24小时响应机制"
    assert _clean_title("7x24小时响应机制") == "7x24小时响应机制"
    assert _clean_title("5×8小时现场服务") == "5×8小时现场服务"
    assert _clean_title("1.2 运维响应机制") == "运维响应机制"
