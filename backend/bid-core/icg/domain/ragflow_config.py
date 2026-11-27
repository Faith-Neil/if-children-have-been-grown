# 为什么有这个文件：实现租户级 RAGFlow 知识库配置的领域实体、密钥安全加密、掩码与连通性测试服务。
# 它解决什么问题：落实 PRD §6.2 与用户拍板决策，为企业租户提供前端弹窗可配的 RAGFlow 端点、密钥、数据集与健康检测能力，杜绝机密泄露并保持多租户强隔离。

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import httpx
from icg.domain.domain import DemoService, DemoState, DomainError, Principal
from icg.infra.model_config_storage import (
    check_revision,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)
from icg.infra.ragflow_client import (
    DEFAULT_TIMEOUT_SECONDS,
    RagflowClientError,
    RagflowConfig,
    RagflowDataset,
    RagflowDocument,
    RagflowRetrievalClient,
    ragflow_run_to_kb_sync_status,
)

# RAGFlow 真实 Dataset ID 是 32 位十六进制；“dataset-alpha-01 / dataset-{company}-01”是应用侧占位值
_REAL_DATASET_ID = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)


def _is_real_dataset_id(value: str) -> bool:
    return bool(_REAL_DATASET_ID.match(str(value or "").strip()))


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


def deployment_default_config(company_id: str) -> RagflowCompanyConfig | None:
    """部署级默认连接（环境变量）的运行时瞬态视图——绝不持久化进公司配置行。

    只在公司与平台都未显式配置时作为最后回落层生效；平台/公司一旦写入显式配置立即盖过它。"""
    env_base = os.environ.get("ICG_RAGFLOW_BASE_URL", "").strip().rstrip("/")
    env_key = os.environ.get("ICG_RAGFLOW_API_KEY", "").strip()
    if not env_key:
        return None
    encrypted_key = None
    masked_key = None
    try:
        encrypted_key = encrypt_api_key(env_key)
        masked_key = mask_api_key(env_key)
    except Exception:
        return None
    return RagflowCompanyConfig(
        company_id=company_id,
        base_url=env_base or "http://127.0.0.1:9380",
        encrypted_api_key=encrypted_key,
        api_key_masked=masked_key,
        dataset_ids=[f"dataset-{company_id}-01"],
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        is_enabled=True,
        revision=1,
    )


def effective_ragflow_connection(state: DemoState, company_id: str) -> RagflowCompanyConfig | None:
    """运行时生效的 RAGFlow 连接配置（ISSUE-059 平台级配置对下属公司生效）。

    优先序：公司级有自己的配置时公司级优先；公司未完成配置（没有密钥，连不上）时回落
    平台管理员写入的 system 配置（端点/密钥/超时/启用开关）。两条红线：
    - 公司显式停用（is_enabled=False 只能来自管理员手动保存）不回落，尊重公司选择；
    - 数据集列表永远保留公司自己的，绝不跨租户共用 dataset_ids（${company_id}:: 隔离不变）。
    密钥不做字段级合并：密钥与端点配套，拼公司地址+平台密钥等于把平台密钥送去错误端点。
    """
    configs = getattr(state, "ragflow_configs", None) or {}
    tenant = configs.get(company_id)
    platform = configs.get("system")
    # 平台显式停用是解析终态：严禁落入环境变量分支把已停用的旧实例重新启用
    if platform is not None and not platform.is_enabled:
        return platform if company_id == "system" else replace(platform, company_id=company_id,
            dataset_ids=list(tenant.dataset_ids) if tenant is not None else [f"dataset-{company_id}-01"])
    if company_id == "system" and tenant is not None:
        return tenant
    if tenant is not None:
        if not tenant.is_enabled:
            return tenant
        if tenant.encrypted_api_key:
            return tenant
    if platform is not None and platform.is_enabled and platform.encrypted_api_key:
        dataset_ids = list(tenant.dataset_ids) if tenant is not None else [f"dataset-{company_id}-01"]
        return replace(platform, company_id=company_id, dataset_ids=dataset_ids)
    # 公司与平台都未显式配置时回落部署级环境变量默认（瞬态，不落盘）；显式配置一旦写入立即盖过它
    deployed = deployment_default_config(company_id)
    if deployed is not None:
        if tenant is not None and tenant.dataset_ids:
            deployed = replace(deployed, dataset_ids=list(tenant.dataset_ids))
        return deployed
    return tenant


def _require_kb_writer(principal: Principal) -> None:
    """知识库数据集创建/同步写操作：仅公司管理员或平台管理员（CWE-862），普通成员 403。"""
    from icg.domain.auth_service import is_super_admin
    from icg.domain.project_access import normalize_role
    if is_super_admin(principal) or normalize_role(principal.user.role) in ("company_admin", "platform_admin"):
        return
    raise DomainError(403, "FORBIDDEN", "知识库写入只能由公司管理员或平台管理员执行。")


class RagflowConfigService:
    """管理租户 RAGFlow 检索配置与连通性测试的领域服务。"""

    def __init__(self, demo_service: DemoService, snippet_publications: Any = None):
        self.service = demo_service
        self.repository = demo_service.repository
        self.snippet_publications = snippet_publications

    def _ensure_company_config(self, state: DemoState, company_id: str) -> RagflowCompanyConfig:
        if not hasattr(state, "ragflow_configs"):
            state.ragflow_configs = {}

        if company_id not in state.ragflow_configs:
            # 写路径实体化：继承当前实际生效的部署连接视图地址（环境变量/平台回落），
            # 但绝不复制任何密钥——仅换密钥保存时地址保持真实生效值而非回环占位。
            deployed = deployment_default_config(company_id)
            state.ragflow_configs[company_id] = RagflowCompanyConfig(
                company_id=company_id,
                base_url=(deployed.base_url if deployed is not None else "http://127.0.0.1:9380"),
                encrypted_api_key=None,
                api_key_masked=None,
                dataset_ids=[f"dataset-{company_id}-01"],
                timeout_seconds=(deployed.timeout_seconds if deployed is not None else DEFAULT_TIMEOUT_SECONDS),
                is_enabled=True,
                revision=1,
            )
        return state.ragflow_configs[company_id]

    def _effective_connection_config(self, state: DemoState, company_id: str) -> RagflowCompanyConfig:
        """运行时连接配置（只读视图，绝不因读取而实体化公司行）：公司显式优先，平台/部署默认回落。"""
        effective = effective_ragflow_connection(state, company_id)
        if effective is not None:
            return effective
        tenant = state.ragflow_configs.get(company_id)
        if tenant is not None:
            return tenant
        return RagflowCompanyConfig(company_id=company_id, dataset_ids=[f"dataset-{company_id}-01"])

    def _public_payload(self, state: DemoState, cfg: RagflowCompanyConfig, company_id: str) -> dict[str, Any]:
        """配置响应附占位检测与已部署真实 Dataset ID 建议，方便管理员回填替换 dataset-*-01 占位。"""
        from icg.domain.knowledge_base import read_index
        payload = cfg.to_public_dict()
        payload["placeholder_dataset_ids"] = [d for d in cfg.dataset_ids if not _is_real_dataset_id(d)]
        suggested: list[str] = []
        try:
            for info in (read_index(state, company_id).get("datasets") or {}).values():
                ds = str((info or {}).get("dataset_id") or "")
                if ds and ds not in suggested:
                    suggested.append(ds)
        except Exception:
            pass
        payload["suggested_dataset_ids"] = suggested
        return payload

    def get(self, principal: Principal) -> dict[str, Any]:
        from icg.domain.platform_security import require_platform_admin
        require_platform_admin(principal)
        company_id = principal.user.company_id

        def operation(state: DemoState):
            # 读路径绝不落盘：无显式配置行时返回运行时生效视图（继承默认/平台回落）
            row = state.ragflow_configs.get(company_id)
            cfg = row if row is not None else self._effective_connection_config(state, company_id)
            return self._public_payload(state, cfg, company_id)

        return self.repository.transaction(operation)

    def update(
        self,
        principal: Principal,
        updates: dict[str, Any],
        if_match: str | None,
    ) -> dict[str, Any]:
        # 连接地址与密钥决定公司资料流向哪里（B5 数据不出内网）：严格仅限平台管理员（ISSUE-059 PM 模型）。
        from icg.domain.platform_security import require_platform_admin
        require_platform_admin(principal)
        company_id = principal.user.company_id

        def operation(state: DemoState):
            cfg = self._ensure_company_config(state, company_id)

            # 1. 乐观锁 If-Match 校验
            check_revision(cfg.revision, if_match)

            # 1.5 base_url 变更检测（CWE-522）：改地址禁止沿用旧密钥/部署默认密钥，
            # 必须显式传入新密钥（明文）或显式空串清除；掩码回传不算显式凭证。
            from icg.infra.model_config_storage import validate_endpoint_url
            url_changing = False
            if "base_url" in updates and updates["base_url"] is not None:
                candidate = validate_endpoint_url(updates["base_url"])
                url_changing = bool(candidate) and candidate != cfg.base_url
            if url_changing:
                supplied = updates.get("api_key")
                if supplied is None or supplied == cfg.api_key_masked:
                    raise DomainError(
                        422, "VALIDATION_ERROR",
                        "变更 RAGFlow 地址时必须显式传入新实例的 API Key，或显式传空串清除旧密钥；禁止携带旧密钥指向新地址。",
                        {"field": "api_key"})

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
                clean_url = validate_endpoint_url(updates["base_url"])
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
            return self._public_payload(state, cfg, company_id)

        return self.repository.transaction(operation)

    def test_connectivity(
        self,
        principal: Principal,
        override_payload: dict[str, Any] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        # 连通性测试会让服务端访问填写的地址：严格仅限平台管理员（与模型配置同一尺度）。
        from icg.domain.platform_security import require_platform_admin
        require_platform_admin(principal)
        company_id = principal.user.company_id

        def get_cfg(state: DemoState) -> RagflowCompanyConfig:
            # 读路径不落盘：测试运行时生效连接（含平台/部署回落）
            return self._effective_connection_config(state, company_id)

        cfg = self.repository.transaction(get_cfg)

        payload = override_payload or {}
        from icg.infra.model_config_storage import validate_endpoint_url
        base_url = validate_endpoint_url(payload.get("base_url") or cfg.base_url)
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

    def get_client(
        self,
        principal: Principal,
        transport: httpx.BaseTransport | None = None,
    ) -> RagflowRetrievalClient:
        """获取当前租户上下文下的 RAGFlow 客户端实例。"""
        company_id = principal.user.company_id

        def get_cfg(state: DemoState) -> RagflowCompanyConfig:
            return self._effective_connection_config(state, company_id)

        cfg = self.repository.transaction(get_cfg)
        plain_key = ""
        if cfg.encrypted_api_key:
            plain_key = decrypt_api_key(cfg.encrypted_api_key)

        return RagflowRetrievalClient(
            base_url=cfg.base_url,
            api_key=plain_key or None,
            timeout_seconds=cfg.timeout_seconds,
            transport=transport,
        )

    def create_dataset(
        self,
        principal: Principal,
        name: str,
        *,
        parser_id: str = "general",
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        """为当前企业租户创建专属隔离数据集，强制注入租户前缀强隔离命名空间。"""
        _require_kb_writer(principal)
        company_id = principal.user.company_id
        client = self.get_client(principal, transport=transport)
        ds = client.create_dataset(name=name, company_id=company_id, parser_id=parser_id)

        # 将新建数据集 ID 登记进当前租户配置中
        def record_ds(state: DemoState):
            cfg = self._ensure_company_config(state, company_id)
            if ds.id not in cfg.dataset_ids:
                cfg.dataset_ids.append(ds.id)
                cfg.revision += 1

        self.repository.transaction(record_ds)
        return {
            "id": ds.id,
            "name": ds.name,
            "company_id": ds.company_id,
            "parser_id": ds.parser_id,
            "document_count": ds.document_count,
        }

    def list_datasets(
        self,
        principal: Principal,
        transport: httpx.BaseTransport | None = None,
    ) -> list[dict[str, Any]]:
        """获取当前企业租户的数据集列表。严格隔离，不展示其他公司数据集。"""
        company_id = principal.user.company_id
        client = self.get_client(principal, transport=transport)
        items = client.list_datasets(company_id=company_id)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "company_id": ds.company_id,
                "parser_id": ds.parser_id,
                "document_count": ds.document_count,
            }
            for ds in items
        ]

    def get_dataset(
        self,
        principal: Principal,
        dataset_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        """获取指定数据集详情。执行租户所有权核验。"""
        company_id = principal.user.company_id
        client = self.get_client(principal, transport=transport)
        ds = client.get_dataset(dataset_id, company_id=company_id)
        return {
            "id": ds.id,
            "name": ds.name,
            "company_id": ds.company_id,
            "parser_id": ds.parser_id,
            "document_count": ds.document_count,
        }

    def upload_document(
        self,
        principal: Principal,
        dataset_id: str,
        name: str,
        content: str | bytes,
        *,
        parser_id: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        """上传文档到指定租户数据集。"""
        company_id = principal.user.company_id
        client = self.get_client(principal, transport=transport)
        doc = client.upload_document(
            dataset_id=dataset_id,
            name=name,
            content=content,
            company_id=company_id,
            parser_id=parser_id,
        )
        return {
            "id": doc.id,
            "name": doc.name,
            "dataset_id": doc.dataset_id,
            "run": doc.run,
            "progress": doc.progress,
            "status": doc.status,
        }

    def _delegate_to_knowledge_base(self, principal: Principal, target_id: str,
                                    transport: httpx.BaseTransport | None) -> dict[str, Any] | None:
        kb = getattr(self.service, "knowledge_base", None)
        if kb is None or not target_id or transport is not None:
            return None
        company_id = principal.user.company_id
        state = self.repository.read()
        records = (state.service_stores.get("snippets") or {}).get("records", {})
        if target_id in records and records[target_id].get("company_id") == company_id:
            key = "snippet:" + target_id
        elif target_id in state.library and state.library[target_id].get("company_id") == company_id:
            key = "library:" + target_id
        else:
            return None
        if not kb.enabled(company_id):
            return None
        summary = kb.sync_company(company_id, keys=[key])
        row = next((r for r in kb.status(company_id)["items"] if r["key"] == key), None)
        if row is None:
            return {"synced": False, "kb_sync_status": "unsynced", "snippet_id": target_id,
                    "dataset_id": kb.status(company_id).get("dataset_id", ""),
                    "message": "该内容尚未发布或未确认，不进入知识库。"}
        status = {"synced": "synced", "failed": "failed"}.get(row["status"], "unsynced")
        return {"synced": status == "synced", "kb_sync_status": status, "snippet_id": target_id,
                "dataset_id": kb.status(company_id).get("dataset_id", ""), "document_id": row.get("document_id", ""),
                "message": {"synced": "同步成功", "failed": row.get("message") or "解析失败"}.get(status, "正在解析"),
                "run": {"synced": "DONE", "failed": "FAIL"}.get(status, "RUNNING"),
                "progress": 1.0 if status == "synced" else 0.0, "summary": summary}

    def sync_knowledge_base(
        self,
        principal: Principal,
        snippet_or_library_id: str | None = None,
        payload: dict[str, Any] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        """将已发布的方案片段或企业资料同步至当前公司绑定的 RAGFlow 知识库中。

        执行步骤：
        1. 寻获并验证方案片段或资料所有权；
        2. 解析或自动建立公司专属隔离数据集；
        3. 上传结构化文本文件并触发 RAGFlow 解析；
        4. 查询解析状态并将 run 映射为统一 kb_sync_status；
        5. 同步回写片段存储记录并返回结构化同步回执。
        """
        _require_kb_writer(principal)
        company_id = principal.user.company_id
        opts = payload or {}
        target_id = snippet_or_library_id or opts.get("snippet_id") or opts.get("id") or ""

        # Wave 12 起由公司知识库服务统一维护“资料/片段 → RAGFlow 文档”映射与同步状态；
        # 已登记的片段与资料一律走它，避免两套逻辑各写一份 kb_sync_status。
        delegated = self._delegate_to_knowledge_base(principal, target_id, transport)
        if delegated is not None:
            return delegated

        snippet_record: dict[str, Any] | None = None
        snippet_title = opts.get("title") or ""
        snippet_body = opts.get("content") or opts.get("body") or ""

        # 1. 尝试从 snippet_publications 查找片段
        pub_store = self.snippet_publications or getattr(self.service, "snippet_publications", None)
        if not pub_store:
            app = getattr(self.service, "application", None)
            pub_store = getattr(getattr(app, "state", None), "snippet_publications", None) if app else None
        if pub_store and target_id:
            try:
                rec = pub_store.records.get(target_id)
                if rec:
                    if rec.get("company_id") != company_id:
                        raise DomainError(404, "NOT_FOUND", "未找到本公司方案片段。")
                    snippet_record = rec
                    if not snippet_title:
                        snippet_title = rec.get("source_group") or rec.get("id") or "snippet"
                    if not snippet_body:
                        snippet_body = rec.get("published_body") or rec.get("draft_body") or ""
            except DomainError:
                raise
            except Exception:
                pass

        # 2. 尝试从 DemoState.library 查找
        if not snippet_body and target_id:
            def find_in_library(state: DemoState):
                lib_item = state.library.get(target_id)
                if lib_item:
                    if lib_item.get("company_id") != company_id:
                        raise DomainError(404, "NOT_FOUND", "未找到本公司资料。")
                    return lib_item
                return None

            lib_item = self.repository.transaction(find_in_library)
            if lib_item:
                snippet_title = snippet_title or lib_item.get("name") or target_id
                snippet_body = snippet_body or lib_item.get("content") or ""

        if not snippet_body and not snippet_record:
            snippet_body = opts.get("draft_body") or opts.get("published_body") or "方案片段默认正文。"
            snippet_title = snippet_title or target_id or "snippet"

        def _write_status(status: str, **extra: Any) -> None:
            # 片段记录是仓储读快照，必须经存储写回才会持久化（ISSUE-041）。
            update = getattr(pub_store, "update_kb_status", None)
            if update is not None:
                update(target_id, status, **extra)
            elif snippet_record is not None:
                snippet_record["kb_sync_status"] = status

        client = self.get_client(principal, transport=transport)

        # 3. 确定目标数据集 ID
        dataset_id = opts.get("dataset_id")
        if dataset_id:
            try:
                client.get_dataset(dataset_id, company_id=company_id)
            except Exception:
                dataset_id = None

        if not dataset_id:
            try:
                existing_list = client.list_datasets(company_id=company_id)
                if existing_list:
                    dataset_id = existing_list[0].id
            except Exception:
                pass

        if dataset_id:
            try:
                client.get_dataset(dataset_id)
            except Exception:
                dataset_id = ""

        if not dataset_id:
            # 自动为租户建立默认隔离数据集
            try:
                ds = client.create_dataset(name="default-knowledge-base", company_id=company_id)
                dataset_id = ds.id

                def save_new_ds(state: DemoState):
                    cfg = self._ensure_company_config(state, company_id)
                    if dataset_id not in cfg.dataset_ids:
                        cfg.dataset_ids.append(dataset_id)
                        cfg.revision += 1

                self.repository.transaction(save_new_ds)
            except Exception as exc:
                if snippet_record:
                    _write_status("failed")
                return {
                    "synced": False,
                    "kb_sync_status": "failed",
                    "snippet_id": target_id,
                    "dataset_id": dataset_id or "",
                    "error": str(exc),
                    "message": f"创建租户数据集异常: {type(exc).__name__}",
                }

        # 4. 执行上传并触发解析
        clean_title = "".join(c for c in snippet_title if c.isalnum() or c in ("-", "_")).strip() or "snippet"
        doc_filename = f"{clean_title}_{target_id or 'doc'}.txt"

        try:
            doc = client.upload_document(
                dataset_id=dataset_id,
                name=doc_filename,
                content=snippet_body,
                company_id=company_id,
            )

            # 触发内置解析
            client.trigger_parse(dataset_id=dataset_id, document_ids=[doc.id])

            # 查询解析后最新状态
            updated_doc = client.get_document_status(dataset_id=dataset_id, document_id=doc.id)
            kb_status = ragflow_run_to_kb_sync_status(updated_doc.run)

            # 回写片段存储状态
            if snippet_record:
                _write_status(kb_status, kb_document_id=doc.id, kb_dataset_id=dataset_id)

            return {
                "synced": (kb_status == "synced"),
                "kb_sync_status": kb_status,
                "snippet_id": target_id,
                "dataset_id": dataset_id,
                "document_id": doc.id,
                "run": updated_doc.run,
                "progress": updated_doc.progress,
                "message": "同步成功" if kb_status == "synced" else ("正在解析" if kb_status == "unsynced" else "解析失败"),
            }
        except Exception as exc:
            if snippet_record:
                _write_status("failed")
            return {
                "synced": False,
                "kb_sync_status": "failed",
                "snippet_id": target_id,
                "dataset_id": dataset_id,
                "error": str(exc),
                "message": f"同步异常: {type(exc).__name__}",
            }

