# 任务交付：RAGFlow 知识库摄入与同步闭环（D4-AI）

为什么有这个文件：记录落实 2026-10-26 用户审计与官方拍板 B5/B6（私有化内网部署、多租户强隔离、无公网依赖）的 RAGFlow 知识库摄入与同步闭环（`dataset/kb_sync`）交付成果。

它解决什么问题：
1. 解决知识库片段发布后仅标记 `unsynced` 而未真正摄入 RAGFlow 知识库的断环问题；
2. 建立端到端多租户命名空间强隔离，杜绝跨租户数据集串用与知识泄露；
3. 扩展客户端与领域服务，支持数据集自动创建、文档解析触发、生命周期轮询与 `run` 到 `kb_sync_status` 状态映射；
4. 实现上游网络/业务故障的优雅降级与真实内网环境门禁保护，保持 OpenAPI 契约 100% 零漂移。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | D4-AI / RAGFLOW-KB-SYNC-2026-10-26 |
| 代码解释 | `docs/code/2026-10-26-ragflow-kb-sync.md` |
| 验收 | 1) `RagflowRetrievalClient` 扩展完成：支持带租户命名空间前缀的 `create_dataset`、租户隔离过滤的 `list_datasets`、所有权强校验的 `get_dataset`、文档 `upload_document`、解析触发 `trigger_parse` 与状态轮询 `get_document_status`；<br>2) 网络代理防劫持：`httpx.Client` 强制 `trust_env=False`，杜绝系统代理劫持内网私有化请求（落实用户拍板 B5/B6）；<br>3) `RagflowConfigService` 领域服务实现 `sync_knowledge_base`：支持从 `snippet_publications` 与 `library` 结构化摄入方案片段，自动智能对齐租户隔离数据集，文档上传后触发解析并将 run 映射为 `kb_sync_status`（`synced` / `failed` / `unsynced`），回写片段存储；<br>4) 跨租户强隔离：非本公司方案片段跨租户同步严格抛出 404 `NOT_FOUND`，数据集强制注入 `${company_id}::` 前缀隔离；<br>5) 优雅降级：上游 500/网络崩溃时优雅降级并返回结构化失败状态，主进程不崩溃；<br>6) 专属测试套件 `tests/backend/test_ragflow_kb_sync.py` 10 项测试全绿（9 passed, 1 skipped，真实端点门禁由 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护）；<br>7) 全量 RAGFlow 相关套件联合回归 71 项全部通过（67 passed, 4 skipped），`export_openapi.py --check` 100% 一致。 |
| 项目进度 | D4 RAGFlow 知识库摄入与同步闭环交付，推进状态为 `in-review` |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-26
- 关联决策：用户官方拍板 B5（招标/投标内容仅走内网本地 Qwen 与自建 RAGFlow，数据严禁出公网）、B6（交付目标环境为公司内网私有化、可离线、Windows/Linux 兼容）
- 关联卡片：`AI-M0`、`AI-RAGFLOW-KB-SYNC`、`D4 产品断环`、`ISSUE-037`、`ISSUE-007`
- 本地验收状态：`in-review`（严格遵守 subagent 治理规则，严禁自行标 done）
- 分支：`feat/opencode-ICG`

---

## 2. 交付成果与实现要点

### 2.1 客户端核心扩展（[`backend/bid-core/icg_demo/ragflow_client.py`](../../backend/bid-core/icg_demo/ragflow_client.py)）
- **代理旁路**：`httpx.Client(..., trust_env=False)`，杜绝外部代理劫持内网 `127.0.0.1` 请求报 502。
- **数据集管理**：
  - `create_dataset(name, company_id, parser_id)`：强制注入 `${company_id}::` 命名空间前缀；
  - `list_datasets(company_id)`：基于租户前缀过滤，返回仅属于当前租户的数据集列表；
  - `get_dataset(dataset_id, company_id)`：严格校验归属租户，非法访问直接抛出 `RagflowBusinessError(102)`。
- **文档生命周期**：
  - `upload_document(dataset_id, name, content, company_id)`：支持文本/字节内容通过 `multipart/form-data` 格式上传；
  - `trigger_parse(dataset_id, document_ids)`：触发 RAGFlow 内置解析引擎；
  - `get_document_status(dataset_id, document_id)`：轮询解析状态与进度。
- **状态转换映射**：
  - `ragflow_run_to_kb_sync_status(run: str) -> str`：映射为 PRD 规范的 `synced`、`failed` 与 `unsynced`。

### 2.2 领域服务摄入闭环（[`backend/bid-core/icg/domain/ragflow_config.py`](../../backend/bid-core/icg/domain/ragflow_config.py)）
- **依赖整合**：`RagflowConfigService` 接入 `MemorySnippetPublicationStore`。
- **闭环方法 `sync_knowledge_base`**：
  1. 寻获并核验方案片段（支持从 `snippet_publications` 或 `DemoState.library` 寻获）；
  2. 租户隔离校验：非本公司方案片段抛出 404 `NOT_FOUND`；
  3. 数据集智能对齐：优先核验指定数据集是否存在；若无可用数据集，自动调用 `create_dataset` 创建以公司为前缀的专属库并更新租户配置版本；
  4. 上传结构化文本文件并触发 RAGFlow 解析；
  5. 轮询解析运行状态并回写片段记录的 `kb_sync_status`；
  6. 优雅降级：捕获网络与上游 500 异常，返回结构化失败状态而不使业务服务抛出未捕获 500 崩溃。

### 2.3 运行时端点（[`backend/bid-core/icg/api/ragflow.py`](../../backend/bid-core/icg/api/ragflow.py)）
- 提供内部运行时路由：
  - `GET /api/v1/ragflow/datasets`
  - `POST /api/v1/ragflow/datasets`
  - `GET /api/v1/ragflow/datasets/{id}`
  - `POST /api/v1/ragflow/sync`
- 均设置 `include_in_schema=False`，保护已冻结的 143 个错误码与 OpenAPI 契约 100% 零漂移。

### 2.4 测试替身（[`tests/backend/fake_ragflow.py`](../../tests/backend/fake_ragflow.py)）
- 内存数据集与文档字典存储；
- 完整模拟 `POST/GET /api/v1/datasets`、`POST/GET /api/v1/datasets/{id}/documents` 与 `POST /api/v1/datasets/{id}/chunks`；
- 支持 `[[sync-fail]]` 标记模拟解析失败，满足确定性自动化测试。

---

## 3. 自动化测试与验证证据

### 3.1 专属知识库摄入套件（10 项测试）
命令：
```powershell
pytest tests/backend/test_ragflow_kb_sync.py -v
```
输出证据：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 10 items

tests/backend/test_ragflow_kb_sync.py::test_client_dataset_crud_and_tenant_isolation PASSED [ 10%]
tests/backend/test_ragflow_kb_sync.py::test_client_document_upload_and_parse_lifecycle PASSED [ 20%]
tests/backend/test_ragflow_kb_sync.py::test_client_document_sync_fail_handling PASSED [ 30%]
tests/backend/test_ragflow_kb_sync.py::test_service_dataset_management_with_tenant_prefix PASSED [ 40%]
tests/backend/test_ragflow_kb_sync.py::test_service_sync_knowledge_base_published_snippet PASSED [ 50%]
tests/backend/test_ragflow_kb_sync.py::test_service_sync_knowledge_base_with_sync_fail_marker PASSED [ 60%]
tests/backend/test_ragflow_kb_sync.py::test_service_sync_knowledge_base_graceful_degradation_on_http_error PASSED [ 70%]
tests/backend/test_ragflow_kb_sync.py::test_service_sync_cross_tenant_isolation PASSED [ 80%]
tests/backend/test_ragflow_kb_sync.py::test_ragflow_sync_api_endpoints_integration PASSED [ 90%]
tests/backend/test_ragflow_kb_sync.py::test_real_ragflow_kb_sync_skipped_without_env_flag SKIPPED [100%]

======================== 9 passed, 1 skipped in 27.17s ========================
```

### 3.2 全量 RAGFlow 相关套件联合回归（71 项测试）
命令：
```powershell
pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_evidence_ragflow.py tests/backend/test_ragflow_config_api.py tests/backend/test_ragflow_kb_sync.py tests/backend/test_chapter_generation_rag_flow.py
```
输出证据：
```text
================== 67 passed, 4 skipped in 72.28s (0:01:12) ===================
```

### 3.3 OpenAPI 契约零漂移核验
命令：
```powershell
python backend/bid-core/export_openapi.py --check
```
输出证据：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 真实环境依赖与 Blocked 说明

根据 subagent 规范，严禁在无真实证据时声称生产模型对接已完成：
1. **当前开发与 CI 环境**：受环境变量门控保护，在 `FakeRagflow` 桩下完成闭环单测验证，100% 稳定运行；
2. **生产环境对接条件**：
   - 依赖内网私有部署的真实 RAGFlow 服务（Windows/Linux 私有化环境）；
   - 运行真实端点测试需配置：
     ```powershell
     $env:ICG_RUN_REAL_RAGFLOW_TESTS="1"
     $env:ICG_RAGFLOW_BASE_URL="http://<真实内网IP>:9380"
     $env:ICG_RAGFLOW_API_KEY="<真实服务密钥>"
     ```
   - 在未提供真实内网服务器端点前，真实端点集成验收保持诚实门控（Blocked 等待真实内网环境部署）。

---

## 5. 治理与文档同步

- [x] 代码说明：[`docs/code/2026-10-26-ragflow-kb-sync.md`](../code/2026-10-26-ragflow-kb-sync.md)
- [x] 任务卡：`docs/tasks/AI-M0.md` 新增 `AI-RAGFLOW-KB-SYNC` 说明并标为 `in-review`
- [x] 任务看板：`docs/TASK_BOARD.md` 更新 D4 状态为 `in-review`
- [x] 文档索引：`docs/DOCUMENT_INDEX.md` 登记交付与代码说明
