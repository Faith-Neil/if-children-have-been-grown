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

from .domain import DemoService, DemoState, DomainError, Principal, Project
from .workflow_schemas import RequestBody, ResponseBody, v1_error_responses

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


def validate_model_config_for_project(project_sensitive: bool, config: ModelConfig) -> None:
    if project_sensitive and (not config.is_local or not config.allow_sensitive):
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
        return OpenAICompatibleModelProvider(cfg, transport=transport)
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


class ModelConfigListResponse(ResponseBody):
    items: list[ModelConfigResponse]


class ModelConfigCreateRequest(RequestBody):
    id: str | None = Field(default=None, max_length=120)
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


class ModelConfigTestResponse(ResponseBody):
    ok: bool
    provider: str
    model: str
    duration_ms: int = Field(ge=0)


class ProjectModelConfigBindingRequest(RequestBody):
    model_config_id: str = Field(min_length=1, max_length=120)


class ProjectModelConfigBindingResponse(ResponseBody):
    project_id: str
    model_config_id: str


class ModelConfigService:
    def __init__(self, demo_service: DemoService):
        self.service = demo_service
        self.repository = demo_service.repository

    def _ensure_default_config(self, state: DemoState, company_id: str) -> ModelConfig:
        config_id = f"default-{company_id}"
        if config_id not in state.model_configs:
            state.model_configs[config_id] = ModelConfig(
                id=config_id,
                company_id=company_id,
                name="默认内网模型",
                provider="openai-compatible",
                base_url="http://127.0.0.1:8000",
                model="qwen2.5-72b",
                is_local=True,
                allow_sensitive=True,
                stream_enabled=True,
                json_mode_enabled=False,
                revision=1,
                timeout_seconds=60.0,
                max_tokens=1024,
            )
        return state.model_configs[config_id]

    def list(self, principal: Principal) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            self._ensure_default_config(state, company_id)
            items = [
                cfg.to_public_dict()
                for cfg in state.model_configs.values()
                if cfg.company_id == company_id
            ]
            return {"items": items}

        return self.repository.transaction(operation)

    def get(self, principal: Principal, config_id: str) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            self._ensure_default_config(state, company_id)
            cfg = state.model_configs.get(config_id)
            if cfg is None or cfg.company_id != company_id:
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def create(self, principal: Principal, payload: dict[str, Any]) -> dict[str, Any]:
        company_id = principal.user.company_id
        config_id = payload.get("id") or f"cfg-{int(self.service._now() * 1000)}"
        plain_key = payload.get("api_key")

        # 密钥加密（若提供明文，需 ICG_SECRET_KEY 可用）
        encrypted_key = None
        masked_key = None
        if plain_key:
            encrypted_key = encrypt_api_key(plain_key)
            masked_key = mask_api_key(plain_key)

        def operation(state: DemoState):
            if config_id in state.model_configs and state.model_configs[config_id].company_id == company_id:
                raise DomainError(409, "REVISION_CONFLICT", "该模型配置已存在。")
            cfg = ModelConfig(
                id=config_id,
                company_id=company_id,
                name=payload.get("name", "默认模型配置"),
                provider=payload.get("provider", "openai-compatible"),
                base_url=payload.get("base_url", "http://127.0.0.1:8000"),
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
            )
            state.model_configs[config_id] = cfg
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def update(self, principal: Principal, config_id: str, updates: dict[str, Any], if_match: str | None) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            self._ensure_default_config(state, company_id)
            cfg = state.model_configs.get(config_id)
            if cfg is None or cfg.company_id != company_id:
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
            for field_name in (
                "name", "provider", "base_url", "model", "is_local",
                "allow_sensitive", "stream_enabled", "json_mode_enabled",
                "timeout_seconds", "max_tokens",
            ):
                if field_name in updates and updates[field_name] is not None:
                    setattr(cfg, field_name, updates[field_name])

            # 4. 递增 revision
            cfg.revision += 1
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def test_connectivity(self, principal: Principal, config_id: str,
                          transport: httpx.BaseTransport | None = None) -> dict[str, Any]:
        company_id = principal.user.company_id

        def get_cfg(state: DemoState) -> ModelConfig:
            self._ensure_default_config(state, company_id)
            cfg = state.model_configs.get(config_id)
            if cfg is None or cfg.company_id != company_id:
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")
            return cfg

        cfg = self.repository.transaction(get_cfg)

        # 解密 API 密钥。如果未设置 ICG_SECRET_KEY 且存在加密密钥，此处抛出 503 SECRET_KEY_UNAVAILABLE
        plain_key = ""
        if cfg.encrypted_api_key:
            plain_key = decrypt_api_key(cfg.encrypted_api_key)

        start = time.time()
        ok = True

        if cfg.provider == "demo":
            duration_ms = max(1, int((time.time() - start) * 1000))
            return {
                "ok": True,
                "provider": "demo",
                "model": cfg.model,
                "duration_ms": duration_ms,
            }

        try:
            url = cfg.base_url.rstrip("/") + "/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            if plain_key:
                headers["Authorization"] = f"Bearer {plain_key}"
            payload = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "stream": False,
            }
            with httpx.Client(transport=transport, timeout=min(cfg.timeout_seconds, 5.0)) as client:
                resp = client.post(url, headers=headers, json=payload)
                ok = (resp.status_code == 200)
        except Exception:
            ok = False

        duration_ms = max(1, int((time.time() - start) * 1000))
        return {
            "ok": ok,
            "provider": cfg.provider,
            "model": cfg.model,
            "duration_ms": duration_ms,
        }

    def bind_project(self, principal: Principal, project_id: str, config_id: str) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            project = self.service._project(state, principal, project_id)
            cfg = state.model_configs.get(config_id)
            if cfg is None or cfg.company_id != company_id:
                raise DomainError(404, "NOT_FOUND", "未找到该模型配置。")

            # 策略门禁：敏感项目尝试绑定非本地或未标记敏感可用的模型
            validate_model_config_for_project(project.sensitive, cfg)

            state.project_model_configs[project_id] = config_id
            return {"project_id": project_id, "model_config_id": config_id}

        return self.repository.transaction(operation)

    def get_project_config(self, principal: Principal, project_id: str) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            self.service._project(state, principal, project_id)
            config_id = state.project_model_configs.get(project_id)
            if config_id and config_id in state.model_configs:
                return state.model_configs[config_id].to_public_dict()
            default_cfg = self._ensure_default_config(state, company_id)
            return default_cfg.to_public_dict()

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

    @router.get("/projects/{project_id}/model-config", response_model=ModelConfigResponse,
                operation_id="getProjectModelConfig")
    def get_project_model_config(project_id: str, response: Response, user: Principal = Depends(current_user)):
        """获取项目绑定的模型配置（未单独绑定时返回公司默认配置）。"""
        result = config_service.get_project_config(user, project_id)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    application.include_router(router)
