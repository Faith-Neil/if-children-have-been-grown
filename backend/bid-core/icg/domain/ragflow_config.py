# 为什么有这个文件：实现租户级 RAGFlow 知识库配置的领域实体、密钥安全加密、掩码与连通性测试服务。
# 它解决什么问题：落实 PRD §6.2 与用户拍板决策，为企业租户提供前端弹窗可配的 RAGFlow 端点、密钥、数据集与健康检测能力，杜绝机密泄露并保持多租户强隔离。

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx
from icg_demo.domain import DemoService, DemoState, DomainError, Principal
from icg_demo.model_config_storage import (
    check_revision,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)
from icg_demo.ragflow_client import (
    DEFAULT_TIMEOUT_SECONDS,
    RagflowClientError,
    RagflowConfig,
    RagflowRetrievalClient,
)


@dataclass
class RagflowCompanyConfig:
    company_id: str
    base_url: str = "http://127.0.0.1:9380"
    encrypted_api_key: str | None = None
    api_key_masked: str | None = None
    dataset_ids: list[str] = field(default_factory=lambda: ["dataset-alpha-01"])
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    is_enabled: bool = True
    revision: int = 1

    @property
    def has_api_key(self) -> bool:
        return bool(self.encrypted_api_key)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "base_url": self.base_url,
            "has_api_key": self.has_api_key,
            "api_key_masked": self.api_key_masked,
            "dataset_ids": list(self.dataset_ids),
            "timeout_seconds": self.timeout_seconds,
            "is_enabled": self.is_enabled,
            "revision": self.revision,
        }


class RagflowConfigService:
    """管理租户 RAGFlow 检索配置与连通性测试的领域服务。"""

    def __init__(self, demo_service: DemoService):
        self.service = demo_service
        self.repository = demo_service.repository

    def _ensure_company_config(self, state: DemoState, company_id: str) -> RagflowCompanyConfig:
        if not hasattr(state, "ragflow_configs"):
            state.ragflow_configs = {}

        if company_id not in state.ragflow_configs:
            # 优先从环境变量加载默认值（若配置），否则使用合规默认值
            env_base = os.environ.get("ICG_RAGFLOW_BASE_URL", "http://127.0.0.1:9380").strip().rstrip("/")
            env_key = os.environ.get("ICG_RAGFLOW_API_KEY", "").strip()
            encrypted_key = None
            masked_key = None
            if env_key:
                try:
                    encrypted_key = encrypt_api_key(env_key)
                    masked_key = mask_api_key(env_key)
                except Exception:
                    pass

            state.ragflow_configs[company_id] = RagflowCompanyConfig(
                company_id=company_id,
                base_url=env_base,
                encrypted_api_key=encrypted_key,
                api_key_masked=masked_key,
                dataset_ids=[f"dataset-{company_id}-01"],
                timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
                is_enabled=True,
                revision=1,
            )
        return state.ragflow_configs[company_id]

    def get(self, principal: Principal) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            cfg = self._ensure_company_config(state, company_id)
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def update(
        self,
        principal: Principal,
        updates: dict[str, Any],
        if_match: str | None,
    ) -> dict[str, Any]:
        company_id = principal.user.company_id

        def operation(state: DemoState):
            cfg = self._ensure_company_config(state, company_id)

            # 1. 乐观锁 If-Match 校验
            check_revision(cfg.revision, if_match)

            # 2. API Key 更新语义
            if "api_key" in updates and updates["api_key"] is not None:
                key_input = updates["api_key"]
                if key_input == "":
                    # 空字符串清除
                    cfg.encrypted_api_key = None
                    cfg.api_key_masked = None
                elif key_input == cfg.api_key_masked:
                    # 传回掩码代表保留
                    pass
                else:
                    # 传入新明文，进行加密
                    cfg.encrypted_api_key = encrypt_api_key(key_input)
                    cfg.api_key_masked = mask_api_key(key_input)

            # 3. 更新基础属性
            if "base_url" in updates and updates["base_url"] is not None:
                clean_url = str(updates["base_url"]).strip().rstrip("/")
                if clean_url:
                    cfg.base_url = clean_url

            if "dataset_ids" in updates and updates["dataset_ids"] is not None:
                dids = updates["dataset_ids"]
                if isinstance(dids, list):
                    cfg.dataset_ids = [str(d).strip() for d in dids if str(d).strip()]
                elif isinstance(dids, str) and dids.strip():
                    cfg.dataset_ids = [d.strip() for d in dids.split(",") if d.strip()]

            if "timeout_seconds" in updates and updates["timeout_seconds"] is not None:
                cfg.timeout_seconds = float(updates["timeout_seconds"])

            if "is_enabled" in updates and updates["is_enabled"] is not None:
                cfg.is_enabled = bool(updates["is_enabled"])

            # 4. 递增 revision
            cfg.revision += 1
            return cfg.to_public_dict()

        return self.repository.transaction(operation)

    def test_connectivity(
        self,
        principal: Principal,
        override_payload: dict[str, Any] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        company_id = principal.user.company_id

        def get_cfg(state: DemoState) -> RagflowCompanyConfig:
            return self._ensure_company_config(state, company_id)

        cfg = self.repository.transaction(get_cfg)

        payload = override_payload or {}
        base_url = (payload.get("base_url") or cfg.base_url).strip().rstrip("/")
        timeout_seconds = float(payload.get("timeout_seconds") or cfg.timeout_seconds or DEFAULT_TIMEOUT_SECONDS)

        # 确定使用的 API Key
        plain_key = ""
        if "api_key" in payload and payload["api_key"] is not None:
            raw_input = payload["api_key"]
            if raw_input and raw_input != cfg.api_key_masked:
                plain_key = raw_input
            elif raw_input == cfg.api_key_masked and cfg.encrypted_api_key:
                plain_key = decrypt_api_key(cfg.encrypted_api_key)
        elif cfg.encrypted_api_key:
            plain_key = decrypt_api_key(cfg.encrypted_api_key)

        start = time.time()
        ok = False
        message = ""
        health_data: dict[str, Any] = {}

        try:
            client = RagflowRetrievalClient(
                base_url=base_url,
                api_key=plain_key or None,
                timeout_seconds=min(timeout_seconds, 10.0),
                transport=transport,
            )
            health_data = client.health()
            ok = True
            message = "连接成功"
        except RagflowClientError as exc:
            ok = False
            message = f"连接失败: {str(exc)}"
        except Exception as exc:
            ok = False
            message = f"请求异常: {type(exc).__name__}"

        duration_ms = max(1, int((time.time() - start) * 1000))
        return {
            "ok": ok,
            "duration_ms": duration_ms,
            "message": message,
            "health": health_data,
        }
