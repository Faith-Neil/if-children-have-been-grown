# 为什么有这个文件：技术卷按节生成的固定阶段机（PR-C）。
# 它解决什么问题：审计与用户能区分「在判偏离」与「在写正文」；偏离后必须进入挂接正文或明确失败。

from __future__ import annotations

ORDER = ("retrieve", "deviate", "write_section")

STAGE_LABELS = {
    "retrieve": "检索",
    "deviate": "判偏离",
    "write_section": "写正文",
}

# 取消后不重放半节：整节重新走 retrieve→deviate→write_section。
STAGE_CANCEL_RESUME = (
    "取消只停在当前阶段，不写入该节正文；恢复须对本节重新点生成，从 retrieve 起完整重跑。"
)


def advance_section_stage(current: str | None) -> str | None:
    """返回下一阶段；write_section 之后返回 None。"""
    if current is None:
        return ORDER[0]
    if current not in ORDER:
        raise ValueError(f"unknown section stage: {current}")
    index = ORDER.index(current)
    if index + 1 >= len(ORDER):
        return None
    return ORDER[index + 1]


def forbid_silent_deviate_only(outcome: str, *, reason: str | None = None) -> None:
    """偏离阶段结束后的出口只能是 write_section、done 或带原因的 failed。"""
    if outcome == "deviate":
        raise AssertionError("偏离结果写入后不得静默停在偏离阶段")
    if outcome in ("write_section", "done", "failed", "cancelled", "skipped"):
        if outcome == "failed" and not (reason or "").strip():
            raise AssertionError("偏离失败须写明原因")
        return
    raise AssertionError(f"未知的节编排出口：{outcome}")


def is_terminal_stage(stage: str) -> bool:
    return stage in {"done", "failed", "cancelled", "skipped"}


def stage_progress_message(tally: dict, *, stage: str | None = None, title: str | None = None) -> str:
    """会话顶栏进度：已完成 x/y，可选当前节与阶段。"""
    base = f"已完成 {int(tally.get('done') or 0)}/{int(tally.get('total') or 0)} 节"
    failed = int(tally.get("failed") or 0)
    if failed:
        base += f"，{failed} 节失败"
    if not stage:
        return base
    label = STAGE_LABELS.get(stage, stage)
    if title:
        return f"{base} · {label}「{title}」"
    return f"{base} · {label}"