为什么有这个文件：记录整改引擎去除编造行为（ISSUE-039）的交付与验收。

它解决什么问题：说明 Wave 10 已签署的整改能力中哪些行为被撤回、依据是什么、如何验证。

# AI-REMEDIATION-NO-FABRICATION：整改引擎不编造交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-REMEDIATION-NO-FABRICATION |
| 代码解释 | [代码说明](../code/AI-REMEDIATION-NO-FABRICATION.md) |
| 验收 | `tests/backend/test_ai_outline_auto_remediation.py` 14 项按 PRD 断言通过；`tests/backend/test_human_queue.py` 中 6 项循环规则用例通过；`test_outline_generation_start.py::test_workflow_service_delegation` 由失败转为通过。QA/PD 未执行 |
| 项目进度 | in-review |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-039](../../issues/ISSUE-039.md)；任务卡 [AI-REMEDIATION-NO-FABRICATION](../tasks/AI-M0.md#ai-remediation-no-fabrication)
- 提交 `1758920`、`06f107d`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 草稿；未合入

## 完成内容与变更文件

- `backend/bid-core/icg/domain/chapter_generation.py`：删除偏离翻转表；`sanitize_and_remediate_paragraph_text` 不再写入任何承诺文字；整改计划把偏离和依据外证据标为 `direct_human`；Prompt 改为不编造约束；`remediate_chapter_candidate` 改走章节循环并写入人工处理队列。
- `backend/bid-core/icg/domain/generation_orchestrator.py`、`domain.py`：透传 `auto_remediate`。
- `tests/backend/test_ai_outline_auto_remediation.py`：断言改为 PRD 口径（偏离与无依据【待补】保留、依据外证据不替换、只有可自动修正问题时收敛）。

## 验收结果

| 验收点 | 结果 | 证据 |
|---|---|---|
| AC-01 偏离、无依据【待补】、依据外证据不被自动修正，进入队列 | 通过 | `test_targeted_in_place_remediation_preserves_untouched_paragraphs`、`test_direct_human_categories_are_never_auto_fixed` |
| AC-02 模型改写带入新数字/引用被拒 | 通过 | `test_unsafe_model_rewrite_is_refused` |
| AC-03 只有可自动修正问题时“问题全部解决”，否则如实待人工 | 通过 | `test_auto_fixable_defects_converge_to_all_resolved`、`test_auto_remediate_flag_in_start_chapter_generation` |
| 涉密项目本地模型、租户与只读门禁不回退 | 通过 | 原有用例 10、11 保持通过 |

## 项目进度

in-review。Wave 10 的 QA（D-836）与 PD（D-837）签署原文保留；本卡建议 QA 对整改能力重新签署。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 实施澄清 A1、A8 |
| ROADMAP | 无影响 |
| ARCHITECTURE | 已登记 |
| Issue 看板/详情 | ISSUE-039 |
| TASK_BOARD / PROJECT_STATUS | 已同步 |
| DOCUMENT_INDEX | 已登记 |

## 风险与后续

- 批量流水线看板中“通过数”会明显下降，这是如实反映，不是回归。
- 安全复核规则较保守，见代码说明。
