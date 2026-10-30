# 为什么有这个文件：把公司内网的 OpenAI 兼容对话接口接到现有模型替换口。
# 它解决什么问题：需要真实建议时才显式启用；失败必须暴露，不能改回演示成功文本。
# 逐字流式（APP-M2-T177）：stream_suggest 边收边把增量文字交给回调，可随时取消（用户点“停止”或断开连接）；
# 已经收到文字后再失败不重试，避免同一写法前后两段内容拼在一起。内网接口一律不读取系统代理（trust_env=False）。
# 兼容实测到的 RAGFlow 行为：上游限流时仍返回 HTTP 200，普通模式正文是“**ERROR**: Error 429 …”，流式模式只有一个空的结束块；
# 部分块带的是“到目前为止的全文”而不是增量，或同一块连发两次。前两种按上游失败处理（限流可改用备用模型），
# 全文块只取新增部分，双发块只算一次。

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import httpx


class ModelCallError(Exception):
    """真实模型调用失败。业务层把它映射为 502 MODEL_UNAVAILABLE，不生成替代正文。"""


class RetryableModelError(ModelCallError):
    """超时、连接失败或暂时性 HTTP 状态。耗尽重试后仍按失败处理。"""


class ModelCancelled(ModelCallError):
    """用户停止生成或断开连接：不重试、不改用备用模型、不保存结果。"""


_ENV_NAMES = {
    "provider": "ICG_MODEL_PROVIDER",
    "base_url": "ICG_MODEL_BASE_URL",
    "model": "ICG_MODEL_NAME",
    "api_key_env": "ICG_MODEL_API_KEY_ENV",
    "timeout": "ICG_MODEL_TIMEOUT_SECONDS",
    "max_tokens": "ICG_MODEL_MAX_TOKENS",
    "retries": "ICG_MODEL_RETRIES",
    "is_local": "ICG_MODEL_IS_LOCAL",
}
_DEFAULT_API_KEY_ENV = "ICG_MODEL_API_KEY"
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}  # 52x：Cloudflare 隧道源站超时或断开
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _required(environ: Mapping[str, str], key: str) -> str:
    value = environ.get(_ENV_NAMES[key], "").strip()
    if not value:
        raise ValueError(f"{_ENV_NAMES[key]} is required when ICG_MODEL_PROVIDER=openai-compatible")
    return value


def _bounded_int(raw: str, name: str, low: int, high: int) -> int:
    try:
        value = int(raw, 10)
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None
    if value < low or value > high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def _bounded_float(raw: str, name: str, low: float, high: float) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number") from None
    if value <= low or value > high:
        raise ValueError(f"{name} must be greater than {low} and at most {high}")
    return value


def _parse_local(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"{_ENV_NAMES['is_local']} must be true or false")


def _validate_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError(f"{_ENV_NAMES['base_url']} must be an absolute http(s) origin without credentials, query, or fragment")
    return base_url.strip().rstrip("/")


def chat_completions_url(base_url: str) -> str:
    """模型地址 → 对话接口地址。支持三种常见填法：只填服务根地址（补 /v1/chat/completions）；
    填到 /v1 或 RAGFlow 对话助手的 /api/v1/openai/{助手 ID}（补 /chat/completions）；已填完整接口地址（原样使用）。"""
    base = base_url.rstrip("/")
    path = urlsplit(base).path
    if path.endswith("/chat/completions"):
        return base
    if re.search(r"/v\d+$", path) or re.search(r"/openai/[^/]+$", path):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    base_url: str
    model: str
    api_key_env: str = ""
    timeout_seconds: float = 60.0
    max_tokens: int = 1024
    retries: int = 1
    is_local: bool = True
    stream_enabled: bool = False
    json_mode_enabled: bool = False
    api_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _validate_base_url(self.base_url))
        if not self.model.strip():
            raise ValueError(f"{_ENV_NAMES['model']} is required")
        object.__setattr__(self, "model", self.model.strip())
        if self.api_key_env and not _ENV_NAME.fullmatch(self.api_key_env):
            raise ValueError(f"{_ENV_NAMES['api_key_env']} must name an environment variable")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 600:
            raise ValueError(f"{_ENV_NAMES['timeout']} must be greater than 0 and at most 600")
        if self.max_tokens < 1 or self.max_tokens > 1_000_000:
            raise ValueError(f"{_ENV_NAMES['max_tokens']} must be between 1 and 1000000")
        if self.retries < 0 or self.retries > 5:
            raise ValueError(f"{_ENV_NAMES['retries']} must be between 0 and 5")
        if not isinstance(self.is_local, bool):
            raise ValueError(f"{_ENV_NAMES['is_local']} must be true or false")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> OpenAICompatibleConfig:
        source = os.environ if environ is None else environ
        timeout = source.get(_ENV_NAMES["timeout"], "").strip() or "60"
        max_tokens = source.get(_ENV_NAMES["max_tokens"], "").strip() or "1024"
        retries = source.get(_ENV_NAMES["retries"], "").strip() or "1"
        api_key_env = source.get(_ENV_NAMES["api_key_env"], "").strip() or _DEFAULT_API_KEY_ENV
        return cls(
            base_url=_required(source, "base_url"),
            model=_required(source, "model"),
            api_key_env=api_key_env,
            timeout_seconds=_bounded_float(timeout, _ENV_NAMES["timeout"], 0, 600),
            max_tokens=_bounded_int(max_tokens, _ENV_NAMES["max_tokens"], 1, 1_000_000),
            retries=_bounded_int(retries, _ENV_NAMES["retries"], 0, 5),
            is_local=_parse_local(_required(source, "is_local")),
            stream_enabled=False,
            json_mode_enabled=False,
        )

    @property
    def chat_completions_url(self) -> str:
        return chat_completions_url(self.base_url)


class OpenAICompatibleModelProvider:
    """OpenAI 兼容 chat completions。支持从环境变量或配置快照动态组装请求参数。"""

    name = "openai-compatible"
    is_real_model = True

    def __init__(self, config: OpenAICompatibleConfig, *, transport: httpx.BaseTransport | None = None,
                 environ: Mapping[str, str] | None = None):
        self._config = config
        self.is_local = config.is_local
        self.stream_enabled = config.stream_enabled
        self.json_mode_enabled = config.json_mode_enabled
        self.model = config.model
        self.base_url = config.base_url
        self.timeout_seconds = config.timeout_seconds
        self.max_tokens = config.max_tokens
        self._transport = transport
        self._environ = environ

    def suggest(self, instruction: str, content: str) -> str:
        if not isinstance(instruction, str) or not isinstance(content, str):
            raise ModelCallError("instruction and content must be strings")
        attempts = self._config.retries + 1
        last_error: ModelCallError | None = None
        for _ in range(attempts):
            try:
                return self._once(instruction, content)
            except RetryableModelError as error:
                last_error = error
        raise ModelCallError("openai-compatible model call failed") from last_error

    def _api_key(self) -> str:
        if self._config.api_key is not None:
            return self._config.api_key
        source = os.environ if self._environ is None else self._environ
        return source.get(self._config.api_key_env, "").strip() if self._config.api_key_env else ""

    def _once(self, instruction: str, content: str) -> str:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": content},
            ],
            "max_tokens": self._config.max_tokens,
            "stream": self._config.stream_enabled,
        }
        if self._config.json_mode_enabled:
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(transport=self._transport, timeout=self._config.timeout_seconds,
                              follow_redirects=False, trust_env=False) as client:
                response = client.post(self._config.chat_completions_url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise RetryableModelError("timeout") from None
        except httpx.TransportError:
            raise RetryableModelError("transport") from None
        if response.status_code in _RETRYABLE_STATUS:
            raise RetryableModelError(f"HTTP {response.status_code}")
        if response.status_code != 200:
            raise ModelCallError(f"HTTP {response.status_code}")
        text = _assistant_text(response)
        raise_upstream_error(text)
        return text

    def stream_suggest(self, instruction: str, content: str, *, on_delta: Callable[[str], None],
                       cancel: Any = None) -> str:
        """流式调用：每收到一段文字就交给 on_delta；cancel（threading.Event）置位即停止并抛 ModelCancelled。
        接口不支持流式时（返回普通 JSON）整段交给 on_delta 一次。"""
        attempts = self._config.retries + 1
        last_error: ModelCallError | None = None
        for _ in range(attempts):
            emitted = [False]

            def relay(text: str) -> None:
                emitted[0] = True
                on_delta(text)
            try:
                return self._stream_once(instruction, content, relay, cancel)
            except RetryableModelError as error:
                if emitted[0]:
                    raise ModelCallError("openai-compatible stream broke after partial output") from error
                last_error = error
        raise ModelCallError("openai-compatible model call failed") from last_error

    def _stream_once(self, instruction: str, content: str, on_delta: Callable[[str], None], cancel: Any) -> str:
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        api_key = self._api_key()
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [{"role": "system", "content": instruction}, {"role": "user", "content": content}],
            "max_tokens": self._config.max_tokens, "stream": True,
        }
        collected: list[str] = []
        pending_error: list[str] = []
        last_raw, skipped_last, doubled = [None], [False], [False]
        try:
            with httpx.Client(transport=self._transport, timeout=self._config.timeout_seconds,
                              follow_redirects=False, trust_env=False) as client:
                with client.stream("POST", self._config.chat_completions_url, headers=headers, json=payload) as response:
                    if response.status_code in _RETRYABLE_STATUS:
                        raise RetryableModelError(f"HTTP {response.status_code}")
                    if response.status_code != 200:
                        raise ModelCallError(f"HTTP {response.status_code}")
                    if "text/event-stream" not in response.headers.get("content-type", ""):
                        response.read()
                        text = _assistant_text(response)
                        raise_upstream_error(text)
                        on_delta(text)
                        return text
                    for line in response.iter_lines():
                        if cancel is not None and cancel.is_set():
                            raise ModelCancelled("cancelled")
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except ValueError:
                            continue
                        choices = chunk.get("choices") if isinstance(chunk, dict) else None
                        if not (isinstance(choices, list) and choices and isinstance(choices[0], dict)):
                            continue
                        piece = (choices[0].get("delta") or {}).get("content")
                        if not isinstance(piece, str) or not piece:
                            continue
                        # 实测 RAGFlow 转发 Gemini 时每块连发两次：头一次出现较长（≥4 字）的连续重复块即认定为“双发”流，
                        # 之后与上一块相同的块只算一次；短块（如“哈”）连续出现可能是正文，判定前不丢
                        if piece == last_raw[0] and not skipped_last[0] and (doubled[0] or len(piece) >= 4):
                            doubled[0], skipped_last[0] = True, True
                            continue
                        last_raw[0], skipped_last[0] = piece, False
                        so_far = "".join(collected)
                        if so_far and len(piece) > len(so_far) and piece.startswith(so_far):
                            piece = piece[len(so_far):]  # 本块是到目前为止的全文，只取新增部分
                        if not so_far:
                            # 开头可能是夹带的上游错误“**ERROR**: …”：能对上这个前缀就先攒着不推给页面，
                            # 整段都是错误时在流结束后按失败处理；一旦对不上就当正文照常推送
                            candidate = "".join(pending_error) + piece
                            head = candidate.lstrip()
                            if head.startswith(_ERROR_MARK) or (head and _ERROR_MARK.startswith(head)):
                                pending_error[:] = [candidate]
                                continue
                            pending_error.clear()
                            piece = candidate
                        collected.append(piece)
                        on_delta(piece)
        except httpx.TimeoutException:
            raise RetryableModelError("timeout") from None
        except httpx.TransportError:
            raise RetryableModelError("transport") from None
        if pending_error:
            text = "".join(pending_error)
            raise_upstream_error(text)  # 以“**ERROR**”开头必然抛出；只差前缀的短文本（如“**”）当正文
            on_delta(text)
            return text
        text = "".join(collected)
        if not text.strip():
            # 实测：上游限流时 RAGFlow 流式只回一个空的结束块；按上游暂时不可用处理，可改用备用模型
            raise RetryableModelError("empty stream")
        return text


_ERROR_MARK = "**ERROR**"
_UPSTREAM_ERROR = re.compile(r"^\s*\*\*ERROR\*\*\s*:?(.*)", re.S)


def raise_upstream_error(text: str) -> None:
    """HTTP 200 里夹带的上游错误：限流与 5xx 归为可降级失败，其他报错直接失败；不能当作模型正文。"""
    match = _UPSTREAM_ERROR.match(text or "")
    if not match:
        return
    detail = match.group(1).strip()
    code = re.search(r"\b(429|5\d\d)\b", detail)
    if code or re.search(r"quota|rate.?limit|overloaded|unavailable|timeout", detail, re.I):
        raise RetryableModelError(f"HTTP {code.group(1)}" if code else "upstream unavailable")
    raise ModelCallError("upstream error")


def _assistant_text(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "")
    raw_text = response.text
    if "text/event-stream" in content_type or raw_text.startswith("data:"):
        collected = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or not line.startswith("data:"):
                continue
            chunk_str = line[5:].strip()
            if chunk_str == "[DONE]":
                break
            try:
                chunk = json.loads(chunk_str)
                choices = chunk.get("choices")
                if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content and isinstance(content, str):
                        collected.append(content)
            except Exception:
                continue
        if collected:
            return "".join(collected)
    try:
        body = response.json()
    except ValueError:
        raise ModelCallError("malformed JSON") from None
    if not isinstance(body, dict):
        raise ModelCallError("malformed JSON")
    if "choices" not in body and body.get("code") not in (None, 0) and isinstance(body.get("message"), str):
        # RAGFlow 的错误包（HTTP 200 + {"code":…, "message":…}），如模型名不存在：属配置错误，不降级
        raise ModelCallError(f"upstream error {body['code']}: {body['message'][:200]}")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ModelCallError("missing assistant content")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ModelCallError("missing assistant content")
    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise ModelCallError("missing assistant content")
    return text


def openai_provider_from_environment(environ: Mapping[str, str] | None = None,
                                     transport: httpx.BaseTransport | None = None) -> OpenAICompatibleModelProvider | None:
    """仅在 ICG_MODEL_PROVIDER=openai-compatible 时构造真实适配器。未设置或 demo 返回 None，由调用方保留演示实现。"""
    source = os.environ if environ is None else environ
    selector = source.get(_ENV_NAMES["provider"], "").strip().lower()
    if selector in {"", "demo"}:
        return None
    if selector != "openai-compatible":
        raise ValueError(f"{_ENV_NAMES['provider']} must be demo or openai-compatible")
    return OpenAICompatibleModelProvider(OpenAICompatibleConfig.from_env(source), transport=transport, environ=source)
