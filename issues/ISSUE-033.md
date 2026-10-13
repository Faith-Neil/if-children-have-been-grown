为什么有这个文件：记录条款挂证据时如何拒绝过期、缺协议和受限资料。

它解决什么问题：挂接只使用已有错误码，避免过期、仅供参考、缺协议或无权的受限资料进入条款。

# ISSUE-033：挂证据规则

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-033 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | evidence-mount-2 |
| 关联 Task | [BE-M0-T18](../docs/tasks/BE-M0.md#be-m0-t18) |
| 关联 PR | 未创建。随既有分支提交，不新开 PR |
| 本地验收 | QA tip `90b2334` 运行时重签通过（REV-M0-T35）。本 Issue / BE-M0-T18 仍 in-review，不标 closed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [BE-M0-T18](../docs/delivery/BE-M0-T18.md) |
| 代码 / 流程解释 | [BE-M0-T18](../docs/code/BE-M0-T18.md) |
| 验证记录 | [2026-10-12 挂证据核对](../docs/testing/2026-10-12-be-m0-t18-evidence-mount.md) |

登记时状态为 new。规格增量写入冻结契约后为 in-progress。运行时接通后改为 in-review。不标 closed。QA 重签之前不标 done。

## 现象与证据

条款 PATCH 挂证据原先只拒绝缺失、他公司、历史标书和未确认资料。过期资料、仅供参考资料、没有协议的合作方资料，以及无权使用的受限资料，仍能挂上。项目经理批准沿用已有错误码，不新增码。

## 规格增量

字典 v1.9 命名仍写在 `spec/openapi/demo-v1.json` 的冻结模型 `EvidenceMountFields`。运行时资料对象返回 `source_tier`、`is_restricted`、`valid_to`、`is_long_term` 和 `partner_entity_id`。`agreement_present` 仍是派生、只读、不入库，挂接时按本项目合作方的 `agreement_attachment_id` 判断，不放进公司级资料行。

| 字段或规则 | 约定 |
|---|---|
| `source_tier` | `own`、`partner`、`reference`。`reference` 不能挂，返回 409 `EVIDENCE_NOT_USABLE` |
| `is_restricted` | 布尔，默认 false。不用 `restricted`。受限时还看 `resource_acl`；没有 ACL 或非管理员返回 403 `FORBIDDEN` |
| `agreement_present` | 派生、只读、不入库。由 `project_partner.agreement_attachment_id` 是否已设置得出。partner 且缺协议返回 409 `EVIDENCE_NOT_USABLE`，message 与 reference 区分 |
| 有效期 | `valid_to` 与 `is_long_term` 对照项目截止时间，对应字典 `bid_deadline_at`，不对照今天。过期返回 409 `EVIDENCE_EXPIRED`。仍覆盖截止日的可以挂接。没有到期日且不是长期有效时，这条 PATCH 不返回 409 |

不新增错误码。`V1Error` 枚举仍是 143 个。不改 `frozen_error_codes.py`，不改 `errors.py`。

## 影响与分流

- 资料字段使用 `is_restricted`。请求里的 `restricted` 返回 422 `VALIDATION_ERROR`。
- `agreement_present` 不入库。挂接时看本项目合作方行的 `agreement_attachment_id`。
- 过期比较 `valid_to`（没有则用既有 `valid_until`）和项目截止时间。`is_long_term` 为真时不因日期拒绝。
- 过期返回 409 `EVIDENCE_EXPIRED`。仅供参考，以及合作方缺协议，都返回 409 `EVIDENCE_NOT_USABLE`，两句说明不同。受限且调用者不是公司管理员、资料管理员，也不在该资料的 `resource_acl` 上，返回 403 `FORBIDDEN`。
- 不新增错误码，不改冻结名单，不改 `docs/reference/`、PRD、ROADMAP、PROJECT_BRIEF、工作流。
- 合作方和授权先留在内存。项目表对齐另见 [ISSUE-035](ISSUE-035.md)，本项不建那两张正式表。
- ISSUE-018 仍为 in-progress。BE-M0-T13 已依据 QA ae38ec3，PM 17:16 确认 done。APP-M2-T114 已 done（QA f521950，PM 17:13 确认）。APP-M2-T078 已 done（QA 19c4862，PM 17:20 确认）。本卡不标 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T18 | 条款 PATCH 拒绝过期、仅供参考、缺协议和无权受限资料 | `workflow.py`；资料与项目请求体；冻结的 `EvidenceMountFields` | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 有效期早于投标截止日且非长期有效时，挂接返回 409 `EVIDENCE_EXPIRED`。长期有效仍可挂接 | 本地通过。见验证记录；QA tip 90b2334 复跑通过 |
| AC-02 | `source_tier=reference` 与合作方缺少协议都返回 409 `EVIDENCE_NOT_USABLE`，说明分别为仅供参考和缺协议 | 本地通过。见验证记录；QA tip 90b2334 复跑通过 |
| AC-03 | `is_restricted` 且调用者不是公司管理员、资料管理员，也不在授权名单时，返回 403 `FORBIDDEN`。有授权或上述身份可以挂接 | 本地通过。见验证记录；QA tip 90b2334 复跑通过 |
| AC-04 | 不新增错误码。卡片为 in-review，QA 重签前不标 done | 错误码名单未改（143）。QA REV-M0-T35 已重签通过；不标 done |

未做浏览器验收，未合入，未发布。in-review 不是 closed，也不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改 | 不改 `docs/PRD.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。理由同 PRD | 不改 `docs/ROADMAP.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 无影响。挂接规则在现有流程里，不改架构基线 | 不改 `docs/ARCHITECTURE.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。BE-M0-T18 改为 in-review | `docs/TASK_BOARD.md`、`docs/tasks/BE-M0.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已改 |
| PROJECT_STATUS | 有影响。活计数把本卡从 planned 改为 in-review | `docs/PROJECT_STATUS.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已改 |
| DOCUMENT_INDEX | 有影响。补交付、代码解释和验证记录 | `docs/DOCUMENT_INDEX.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已改 |
| PROJECT_BRIEF | 无影响。里程碑快照不改 | 不改 `docs/PROJECT_BRIEF.md` | evidence-mount-2 / ISSUE-033 / 2026-10-12 | 已核对 |

同步摘要见 [ISSUE-033 同步](../docs/governance/ISSUE-033-sync.md)。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | evidence-mount-1 / new | 项目经理暂停。只登记 ISSUE-033 与 BE-M0-T18。不写字典对照，不定错误码，不改接口 | 本文件 |
| 2026-10-12 | evidence-mount-spec-1 / in-progress | 按字典 v1.9 写入冻结的 `EvidenceMountFields`。挂接拒绝复用 409 `EVIDENCE_EXPIRED`、409 `EVIDENCE_NOT_USABLE`、403 `FORBIDDEN`。当时运行时未接通 | [同步](../docs/governance/ISSUE-033-sync.md) |
| 2026-10-12 | evidence-mount-2 / in-review | 条款 PATCH 已按上述规则拒绝。不新增错误码。等待 QA 重签 | [BE-M0-T18](../docs/delivery/BE-M0-T18.md) |
| 2026-10-13 | evidence-mount-2 / in-review | QA 运行时重签（REV-M0-T35，tip `90b2334`）：AC-01～04 通过；无库 381/13；不标 closed | 成长测试QA |

## 本地验收与后续合入发布

- 本地验收：后台测试已跑。见验证记录。
- 未覆盖：浏览器抽屉、QA 重签、正式 `bid_project` 表。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-033-sync.md)。
- PR：未新开。合入与发布均未发生。
