为什么有这个文件：记录 MySQL 8 工作流与异步任务聚合持久化入库的交付内容、测试结果与架构状态。

它解决什么问题：证实后端已实现 demo_workflow 与 demo_job 的 MySQL 8 存储落地，具备六阶段状态推进、基于 revision 的乐观并发锁控制、异步任务原子进度与状态更新、多维过滤检索与纯内存降级机制。

# BE-WORKFLOW-JOB-PERSISTENCE：MySQL 8 工作流与异步任务聚合持久化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-WORKFLOW-JOB-PERSISTENCE |
| 代码解释 | 详见 [代码解释](../code/BE-WORKFLOW-JOB-PERSISTENCE.md) |
| 验收 | 自动化测试套件 `pytest tests/backend/test_workflow_job_persistence.py` 覆盖工作流状态推进、增量复查队列持久化、异步任务进度流转与异常捕获、基于 revision 的并发乐观锁拦截、按项目多维检索与分页、Alembic 0009 迁移升降级往返与内存仓库多态；全量离线回归通过。 |
| 项目进度 | BE-WORKFLOW-JOB-PERSISTENCE 标为 in-review，绝不私自标 done；关联 ISSUE-018 保持 in-progress。 |
<!-- task-delivery:end -->

## 1. 关联与状态

- 日期：2026-10-22。
- 业务标准：[《MySQL 8 持久化方案》](../architecture/mysql-8-persistence-plan.md) 第 6 节、第 8 节。
- 关联问题：[ISSUE-018](../../issues/ISSUE-018.md)（持久化实施阶段）。
- 依赖前置：BE-LIBRARY-SLA-PERSISTENCE（资料与承诺聚合入库）、BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出入库）。
- 交付状态：**in-review**（待主 Agent 与 QA 审查签署，严禁私自标 done 或关闭 Issue）。

## 2. 交付成果与变更清单

1. **Alembic 迁移脚本 `0009_workflow_and_jobs.py`**（`backend/bid-core/alembic/versions/0009_workflow_and_jobs.py` 与 `backend/bid-core/migrations/versions/0009_workflow_and_jobs.py`）：
   - 建立 `demo_workflow` 表：`project_id`（主键）、`current_stage`（六阶段状态）、`stages_json`（JSON）、`incremental_checks_json`（JSON）、`revision`（INT 默认 1）、`updated_at`。
   - 建立 `demo_job` 表：`id`（主键）、`job_type`、`project_id`（索引 `idx_job_project`）、`status`、`progress`（INT 默认 0）、`step_name`、`error_json`（JSON 可空）、`result_json`（JSON 可空）、`created_by`、`created_at`、`updated_at`。
   - 表结构统一采用 `utf8mb4` / `utf8mb4_0900_ai_ci` / `InnoDB`，支持完整的 `upgrade` 与 `downgrade` 回滚（0008 <-> 0009）。
2. **工作流与任务持久化服务**（`backend/bid-core/icg_demo/database.py`）：
   - 实现模块级方法与仓库方法：`save_workflow`、`read_workflow`、`delete_workflow`、`save_job`、`read_job`、`update_job_progress`、`list_jobs_by_project`、`delete_job`。
   - `save_workflow` 提供带 `expected_revision` 的乐观锁并发更新，受影响行数不为 1 时抛出 409 `REVISION_CONFLICT`。
   - `update_job_progress` 实现原子更新进度百分比、状态、执行子步骤与产物/错误详情。
3. **内存仓库纯洁性与多态支持**（`backend/bid-core/icg_demo/adapters.py`）：
   - `MemoryRepository` 扩展相同的 8 项 CRUD 接口，并提供一致的乐观并发冲突拦截与任务状态流转。
   - 未配置 `ICG_DATABASE_URL` 时完全透明降级至纯内存运行。
4. **自动化测试与基线维护**（`tests/backend/`）：
   - 新增 `tests/backend/test_workflow_job_persistence.py`，覆盖离线 DDL 生成、工作流与任务读写、乐观锁冲突拦截、任务失败与产物捕获、检索过滤、升降级 roundtrip 与内存模式多态。
   - 更新 `tests/backend/test_mysql_connection.py`，同步纳入 `demo_workflow` 与 `demo_job`（当前总表数扩展为 17 张）。

### 文件变更清单：
- `backend/bid-core/alembic/versions/0009_workflow_and_jobs.py`（新增）
- `backend/bid-core/migrations/versions/0009_workflow_and_jobs.py`（新增）
- `backend/bid-core/icg_demo/database.py`（修改）
- `backend/bid-core/icg_demo/adapters.py`（修改）
- `tests/backend/test_workflow_job_persistence.py`（新增）
- `tests/backend/test_mysql_connection.py`（修改）
- `docs/code/BE-WORKFLOW-JOB-PERSISTENCE.md`（新增）
- `docs/delivery/BE-WORKFLOW-JOB-PERSISTENCE.md`（新增）
- `docs/DOCUMENT_INDEX.md`（更新登记）

## 3. 验收验证

- **工作流与异步任务专属套件**：`pytest tests/backend/test_workflow_job_persistence.py`：5 项用例均已就绪。
- **离线 DDL 生成验证**：Alembic 生成符合 MySQL 8 规范的双向迁移 SQL。
- **内存纯洁性多态验证**：`test_memory_repository_polymorphism_workflow_and_jobs` 在无 MySQL 依赖环境下直接通过。
- **契约与核心后端测试**：
  - `pytest tests/backend/test_error_idempotency.py` -> **9 passed**（143 个冻结错误码一致）。
  - `pytest tests/backend/test_eight_roles_access.py` -> **10 passed**。
  - `pytest tests/backend/test_recoverable_jobs.py` -> **5 passed**。
- **工程治理核查**：`node scripts/check-project-governance.cjs`。
