# 为什么有这个文件：账号与公司安全事件的审计记录（PRD v1.8 §5.12.1 规则 4、§7.3 第 1、14 条；APP-M2-T260）。
# 它解决什么问题：登录、登录失败、锁定、解锁、改密、重置、角色调整、停用转交、注销、公司停用启用原先写进章节审计列表且没有事件编号，
# MySQL 只持久化带编号的章节审计，这些事件重启即丢；现在单独存入 DemoState.security_audit，按事件编号逐条持久化。

from __future__ import annotations

import time
from typing import Any

from .domain import iso_time, new_id


def record(state: Any, action: str, *, operator: str, **fields: Any) -> dict:
    """在当前事务里追加一条安全事件。operator 为执行人账号，系统自动动作写 system。"""
    now = time.time()
    event = {"id": new_id("sec"), "action": action, "operator": operator,
             "timestamp": now, "at": iso_time(now), **fields}
    state.security_audit[event["id"]] = event
    return event


def events(state: Any, action: str | None = None) -> list[dict]:
    """按时间先后列出安全事件，可按动作过滤。"""
    items = sorted(state.security_audit.values(), key=lambda e: e.get("timestamp", 0))
    return [e for e in items if action is None or e.get("action") == action]
