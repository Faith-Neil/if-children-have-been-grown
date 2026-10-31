为什么有这个文件：解释业务状态写入 MySQL 通用条目表的代码路径。

它解决什么问题：说明条目如何划分、何时加载与保存、并发冲突如何判定，便于后续按聚合拆表。

# BE-WORKFLOW-DURABILITY：代码解释

- 任务 BE-WORKFLOW-DURABILITY；Issue [ISSUE-041](../../issues/ISSUE-041.md)；交付 [交付](../delivery/BE-WORKFLOW-DURABILITY.md)；提交 `e9ee182`

## 数据结构

`demo_state_entry(scope, entry_id, rev, body LONGTEXT, updated_at)`，主键 `(scope, entry_id)`。

| scope | entry_id | 内容 |
|---|---|---|
| workflow | 项目 id | `state.workflows[pid]` 整个字典 |
| account / library / sla_template / job / partners / ragflow_config | 记录 id 或公司 id | 对应 DemoState 字段的单条记录 |
| service_store | 存储名 | `state.service_stores[name]`：`company_settings`、`dict_config`、`snippets`、`kb_index` |
| audit / singleton | 固定名 | 审计列表、`library_revisions`、`resource_acl` |

`state_entries.py` 负责编码：集合、元组、dataclass、pydantic 对象带类型标记往返；键不排序，保留插入顺序。

## 调用顺序

1. `MysqlConnectionRepository._load_shared` 读 `(scope, entry_id, rev)`，与进程内 rev 缓存比较，只取变化或新增条目的 `body` 合并进 DemoState；数据库里消失的条目从内存删除。
2. 操作前对每个条目做序列化快照。
3. `_save_shared` 对比操作后快照：新增 `INSERT`（rev=1）；变化 `UPDATE ... WHERE rev = 旧rev` 并把 rev+1，影响行数为 0 即抛 409 `VERSION_CONFLICT`，整个事务回滚；删除 `DELETE ... WHERE rev = 旧rev`。
4. 服务内存储（企业设置、字典、片段）读时取仓储快照，写时在仓储事务里绑定 `state.service_stores`，因此与其他状态同一事务提交。

## 限制

- 一个项目的工作流是一个条目：同一项目两人同时写不同子键也会冲突（安全但偏保守），后续可按聚合拆分。
- 片段知识库状态写回走 `MemorySnippetPublicationStore.update_kb_status`，不能直接改读快照。
