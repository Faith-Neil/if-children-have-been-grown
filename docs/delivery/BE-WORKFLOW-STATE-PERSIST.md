为什么有这个文件：记录 Wave 11 新聚合 MySQL 持久化的交付。

它解决什么问题：让分册定稿、交叉复核、人工处理队列与兜底扫描结果在重启和多进程下不丢失，并如实说明尚未持久化的部分。

# BE-WORKFLOW-STATE-PERSIST：工作流新聚合持久化交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-WORKFLOW-STATE-PERSIST |
| 代码解释 | [代码说明](../code/BE-WORKFLOW-STATE-PERSIST.md) |
| 验收 | CI `backend-mysql` 在 `2c8d51c` 全部通过（[CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468)）；首次运行（`06f107d`）表清单断言 2 项失败已修正。本机无 MySQL，未本地执行 |
| 项目进度 | in-review；其余工作流键持久化转 BE-WORKFLOW-DURABILITY（planned） |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-040](../../issues/ISSUE-040.md)、[ISSUE-041](../../issues/ISSUE-041.md)；任务卡 [BE-WORKFLOW-STATE-PERSIST](../tasks/BE-M0.md#be-workflow-state-persist)
- [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 草稿；未合入

## 完成内容与变更文件

- `backend/bid-core/alembic/versions/0012_workflow_state.py`（新）
- `backend/bid-core/icg/infra/repositories/workflow_state.py`（新）
- `backend/bid-core/icg/infra/repositories/mysql_repository.py`：加载与差量保存
- `tests/backend/test_mysql_workflow_state.py`（新）、`tests/backend/test_mysql_connection.py`

## 验收结果

| 验收点 | 结果 | 证据 |
|---|---|---|
| 另一仓储实例读到已定稿分册、复核通过、待人工问题数 | 通过（CI） | [CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468) `backend-mysql` 作业 |
| 迁移可降级再升级 | 通过（CI） | [CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468) `backend-mysql` 作业 |
| 内存模式行为不变 | 通过 | 后端全量回归 |

## 项目进度

in-review。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响 |
| ROADMAP | 无影响 |
| ARCHITECTURE | 已登记持久化边界 |
| Issue 看板/详情 | ISSUE-040、ISSUE-041 |
| TASK_BOARD / PROJECT_STATUS | 已同步 |
| DOCUMENT_INDEX | 已登记 |

## 风险与后续

工作流主体未持久化（ISSUE-041）前，不能宣称 `ICG_REQUIRE_MYSQL=1` 生产路径可恢复。
