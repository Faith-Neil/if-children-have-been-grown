为什么有这个文件：登记挂证据规则这张卡，排在 T13 之后。

它解决什么问题：先占住 ISSUE-033 和任务号，避免别人另开一张。本轮不查字典、不定错误码、不改接口。

# ISSUE-033：挂证据规则

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-033 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | new |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | evidence-mount-1 |
| 关联 Task | [BE-M0-T18](../docs/tasks/BE-M0.md#be-m0-t18) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 未执行。本轮只登记，不改接口 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 尚未建立。任务为 planned，无运行时代码 |
| 代码 / 流程解释 | 无代码影响 |
| 验证记录 | 未执行。实现后再补 |

登记时 Issue 看板没有 planned。本项已登记、未开工、未关闭，因此状态记为 new。任务卡状态是 planned。规格增量由 AI bot 另交。QA 在实现后重签，本轮不请 QA。

## 现象与证据

项目经理暂停后，本项只保留登记。过期、缺协议、受限资料能不能挂为证据，字典字段和错误码都不在本文件里写。不改 `workflow.py`，不改错误表，不改 OpenAPI。

## 影响与分流

- 开工条件：排在 BE-M0-T13 之后。规格增量由 AI bot 提交后再实现。
- 本轮不改接口、错误表、冻结名单、OpenAPI、`docs/reference/`、PRD、ROADMAP、PROJECT_BRIEF、工作流。
- 实现后由 QA 重签。不重开 ISSUE-031。
- ISSUE-018 仍为 in-progress。BE-M0-T13 仍为 in-review。APP-M2-T114 仍为 in-review。不标 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T18 | 挂证据规则。字典对照和错误码本轮不定 | 实现时再定 | AC-01～AC-02 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 规格增量到位后再改挂接拒绝。本轮无接口改动 | 未执行 |
| AC-02 | 实现后由 QA 重签。卡片完成后为 in-review，不由开发者标 done | 未执行 |

未做浏览器、服务或发布验收。new 不是 closed，planned 不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改 | 不改 `docs/PRD.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。理由同 PRD | 不改 `docs/ROADMAP.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。本轮不改运行结构 | 不改 `docs/ARCHITECTURE.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 BE-M0-T18，状态 planned | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。活计数加一张 planned 卡 | `docs/PROJECT_STATUS.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue 与同步表 | `docs/DOCUMENT_INDEX.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已改 |
| PROJECT_BRIEF | 无影响。里程碑快照不改 | 不改 `docs/PROJECT_BRIEF.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已核对 |

同步摘要见 [ISSUE-033 同步](../docs/governance/ISSUE-033-sync.md)。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | evidence-mount-1 / new | 项目经理暂停。只登记 ISSUE-033 与 BE-M0-T18。不写字典对照，不定错误码，不改接口 | 本文件 |

## 本地验收与后续合入发布

- 本地验收：未执行。本轮不改接口。
- 未覆盖：挂接拒绝、规格增量和 QA 重签。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-033-sync.md)。
- PR：未新开。合入与发布均未发生。
