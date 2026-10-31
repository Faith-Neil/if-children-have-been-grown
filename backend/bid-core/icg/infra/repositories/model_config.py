# 为什么有这个文件：模型配置与项目模型绑定的 MySQL 持久化。
# 它解决什么问题：集中管理 demo_model_config 与 demo_project_model_config 表的数据写入。

from __future__ import annotations

from typing import Any
from sqlalchemy import text


def save_model_configs(
    connection: Any,
    before_configs: dict,
    after_configs: dict,
    before_bindings: dict,
    after_bindings: dict,
) -> None:
    """持久化模型配置与项目-模型绑定关系差异。"""
    try:
        for cid, cfg in after_configs.items():
            prev = before_configs.get(cid)
            if prev == cfg:
                continue
            payload = {
                "id": cfg.id,
                "company_id": cfg.company_id,
                "name": cfg.name,
                "provider": cfg.provider,
                "base_url": cfg.base_url,
                "model": cfg.model,
                "encrypted_api_key": cfg.encrypted_api_key,
                "api_key_masked": cfg.api_key_masked,
                "is_local": 1 if cfg.is_local else 0,
                "allow_sensitive": 1 if cfg.allow_sensitive else 0,
                "stream_enabled": 1 if cfg.stream_enabled else 0,
                "json_mode_enabled": 1 if cfg.json_mode_enabled else 0,
                "revision": cfg.revision,
                "timeout_seconds": cfg.timeout_seconds,
                "max_tokens": cfg.max_tokens,
                "fallback_config_id": cfg.fallback_config_id,
            }
            if prev is None:
                connection.execute(
                    text(
                        "INSERT INTO demo_model_config (id, company_id, name, provider, base_url, model, "
                        "encrypted_api_key, api_key_masked, is_local, allow_sensitive, stream_enabled, "
                        "json_mode_enabled, revision, timeout_seconds, max_tokens, fallback_config_id) "
                        "VALUES (:id, :company_id, :name, :provider, :base_url, :model, :encrypted_api_key, "
                        ":api_key_masked, :is_local, :allow_sensitive, :stream_enabled, :json_mode_enabled, "
                        ":revision, :timeout_seconds, :max_tokens, :fallback_config_id)"
                    ),
                    payload,
                )
            else:
                connection.execute(
                    text(
                        "UPDATE demo_model_config SET name = :name, provider = :provider, base_url = :base_url, "
                        "model = :model, encrypted_api_key = :encrypted_api_key, api_key_masked = :api_key_masked, "
                        "is_local = :is_local, allow_sensitive = :allow_sensitive, stream_enabled = :stream_enabled, "
                        "json_mode_enabled = :json_mode_enabled, revision = :revision, "
                        "timeout_seconds = :timeout_seconds, max_tokens = :max_tokens, "
                        "fallback_config_id = :fallback_config_id WHERE id = :id"
                    ),
                    payload,
                )
        for pid, mid in after_bindings.items():
            if before_bindings.get(pid) != mid:
                connection.execute(
                    text(
                        "INSERT INTO demo_project_model_config (project_id, model_config_id) "
                        "VALUES (:project_id, :model_config_id) "
                        "ON DUPLICATE KEY UPDATE model_config_id = :model_config_id"
                    ),
                    {"project_id": pid, "model_config_id": mid},
                )
    except Exception:
        # 不能吞掉：吞掉会让配置看似保存成功、重启后却丢失（事务整体回滚并报错）
        raise


# 兼容既有私有函数引用
_save_model_configs = save_model_configs
