为什么有这个文件：记录 BE-M0-T19 demo_project 对齐数据字典 bid_project 的交付事实、数据库迁移规范与测试证据。

它解决什么问题：作为质量门禁依据，证明项目表字段已对齐数据字典规范、Alembic 迁移绝对保留已有历史数据、前后端契约兼容无损，并将任务卡状态推进至 in-review，绝不私自标 done。

# BE-M0-T19：项目表 demo_project 对齐数据字典 bid_project 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T19 |
| 代码解释 | [BE-M0-T19](../code/BE-M0-T19.md) |
| 验收 | 2026-10-22：demo_project 表及 Project 领域模型完全对齐 bid_project 字典定义（增加 tender_type, budget_amount_cents, deadline_at, security_level, industry, is_archived 与 A 组系统审计字段）；Alembic 增量迁移脚本 0011 就绪，绝对保留已有历史项目数据；GET /api/v1/projects、GET /api/v1/projects/{id} 与旧接口无损兼容；自动化测试与全量回归通过 |
| 项目进度 | 任务看板是准绳。本卡从 planned 改为 in-review。看板状态保持 0 错误，严禁私自标 done，等待项目经理复审 |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-035](../../issues/ISSUE-035.md)、[ISSUE-018](../../issues/ISSUE-018.md)
- **关联任务**：[BE-M0-T19](../tasks/BE-M0.md#be-m0-t19)
- **状态流转**：从 `planned` 流转为 `in-review`。严格遵循工作规范，严禁私自将任务标为 `done` 或私自关闭 Issue，统一交由主 Agent 与项目经理进行验收关闭。

## 完成内容与变更清单
1. **领域模型与响应契约标准化**：
   - 扩充 `Project` 领域实体与 `ProjectResponse` 契约，支持 `tender_type`（技术标/商务标/综合）、`budget_amount_cents`（BIGINT，预算分）、`deadline_at`（ISO 8601 / 时间戳）、`security_level`（保密级别）、`industry`（所属行业）、`is_archived`（归档状态）及 A 组系统审计字段（`created_by`, `created_at`, `updated_by`, `updated_at`, `record_version`, `is_deleted`）。
   - 保留 `is_sensitive` 属性别名支持，兼容旧前端调用。
   - `create_project` 自动写入创建审计信息；`projects` 和 `project` 自动过滤 `is_deleted=True` 软删除记录。
2. **数据库加载与双模式兼容持久化**：
   - `_load_shared` 优先查询 19 列完整对齐结构，自动兼容旧数据库结构 fallback。
   - `_project_snapshot` 生成 18 元组快照，支持精细脏检查。
   - `_save_projects` 支持解构全量 18 元组与旧版元组，写入与更新自带旧表 fallback 保护。
3. **Alembic 增量无损迁移（0011）**：
   - 创建 `backend/bid-core/alembic/versions/0011_bid_project_alignment.py`。
   - 严格采用 `ALTER TABLE demo_project ADD COLUMN` 语法，**绝对保留已有历史项目记录，严禁清空旧数据**。
   - 不增加新表名，维持 MySQL 17 张表基线不变；提供完整 `downgrade()` 逆向回滚脚本。
4. **接口路由与 OpenAPI 契约兼容**：
   - `main.py` 挂载 `GET /api/v1/projects`（`listV1Projects`）、`GET /api/v1/projects/{id}`（`getV1Project`）和 `GET /api/projects/{id}`（`getProject`）。
   - 保持旧接口 `GET /api/projects` 和 `POST /api/projects` 正常工作。
   - 同步 `spec/openapi/demo-v1.json`，确保 `implemented_contract` 100% 匹配。

## 变更文件清单
- `backend/bid-core/alembic/versions/0011_bid_project_alignment.py`: Alembic 增量迁移脚本。
- `backend/bid-core/icg_demo/domain.py`: 扩充 `Project` 领域模型，增加审计字段生成与软删除过滤。
- `backend/bid-core/icg_demo/schemas.py`: 扩充 `ProjectResponse` 响应契约。
- `backend/bid-core/icg_demo/database.py`: 扩充 `_load_shared`、`_project_snapshot`、`_save_projects` 与时间戳转换。
- `backend/bid-core/icg_demo/main.py`: 挂载 v1 与旧版项目详情/列表 GET 路由。
- `spec/openapi/demo-v1.json`: OpenAPI 规范同步。
- `tests/backend/test_project_dictionary_alignment.py`: 新增 5 项专属自动化测试。
- `docs/code/BE-M0-T19.md`: 代码说明文档。
- `docs/delivery/BE-M0-T19.md`: 本交付文档。

## 验收结果
- `pytest tests/backend/test_project_dictionary_alignment.py`: 5 passed in 2.02s。
- `pytest tests/backend/test_operation_ids.py tests/backend/test_error_idempotency.py`: 17 passed in 10.32s。
- `pytest tests/backend/test_project_dictionary_alignment.py tests/backend/test_operation_ids.py tests/backend/test_error_idempotency.py tests/backend/test_reference_flow.py`: 43 passed in 28.47s。
- `node scripts/check-project-governance.cjs`: 治理检查通过（0 错误）。

## 限制与未完成事项
- 遵循工作规范，本卡状态标为 `in-review`，绝不私自标为 `done`。
- ISSUE-035 保持 `in-review` 状态，待主 Agent 与项目经理确认后关闭。
