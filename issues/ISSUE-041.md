为什么有这个文件：登记 MySQL 模式下项目工作流主体仍只在进程内存的持久化缺口。

它解决什么问题：防止把 `ICG_REQUIRE_MYSQL=1` 测绿当成生产可恢复；重启或多进程部署会丢失已解析条款、矩阵、事实、检查与导出记录。

# ISSUE-041：项目工作流主体未写入 MySQL

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-041 |
| 类型 | bug |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 2 |
| 关联 Task | [BE-WORKFLOW-DURABILITY](../docs/tasks/BE-M0.md#be-workflow-durability)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) |
| 本地验收 | 开发自测：沙箱 MySQL 8.4.13 `-m mysql` 40 passed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [交付](../docs/delivery/BE-WORKFLOW-DURABILITY.md) |
| 代码 / 流程解释 | [代码说明](../docs/code/BE-WORKFLOW-DURABILITY.md) |
| 验证记录 | [Wave 12 开发自测](../docs/testing/2026-10-28-wave-12-verification.md) |

## 现象与证据

`backend/bid-core/icg/infra/repositories/mysql_repository.py` 的 `transaction` 只同步会话、回执、租约、项目与团队、模型配置、章节与版本、`demo_check`。`state.workflows[project_id]` 中的 `files`、`requirements`、`facts`、`conflicts`、`candidates`、`checks`、`exports`、`writing_plan`、`sla` 等只保存在仓储内部的 `MemoryRepository`。`demo_workflow` 表（Alembic 0009）存在但事务路径从不写入。Wave 11 已把分册定稿、交叉复核、人工处理队列、兜底扫描写入新表 `demo_project_workflow_state`（ISSUE-040），其余键未处理。

## 影响与分流

- 影响：生产内网部署重启后，已上传的招标文件、确认的条款与矩阵、项目事实、检查与导出记录丢失；多进程/多副本时互不可见。AGENTS.md 金标准第 3 条“关演示正式可用”因此不能宣称达成。
- 处理方向：把 workflow 其余键纳入同一 JSON 按项目持久化，或按聚合拆表；先核对键内类型（集合、字节、整型键）能否无损往返 JSON，`recheck_queue` 为集合须改为列表；文件原件改存对象存储或独立表。
- 依赖：无；排在 Wave 12 首位。

## 处理结果（2026-10-28）

通用条目表 `demo_state_entry` 持久化项目工作流全部键以及账号、资料库、SLA 模板、作业、合作方、RAGFlow 配置、企业设置、字典、方案片段、知识库索引；每条目 rev 乐观锁，并发写返回 409。详见交付说明。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-WORKFLOW-DURABILITY | 项目工作流全部业务键写入 MySQL，跨进程可见 | `backend/bid-core/icg/infra/repositories/`、`backend/bid-core/alembic/versions/` | 跨进程读取解析、矩阵、检查、导出记录一致；`backend-mysql` 作业全绿 | in-review |

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 无影响 | PRD §7.1/§7.5 已要求私有化持久化与备份，本 Issue 是实现缺口 |
| ROADMAP | 无影响 | 阶段不变 |
| ARCHITECTURE | 有影响 | 在 [ARCHITECTURE](../docs/ARCHITECTURE.md) 登记当前持久化边界 |
| TASK_BOARD | 有影响 | 新增 BE-WORKFLOW-DURABILITY |
| PROJECT_STATUS | 有影响 | 如实记录持久化边界 |
| DOCUMENT_INDEX | 有影响 | 登记本 Issue |
