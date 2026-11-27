# 为什么有这个文件：实现模型配置的数据存储、Fernet 密钥加密、掩码与 API 接口。
# 它解决什么问题：支持模型配置的多租户隔离、乐观锁、密钥安全存储与连通性测试，对敏感项目实施本地模型门禁。

from __future__ import annotations

import base64
import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field

from icg.domain.domain import DemoService, DemoState, DomainError, Principal, Project
from icg.domain.workflow_schemas import RequestBody, ResponseBody, v1_error_responses

ICG_SECRET_KEY_ENV = "ICG_SECRET_KEY"


def get_master_key() -> str:
    key = os.environ.get(ICG_SECRET_KEY_ENV, "").strip()
    if not key:
        raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥未配置或不可用。")
    return key


def _fernet_from_secret(secret: str) -> Fernet:
    if not secret:
        raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥未配置或不可用。")
    try:
        return Fernet(secret.encode("ascii"))
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        return Fernet(derived)


def mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}***{key[-4:]}"


def encrypt_api_key(plain: str | None, master_key: str | None = None) -> str | None:
    if not plain:
        return None
    secret = master_key if master_key is not None else get_master_key()
    fernet = _fernet_from_secret(secret)
    return fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_api_key(cipher: str | None, master_key: str | None = None) -> str:
    if not cipher:
        return ""
    secret = master_key if master_key is not None else get_master_key()
    fernet = _fernet_from_secret(secret)
    try:
        return fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception:
        raise DomainError(503, "SECRET_KEY_UNAVAILABLE", "主密钥解密失败或不可用。")


@dataclass
class ModelConfig:
    id: str
    company_id: str = "alpha"
    name: str = "默认模型配置"
    provider: str = "openai-compatible"
    base_url: str = "http://127.0.0.1:8000"
    model: str = "qwen2.5-72b"
    encrypted_api_key: str | None = None
    api_key_masked: str | None = None
    is_local: bool = True
    allow_sensitive: bool = True
    stream_enabled: bool = True
    json_mode_enabled: bool = False
    revision: int = 1
    timeout_seconds: float = 60.0
    max_tokens: int = 1024
    fallback_config_id: str | None = None  # 备用模型（PRD §6.4/§6.5）：本地主模型只能配本地备用

    @property
    def has_api_key(self) -> bool:
        return bool(self.encrypted_api_key)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "is_local": self.is_local,
            "allow_sensitive": self.allow_sensitive,
            "stream_enabled": self.stream_enabled,
            "json_mode_enabled": self.json_mode_enabled,
            "revision": self.revision,
            "has_api_key": self.has_api_key,
            "api_key_masked": self.api_key_masked,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "fallback_config_id": self.fallback_config_id,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "is_real_model": (self.provider != "demo"),
            "is_local": self.is_local,
            "allow_sensitive": self.allow_sensitive,
            "stream_enabled": self.stream_enabled,
            "json_mode_enabled": self.json_mode_enabled,
            "base_url": self.base_url,
            "revision": self.revision,
        }


def check_revision(actual: int, if_match: str | None) -> None:
    if if_match is None or not if_match.strip():
        raise DomainError(428, "IF_MATCH_REQUIRED", "此操作需要最新版本号，请刷新页面后再保存。")
    raw = if_match.strip().strip('"')
    if not raw.isdigit() or int(raw) != actual:
        raise DomainError(409, "REVISION_CONFLICT", "模型配置已被更新，请刷新核对后再保存。", {"current_revision": actual})


def fallback_problem(primary: ModelConfig, fallback: ModelConfig | None) -> str | None:
    """保存时核对备用模型（字典 llm_model.fallback_model_id）：同公司、不是自己、本地主模型只能配本地备用。"""
    if fallback is None or fallback.company_id != primary.company_id:
        return "备用模型不存在或不属于本公司。"
    if fallback.id == primary.id:
        return "备用模型不能是它自己。"
    if fallback.provider == "demo":
        return "备用模型必须是真实模型。"
    if primary.is_local and not fallback.is_local:
        return "本地主模型的备用只能是本地模型（不改走云端）。"
    return None


def config_compliant_for_sensitive(config: ModelConfig) -> bool:
    """涉密项目可用性核对（防御纵深）：本地 + 允许敏感 + 端点不是公网地址。

    is_local 只是管理员填写的标志，可能填错；只要实际 URL 是公网端点，
    涉密内容就绝不能发过去，与标志怎么填无关（ISSUE-059）。"""
    if not config.is_local or not config.allow_sensitive:
        return False
    if config.provider != "demo":
        from .openai_model import is_public_model_url
        if is_public_model_url(config.base_url):
            return False
    return True


def usable_fallback(state: Any, primary: ModelConfig, project_sensitive: bool) -> ModelConfig | None:
    """运行时取备用模型：再核对一次（备用模型可能事后被改成云端）；敏感项目只能用本地且允许敏感的备用。"""
    if not primary.fallback_config_id:
        return None
    fallback = state.model_configs.get(primary.fallback_config_id)
    if fallback_problem(primary, fallback) is not None:
        return None
    if project_sensitive and not config_compliant_for_sensitive(fallback):
        return None
    return fallback


def validate_model_config_for_project(project_sensitive: bool, config: ModelConfig) -> None:
    if project_sensitive and not config_compliant_for_sensitive(config):
        raise DomainError(403, "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL", "敏感项目只能使用本地模型配置。")


def provider_from_model_config(
    config: ModelConfig,
    *,
    transport: httpx.BaseTransport | None = None,
    master_key: str | None = None,
    default_provider: Any = None,
) -> Any:
    if config.provider == "demo":
        if default_provider is not None:
            return default_provider
        from .adapters import DemoModelProvider
        return DemoModelProvider()
    if config.provider == "openai-compatible":
        from .openai_model import OpenAICompatibleConfig, OpenAICompatibleModelProvider
        plain_key = ""
        if config.encrypted_api_key:
            plain_key = decrypt_api_key(config.encrypted_api_key, master_key=master_key)
        cfg = OpenAICompatibleConfig(
            base_url=config.base_url,
            model=config.model,
            api_key_env="",
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            retries=1,
            is_local=config.is_local,
            stream_enabled=config.stream_enabled,
            json_mode_enabled=config.json_mode_enabled,
            api_key=plain_key or None,
        )
        provider = OpenAICompatibleModelProvider(cfg, transport=transport)
        # 经 RAGFlow 对话助手时请求里的模型名只能是占位的 “model”，页面改显示配置名称
        provider.display_name = config.name if config.model.strip().lower() == "model" else config.model
        return provider
    raise DomainError(502, "MODEL_UNAVAILABLE", f"不支持的模型提供者: {config.provider}")


def provider_from_model_snapshot(
    snapshot: dict[str, Any],
    *,
    transport: httpx.BaseTransport | None = None,
    master_key: str | None = None,
    default_provider: Any = None,
) -> Any:
    provider_name = snapshot.get("provider", "demo")
    if provider_name == "demo" or not snapshot.get("is_real_model"):
        if default_provider is not None:
            return default_provider
        from .adapters import DemoModelProvider
        return DemoModelProvider()
    if provider_name == "openai-compatible":
        from .openai_model import OpenAICompatibleConfig, OpenAICompatibleModelProvider
        plain_key = ""
        encrypted_key = snapshot.get("encrypted_api_key")
        if encrypted_key:
            plain_key = decrypt_api_key(encrypted_key, master_key=master_key)
        cfg = OpenAICompatibleConfig(
            base_url=snapshot.get("base_url") or "http://127.0.0.1:8000",
            model=snapshot.get("model") or "qwen2.5-72b",
            api_key_env="",
            timeout_seconds=float(snapshot.get("timeout_seconds", 60.0)),
            max_tokens=int(snapshot.get("max_tokens", 1024)),
            retries=1,
            is_local=bool(snapshot.get("is_local", True)),
            stream_enabled=bool(snapshot.get("stream_enabled", True)),
            json_mode_enabled=bool(snapshot.get("json_mode_enabled", False)),
            api_key=plain_key or None,
        )
        return OpenAICompatibleModelProvider(cfg, transport=transport)
    raise DomainError(502, "MODEL_UNAVAILABLE", f"不支持的模型提供者: {provider_name}")


class ModelConfigResponse(ResponseBody):
    id: str
    name: str
    provider: str
    base_url: str
    model: str
    is_local: bool
    allow_sensitive: bool
    stream_enabled: bool = True
    json_mode_enabled: bool = False
    revision: int
    has_api_key: bool
    api_key_masked: str | None = None
    timeout_seconds: float = 60.0
    max_tokens: int = 1024
    fallback_config_id: str | None = Field(default=None, description="备用模型配置；主模型超时、连接失败、5xx 或限流时改用")


class ModelConfigListResponse(ResponseBody):
    items: list[ModelConfigResponse]


class ModelConfigCreateRequest(RequestBody):
    id: str | None = Field(default=None, max_length=120)
    company_id: str | None = Field(default=None, max_length=120, description="目标公司（仅平台管理员跨租户代管时显式指定，缺省为自身租户）")
    name: str = Field(default="默认模型配置", min_length=1, max_length=300)
    provider: str = Field(default="openai-compatible", min_length=1, max_length=100)
    base_url: str = Field(default="http://127.0.0.1:8000", min_length=1, max_length=500)
    model: str = Field(default="qwen2.5-72b", min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=1000)
    is_local: bool = True
    allow_sensitive: bool = True
    stream_enabled: bool = True
    json_mode_enabled: bool = False
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    max_tokens: int = Field(default=1024, ge=1, le=1_000_000)
    fallback_config_id: str | None = Field(default=None, max_length=120, description="备用模型配置 ID；本地主模型只能配本地备用")


class ModelConfigUpdateRequest(RequestBody):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    provider: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=1000)
    is_local: bool | None = None
    allow_sensitive: bool | None = None
    stream_enabled: bool | None = None
    json_mode_enabled: bool | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    max_tokens: int | None = Field(default=None, ge=1, le=1_000_000)
    fallback_config_id: str | None = Field(default=None, max_length=120, description="备用模型配置 ID；空字符串表示不配备用")


class ModelConfigTestResponse(ResponseBody):
    ok: bool
    provider: str
    model: str
    duration_ms: int = Field(ge=0)
    message: str = Field(default="", description="不通时的原因（HTTP 状态、上游错误、超时等）")


class ProjectModelConfigBindingRequest(RequestBody):
    model_config_id: str = Field(min_length=1, max_length=120)


class ProjectModelConfigBindingResponse(ResponseBody):
    project_id: str
    model_config_id: str


def validate_endpoint_url(url: str, *, field: str = "base_url") -> str:
    """SSRF 纵深防御：端点只允许 http/https 与合法主机，拒绝 userinfo 注入与空主机。"""
    from urllib.parse import urlsplit
    clean = str(url or "").strip().rstrip("/")
    if not clean or len(clean) > 500 or any(ch.isspace() for ch in clean):
        raise DomainError(422, "VALIDATION_ERROR", "端点地址为空、超长或含空白字符。", {"field": field})
    try:
        parts = urlsplit(clean)
    except ValueError:
        raise DomainError(422, "VALIDATION_ERROR", "端点地址不是合法 URL。", {"field": field}) from None
    if parts.scheme not in ("http", "https"):
        raise DomainError(422, "VALIDATION_ERROR", "端点只允许 http/https 协议。", {"field": field})
    if not parts.hostname:
        raise DomainError(422, "VALIDATION_ERROR", "端点缺少合法主机名。", {"field": field})
    if parts.username is not None or parts.password is not None:
        raise DomainError(422, "VALIDATION_ERROR", "端点不允许携带 userinfo 凭据。", {"field": field})
    return clean


def placeholder_default(config: ModelConfig) -> bool:
    """系统自动塞进公司的「默认内网模型」，不是管理员添加的配置。"""
    return (config.id == f"default-{config.company_id}" and config.name == "默认内网模型"
            and config.model == "qwen2.5-72b" and not config.encrypted_api_key)


def saved_company_model(state: Any, company_id: str) -> ModelConfig | None:
    """没有项目绑定、也没有任务对应表时，用管理员添加的模型。有本地模型时不用非本地的那一份。

    平台 system 兜底对全公司生效、公司管理员未必知情，绝不回落到公网端点：
    公网 URL 的平台配置不参与兜底（ISSUE-059 数据不出内网红线）。"""
    saved = [cfg for cfg in state.model_configs.values()
             if cfg.company_id == company_id and cfg.provider != "demo" and not placeholder_default(cfg)]
    if not saved and company_id != "system":
        from .openai_model import is_public_model_url
        saved = [cfg for cfg in state.model_configs.values()
                 if cfg.company_id == "system" and cfg.provider != "demo" and not placeholder_default(cfg)
                 and not is_public_model_url(cfg.base_url)]
    if not saved:
        return None
    local = [cfg for cfg in saved if cfg.is_local]
    pool = local or saved

    def added_at(cfg: ModelConfig) -> int:
        suffix = cfg.id.removeprefix("cfg-")
        return int(suffix) if suffix.isdigit() else 0

    return max(pool, key=added_at)


class ModelConfigService:
    def __init__(self, demo_service: DemoService):
        self.service = demo_service
        self.repository = demo_service.repository

    def list(self, principal: Principal) -> dict[str, Any]:
        self._require_manager(principal)
        company_id = principal.user.company_id

        def operation(state: DemoState):
            for config_id, cfg in list(state.model_configs.items()):
                if cfg.company_id == company_id and placeholder_default(cfg):
                    del state.model_configs[config_id]
            # 只有平台管理员能走到这里（见 _require_manager）：列出全部租户配置供统一代管
            items = [
                cfg.to_public_dict()
                for cfg in state.model_configs.values()
            ]
            return {"items": items}

        return self.repository.transaction(operation)

    def get(self, principal: Principal, config_id: str) -> dict[str, Any]:
        self._require_manager(principal)
        company_id = principal.user.company_id

        def operation(state: DemoState):
            cfg = state.model_configs.get(config_id)
            # 只有平台管理员能走到这里（见 _require_manager）：跨租户代管可读任一租户配置
            if cfg is None or placeholder_default(cfg):
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    @staticmethod
    def _require_manager(principal: Principal) -> None:
        """模型配置管理严格仅限平台管理员（ISSUE-059 PM 最终权限模型）。

        模型地址决定标书正文发往哪里，测试连接会让服务端访问填写的地址；
        公司管理员与普通成员一律 403，杜绝租户侧把正文外发或探测内网。"""
        from icg.domain.platform_security import require_platform_admin
        try:
            require_platform_admin(principal)
        except DomainError:
            raise DomainError(403, "FORBIDDEN", "模型配置只能由平台管理员新建、修改、轮换密钥和测试。") from None

    def create(self, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_manager(principal)
        # 平台管理员可跨租户代管：显式 company_id 指定目标公司，缺省为自身租户
        company_id = str(payload.get("company_id") or principal.user.company_id).strip()
        if not company_id or len(company_id) > 120 or any(ch.isspace() for ch in company_id):
            raise DomainError(422, "VALIDATION_ERROR", "目标公司标识非法。", {"field": "company_id"})
        config_id = payload.get("id") or f"cfg-{int(self.service._now() * 1000)}"
        plain_key = payload.get("api_key")

        # 密钥加密（若提供明文，需 ICG_SECRET_KEY 可用）
        encrypted_key = None
        masked_key = None
        if plain_key:
            encrypted_key = encrypt_api_key(plain_key)
            masked_key = mask_api_key(plain_key)

        def operation(state: DemoState):
            # CWE-639：模型 ID 全局唯一，任何租户已占用都拒绝，杜绝覆写其他租户配置
            if config_id in state.model_configs:
                raise DomainError(409, "REVISION_CONFLICT", "该模型配置已存在。")
            cfg = ModelConfig(
                id=config_id,
                company_id=company_id,
                name=payload.get("name", "默认模型配置"),
                provider=payload.get("provider", "openai-compatible"),
                base_url=validate_endpoint_url(payload.get("base_url", "http://127.0.0.1:8000")),
                model=payload.get("model", "qwen2.5-72b"),
                encrypted_api_key=encrypted_key,
                api_key_masked=masked_key,
                is_local=payload.get("is_local", True),
                allow_sensitive=payload.get("allow_sensitive", True),
                stream_enabled=payload.get("stream_enabled", True),
                json_mode_enabled=payload.get("json_mode_enabled", False),
                revision=1,
                timeout_seconds=payload.get("timeout_seconds", 60.0),
                max_tokens=payload.get("max_tokens", 1024),
                fallback_config_id=payload.get("fallback_config_id") or None,
            )
            if cfg.fallback_config_id:
                problem = fallback_problem(cfg, state.model_configs.get(cfg.fallback_config_id))
                if problem:
                    raise DomainError(422, "VALIDATION_ERROR", problem, {"field": "fallback_config_id"})
            state.model_configs[config_id] = cfg
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def update(self, principal: Principal, config_id: str, updates: dict[str, Any], if_match: str | None) -> dict[str, Any]:
        self._require_manager(principal)
        company_id = principal.user.company_id

        def operation(state: DemoState):
            cfg = state.model_configs.get(config_id)
            # 只有平台管理员能走到这里（见 _require_manager），允许跨租户代管但严禁改归属
            if cfg is None:
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")

            # 1. 乐观锁 If-Match 校验
            check_revision(cfg.revision, if_match)

            # 2. 密钥更新规则
            if "api_key" in updates and updates["api_key"] is not None:
                key_input = updates["api_key"]
                if key_input == "":
                    # 空字符串代表清除
                    cfg.encrypted_api_key = None
                    cfg.api_key_masked = None
                elif key_input == cfg.api_key_masked:
                    # 传回掩码代表不修改
                    pass
                else:
                    # 传入新明文密钥进行加密
                    cfg.encrypted_api_key = encrypt_api_key(key_input)
                    cfg.api_key_masked = mask_api_key(key_input)

            # 3. 更新其他配置字段
            if "company_id" in updates and updates["company_id"] not in (None, cfg.company_id):
                raise DomainError(422, "VALIDATION_ERROR", "不允许变更模型配置的租户归属。", {"field": "company_id"})
            for field_name in (
                "name", "provider", "base_url", "model", "is_local",
                "allow_sensitive", "stream_enabled", "json_mode_enabled",
                "timeout_seconds", "max_tokens",
            ):
                if field_name in updates and updates[field_name] is not None:
                    value = updates[field_name]
                    if field_name == "base_url":
                        value = validate_endpoint_url(value)
                    setattr(cfg, field_name, value)
            if "fallback_config_id" in updates and updates["fallback_config_id"] is not None:
                cfg.fallback_config_id = updates["fallback_config_id"] or None
            if cfg.fallback_config_id:
                problem = fallback_problem(cfg, state.model_configs.get(cfg.fallback_config_id))
                if problem:
                    raise DomainError(422, "VALIDATION_ERROR", problem, {"field": "fallback_config_id"})
            # 本配置是别的本地主模型的备用时，不能改成云端
            if not cfg.is_local and any(other.fallback_config_id == cfg.id and other.is_local
                                        for other in state.model_configs.values() if other.company_id == cfg.company_id):
                raise DomainError(422, "VALIDATION_ERROR", "这个配置是本地主模型的备用模型，不能改成非本地模型。",
                                  {"field": "is_local"})

            # 4. 递增 revision
            cfg.revision += 1
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def test_connectivity(self, principal: Principal, config_id: str,
                          transport: httpx.BaseTransport | None = None) -> dict[str, Any]:
        self._require_manager(principal)
        company_id = principal.user.company_id

        def get_cfg(state: DemoState) -> ModelConfig:
            cfg = state.model_configs.get(config_id)
            # 只有平台管理员能走到这里（见 _require_manager），允许跨租户代管
            if cfg is None:
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")
            return cfg

        cfg = self.repository.transaction(get_cfg)

        # 解密 API 密钥。如果未设置 ICG_SECRET_KEY 且存在加密密钥，此处抛出 503 SECRET_KEY_UNAVAILABLE
        plain_key = ""
        if cfg.encrypted_api_key:
            plain_key = decrypt_api_key(cfg.encrypted_api_key)

        start = time.time()
        ok = True

        if cfg.is_local:
            from .openai_model import is_public_model_url
            if is_public_model_url(cfg.base_url):
                return {
                    "ok": False,
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "duration_ms": 1,
                    "message": "本地部署已打开，公网地址不会连接，正文也不会发出去。",
                }

        if cfg.provider == "demo":
            duration_ms = max(1, int((time.time() - start) * 1000))
            return {
                "ok": True,
                "provider": "demo",
                "model": cfg.model,
                "duration_ms": duration_ms,
            }

        try:
            from .openai_model import chat_completions_url
            url = chat_completions_url(validate_endpoint_url(cfg.base_url))
            headers = {"Content-Type": "application/json"}
            if plain_key:
                headers["Authorization"] = f"Bearer {plain_key}"
            payload = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "stream": False,
            }
            # 云端模型首字常要十几秒（实测 RAGFlow 转发 8～30 秒），5 秒会把可用模型判成不通；上限 30 秒
            with httpx.Client(transport=transport, timeout=min(cfg.timeout_seconds, 30.0), trust_env=False) as client:
                resp = client.post(url, headers=headers, json=payload)
            message = ""
            if resp.status_code != 200:
                ok, message = False, f"HTTP {resp.status_code}"
            else:
                # HTTP 200 也可能是上游错误（RAGFlow 的“**ERROR**: …”正文或 {"code":…} 错误包），要看内容
                from .openai_model import ModelCallError, _assistant_text, raise_upstream_error
                try:
                    raise_upstream_error(_assistant_text(resp))
                    ok = True
                except ModelCallError as error:
                    ok, message = False, str(error.__cause__ or error)
        except Exception as error:
            ok, message = False, type(error).__name__

        duration_ms = max(1, int((time.time() - start) * 1000))
        return {
            "ok": ok,
            "provider": cfg.provider,
            "model": cfg.model,
            "duration_ms": duration_ms,
            "message": message,
        }

    def bind_project(self, principal: Principal, project_id: str, config_id: str) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            from icg.domain.auth_service import is_super_admin
            from icg.domain.project_access import lead, normalize_role
            project = state.projects.get(project_id)
            role = normalize_role(principal.user.role)
            platform = is_super_admin(principal) or role == "platform_admin"
            admin = (project is not None and not project.is_deleted
                     and (platform or (project.company_id == company_id and role == "company_admin")))
            if not admin:
                project = self.service._project(state, principal, project_id)
                if not lead(state, project_id, principal.user.id):
                    raise DomainError(403, "PROJECT_LEAD_REQUIRED", "只有项目负责人或公司管理员能为项目选择模型配置。")
            cfg = state.model_configs.get(config_id)
            # 可绑定池：本公司配置 + 平台 system 合规配置（平台管理员代管的统一合规模型）
            if cfg is None or cfg.company_id not in (company_id, "system"):
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")

            # 策略门禁：敏感项目尝试绑定非本地或未标记敏感可用的模型
            validate_model_config_for_project(project.sensitive, cfg)

            state.project_model_configs[project_id] = config_id
            return {"project_id": project_id, "model_config_id": config_id}

        return self.repository.transaction(operation)

    def list_bindable(self, principal: Principal, project_id: str) -> dict[str, Any]:
        """项目负责人/公司管理员绑模型时的只读可选列表（PM 独立授权；绝不暴露明文密钥）。"""
        company_id = principal.user.company_id

        def operation(state: DemoState):
            from icg.domain.auth_service import is_super_admin
            from icg.domain.project_access import lead, normalize_role
            project = state.projects.get(project_id)
            role = normalize_role(principal.user.role)
            platform = is_super_admin(principal) or role == "platform_admin"
            admin = (project is not None and not project.is_deleted
                     and (platform or (project.company_id == company_id and role == "company_admin")))
            if not admin:
                project = self.service._project(state, principal, project_id)
                if not lead(state, project_id, principal.user.id):
                    raise DomainError(403, "PROJECT_LEAD_REQUIRED", "只有项目负责人或公司管理员能为项目选择模型配置。")
            items = [
                cfg.to_public_dict()
                for cfg in state.model_configs.values()
                if cfg.company_id in (company_id, "system") and not placeholder_default(cfg)
            ]
            items.sort(key=lambda item: (0 if item["is_local"] else 1, item["id"]))
            return {"items": items}

        return self.repository.transaction(operation)

    def get_project_config(self, principal: Principal, project_id: str) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            self.service._project(state, principal, project_id)
            config_id = state.project_model_configs.get(project_id)
            if config_id and config_id in state.model_configs:
                return state.model_configs[config_id].to_public_dict()
            chosen = saved_company_model(state, company_id)
            if chosen is None:
                raise DomainError(404, "NOT_FOUND", "还没有可用的模型配置。请先添加模型。")
            return chosen.to_public_dict()

        return self.repository.transaction(operation)


def include_model_config_routes(application, service: DemoService, current_user) -> None:
    config_service = ModelConfigService(service)
    application.state.model_config_service = config_service
    router = APIRouter(prefix="/api/v1", responses=v1_error_responses(401, 403, 404, 409, 422, 428, 500, 503))

    @router.get("/model-configs", response_model=ModelConfigListResponse, operation_id="listModelConfigs")
    def list_model_configs(user: Principal = Depends(current_user)):
        """列出当前公司的模型配置。响应中绝不暴露明文密钥，只返回 api_key_masked 与 has_api_key。"""
        return config_service.list(user)

    @router.post("/model-configs", response_model=ModelConfigResponse, operation_id="createModelConfig")
    def create_model_config(body: ModelConfigCreateRequest, response: Response, user: Principal = Depends(current_user)):
        """新建模型配置。若提供 api_key，需环境变量 ICG_SECRET_KEY 可用以进行 Fernet 加密；若未配置则返回 503 SECRET_KEY_UNAVAILABLE。"""
        result = config_service.create(user, body.model_dump(exclude_unset=True))
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.get("/model-configs/{id}", response_model=ModelConfigResponse, operation_id="getModelConfig")
    def get_model_config(id: str, response: Response, user: Principal = Depends(current_user)):
        """获取单个模型配置详情。响应头 ETag 为当前 revision。"""
        result = config_service.get(user, id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.put("/model-configs/{id}", response_model=ModelConfigResponse, operation_id="updateModelConfig")
    def update_model_config(id: str, body: ModelConfigUpdateRequest, response: Response,
                            user: Principal = Depends(current_user),
                            if_match: str | None = Header(default=None)):
        """更新模型配置。需通过 If-Match 请求头核对 revision 进行乐观锁并发保护。省略 api_key 表示保留原密钥，空字符串表示清除，传回掩码表示不修改。若需要加密新密钥且 ICG_SECRET_KEY 未配置，返回 503 SECRET_KEY_UNAVAILABLE。"""
        result = config_service.update(user, id, body.model_dump(exclude_unset=True), if_match)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    @router.post("/model-configs/{id}/test", response_model=ModelConfigTestResponse, operation_id="testModelConfig")
    def test_model_config(id: str, user: Principal = Depends(current_user)):
        """测试模型配置连通性。返回 ok、provider、model 与 duration_ms。若配置包含加密密钥且 ICG_SECRET_KEY 不可用，返回 503 SECRET_KEY_UNAVAILABLE 且无 Retry-After。"""
        return config_service.test_connectivity(user, id)

    @router.post("/projects/{project_id}/model-config", response_model=ProjectModelConfigBindingResponse,
                 operation_id="bindProjectModelConfig")
    def bind_project_model_config(project_id: str, body: ProjectModelConfigBindingRequest,
                                  user: Principal = Depends(current_user)):
        """将模型配置绑定到指定项目。敏感项目尝试绑定非本地或未标记敏感可用的模型时，返回 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
        return config_service.bind_project(user, project_id, body.model_config_id)

    @router.get("/projects/{project_id}/model-options", response_model=ModelConfigListResponse,
                operation_id="listProjectModelOptionsLegacy", include_in_schema=False)
    def list_project_model_options(project_id: str, user: Principal = Depends(current_user)):
        """兼容路由：只读绑定候选列表。"""
        return config_service.list_bindable(user, project_id)

    @router.get("/projects/{project_id}/model-config", response_model=ModelConfigResponse,
                operation_id="getProjectModelConfig")
    def get_project_model_config(project_id: str, response: Response, user: Principal = Depends(current_user)):
        """获取项目绑定的模型配置（未单独绑定时返回公司默认配置）。"""
        result = config_service.get_project_config(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    application.include_router(router)
