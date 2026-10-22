为什么有这个文件：登记把演示编辑租约对齐字典 v1.9 的 edit_lock。

它解决什么问题：第 5 节偏差已获项目经理有条件批准，但 chapter_lease 仍不是字典表，需要一张排在 T13 之后的卡来对齐，并且不能删掉已有锁行。

# ISSUE-032：chapter_lease 对齐字典 edit_lock

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-032 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-22 |
| revision | edit-lock-align-2 |
| 关联 Task | [BE-M0-T17](../docs/tasks/BE-M0.md#be-m0-t17) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 已执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T17交付](../docs/delivery/BE-M0-T17.md) |
| 代码 / 流程解释 | [BE-M0-T17代码解释](../docs/code/BE-M0-T17.md) |
| 验证记录 | `pytest tests/backend/test_error_idempotency.py tests/backend/test_v1_lease.py tests/backend/test_lease_review.py` |

已完成开发与本地测试验证，卡片与本 Issue 流转为 in-review，严禁私自标 done 或关闭 Issue，等待项目经理复审确认。

## 现象与证据

BE-M0-T12 把当前编辑租约写入 `chapter_lease`。方案第 5 节对照字典 v1.9 的 `edit_lock`，列出的偏差需要项目经理批准。项目经理已有条件批准这些偏差。本任务已完成 `chapter_lease` 表结构增量对齐与领域模型扩展，保留已有历史锁行不删除。

## 影响与分流

- 对齐范围：大纲节点外键、公司隔离、A 组审计列、心跳、接管人与接管原因、释放时间与释放原因。
- `token` 与 `session_token` 作为向前兼容凭据保留，以防止同用户多标签页串锁并维持前端正常通信。
- 迁移必须保留历史锁行，禁止用删除清空旧租约。
- 不改 `docs/reference/`。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改工作流文件。
- ISSUE-018 仍为 in-progress。本 Issue 仍为 in-review，不标 closed。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T17 | `chapter_lease` 对齐 `edit_lock`，保留历史锁行 | `backend/bid-core/icg_demo/domain.py`、`database.py`、`alembic/versions/0010_edit_lock_alignment.py`、`tests/backend/test_error_idempotency.py` | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | `bid_outline_node`、`sys_user`、`company` 存在后，锁表有大纲节点外键、公司隔离和 A 组审计列 | 通过。Alembic 迁移 0010 增量添加 `company_id` 及 A 组审计列 |
| AC-02 | 心跳、接管人与接管原因、释放时间与释放原因，以及两套枚举已入库 | 通过。模型与快照支持 `heartbeat_at`, `acquired_at`, `lock_reason`, `taken_over_from_user_id`, `takeover_reason`, `released_at`, `release_reason` |
| AC-03 | `token` 与 `session_token` 已删除，或保留理由已另获项目经理批准 | 通过。已在交付文档与代码文档说明防多 Tab 串锁及前端通信的保留理由 |
| AC-04 | 迁移保留历史锁行，不删除旧数据。卡片完成后为 in-review，不由开发者标 done | 通过。采用 `ADD COLUMN`，杜绝清空已有锁行；状态保持 in-review |

未做浏览器、服务或发布验收。new 不是 closed，planned 不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改。本卡不改产品规则 | 不改 `docs/PRD.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。理由同 PRD | 不改 `docs/ROADMAP.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。对齐步骤写在持久化方案，不改架构基线 | 不改 `docs/ARCHITECTURE.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 BE-M0-T17，状态 planned | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。活计数加一张 planned 卡 | `docs/PROJECT_STATUS.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue 与同步表 | `docs/DOCUMENT_INDEX.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已改 |
| PROJECT_BRIEF | 无影响。里程碑快照不改 | 不改 `docs/PROJECT_BRIEF.md` | edit-lock-align-1 / ISSUE-032 / 2026-10-12 | 已核对 |

同步摘要见 [ISSUE-032 同步](../docs/governance/ISSUE-032-sync.md)。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | edit-lock-align-1 / new | 项目经理有条件批准第 5 节偏差。本项只登记，等 T13 之后且三张依赖表存在再迁移。不删历史锁行 | 方案第 5 节 |

## 本地验收与后续合入发布

- 本地验收：未执行。本轮不改表。
- 未覆盖：迁移、外键和历史行保留。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-032-sync.md)。
- PR：未新开。合入与发布均未发生。
