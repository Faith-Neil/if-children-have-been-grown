为什么有这个文件：解释 Wave 11 新聚合写入 MySQL 的代码路径。

它解决什么问题：说明哪些工作流键已持久化、何时读写、旧库缺表时如何处理，以及仍未持久化的部分。

# BE-WORKFLOW-STATE-PERSIST：代码解释

- 对应任务 BE-WORKFLOW-STATE-PERSIST；Issue [ISSUE-040](../../issues/ISSUE-040.md)；交付 [交付](../delivery/BE-WORKFLOW-STATE-PERSIST.md)
- 提交 `06f107d`、`2c8d51c`


> 2026-10-28 Wave 12 更新：本卡的 `demo_project_workflow_state` 表与 `workflow_state.py` 已被 [BE-WORKFLOW-DURABILITY](BE-WORKFLOW-DURABILITY.md) 的通用条目表 `demo_state_entry` 取代（Alembic 0012 原位改写，0012 从未合入长期分支）。下文保留 Wave 11 原记录。

## 入口和调用顺序

1. Alembic `0012_workflow_state`：`demo_project_workflow_state(project_id PK, state_json JSON, updated_at DATETIME(6))`。
2. `MysqlConnectionRepository.transaction`：`_load_shared` 末尾调用 `_load_workflow_state` → `load_workflow_state` 把每个项目的 JSON 合并回 `state.workflows[pid]`（项目工作流不存在时先建空白工作流）。
3. 操作前后各取一次 `workflow_state_snapshot`（只含 `volumes`、`volume_reviews`、`volume_epochs`、`human_queue`、`post_process`，按项目 `json.dumps(sort_keys=True)`）。
4. `_save_shared` 中 `save_workflow_state_diff` 只写有变化的项目：`INSERT ... AS incoming ON DUPLICATE KEY UPDATE`；快照消失则删除。
5. 读到缺表错误（未执行 0012 的旧库）时置 `_workflow_state_table=False`，本进程不再写该表，其他写操作不受影响；其他异常照常抛出。

## 数据与状态

内存模式不受影响。MySQL 模式下上述五个键跨进程可见；`files`、`requirements`、`facts`、`checks`、`exports`、`candidates` 等其余键仍只在进程内存（[ISSUE-041](../../issues/ISSUE-041.md)）。

## 验证与限制

`tests/backend/test_mysql_workflow_state.py`（mysql 标记）用两个独立 `create_app()`（各自独立内存）模拟两个进程，核对定稿、复核与队列计数；`test_mysql_connection.py` 的表清单加入新表。本机没有 MySQL，结果以 CI `backend-mysql` 作业为准。
