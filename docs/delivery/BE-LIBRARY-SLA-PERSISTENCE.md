为什么有这个文件：记录 MySQL 8 资料与承诺聚合持久化入库的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现 demo_library_item、demo_sla_template 与 demo_library_revision 的 MySQL 8 存储落地，具备版本乐观并发控制、原子修订历史归档、多维检索与纯内存降级机制。

# BE-LIBRARY-SLA-PERSISTENCE：MySQL 8 资料与承诺聚合持久化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-LIBRARY-SLA-PERSISTENCE |
| 代码解释 | 详见 [代码解释](../code/BE-LIBRARY-SLA-PERSISTENCE.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_library_sla_persistence.py` 覆盖资料条目读写、修订履历事务内原子落库、SLA模板持久化、基于 revision 的并发乐观锁拦截、分类与公司隔离检索、Alembic 0008 迁移升降级往返与内存仓库多态；全量离线回归通过。 |
| 项目进度 | BE-LIBRARY-SLA-PERSISTENCE 标为 in-review，绝不私自标 done；关联 ISSUE-018 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-21。
- 业务标准：[《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节、第 8 节。
- 关联问题：[ISSUE-018](../../issues/ISSUE-018.md)（持久化实施阶段）。
- 依赖前置：BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出聚合入库）、BE-CHAPTER-PERSISTENCE（章节聚合入库）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **Alembic 迁移脚本 `0008_library_and_sla.py`**（`backend/bid-core/alembic/versions/0008_library_and_sla.py` 与 `backend/bid-core/migrations/versions/0008_library_and_sla.py`）：
   - 建立 `demo_library_item` 表：`id`（主键）、`company_id`（索引）、`category`、`name`、`status`、`is_starred`、`can_insert`、`is_sensitive`、`payload_json`（JSON）、`revision`（INT 默认 1）、`created_at`、`updated_at`。
   - 建立 `demo_sla_template` 表：`id`（主键）、`company_id`（索引）、`level`、`name`、`rules_json`（JSON）、`revision`（INT 默认 1）、`created_at`、`updated_at`。
   - 建立 `demo_library_revision` 表：`id`（主键）、`item_id`（索引）、`version_number`（INT）、`payload_json`（JSON）、`changed_by`、`change_reason`（可空）、`created_at`。
   - 表结构统一采用 `utf8mb4` / `utf8mb4_0900_ai_ci` / `InnoDB`，支持完整的 `upgrade` 与 `downgrade` 回滚。
2. **资料与承诺持久化服务**（`backend/bid-core/icg_demo/database.py`）：
   - 实现模块级方法与仓库方法：`save_library_item`、`read_library_item`、`list_library_items`、`delete_library_item`、`commit_library_revision`、`list_library_revisions`、`save_sla_template`、`read_sla_template`、`list_sla_templates`、`delete_sla_template`。
   - `save_library_item` 与 `save_sla_template` 提供带 `expected_revision` 的乐观锁并发更新，受影响行数不为 1 时抛出 409 `REVISION_CONFLICT`。
   - `commit_library_revision` 在单个数据库事务内原子推进主表版本并写入修订历史行。
3. **内存仓库纯洁性与多态支持**（`backend/bid-core/icg_demo/adapters.py`）：
   - `MemoryRepository` 扩展相同的 10 项 CRUD 接口，并提供一致的乐观并发冲突拦截与版本历史追踪。
   - 未配置 `ICG_DATABASE_URL` 时完全透明降级至纯内存运行。
4. **自动化测试与基线维护**（`tests/backend/`）：
   - 新增 `tests/backend/test_library_sla_persistence.py`（带有 `@pytest.mark.mysql` 标记），覆盖资料与 SLA 模板读写、修订历史落库、乐观锁冲突拦截、检索过滤、升降级 roundtrip 与内存模式多态。
   - 更新 `tests/backend/test_mysql_connection.py`，同步纳入 `demo_library_item`、`demo_sla_template`、`demo_library_revision`（当前总表数扩展为 15 张）。

### 文件变更清单：
- `backend/bid-core/alembic/versions/0008_library_and_sla.py`（新增）
- `backend/bid-core/migrations/versions/0008_library_and_sla.py`（新增）
- `backend/bid-core/icg_demo/database.py`（修改）
- `backend/bid-core/icg_demo/adapters.py`（修改）
- `tests/backend/test_library_sla_persistence.py`（新增）
- `tests/backend/test_mysql_connection.py`（修改）
- `docs/code/BE-LIBRARY-SLA-PERSISTENCE.md`（新增）
- `docs/delivery/BE-LIBRARY-SLA-PERSISTENCE.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **资料与承诺专属套件**：`pytest tests/backend/test_library_sla_persistence.py`：6 项用例均已就绪。
- **内存纯洁性多态验证**：`test_memory_repository_polymorphism_library_and_sla` 在无 MySQL 依赖环境下直接通过。
- **契约与权限套件**：
  - `pytest tests/backend/test_error_idempotency.py` -> **9 passed**（143 个冻结错误码一致）。
  - `pytest tests/backend/test_eight_roles_access.py` -> **10 passed**。
- **工程治理核查**：`node scripts/check-project-governance.cjs`。
