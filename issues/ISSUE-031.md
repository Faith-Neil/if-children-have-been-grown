为什么有这个文件：登记把 143 个错误码名字冻成一份名单。

它解决什么问题：避免删掉一个旧码、加上一个新码之后，总数仍是 143，导出的接口说明也跟着新表走，检查却发现不了。

# ISSUE-031：冻结错误码名字

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-031 |
| 类型 | change |
| 优先级 | P2 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | frozen-names-1 |
| 关联 Task | [BE-M0-T16](../docs/tasks/BE-M0.md#be-m0-t16) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 2026-10-12 后台测试通过。删 `SECRET_KEY_UNAVAILABLE`、加 `NOT_A_REAL_CODE` 并重新导出后，名单对照失败。等待项目经理 QA 签收 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T16](../docs/delivery/BE-M0-T16.md) |
| 代码 / 流程解释 | [BE-M0-T16](../docs/code/BE-M0-T16.md) |
| 验证记录 | [2026-10-12 冻结名单](../docs/testing/2026-10-12-issue-031-frozen-error-codes.md) |

## 现象与证据

`tests/backend/qa_error_idempotency_live_http.py` 已经按名字比较 `x-error-status`、`ERROR_STATUS` 和 `V1Error.code` 枚举，并核对总数 143。这三份都来自同一张运行时表，或由 `export_openapi.py` 从这张表写出。因此把 `errors.py` 里的一个旧码换成一个新码，再导出 OpenAPI，总数仍是 143，spec 与代码仍然相等。

## 影响与分流

- 本卡只增加一份不随导出重写的名字名单，并让测试拿 `set(ERROR_STATUS)` 和 spec 枚举去对它。
- 不新增、不删除任何一个现有错误码。不改 HTTP 状态。不改重试说明。
- 不改 `docs/reference/`。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。不改工作流文件。
- ISSUE-005 仍为 in-progress。ISSUE-024 仍为 new。ISSUE-030 不使用。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T16 | 143 个错误码名字写入冻结名单，增删必须同一提交更新 | `backend/bid-core/icg_demo/frozen_error_codes.py` | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | `set(ERROR_STATUS) == FROZEN_NAMES`，且 spec 的 `V1Error.code` 枚举与这份名单相同 | 2026-10-12 契约测试通过。见验证记录 |
| AC-02 | 在代码和 spec 里删一个旧码、加一个新码，再用 `export_openapi.py` 导出后，上述对照失败；总数仍可为 143 | 临时把 `SECRET_KEY_UNAVAILABLE` 换成 `NOT_A_REAL_CODE`。对照失败后已还原，仓库里没有这个探测码 |
| AC-03 | 接口约定写明：增删错误码必须在同一提交更新冻结名单 | `spec/openapi/README.md` 修改与验收 |
| AC-04 | 卡片与本 Issue 均为 in-review，不标 done，不标 closed | 看板与本文件 |

未做浏览器、服务或发布验收。in-review 不是 closed，也不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改。本卡不改产品规则 | 不改 `docs/PRD.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。理由同 PRD | 不改 `docs/ROADMAP.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。错误码名单在接口约定和代码里 | 不改 `docs/ARCHITECTURE.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。新增 BE-M0-T16，状态 in-review | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。活计数加一张 in-review 卡 | `docs/PROJECT_STATUS.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、说明和验证 | `docs/DOCUMENT_INDEX.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已改 |
| PROJECT_BRIEF | 无影响。里程碑快照不改 | 不改 `docs/PROJECT_BRIEF.md` | frozen-names-1 / ISSUE-031 / 2026-10-12 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | frozen-names-1 / in-review | 冻结名单已写入。done 与 closed 等待项目经理在 QA 后设置 | [验证](../docs/testing/2026-10-12-issue-031-frozen-error-codes.md) |

## 本地验收与后续合入发布

- 本地验收：2026-10-12，见验证记录。只用合成数据。
- 未覆盖：项目经理 QA 签收。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-031-sync.md)。
- PR：未新开。合入与发布均未发生。
