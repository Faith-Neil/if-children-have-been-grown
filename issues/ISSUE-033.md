为什么有这个文件：登记挂证据时过期、缺协议和受限资料的拒绝规则。

它解决什么问题：前端抽屉已经拦住这三类资料，条款 PATCH 还没有；先把字典字段和可复用错误码写清楚，避免另造一套码。

# ISSUE-033：挂证据拒绝过期、缺协议和受限资料

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
| 本地验收 | 未执行。本轮只登记研究，不改接口 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 尚未建立。任务为 planned，无运行时代码 |
| 代码 / 流程解释 | 无代码影响。当前拒绝只在 `workflow.py` 的 `patch_requirement` |
| 验证记录 | 未执行。实现后再补 |

登记时 Issue 看板没有 planned。本项已登记、未开工、未关闭，因此状态记为 new。任务卡状态是 planned。规格增量由 AI bot 另交。QA 在实现后重签，本轮不请 QA。

## 现象与证据

`PATCH /api/v1/projects/{project_id}/requirements/{requirement_id}` 在 `workflow.py` 454–461 行只做三件事：证据不存在或不是本公司返回 404 `NOT_FOUND`；`type == "history"` 或 `status != "confirmed"` 返回 409 `EVIDENCE_NOT_USABLE`（文案「历史标书仅可参考；其他证据必须先确认。」）；`evidence_ids` 重复返回 422 `DUPLICATE_EVIDENCE`。这条 PATCH 不看有效期、协议和受限。

前端 `evidenceDecision`（`frontend/web/src/evidence-drawer.ts`）另外拒绝：`restricted` 为「受限无权」；`source_tier === 'partner'` 且 `agreement_present !== true` 为「缺协议」；`valid_until` 早于投标截止日为「过期」。这三项后台还没拦截。

检查发现里已经有同名码，但不是这次 PATCH 的 HTTP 错误：`workflow.py` 约 817 行对失效或不能作证据的挂接记 `EVIDENCE_NOT_USABLE`；约 823 行在 `valid_until` 早于投标截止时间时记 `EVIDENCE_EXPIRED`。`generation_context.py` 也用这两个发现码。

## 字典字段对照

只读依据是 `docs/reference/product/kb-data-dictionary-v1.9.md` 与 `prd-mvp-v1.8.md`。本项不改这两份。前端三个名字里，只有 `source_tier` 与字典列名相同。`matrix_evidence` 不存这三列，只快照挂接时的确认状态和截止时有效期状态。

| 前端字段 | 字典列 | 所在表 | 类型 | 必填 | 枚举或取值 |
|---|---|---|---|---|---|
| `source_tier` | `source_tier` | G 组。带 G 组的业务表都有（资质、证明、人员、人员证书、授权、业绩、方案片段等）。不是 `matrix_evidence` | 代码〈source_tier〉 | 是 | `own` 本公司、`partner` 合作伙伴、`reference` 仅供参考（4.1 节，内置） |
| `source_tier` 的引用快照 | `source_tier_at_use` | `bid_archive_ref` | 代码〈source_tier〉 | 系统 | 同上 |
| `restricted` | `is_restricted` | 同上，G 组。没有名为 `restricted` 的列 | 布尔 | 是 | 默认否。为是时，只有公司管理员、资料管理员和 `resource_acl` 中的人可见、可引用 |
| 受限授权名单 | `ref_type`、`ref_id`、`user_id` | `resource_acl`（3.10.7.6） | `ref_type` 代码〈owner_type〉；`ref_id` 标识；`user_id` 引用→sys_user | 三列都是 | 唯一 `(ref_type, ref_id, user_id)`。被授权人须属同一公司 |
| `agreement_present` | 无此列。由 `agreement_attachment_id` 是否已填派生 | `project_partner`（3.10.1.3） | 引用→attachment | 条件 | 引用合作方资料前必填。槽位 `consortium_agreement` 或 `subcontract_agreement` |
| 合作关系 | `relation_type` | `project_partner` | 代码〈partner_relation〉 | 是 | `consortium_member` 联合体成员、`subcontractor` 分包方 |
| 合作方主体 | `partner_entity_id` | `project_partner` | 引用→org_entity | 是 | 主体范围须为合作伙伴 |
| 前端 `valid_until` | `valid_to` | V 组。有有效期的表才有 | 日期 ★ | 条件 | 未勾选长期有效时必填 |
| 有效期起 | `valid_from` | V 组 | 日期 | 否 | |
| 长期有效 | `is_long_term` | V 组 | 布尔 | 是 | 默认否 |
| 有效期状态 | `validity_status` | V 组 | 代码〈validity_status〉 | 系统 | `valid` 有效（剩余＞90 天或长期）、`expiring` 临期（0～90 天）、`expired` 过期、`unknown` 待补录 |
| 剩余天数 | `days_to_expiry` | V 组 | 整数 | 系统 | 长期有效为空 |
| 已提醒阶段 | `alert_stage` | V 组 | 代码〈alert_stage〉 | 系统 | `none`、`d90`、`d30`、`d7`、`overdue` |
| 截止时快照 | `validity_status_at_deadline` | `matrix_evidence` | 代码〈validity_status〉 | 系统 | 按 `bid_project.bid_deadline_at` 计算；变化时矩阵行回到「已响应待确认」 |

PRD 5.4.1 与字典 R01～R03：可引用须同时满足已启用、未删除、确认状态为已确认、审核开关打开时已审、来源为 `own` 或（`partner` 且项目已登记该合作方并上传协议）、有有效期的资料在投标截止时间仍有效。`reference` 永不进入正文（R02，阻断）。合作方无协议阻断（R02）。有效期止早于投标截止时间阻断；待补录是警告不是阻断（R03）。受限资料还须在授权名单内（R01）。判断用投标截止时间，不用今天。

## 错误码：复用，不新增

冻结表里没有协议、`is_restricted` 或 `source_tier` 专用码。建议复用，本轮不改 `errors.py`、`frozen_error_codes.py` 和 OpenAPI。

| 拒绝情形 | 现有冻结码 | HTTP | 建议 |
|---|---|---|---|
| 有有效期，且 `valid_to` 早于 `bid_deadline_at`（非长期） | `EVIDENCE_EXPIRED` | 409 | 复用。检查发现已经用这个名字。不要再造一个过期码 |
| `source_tier=reference`，或 `partner` 但项目没有该合作方的 `agreement_attachment_id` | `EVIDENCE_NOT_USABLE` | 409 | 复用。文案或 details 写明「仅供参考」或「缺协议」。没有缺协议专用码 |
| `is_restricted` 且调用人不是公司管理员、资料管理员，也不在 `resource_acl` | `FORBIDDEN` | 403 | 复用。这是权限拒绝。不要用 `MATRIX_RESPONSE_FORBIDDEN`，那个码只表示「只能填写本人负责分册或章节」 |
| 不存在或他公司 | `NOT_FOUND` | 404 | 已在用，保持 |
| 历史标书或未确认 | `EVIDENCE_NOT_USABLE` | 409 | 已在用，保持 |
| 同一证据重复挂接 | `DUPLICATE_EVIDENCE` | 422 | 已在用，保持 |

`expiring` 只要截止时仍覆盖，可以挂。`unknown`（待补录）按 R03 是警告，不在这条 PATCH 上做成 409，除非规格增量另写。

若 AI bot 的规格增量改为新码，那个提交必须同时更新 `FROZEN_NAMES`。在保住草案操作和 `deprecated` 标注之前，不要重跑 `export_openapi.py`。本轮两种都不做。

## 影响与分流

- 开工条件：排在 BE-M0-T13 之后。规格增量由 AI bot 提交后再实现拒绝。
- 本轮不改 `workflow.py`、错误表、冻结名单、OpenAPI、`docs/reference/`、PRD、ROADMAP、PROJECT_BRIEF、工作流。
- 实现后由 QA 重签挂接拒绝。若那个提交新增了错误码，冻结名单一并重签。不重开 ISSUE-031。
- ISSUE-018 仍为 in-progress。BE-M0-T13 仍为 in-review。APP-M2-T114 仍为 in-review。不标 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| BE-M0-T18 | 条款 PATCH 按上表拒绝过期、缺协议、仅供参考和受限证据 | `workflow.py` 的 `patch_requirement`；规格增量另由 AI bot 提交 | AC-01～AC-04 | planned |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 截止时已过期的证据，PATCH 返回 409 `EVIDENCE_EXPIRED` | 未执行 |
| AC-02 | `reference`，以及已登记合作方但没有 `agreement_attachment_id` 的 `partner`，PATCH 返回 409 `EVIDENCE_NOT_USABLE`，文案能区分缺协议 | 未执行 |
| AC-03 | 受限且调用人不在授权范围时，PATCH 返回 403 `FORBIDDEN`，不用 `MATRIX_RESPONSE_FORBIDDEN` | 未执行 |
| AC-04 | 未新增错误码；若规格增量改为新码，同一提交更新冻结名单，并由 QA 重签。卡片完成后为 in-review，不由开发者标 done | 未执行 |

未做浏览器、服务或发布验收。new 不是 closed，planned 不是 done。

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。里程碑快照不改。产品规则仍以参考 PRD v1.8 为准 | 不改 `docs/PRD.md` | evidence-mount-1 / ISSUE-033 / 2026-10-12 | 已核对 |
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
| 2026-10-12 | evidence-mount-1 / new | 对照字典 v1.9 与 PRD v1.8。建议复用 `EVIDENCE_EXPIRED`、`EVIDENCE_NOT_USABLE`、`FORBIDDEN`。规格增量交给 AI bot。实现后 QA 重签 | 字典 G/V 组、`project_partner`、`resource_acl`、`matrix_evidence`；`workflow.py` 454–461 与 817–823 |

## 本地验收与后续合入发布

- 本地验收：未执行。本轮不改接口。
- 未覆盖：PATCH 拒绝、规格增量和 QA 重签。
- 六份基线：见上表与 [同步表](../docs/governance/ISSUE-033-sync.md)。
- PR：未新开。合入与发布均未发生。
