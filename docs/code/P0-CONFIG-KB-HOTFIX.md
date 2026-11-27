为什么有这个文件：说明 P0-CONFIG-KB-HOTFIX RAGFlow 配置生效链、模型配置 RBAC、知识库重建转换与种子账号代码的修改原因、运行过程与限制。

# P0-CONFIG-KB-HOTFIX：代码解释

- 对应任务、Issue、交付文档：[P0-CONFIG-KB-HOTFIX](../tasks/P0-HOTFIX.md#p0-config-kb-hotfix)、[ISSUE-059](../../issues/ISSUE-059.md)、[交付说明](../delivery/P0-CONFIG-KB-HOTFIX.md)
- 日期、实际代码路径、提交 / PR：2026-11-27；`backend/bid-core/icg/domain/ragflow_config.py`、`backend/bid-core/icg/api/ragflow.py`、`backend/bid-core/icg/api/model_configs.py`、`backend/bid-core/icg/domain/kb_admin.py`、`backend/bid-core/icg/domain/errors.py`、`backend/bid-core/icg/domain/frozen_error_codes.py`、`backend/bid-core/icg/infra/repositories/hot_reads.py`、`backend/bid-core/icg/infra/repositories/mysql_repository.py`；分支 `feat/iss-059-p0-security-export-deploy-hotfix`，PR 未创建。

## 改了什么以及为什么

原行为有四处 P0 缺陷：

1. 平台级 RAGFlow 配置更新后对下属公司不生效：`get_client` / `_configured_client` 只认公司级配置或环境变量；且 `api/ragflow.py` 在 `59f091e` 被误加 10 处 `require_platform_admin`，偏离 `5c3ec77` 既定设计，公司管理员无法正常管理本公司检索配置。
2. `api/model_configs.py` 在 `59f091e` 被误加 9 行 `require_platform_admin` 一刀切，项目负责人无法绑定本项目模型（ISSUE-056 之前既有能力丧失），公司管理员连密钥轮换 PUT 都到不了——这是组 1「在用公司模型无法轮换密钥」的真正根因。
3. 知识库重建时已转换 PDF 字节沿用原 `.docx` 文件名推入 RAGFlow，类型错配导致解析失败；存量未转换 Word 字节不补转换；转换失败误报 500 且发生在数据集移动/删除之后，现场被破坏。
4. 本机 MySQL 开发种子账号只在内存、从未写入 `demo_state_entry`，热路径 `read_auth_state` 按条目加载时账号缺失，登录后会话立即失效。

目标行为与实现：

- `ragflow_config.py` 新增 `effective_ragflow_connection(state, company_id)`：公司配置缺密钥时回落平台 system 端点/密钥/超时，但**保留公司租户身份与 `dataset_ids`**；公司显式停用时不回落。`get_client` 与 `knowledge_base.py` 的 `_configured_client` 统一走该函数，消除双口径。
- `api/ragflow.py` 移除 10 处误加的 `require_platform_admin`；`api/model_configs.py` 移除 9 行误加的一刀切，恢复：公司管理员 CRUD、项目负责人绑定本项目模型、编写人/只读 403。`tests/backend/test_admin_rbac_security_cleanup.py` 中与既定设计矛盾的 ISSUE-056 测试经主 Agent 裁定改写为真正安全边界（普通成员写操作 403、跨租户/平台配置不可触达 404）。
- `kb_admin.py` 重建链路：已转换 PDF 字节用 `.pdf` 文件名 + `application/pdf` 推送；存量未转换 Word 字节先补转换；**先完成全部转换校验再 detach/移动/删除旧数据集**；转换失败抛 422 `FILE_CONVERSION_FAILED`（冻结进 `errors.py`、`frozen_error_codes.py`、OpenAPI）。顺带修复冻结名单漏收 `COMPANY_NAME_DUPLICATED` 的既有问题。
- 种子账号：`mysql_repository` 构造时保留只读 `_development_seed_accounts`（生产环境为空）；`hot_reads.py` 新增 `apply_development_seed_accounts()`——只填补缺失账号、绝不覆盖条目表真实账号、只接受 `_DEMO_ONLY` 种子；接入全部 4 条热路径。

## 入口和调用顺序

- 配置生效链：平台管理员更新平台级 RAGFlow 配置 → 公司检索/摄入请求 → `effective_ragflow_connection` → 公司级优先、缺密钥回落平台 system → RAGFlow 客户端（`trust_env=False`）。
- 模型绑定链：`PUT /projects/{id}/model-binding` → 角色判定（公司管理员/项目负责人放行，编写人/只读 403）→ 敏感项目本地模型门禁复核 → 落盘。
- 重建链：重建请求 → 遍历文档 → 已转换 PDF 用 `.pdf`+`application/pdf` / 未转换 Word 先补转换 → 任一转换失败立即 422（数据集尚未动）→ 全部校验通过 → detach 旧数据集 → 推入新数据集。
- 种子账号链：热路径 `read_auth_state` → 条目表加载 → `apply_development_seed_accounts` 填补缺失 `_DEMO_ONLY` 种子（不覆盖条目表已有账号）→ 会话校验通过。

## 数据与状态

- RAGFlow/模型配置均持久化 MySQL；平台回落只读运行时生效配置，不改公司落盘数据，租户隔离 `${company_id}::` 前缀不变。
- 种子账号填补为内存态只读合并，不写回 `demo_state_entry`，生产环境种子集合为空、行为零变化。

## 关键判断与异常

- 显式停用是强语义：公司 `enabled=false` 时绝不因平台配置存在而复活检索。
- 转换失败 422 必须先于任何数据集移动/删除，保证旧现场完整可重试。
- `FILE_CONVERSION_FAILED` 属冻结错误码，契约零漂移经 `export_openapi.py --check` 验证。

## 验证与限制

- `tests/backend/test_issue059_ragflow_fallback.py` 11 passed；`tests/backend/test_issue059_model_config_rbac.py` 7 passed；`tests/backend/test_admin_rbac_security_cleanup.py` 8 passed；`tests/backend/test_iss059_backend_hotfix.py` + `test_kb_admin` 23 passed 2 skipped；真实 MySQL 标记用例 2 passed（种子账号登录后可建项目、读 workspace，3407 复现）；`tests/backend/test_reference_flow.py` 21 passed。
- 验证登记见 [iss-059-p0-hotfix-verification](../testing/iss-059-p0-hotfix-verification.md)。
- 限制：真实 RAGFlow 连通性未验证（`ICG_RUN_REAL_RAGFLOW_TESTS=1` 门控）；知识库测试为进程内 Fake RAGFlow；skipped 用例为真实服务门控跳过。解释只对应当前实现。


## 第三轮补充（PM 最终权限模型统一口径）

模型与 RAGFlow 连接配置管理（新建/修改/密钥轮换/连通性测试）**严格仅限 `platform_admin`**；公司管理员与普通成员一律 403。项目绑定与任务路由为独立授权：可选本公司或平台 system 池的合规本地非模拟模型，公网端点在候选/绑定/路由/运行时四处同一口径拦截。
