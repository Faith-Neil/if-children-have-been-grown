为什么有这个文件：记录 APP-M2-T144 分册检查后的交叉复核、定稿与解锁的实际交付。

它解决什么问题：说明“交叉复核和完整分册定稿”从未实现清单移出所依据的证据与仍未完成的部分。

# APP-M2-T144：分册检查 / 定稿 / 解锁 / 交叉复核交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T144 |
| 代码解释 | [APP-M2-T144 代码说明](../code/APP-M2-T144.md) |
| 验收 | `tests/backend/test_volume_cross_review.py` 5 项、更新后的 `test_volume_finalize_gate.py` 10 项与 `test_submission_finalize_gate.py` 1 项通过；前端定稿动作逻辑单测通过。QA/PD 未执行 |
| 项目进度 | in-review；同批 5 张卡 in-review |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-040](../../issues/ISSUE-040.md)；任务卡 [APP-M2-T144](../tasks/APP-M2.md#app-m2-t144)
- 分支 `feat/wave-11-main-path`，提交 `06f107d`、`2c8d51c`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 草稿
- 未合入、未发布

## 完成内容与变更文件

- `backend/bid-core/icg/domain/volume_review.py`（新）：编写人判定、章节快照、指定与确认复核、解锁重置。
- `backend/bid-core/icg/domain/volume_finalize.py`：本册负责人可定稿本册；定稿要求待人工问题清零与有效复核；保存快照；解锁使复核作废并推进解锁轮次。
- `backend/bid-core/icg/domain/input_snapshot.py`：解锁轮次进入输入指纹。
- `backend/bid-core/icg/domain/domain.py`：已定稿分册章节后台只读。
- `backend/bid-core/icg/domain/export_service.py`：递交版导出核对定稿快照。
- `backend/bid-core/icg/api/volumes.py`：`assignCrossReviewer`、`confirmCrossReview`；状态响应带 `cross_review`、`pending_human_issues`。
- `backend/bid-core/icg/domain/workflow_orchestrator.py`：`UNIMPLEMENTED_RULES` 移除“交叉复核和完整分册定稿”。
- `frontend/web/src/project/VolumeFinalizePanel.tsx`（新）接入导出页。

## 验收结果

| 验收点（任务卡） | 结果 | 证据 |
|---|---|---|
| 指定非本册编写人交叉复核再定稿 | 通过 | `test_reviewer_rules`：编写人做复核 409、只读 422、编写人指定 403、他人确认 403 |
| 定稿绑定章节快照 | 通过 | `test_finalize_requires_review_on_current_content`：复核后改正文 → `stale` → 定稿 409；重新复核后定稿记录含快照 |
| 解锁理由必填并让检查/输出过期 | 通过 | `test_finalized_volume_is_read_only_in_backend_and_unlock_invalidates`：解锁后旧检查为 `stale`，复核 `none` |
| 阻断级无放行 | 保持 | 定稿仍由 `check_volume_blockers` 拦截；本卡未新增警告放行入口 |
| 待人工问题未清零不能定稿 | 通过 | `test_pending_human_issues_block_finalize` |
| 定稿后后台拒绝写入 | 通过 | 取得编辑权 409 `VOLUME_FINALIZED`；重新检查 409 |
| 本册负责人定稿本册、不能定稿他册 | 通过 | `test_volume_owner_can_finalize_own_volume` |
| 与 05 检查页并排截图 | 未执行 | 本轮无截图留证 |
| 关演示 + MySQL 冒烟 | 部分 | 跨仓储读取定稿与复核由 `test_mysql_workflow_state.py` 在 CI `backend-mysql` 覆盖；完整关演示人工冒烟未执行 |

## 项目进度

APP-M2-T144 → in-review。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 实施澄清 A2～A4、A7，见 [PRD 实施澄清](../decisions/2026-10-28-prd-amendments-wave11.md) |
| ROADMAP | 无影响 |
| ARCHITECTURE | 已登记 |
| Issue 看板/详情 | ISSUE-040 |
| TASK_BOARD / PROJECT_STATUS | 已同步 |
| DOCUMENT_INDEX | 已登记 |

## 风险与后续

- 递交版仍会被未实现的规则组（`UNIMPLEMENTED_RULES` 余 4 组）与检查结果拦截，本卡不改变 `RULES_INCOMPLETE` 的诚实口径。
- 全文检查三场景、警告逐条放行留痕、“结果已过期”提示（APP-M2-T145）未做。
- 前端角色判断仅用于显示；后台每次重新核对。
