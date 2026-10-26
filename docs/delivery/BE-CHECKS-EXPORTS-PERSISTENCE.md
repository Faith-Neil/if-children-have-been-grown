为什么有这个文件：记录 MySQL 8 检查与导出聚合持久化入库的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现 demo_check 与 demo_export 的 MySQL 8 存储落地，具备问题明细 JSON 存储、阻塞项自动派生与拦截、导出快照持久化、状态机流转与纯内存降级机制。

# BE-CHECKS-EXPORTS-PERSISTENCE：MySQL 8 检查与导出聚合持久化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-CHECKS-EXPORTS-PERSISTENCE |
| 代码解释 | 详见 [代码解释](../code/BE-CHECKS-EXPORTS-PERSISTENCE.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_checks_exports_persistence.py` 覆盖检查保存/读取、严重程度派生、阻塞项拦截、项目/分册过滤与删除，导出快照保存、状态流转、分页检索与删除，以及 Alembic 0007 迁移升降级往返和纯内存多态；全量回归全部通过。 |
| 项目进度 | BE-CHECKS-EXPORTS-PERSISTENCE 标为 in-review，绝不私自标 done；关联 ISSUE-018 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-21。
- 业务标准：[《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节、第 8 节。
- 关联问题：[ISSUE-018](../../issues/ISSUE-018.md)（持久化实施阶段）。
- 依赖前置：BE-CHAPTER-PERSISTENCE（章节聚合入库）、BE-M0-T13（项目聚合入库）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **Alembic 迁移脚本 `0007_checks_and_exports.py`**（`backend/bid-core/alembic/versions/0007_checks_and_exports.py` 与 `backend/bid-core/migrations/versions/0007_checks_and_exports.py`）：
   - 建立 `demo_check` 表：`id`（主键）、`project_id`（索引）、`volume_id`（可空）、`status`、`blocking_count`、`warning_count`、`issues_json`（JSON）、`created_at`、`updated_at`。
   - 建立 `demo_export` 表：`id`（主键）、`project_id`（索引）、`export_type`、`status`、`format`、`file_path`（可空）、`file_size`（可空）、`snapshot_json`（JSON 可空）、`created_by`、`created_at`。
   - 表结构使用 `utf8mb4` / `utf8mb4_0900_ai_ci` / `InnoDB`，支持完整的 `upgrade` 与 `downgrade` 回滚。
2. **检查与导出持久化服务**（`backend/bid-core/icg_demo/database.py`）：
   - 实现模块级方法与仓库方法：`save_check`、`read_check`、`list_checks_by_project`、`delete_check`、`save_export`、`read_export`、`update_export_status`、`list_exports_by_project`、`delete_export`。
   - `save_check` 自动根据 `blocking_count` 与 `warning_count` 派生 `status` 并序列化问题列表。
   - `update_export_status` 支持原子将导出任务流转至 `running`、`completed` 或 `failed`，并回填文件大小与路径。
   - `list_exports_by_project` 满足分页并返回 `(items, total)` 元组。
3. **内存仓库纯洁性与多态支持**（`backend/bid-core/icg_demo/adapters.py`）：
   - `MemoryRepository` 扩展相同的 9 个 Check 与 Export CRUD 接口，并提供一致的过滤、分页与派生逻辑。
   - 未配置 `ICG_DATABASE_URL` 时完全透明降级至纯内存运行。
4. **自动化测试与基线维护**（`tests/backend/`）：
   - 新增 `tests/backend/test_checks_exports_persistence.py`（带有 `@pytest.mark.mysql` 标记），覆盖检查与导出读写、JSON 存储、严重程度派生、状态流转、分页检索、迁移升降级 roundtrip 与内存模式多态。
   - 更新 `tests/backend/test_mysql_connection.py`，同步纳入 `demo_check` 与 `demo_export` 新增表结构（当前总表数扩展为 12 张）。

### 文件变更清单：
- `backend/bid-core/alembic/versions/0007_checks_and_exports.py`（新增）
- `backend/bid-core/migrations/versions/0007_checks_and_exports.py`（新增）
- `backend/bid-core/icg_demo/database.py`（修改）
- `backend/bid-core/icg_demo/adapters.py`（修改）
- `tests/backend/test_checks_exports_persistence.py`（新增）
- `tests/backend/test_mysql_connection.py`（修改）
- `docs/code/BE-CHECKS-EXPORTS-PERSISTENCE.md`（新增）
- `docs/delivery/BE-CHECKS-EXPORTS-PERSISTENCE.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **检查与导出专属套件**：`pytest tests/backend/test_checks_exports_persistence.py`：包含 7 项完备用例。
- **内存纯洁性多态验证**：`test_memory_repository_polymorphism_checks_and_exports` 在无 MySQL 依赖环境下直接通过。
- **契约与权限套件**：全量回归覆盖现有 500+ 项测试，无回归破坏。
- **工程治理核查**：`node scripts/check-project-governance.cjs` -> 校验通过。
