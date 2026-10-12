为什么有这个文件：登记挂证据规则这张卡，排在 T13 之后。

它解决什么问题：先占住 ISSUE-033 和任务号，避免别人另开一张。本轮不查字典、不定错误码、不改接口。

# ISSUE-033：挂证据规则

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-033 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-progress |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | evidence-mount-spec-1 |
| 关联 Task | [BE-M0-T18](../docs/tasks/BE-M0.md#be-m0-t18) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | 冻结契约已写字段和挂接拒绝。运行时未接通。见 [同步](../docs/governance/ISSUE-033-sync.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 尚未建立。任务为 planned，无运行时代码 |
| 代码 / 流程解释 | 只改冻结契约。不改 `backend/bid-core` 应用代码 |
| 验证记录 | 未执行。实现后再补 |

登记时 Issue 看板没有 planned，当时状态记为 new。项目经理批准后，规格增量写入冻结契约，状态改为 in-progress。BE-M0-T18 仍是 planned。后台另实现运行时。QA 在实现后重签。不标 closed。

## 现象与证据

项目经理暂停后，本项只保留登记。过期、缺协议、受限资料能不能挂为证据，字典字段和错误码都不在本文件里写。不改 `workflow.py`，不改错误表，不改 OpenAPI。

## 规格增量

字典 v1.9 命名，写在 `spec/openapi/demo-v1.json` 的冻结模型 `EvidenceMountFields`，以及 `GET /api/v1/library` 和条款 `PATCH` 的 `x-issue-033`。`x-implemented` 仍是 false。运行中的 `LibraryItem` 不增加这些字段。

| 字段或规则 | 约定 |
|---|---|
| `source_tier` | `own`、`partner`、`reference`。`reference` 不能挂，返回 409 `EVIDENCE_NOT_USABLE` |
| `is_restricted` | 布尔，默认 false。不用 `restricted`。受限时还看 `resource_acl`；没有 ACL 或非管理员返回 403 `FORBIDDEN` |
| `agreement_present` | 派生、只读、不入库。由 `project_partner.agreement_attachment_id` 是否已设置得出。partner 且缺协议返回 409 `EVIDENCE_NOT_USABLE`，message 可以和 reference 区分 |
| 有效期 | `valid_to` 与 `is_long_term` 对照项目 `bid_deadline_at`，不对照今天。过期返回 409 `EVIDENCE_EXPIRED`。`expiring` 仍覆盖截止时间，允许挂接。`unknown` 只警告，不返回 409 |

不新增错误码。`V1Error` 枚举仍是 143 个。不改 `frozen_error_codes.py`，不改 `errors.py`。

## 影响与分流

- 开工条件：排在 BE-M0-T13 之后。规格增量已写入冻结契约，运行时由后台另实现。
- 本轮不改应用代码、错误表、冻结名单、`docs/reference/`、PRD、ROADMAP、PROJECT_BRIEF、工作流。
- 实现后由 QA 重签。不重开 ISSUE-031。不标 closed。
- ISSUE-018 仍为 in-progress。BE-M0-T13 仍为 in-review。APP-M2-T114 已 done（QA f521950，PM 17:13 确认）。BE-M0-T18 仍为 planned。本 Issue 不标 closed。缺协议、受限、智能匹配和规则 2 端到端仍在本 Issue。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T18 | 挂证据规则。规格已冻结，运行时未接通 | `spec/openapi/demo-v1.json` 的 `EvidenceMountFields` 与 `x-issue-033` | AC-01～AC-02 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 规格增量到位后再改挂接拒绝。字段和拒绝规则已写入冻结契约 | 契约测试核对字段名和三个已有错误码。运行时未接通 |
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
| 2026-10-12 | evidence-mount-spec-1 / in-progress | 项目经理批准后，按字典 v1.9 写入 `source_tier`、`is_restricted`、派生的 `agreement_present`，以及对照 `bid_deadline_at` 的 `valid_to` / `is_long_term`。挂接拒绝复用 409 `EVIDENCE_EXPIRED`、409 `EVIDENCE_NOT_USABLE`、403 `FORBIDDEN`。不新增错误码。BE-M0-T18 仍 planned。不标 closed | [同步](../docs/governance/ISSUE-033-sync.md) |

## 本地验收与后续合入发布

- 本地验收：2026-10-12 只核对冻结契约。运行时挂接拒绝未执行。
- 未覆盖：后台尚未按这些规则拒绝挂接。QA 重签留到实现之后。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-033-sync.md)。
- PR：未新开。合入与发布均未发生。
