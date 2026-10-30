# 为什么有这个文件：主模型失败时改用备用模型（PRD v1.8 §6.4 任务与模型表“备用”列、§6.5 路由与降级规则 2、3；
# 字典 llm_model.fallback_model_id；APP-M2-T177）。
# 它解决什么问题：
# 1. 只在健康类失败（超时、连接失败、5xx、限流 429）时降级；参数错误等 4xx 直接报错，不换模型掩盖问题；
# 2. 降级后告诉调用方实际用了哪个模型、为什么换，页面显示“已使用备用模型 X”，记录里存实际模型；
# 3. 已经流式输出了一部分再失败时，先通知调用方清空这一条的预览，再从备用模型重新输出；
# 4. 用户停止（ModelCancelled）不降级；备用模型是否合规（本地/敏感项目）由组装备用模型的一方事先核对。

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .openai_model import ModelCancelled, RetryableModelError


@dataclass(frozen=True)
class ModelCall:
    text: str
    model: str
    is_local: bool
    is_fallback: bool
    fallback_reason: str = ""


def model_name(provider: Any) -> str:
    return (getattr(provider, "display_name", "") or getattr(provider, "model", "") or getattr(provider, "name", "")
            or "模型")


def degradable(error: BaseException) -> bool:
    """健康类失败：本身或其原因是 RetryableModelError（重试耗尽后包成 ModelCallError）。"""
    if isinstance(error, ModelCancelled):
        return False
    return isinstance(error, RetryableModelError) or isinstance(error.__cause__, RetryableModelError)


def _reason(error: BaseException) -> str:
    cause = error.__cause__ if isinstance(error.__cause__, RetryableModelError) else error
    text = str(cause) or type(cause).__name__
    if text == "timeout":
        return "主模型超时"
    if text == "transport":
        return "主模型连接失败"
    if text.startswith("HTTP 429"):
        return "主模型限流"
    if text == "empty stream":
        return "主模型没有返回内容（多为额度用完或限流）"
    return f"主模型暂时不可用（{text}）"


def failure_text(error: BaseException) -> str:
    """写法失败时给用户看的原因：健康类失败说明是超时、连接、限流还是没返回内容，其他写明上游返回。"""
    if degradable(error):
        return _reason(error).replace("主模型", "模型")
    return str(error) or type(error).__name__


def call_model(provider: Any, system: str, user: str, *, on_delta: Callable[[str], None] | None = None,
               on_reset: Callable[[str, str], None] | None = None, cancel: Any = None) -> ModelCall:
    """调用主模型；健康类失败且配置了 provider.fallback 时改用备用模型。on_reset(备用模型名, 原因) 在切换时调用。"""
    chain = [provider]
    fallback = getattr(provider, "fallback", None)
    if fallback is not None:
        chain.append(fallback)
    reason = ""
    for index, current in enumerate(chain):
        streaming = on_delta is not None and callable(getattr(current, "stream_suggest", None)) \
            and bool(getattr(current, "stream_enabled", False))
        try:
            if streaming:
                text = current.stream_suggest(system, user, on_delta=on_delta, cancel=cancel)
            else:
                text = current.suggest(system, user)
                if cancel is not None and cancel.is_set():
                    raise ModelCancelled("cancelled")
        except Exception as error:
            if index + 1 < len(chain) and degradable(error):
                reason = _reason(error)
                if on_reset is not None:
                    on_reset(model_name(chain[index + 1]), reason)
                continue
            raise
        return ModelCall(text if isinstance(text, str) else str(text), model_name(current),
                         bool(getattr(current, "is_local", False)), index > 0, reason)
    raise RuntimeError("unreachable")
