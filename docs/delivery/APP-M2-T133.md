为什么有这个文件：记录 APP-M2-T133 人工处理队列的实际交付、验收与限制。

它解决什么问题：说明主导航“人工处理队列”已由占位页换成真实队列，以及哪些部分仍未完成。

# APP-M2-T133：人工处理队列列表交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T133 |
| 代码解释 | [APP-M2-T133 代码说明](../code/APP-M2-T133.md) |
| 验收 | 后端 `tests/backend/test_human_queue.py` 11 项通过；前端 `tests/unit/main-path-core.test.mjs` 8 项通过；全量回归见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。QA 独立复测与 PD 验收未执行 |
| 项目进度 | in-review；Wave 11 共 5 张卡 in-review；下一步 QA/PD 签署，建议 PM 标 done 由 PM 决定 |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-040](../../issues/ISSUE-040.md)、[ISSUE-007](../../issues/ISSUE-007.md)；任务卡 [APP-M2-T133](../tasks/APP-M2.md#app-m2-t133)
- 分支 `feat/wave-11-main-path`，提交 `06f107d`（后端）、`2c8d51c`（前端）；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 草稿
- 本地验收：开发自测通过；未合入、未发布

## 完成内容与变更文件

- 章节循环规则引擎 `backend/bid-core/icg/domain/chapter_loop.py`：按 PRD §5.7.4 判定处理路径（直接转人工 7 类原因、升级转人工 2 类原因）、停止条件（修正引入新问题回退 / 全部解决 / 剩余需人工 / 达到最大轮数 / 未减少）、同一问题修正 2 次升级转人工、问题指纹跨轮沿用编号。
- 队列服务 `backend/bid-core/icg/domain/human_queue.py` 与接口 `backend/bid-core/icg/api/chapter_loop.py`：`listHumanQueue`、`getChapterLoop`、`resolveHumanIssue`、`rejectHumanIssue`、`recheckChapter`。
- 生成与整改路径接入：`auto_remediate` 和 `/remediate-candidate` 的循环结果写入队列（`chapter_generation.py`）。
- 前端 `frontend/web/src/project/ManualQueuePage.tsx`、`main-path-core.ts`：替换 `manual` 页签的 `PendingPage`；页签角标改为后台返回的 `human_queue_pending`。
- 新错误码：`HUMAN_ISSUE_NOT_PENDING`、`BLOCKER_NOT_REJECTABLE`、`VOLUME_FINALIZED`、`CHAPTER_CONTENT_EMPTY`。

## 验收结果

| 验收点（PRD §5.7.7） | 结果 | 证据 |
|---|---|---|
| ① 七类直接转人工问题从不出现在自动修正中 | 通过 | `test_direct_human_categories_are_never_auto_fixed`、`test_star_requirement_routes_placeholder_to_human_and_fact_variable_is_auto`、`test_system_generated_chapter_problems_go_to_human` |
| ② 阻断级问题没有“驳回” | 通过 | 后台 409 `BLOCKER_NOT_REJECTABLE`；接口返回 `permissions.reject=false`，页面不渲染按钮 |
| ③ 全部待人工问题处理完自动“人工已处理” | 通过 | `test_blocker_cannot_be_rejected_and_resolving_all_marks_human_handled` |
| ④ 未经确认的审查清单候选不进入检查 | 不适用 | 审查清单候选（§5.7.7 操作 5）未实现，见限制 |
| ⑤ 重新检查产生新一次循环、历史保留 | 通过 | 同上测试：`loop_no=2`，同指纹沿用原编号 |
| 权限：只读可看不可操作、跨公司 404、警告只能负责人驳回 | 通过 | `test_queue_visibility_and_tenant_isolation`、`test_warning_rejection_requires_project_lead` |
| 编辑中章节不能重新检查；缺版本号 428 | 通过 | `test_recheck_refuses_locked_chapter_and_needs_version` |
| 关演示 + MySQL 主路径冒烟 | 未执行 | 本机无 MySQL；持久化由 CI `backend-mysql` 的 `test_mysql_workflow_state.py` 覆盖 |

## 项目进度

APP-M2-T133 → in-review。同批 APP-M2-T144、APP-M2-T111、AI-REMEDIATION-NO-FABRICATION、BE-WORKFLOW-STATE-PERSIST 均为 in-review。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 实施澄清 A1、A7、A8 见 [PRD 实施澄清](../decisions/2026-10-28-prd-amendments-wave11.md)，[PRD](../PRD.md) 正文登记 |
| ROADMAP | 无影响：阶段不变 |
| ARCHITECTURE | 已登记章节循环与队列模块 |
| Issue 看板/详情 | ISSUE-040、ISSUE-039 登记 |
| TASK_BOARD / PROJECT_STATUS | 已同步 |
| DOCUMENT_INDEX | 已登记 |

## 风险与后续

- 章节循环进度页与轮次时间线（APP-M2-T130/T131）未做；后台 `getChapterLoop` 已返回轮次数据。
- “重新检查”只做确定性修正，不调用模型；模型评审 R28 尚未进入循环。
- 未做：审查清单候选、队列详情单段编辑（APP-M2-T134）、站内提醒（APP-M2-T029 起）。
- 规则层检查目前覆盖 R15/R34/R37/R24/R01/R02 六类；其他规则在分册与全文检查中运行，不进入循环。
