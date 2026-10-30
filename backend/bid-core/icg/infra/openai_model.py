# 为什么有这个文件：把公司内网的 OpenAI 兼容对话接口接到现有模型替换口。
# 它解决什么问题：需要真实建议时才显式启用；失败必须暴露，不能改回演示成功文本。
# 逐字流式（APP-M2-T177）：stream_suggest 边收边把增量文字交给回调，可随时取消（用户点“停止”或断开连接）；
# 已经收到文字后再失败不重试，避免同一写法前后两段内容拼在一起。内网接口一律不读取系统代理（trust_env=False）。

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
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
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
        return self.base_url + "/v1/chat/completions"


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
        return _assistant_text(response)

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
                        if isinstance(piece, str) and piece:
                            collected.append(piece)
                            on_delta(piece)
        except httpx.TimeoutException:
            raise RetryableModelError("timeout") from None
        except httpx.TransportError:
            raise RetryableModelError("transport") from None
        text = "".join(collected)
        if not text.strip():
            raise ModelCallError("missing assistant content")
        return text


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
