为什么有这个文件：解释分册交叉复核、定稿快照与解锁失效的代码路径。

它解决什么问题：说明定稿前要满足哪些条件、快照怎样绑定、解锁后哪些结果过期。

# APP-M2-T144：代码解释

- 对应任务 APP-M2-T144；Issue [ISSUE-040](../../issues/ISSUE-040.md)；交付 [APP-M2-T144 交付](../delivery/APP-M2-T144.md)
- 提交 `06f107d`、`2c8d51c`

## 改了什么以及为什么

原定稿只看锁、正文和 blocker，不要求交叉复核，不绑定快照，解锁不让结果过期，页面没有入口，已定稿分册后台仍可取得编辑权。现按 PRD §2.3、§5.8.5 与 [实施澄清](../decisions/2026-10-28-prd-amendments-wave11.md) A2～A4、A7 补齐。

## 入口和调用顺序

1. `POST /volumes/{vid}/cross-review`（`assignCrossReviewer`）→ `VolumeReviewMixin.assign_cross_reviewer` → `_write`：管理者（项目负责人、本册负责人、公司管理员成员）才可指定；复核人须是可编辑成员且不在 `volume_editors` 中。
2. `POST /volumes/{vid}/cross-review/confirm`（`confirmCrossReview`）→ 只有被指定人；`approved` 写入 `volume_snapshot`，`returned` 必须写原因。
3. `POST /volumes/{vid}/finalize` → `VolumeFinalizeMixin.finalize_volume`：权限（新增本册负责人）→ 锁/正文 → `check_volume_blockers` → `require_cross_review`（待人工问题为 0、复核通过且快照一致）→ 写入 `workflow["volumes"][vid]`（含 `snapshot`、`cross_reviewer_id`）。
4. `POST /volumes/{vid}/unlock` → 写原因 → `reset_review_on_unlock`：`volume_epochs[vid] += 1`，复核作废并留历史。
5. `project_input_fingerprint` 在 `volume_epochs` 非空时纳入它，旧检查与导出变 `stale`；为空时不写入，既有指纹不变。
6. `DemoService._chapter_writer` 在分册已定稿时拒绝（409 `VOLUME_FINALIZED`），覆盖取得编辑权、提交、草稿等全部章节写入。
7. 递交版导出（`export_service.py`）额外比对定稿快照与当前正文，不一致则 409 `RULES_INCOMPLETE`。
8. 前端 `VolumeFinalizePanel`（导出页）按 `volumeActions` 显示指定、确认、定稿、解锁；定稿按钮在前提未满足时禁用并提示原因。

## 数据与状态

- `workflow["volume_reviews"][vid] = {status: none|pending|approved|returned, reviewer_id, assigned_by, assigned_at, decided_at, decision_note, snapshot, history[]}`
- `workflow["volumes"][vid]` 新增 `snapshot`、`cross_reviewer_id`；`workflow["volume_epochs"][vid]`
- 对外状态 `list_volumes_status` 增加 `cross_review`（去掉 `snapshot`，含 `stale`）与 `pending_human_issues`

## 关键判断与异常

- `CROSS_REVIEWER_IS_EDITOR`（409）、`CROSS_REVIEWER_REQUIRED`（403）、`CROSS_REVIEW_REQUIRED`（409，details.status = none/pending/returned/stale）、`HUMAN_ISSUES_PENDING`（409，details.chapter_ids）、`VOLUME_FINALIZED`（409）
- 编写人判定排除 `source=chapter_loop` 的系统修正版本和空正文初始版本。

## 验证与限制

见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。全文检查三场景与警告人工放行留痕（APP-M2-T145 等）未在本卡实现。
