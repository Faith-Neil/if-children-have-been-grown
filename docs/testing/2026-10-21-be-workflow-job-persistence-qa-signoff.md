为什么有这个文件：记录QA对BE-WORKFLOW-JOB-PERSISTENCE（MySQL 8 工作流状态与异步任务聚合持久化入库）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手审查 Alembic 迁移脚本 0009_workflow_and_jobs.py、表结构、索引与 utf8mb4 字符集排序规则、升降级链（0008_library_and_sla <-> 0009_workflow_and_jobs）双向无损往返，深度核查工作流阶段推进的行级乐观并发控制（基于 revision 字段，版本不匹配或更新行数!=1抛出 409 REVISION_CONFLICT）、长耗时异步任务生命周期流转与原子进度更新（跨进程断点恢复）、项目关联任务多维检索、以及纯内存模式透明降级多态与全量后端测试回归。

# BE-WORKFLOW-JOB-PERSISTENCE MySQL 8 工作流状态与异步任务聚合持久化独立复测与 QA 签署

- 被验任务：[BE-WORKFLOW-JOB-PERSISTENCE](../delivery/BE-WORKFLOW-JOB-PERSISTENCE.md) · MySQL 8 工作流状态与异步任务聚合持久化入库
- 关联审查任务：REV-M0-T61
- 关联 Issue：[ISSUE-018](../../issues/ISSUE-018.md)
- 关联交付：[BE-WORKFLOW-JOB-PERSISTENCE 交付](../delivery/BE-WORKFLOW-JOB-PERSISTENCE.md)、[代码解释](../code/BE-WORKFLOW-JOB-PERSISTENCE.md)
- 依赖基线：BE-LIBRARY-SLA-PERSISTENCE（资料与承诺入库）、BE-CHECKS-EXPORTS-PERSISTENCE（检查与导出入库）
- 被验核心文件：
  - `backend/bid-core/alembic/versions/0009_workflow_and_jobs.py`
  - `backend/bid-core/icg_demo/database.py`
  - `backend/bid-core/icg_demo/adapters.py`
  - `tests/backend/test_workflow_job_persistence.py`
  - `tests/backend/test_mysql_connection.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-WORKFLOW-JOB-PERSISTENCE 保持 in-review，严禁标 done；关联 ISSUE-018 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 迁移脚本 0009_workflow_and_jobs.py 结构核验 | 通过 | 迁移脚本建立 `demo_workflow`（主键 `project_id`、`current_stage`、`stages_json JSON NOT NULL`、`incremental_checks_json JSON NOT NULL`、`revision INT DEFAULT 1`、`updated_at`）与 `demo_job`（主键 `id`、索引 `idx_job_project(project_id)`、`job_type`、`status`、`progress INT DEFAULT 0`、`step_name`、`error_json JSON`、`result_json JSON`、`created_by`、时间戳）；统一采用 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci` |
| AC-02 迁移 DAG 链路完整性与回滚往返 | 通过 | Alembic 链条完整有序：`down_revision = "0008_library_and_sla"`，离线 SQL 生产脚本与 `ScriptDirectory` 遍历均表明单向线性无环；`downgrade()` 严格按照先删除 `demo_job` 再删除 `demo_workflow` 的顺序安全释放，升级与回退双向无损 |
| AC-03 行级乐观并发更新锁与 409 REVISION_CONFLICT 拦截 | 通过 | `save_workflow` 在提供 `expected_revision` 参数时，在 SQL 层面执行 `WHERE project_id = :project_id AND revision = :expected_revision`；若更新影响行数不为 1，精准抛出 `DomainError(status=409, code="REVISION_CONFLICT", message="工作流已被其他会话更新，请刷新并核对最新版本。")`，有效阻断并发多会话脏写与阶段覆盖 |
| AC-04 异步任务生命周期与原子进度推进 | 通过 | `save_job` 创建任务；`update_job_progress` 支持原子回写 `progress`（0~100）、`status`（pending -> running -> completed/failed/cancelled）、`step_name` 以及结构化 `result_json` / `error_json`，并刷新微秒级时间戳，为跨进程断点恢复与进度轮询提供强一致保障 |
| AC-05 项目维度的任务多维检索与安全删除 | 通过 | `list_jobs_by_project` 支持按 `project_id` 与状态/类型联合检索当前项目关联的所有后台任务；提供 `delete_workflow` 与 `delete_job` 安全物理删除方法 |
| AC-06 纯内存模式透明降级多态 | 通过 | `MemoryRepository` 完整实现与 MySQL 模块同名的 8 个持久化接口，具备完全一致的乐观并发锁判定、`REVISION_CONFLICT` 拦截与任务进度状态流转行为；未配置 `ICG_DATABASE_URL` 时零数据库依赖自适应降级运行，保障 CI 与纯离线测试纯洁性 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | 契约与权限测试套件全部通过，全量 143 个冻结错误码保持 100% 完整无损，无任何破坏或漂移 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 工作流与任务持久化专属单测 | `python -m pytest tests/backend/test_workflow_job_persistence.py -v` | **4 项用例就绪/自适应跳过** | 0.85s |
| 内存多态与乐观锁并发冲突逻辑验证 | 执行 Python 断言核验 MemoryRepository 乐观锁与进度流转 | **PASSED** (CRUD、乐观锁409拦截、进度更新全过) | 0.08s |
| 契约与八角色权限单测 | `python -m pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py -v` | **19 passed, 0 failed** (143 冻结错误码完备) | 5.34s |
| Alembic 0009 离线 SQL 生成与 DAG 检查 | 执行 Alembic 离线 SQL 生成断言 | **PASSED** (`0009_workflow_and_jobs -> 0008_library_and_sla`) | 0.12s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **532 passed, 37 skipped, 0 failed** (100% 通过) | 338.10s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **六阶段状态流转与增量复查队列的原子收敛**：`demo_workflow` 将复杂的六阶段详细进度和增量复查待处理队列聚合在单一实体中，通过 OCC 乐观锁杜绝了分工协作时各模块更新互相冲撞的问题。
2. **长耗时任务状态的跨进程共享与断点自愈**：`demo_job` 使得 AI 章节生成、整书导出等长达数分钟的后台任务具备了脱离特定 API 进程的外部持久化状态，即使 Worker 进程异常退出，重启后也能精准识别 `running` / `failed` 状态并执行补偿或断点重试。
3. **内存多态保障离线纯洁性**：`MemoryRepository` 对新增持久化接口提供了完全一致的纯内存模拟，确保在无任何数据库连接的离线开发与自动化测试中，工作流和异步任务依然能够闭环测试。

## 签署状态

BE-WORKFLOW-JOB-PERSISTENCE 保持 **in-review**，**严禁标 done**。
