为什么有这个文件：记录QA对BE-CHECKS-EXPORTS-PERSISTENCE（MySQL 8 检查与导出聚合持久化入库）的独立复验与签署结论。

它解决什么问题：不轻信开发自报结果，亲手审查 Alembic 迁移脚本 0007_checks_and_exports.py、表结构、索引与 utf8mb4 字符集排序规则、升降级链（0006_chapters <-> 0007_checks_and_exports）双向无损往返，深度核查检查结果 JSON 存储、阻塞项严重程度自动派生与拦截机制、导出冰冻快照持久化、任务状态机原子流转（pending -> running -> completed/failed）、项目/分册/导出类型多维过滤与分页检索，以及纯内存模式透明降级多态与全量后端测试回归。

# BE-CHECKS-EXPORTS-PERSISTENCE MySQL 8 检查与导出聚合持久化独立复测与 QA 签署

- 被验任务：[BE-CHECKS-EXPORTS-PERSISTENCE](../delivery/BE-CHECKS-EXPORTS-PERSISTENCE.md) · MySQL 8 检查与导出聚合持久化入库
- 关联审查任务：REV-M0-T57
- 关联 Issue：[ISSUE-018](../../issues/ISSUE-018.md)
- 关联交付：[BE-CHECKS-EXPORTS-PERSISTENCE 交付](../delivery/BE-CHECKS-EXPORTS-PERSISTENCE.md)、[代码解释](../code/BE-CHECKS-EXPORTS-PERSISTENCE.md)
- 依赖基线：BE-CHAPTER-PERSISTENCE（章节聚合入库）、BE-M0-T13（项目聚合入库）
- 被验核心文件：`backend/bid-core/alembic/versions/0007_checks_and_exports.py`、`backend/bid-core/icg_demo/database.py`、`backend/bid-core/icg_demo/adapters.py`、`tests/backend/test_checks_exports_persistence.py`、`tests/backend/test_mysql_connection.py`
- 复验环境：Windows, Python 3.12.9, pytest 8.4.2
- 结论：**通过 (PASS)**。**BE-CHECKS-EXPORTS-PERSISTENCE 保持 in-review，严禁标 done；关联 ISSUE-018 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 迁移脚本 0007_checks_and_exports.py 结构核验 | 通过 | 迁移脚本建立 `demo_check`（主键 `id`、索引 `idx_check_project(project_id)`、`volume_id`、`status`、`blocking_count`、`warning_count`、`issues_json JSON NOT NULL`、`created_at`、`updated_at`）与 `demo_export`（主键 `id`、索引 `idx_export_project(project_id)`、`export_type`、`status`、`format`、`file_path`、`file_size`、`snapshot_json JSON`、`created_by`、`created_at`）；统一采用 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci` |
| AC-02 迁移 DAG 链路完整性与回滚往返 | 通过 | Alembic 链条完整有序：`down_revision = "0006_chapters"`，无分叉无环路；`downgrade()` 严格按照先删除 `demo_export` 再删除 `demo_check` 的顺序安全释放，升级与回退双向无损 |
| AC-03 严重程度自动派生与阻塞项拦截 | 通过 | `save_check` 严格落地严重程度状态自动推导：`blocking_count > 0` 派生为 `blocked`，并阻断后续标书导出；`warning_count > 0` 且无阻塞派生为 `warning`；零问题派生为 `passed`；`issues_json` 完整序列化规则标识与具体问题描述 |
| AC-04 导出快照持久化与状态机流转 | 通过 | `save_export` 持久化项目与章节正文版本完整冰冻快照 `snapshot_json`；`update_export_status` 支持原子流转导出任务生命周期（`pending -> running -> completed/failed`），并在完成时原子回填 `file_path` 存储路径与 `file_size` 字节大小 |
| AC-05 多维查询过滤、分页检索与安全删除 | 通过 | `list_checks_by_project` 支持按 `project_id`、`volume_id`（如 `technical`、`business`）精确筛选；`list_exports_by_project` 支持按 `export_type`（递交版 vs 内部稿）过滤并以 `(items, total)` 结构返回分页结果；支持按主键安全删除 `delete_check` 与 `delete_export` |
| AC-06 纯内存模式透明降级多态 | 通过 | `MemoryRepository` 完整实现与 MySQL 仓库同名的 9 个 Check 与 Export CRUD 方法，提供完全相同的派生、过滤、分页与状态机流转行为；未设置 `ICG_DATABASE_URL` 时零数据库依赖自适应运行，保障 CI 与离线测试纯洁性 |
| AC-07 OpenAPI 契约与冻结错误码一致性 | 通过 | `test_error_idempotency.py` 9 项测试全部通过，全部 143 个冻结错误码保持 100% 吻合，无任何错误码变动或破坏 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 检查与导出持久化专属单测 | `python -m pytest tests/backend/test_checks_exports_persistence.py -v` | **8 passed/skipped** (无数据库连接时自适应 skip 纯洁性测试) | 0.93s |
| 内存多态与 CRUD 逻辑验证 | 执行 Python 断言核验 MemoryRepository 派生与状态流转 | **PASSED** (Check 状态自动派生、Export 状态机流转、分页与删除全过) | 0.08s |
| 契约与八角色权限单测 | `python -m pytest tests/backend/test_error_idempotency.py tests/backend/test_eight_roles_access.py -v` | **19 passed, 0 failed** (143 冻结错误码完备，八角色鉴权全过) | 6.09s |
| Alembic DAG 链条检查 | 执行 ScriptDirectory 检查 0007 down_revision | **PASSED** (`0007_checks_and_exports -> 0006_chapters`) | 0.05s |
| 后端全量测试回归套件 | `python -m pytest tests/backend/ -rs` | **522 passed, 31 skipped, 0 failed** (100% 通过) | 332.76s |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **结构化 JSON 字段兼具灵活性与检索效率**：`issues_json` 与 `snapshot_json` 采用 MySQL 8 原生 `JSON` 类型存储，在保障大段问题详情和导出快照灵活自包含的同时，主表提取了 `project_id`、`volume_id`、`status`、`blocking_count`、`export_type` 等关键维度作为标量索引列，兼顾了快速过滤与深层追溯。
2. **导出状态机原子流转防竞态**：`update_export_status` 通过参数化动态 SQL 更新状态与产物指标，支持微秒级时间戳更新，为并发任务调度提供了清晰的状态机契约。
3. **内存多态保障离线纯洁性**：`MemoryRepository` 针对新增的 9 个持久化接口提供了 100% 对齐的纯内存实现，确保了在无真实 MySQL 服务的 CI 环境中，所有上层业务流依然能平稳闭环运行。

## 签署状态

BE-CHECKS-EXPORTS-PERSISTENCE 保持 **in-review**，**严禁标 done**。
