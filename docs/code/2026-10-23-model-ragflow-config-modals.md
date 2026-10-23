# 代码解释：大模型服务与 RAGFlow 知识库弹窗配置及连通性闭环

## 1. 结构与架构分层

依据 `AGENTS.md` 现行骨架约束：
- **前端八域划分**：弹窗组件 `ModelConfigModal.tsx`、`RagflowConfigModal.tsx` 及纯计算核心 `model-config-core.ts`、`ragflow-config-core.ts` 全部位于 `frontend/web/src/admin/`，顶栏胶水位于 `frontend/web/src/app/App.tsx`，无平铺于根目录；
- **后端上下文分包**：实体与服务实现位于 `backend/bid-core/icg/domain/ragflow_config.py`，对外 API 契约位于 `backend/bid-core/icg/api/ragflow.py`，严禁再往 `icg_demo` 根目录平铺业务逻辑；
- **契约收敛**：新端点统一落在 `/api/v1` 前缀下（`/api/v1/ragflow-config`、`/api/v1/ragflow-config/test`），`operationId` 遵循 lowerCamelCase 命名。

## 2. 核心状态与数据流

### 2.1 大模型配置交互（ModelConfigModal）
```mermaid
sequenceDiagram
    participant User as 用户界面 (Modal)
    participant Core as 前端核心 (model-config-core)
    participant BE as 后端 API (/api/v1/model-configs)
    participant LLM as 大模型目标端点

    User->>BE: GET /api/v1/model-configs
    BE-->>User: 返回配置列表 (api_key_masked，明文绝不回显)
    User->>Core: 修改参数或输入新 API Key
    Core-->>User: 校验 URL、超时及涉密本地模型约束
    opt 连通性测试
        User->>BE: POST /api/v1/model-configs/{id}/test
        BE->>LLM: 发送 ping 试探请求 (max_tokens=1)
        LLM-->>BE: 200 OK
        BE-->>User: 返回 { ok: true, duration_ms: 120 }
    end
    User->>BE: PUT /api/v1/model-configs/{id} (If-Match: "revision")
    BE-->>User: 更新成功，版本号递增
```

### 2.2 RAGFlow 检索配置交互（RagflowConfigModal）
```mermaid
sequenceDiagram
    participant User as 用户界面 (Modal)
    participant BE as 后端 API (/api/v1/ragflow-config)
    participant RF as RAGFlow 真实/CI服务

    User->>BE: GET /api/v1/ragflow-config
    BE-->>User: 租户配置 (base_url, dataset_ids, api_key_masked)
    opt 连通性测试
        User->>BE: POST /api/v1/ragflow-config/test (携带覆盖或当前配置)
        BE->>RF: GET /api/v1/system/healthz
        RF-->>BE: { status: "ok" }
        BE-->>User: 返回 { ok: true, message: "连接成功", duration_ms }
    end
    User->>BE: PUT /api/v1/ragflow-config (If-Match: "revision")
    BE-->>User: 保存成功 (Fernet 加密密钥存储)
```

## 3. 安全与合规底线

1. **API Key 零泄露机制**：
   - 数据库与内存中密文存储（Fernet 算法，使用 `ICG_SECRET_KEY` 对称加密）；
   - GET 响应及日志排查绝不输出明文密钥，仅暴露掩码（如 `rag***-xyz`）与布尔标识 `has_api_key`；
   - 客户端提交掩码原样回传时不重新加密，避免掩码覆盖真密钥。
2. **多租户数据隔离**：
   - RAGFlow 配置严格绑定 `principal.user.company_id`，Alpha 公司与 Beta 公司各自持有独立的 RAGFlow 服务端点与 Dataset 集合，杜绝跨租户越权召回；
3. **并发安全与版本保护**：
   - 更新操作强制要求 `If-Match: "<revision>"` 头；若被其他管理员提前更新，立即抛出 409 `REVISION_CONFLICT`，彻底防止脏写覆盖。
