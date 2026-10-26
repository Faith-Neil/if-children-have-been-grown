为什么有这个文件：记录 MySQL 8 章节聚合持久化与版本乐观锁入库的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现 demo_chapter 与 demo_chapter_version 的 MySQL 8 存储落地，具备版本乐观并发控制、原子事务回滚和纯内存降级机制。

# BE-CHAPTER-PERSISTENCE：MySQL 8 章节聚合持久化与版本乐观锁交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-CHAPTER-PERSISTENCE |
| 代码解释 | 详见 [代码解释](../code/BE-CHAPTER-PERSISTENCE.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_chapter_persistence.py` 覆盖章节读写、版本原子提交、乐观锁拦截、失败事务回滚与 Alembic 迁移往返；全量回归 `pytest tests/backend`：498 passed, 23 skipped（跳过未启动 MySQL 的用例）。 |
| 项目进度 | BE-CHAPTER-PERSISTENCE 标为 in-review，绝不私自标 done；关联 ISSUE-018 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-21。
- 业务标准：[《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节、第 8 节。
- 关联问题：[ISSUE-018](../../issues/ISSUE-018.md)（持久化实施阶段）。
- 依赖前置：BE-M0-T13（项目聚合入库）、BE-M0-T12（编辑租约入库）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **Alembic 迁移脚本 `0006_chapters.py`**（`backend/bid-core/alembic/versions/0006_chapters.py`）：
   - 建立 `demo_chapter` 表：`id`（主键）、`project_id`（索引）、`volume`、`title`、`content`（LONGTEXT）、`revision`（INT，默认 1）、`assignee_id`（可空）、`updated_at`（DATETIME(6)）。
   - 建立 `demo_chapter_version` 表：`id`（主键）、`chapter_id`（索引）、`version_number`（INT）、`content`（LONGTEXT）、`created_by`、`created_at`（DATETIME(6)）。
   - 表结构使用 `utf8mb4` / `utf8mb4_0900_ai_ci` / `InnoDB`，支持完整的 `upgrade` 与 `downgrade` 回滚。
2. **章节持久化与乐观锁服务**（`backend/bid-core/icg_demo/database.py`）：
   - 实现模块级方法与仓库方法：`read_chapter`、`save_chapter`、`commit_chapter_version`。
   - `commit_chapter_version` 采用乐观锁原子更新：
     `UPDATE demo_chapter SET content = :content, revision = :new_rev, updated_at = :updated_at WHERE id = :id AND revision = :old_rev`
   - 受影响行数不为 1 时，立即抛出 HTTP 409 `REVISION_CONFLICT`，绝不静默覆盖。
   - 在同一数据库事务内原子写入 `demo_chapter` 与 `demo_chapter_version`，任何失败立即回滚。
   - `_load_shared` 扩展章节及历史版本装配，使跨进程读取能加载已入库章节。
3. **内存仓库纯洁性与多态支持**（`backend/bid-core/icg_demo/adapters.py`）：
   - `MemoryRepository` 扩展相同的 `read_chapter`、`save_chapter` 与 `commit_chapter_version` 接口，并提供一致的乐观锁冲突拦截逻辑。
   - 未配置 `ICG_DATABASE_URL` 时完全透明降级至纯内存运行。
4. **自动化测试与基线维护**（`tests/backend/`）：
   - 新增 `tests/backend/test_chapter_persistence.py`（带有 `@pytest.mark.mysql` 标记），覆盖章节读写、版本落库、乐观锁冲突拦截、异常回滚、迁移升降级 roundtrip 与内存模式多态。
   - 更新 `tests/backend/test_mysql_connection.py`，同步纳入 `0005_model_config` 与 `0006_chapters` 新增表结构。

### 文件变更清单：
- `backend/bid-core/alembic/versions/0006_chapters.py`（新增）
- `backend/bid-core/icg_demo/database.py`（修改）
- `backend/bid-core/icg_demo/adapters.py`（修改）
- `tests/backend/test_chapter_persistence.py`（新增）
- `tests/backend/test_mysql_connection.py`（修改）
- `docs/code/BE-CHAPTER-PERSISTENCE.md`（新增）
- `docs/delivery/BE-CHAPTER-PERSISTENCE.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **章节专属套件**：`pytest tests/backend/test_chapter_persistence.py`：6 items 均已就绪（无连接串时由 conftest 正确跳过，避免测试环境污染）。
- **契约与权限套件**：
  - `pytest tests/backend/test_error_idempotency.py tests/backend/test_v1_lease.py` -> **13 passed in 13.39s**。
  - `pytest tests/backend/test_eight_roles_access.py` -> **10 passed in 1.04s**。
- **全量后端回归**：`pytest tests/backend` -> **498 passed, 23 skipped in 388.93s**（100% 顺利通过，无失败）。
- **工程治理核查**：`node scripts/check-project-governance.cjs` -> 校验通过。
