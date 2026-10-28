为什么有这个文件：记录 ISSUE-041 工作流主体与其余业务状态写入 MySQL 的交付。

它解决什么问题：说明哪些状态已跨进程/重启可见、怎么验证的、还剩什么没做。

# BE-WORKFLOW-DURABILITY：业务状态写入 MySQL 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-WORKFLOW-DURABILITY |
| 代码解释 | [代码说明](../code/BE-WORKFLOW-DURABILITY.md) |
| 验收 | 沙箱本地 MySQL 8.4.13：`-m mysql` 40 passed；内存模式后端全量 879 passed（开发自测，非 QA 签署） |
| 项目进度 | in-review |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-041](../../issues/ISSUE-041.md)；任务卡 [BE-WORKFLOW-DURABILITY](../tasks/BE-M0.md#be-workflow-durability)
- 分支 `feat/wave-11-main-path`，提交 `e9ee182`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)

## 完成内容

- 通用条目表 `demo_state_entry(scope, entry_id, rev, body, updated_at)`（Alembic 0012 原位改写；0012 未合入任何长期分支，替换了 Wave 11 的 `demo_project_workflow_state`）。
- 已持久化：项目工作流全部键（文件、条款、事实、冲突、候选、检查、导出、写作计划、SLA、分册定稿、交叉复核、人工队列等）、新建账号、资料库与资料版本、资源授权、SLA 模板、后台作业、合作方、RAGFlow 配置、企业设置、字典、方案片段与审计、知识库索引。
- 每条目独立 `rev` 乐观锁：两个进程并发写同一条目，后写者得到 409 `VERSION_CONFLICT`，不会静默覆盖。
- 只加载 rev 变化的条目；JSON 序列化保留字典插入顺序（条款、章节顺序重启后不变）。

## 变更文件

- `backend/bid-core/icg/infra/repositories/state_entries.py`（新）、`mysql_repository.py`、`alembic/versions/0012_workflow_state.py`；删除 `workflow_state.py`
- `icg/domain/company_settings.py`、`dict_config.py`、`snippet_publication.py`：服务内存储改为绑定仓储
- `tests/backend/test_mysql_workflow_state.py`（3 项，含并发冲突）、`test_mysql_connection.py`

## 验收结果

| 验收点 | 结果 | 证据 |
|---|---|---|
| 新仓储实例读到项目工作流（条款顺序、文件原件、检查、定稿、人工队列） | 通过 | `test_project_workflow_and_main_path_survive_a_new_repository` |
| 账号、资料库、企业设置、字典、片段跨实例可见 | 通过 | `test_accounts_library_and_service_stores_survive_a_new_repository` |
| 并发写同一条目被拦截 | 通过 | `test_concurrent_write_to_same_entry_is_rejected` |
| 内存模式行为不变 | 通过 | 后端全量 879 passed |

## 风险与后续

- 在 MySQL 上跑全量后端用例有约 50 项因共享库数据互相影响失败（基线分支同样失败），CI 只跑 `-m mysql`；测试隔离另行处理。
- 文件原件仍以 JSON 字段存放，大文件应改对象存储（未做）。
