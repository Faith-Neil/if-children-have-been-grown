# 为什么有这个文件：让项目写入和旧章节提交共用同一套重复请求规则。
# 它解决什么问题：同一次操作的重试返回第一次的成功结果，失败和过期标记可以再次使用，内存不会无限增长。

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from typing import Any

from .domain import DemoState, DomainError, content_hash

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60
MAX_IDEMPOTENCY_RECEIPTS = 2048
KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,120}$")
IDEMPOTENCY_HEADER_DESCRIPTION = (
    "同一次用户动作的重复请求标记，格式为 [A-Za-z0-9_-]{8,120}，UUID 符合该格式。"
    "作用域是 scope_id + user_id + key：项目写入的 scope_id 为 project_id，"
    "公司资料和公司服务承诺模板为 library:{company_id}。"
    "指纹是 action、规范化 payload 和 If-Match。同键同指纹重放首次成功结果，"
    "响应头 Idempotent-Replayed 为 true；同键不同指纹返回 409 IDEMPOTENCY_CONFLICT；"
    "缺失或格式不符返回 428 IDEMPOTENCY_KEY_REQUIRED。失败不登记回执，可用同键重试。"
    f"回执保留 {IDEMPOTENCY_TTL_SECONDS // 3600} 小时，内存最多 {MAX_IDEMPOTENCY_RECEIPTS} 条，"
    "超出时删除最旧回执。客户端只对网络错误、502、503 复用本标记重试。"
)

_request: ContextVar[Any] = ContextVar("idempotency_request", default=None)


def bind_request(request: Any):
    return _request.set(request)


def reset_request(token) -> None:
    _request.reset(token)


def replayed_for(request: Any) -> bool:
    return bool(getattr(request.state, "idempotent_replayed", False))


def mark_replayed() -> None:
    request = _request.get()
    if request is not None:
        request.state.idempotent_replayed = True


def validate_key(key: str | None) -> str:
    if key is None or KEY_PATTERN.fullmatch(key) is None:
        raise DomainError(428, "IDEMPOTENCY_KEY_REQUIRED", "此操作需要有效的重复请求标记。")
    return key


def fingerprint(action: str, payload: dict, expected: str | None) -> str:
    normalized = expected.strip().strip('"') if expected is not None else None
    return content_hash(json.dumps({"action": action, "payload": payload, "if_match": normalized},
                                   sort_keys=True, ensure_ascii=False))


def _receipt_key(scope_id: str, user_id: str, key: str) -> tuple[str, str, str]:
    return (scope_id, user_id, key)


def _expired(receipt: dict, now: float) -> bool:
    created = receipt.get("created_at")
    return not isinstance(created, (int, float)) or now - float(created) >= IDEMPOTENCY_TTL_SECONDS


def _failed_outcome(result: Any) -> bool:
    job = result.get("job") if isinstance(result, dict) else None
    return isinstance(job, dict) and job.get("status") == "failed"


def enforce_bounds(state: DemoState, now: float) -> None:
    receipts = state.workflow_receipts
    expired = [key for key, receipt in receipts.items() if _expired(receipt, now)]
    for key in expired:
        del receipts[key]
    overflow = len(receipts) - MAX_IDEMPOTENCY_RECEIPTS
    if overflow <= 0:
        return
    oldest = sorted(receipts, key=lambda key: (float(receipts[key].get("created_at", 0)), str(key)))
    for key in oldest[:overflow]:
        del receipts[key]


def lookup(state: DemoState, scope_id: str, user_id: str, key: str, request_fingerprint: str, now: float):
    enforce_bounds(state, now)
    receipt_key = _receipt_key(scope_id, user_id, key)
    receipt = state.workflow_receipts.get(receipt_key)
    if receipt is None or _expired(receipt, now) or _failed_outcome(receipt.get("result")):
        if receipt is not None:
            state.workflow_receipts.pop(receipt_key, None)
        return None
    if receipt["fingerprint"] != request_fingerprint:
        raise DomainError(409, "IDEMPOTENCY_CONFLICT", "重复请求标记已用于其他操作或内容。")
    mark_replayed()
    return receipt["result"]


def remember(state: DemoState, scope_id: str, user_id: str, key: str, request_fingerprint: str,
             result: dict, now: float) -> None:
    if _failed_outcome(result):
        return
    state.workflow_receipts[_receipt_key(scope_id, user_id, key)] = {
        "fingerprint": request_fingerprint, "result": result, "created_at": now}
    enforce_bounds(state, now)


def resolve_legacy_key(body_key: str, header_key: str | None) -> str:
    # 旧章节提交仍接受正文标记，因为现有测试和演示页发送该字段。头如果同时出现，必须一致。
    resolved = validate_key(body_key)
    if header_key is not None:
        header = validate_key(header_key)
        if header != resolved:
            raise DomainError(409, "IDEMPOTENCY_CONFLICT", "请求头与正文的重复请求标记不一致。")
    return resolved
