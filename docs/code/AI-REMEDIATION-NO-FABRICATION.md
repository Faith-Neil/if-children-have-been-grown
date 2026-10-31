为什么有这个文件：解释整改引擎去除编造行为后的代码路径。

它解决什么问题：说明哪些问题仍可自动修正、模型改写如何被复核，以及与人工处理队列的衔接。

# AI-REMEDIATION-NO-FABRICATION：代码解释

- 对应任务 AI-REMEDIATION-NO-FABRICATION；Issue [ISSUE-039](../../issues/ISSUE-039.md)；交付 [交付](../delivery/AI-REMEDIATION-NO-FABRICATION.md)
- 提交 `06f107d`

## 改了什么以及为什么

| 原行为（Wave 10） | 现行为 |
|---|---|
| `POSITIVE_RESPONSE_REPLACEMENTS` 把偏离改成“完全满足” | 删除该表；偏离保留原文，转人工（`BUSINESS_DEVIATION`，★/废标章节为 `STAR_OR_DISQUALIFY`） |
| 无依据【待补】/TODO 改成“已全面落实…” | 只有已确认事实时替换为事实变量，否则保留并转人工 |
| 依据外 `[证:x]` 换成白名单第一项 | 循环中不改动、转人工（`EVIDENCE_CITATION`）；仅整改建议文本中改为【待补：依据】 |
| 最多 5 轮“重写直到通过” | 按 PRD §5.7.4 停止条件，默认 3 轮检查、2 次修正 |
| 整改 Prompt 要求“严禁负偏离”“100%正向承诺” | 改为“不得新增或改动数字、人员、证据；无依据写【待补】；偏离原样保留” |

## 入口和调用顺序

`ChapterGenerationService.remediate_chapter_candidate` → 组装 `LoopContext`（本章证据、片段、事实、是否★/废标）→ `run_chapter_loop(..., model_fix)`；`model_fix` 调 `model_provider.suggest`，返回结果经 `model_fix_is_safe` 复核，不通过则用 `deterministic_fix` → 用 `validate_chapter_candidate` 计算分数 → 保存候选并 `record_loop` 写入人工处理队列。`start_chapter_generation(auto_remediate=True)` 用 `auto_save=False` 调用，再在自身保存事务中记录循环。

## 关键判断与异常

- `model_fix_is_safe`：新数字、新引用、新的非自动修正类缺陷、对话残留或换行任一出现即拒绝。
- 返回结构保留原字段（`remediation_passed` 等），新增 `loop_stop_reason`、`human_issues`、`loop`。`remediation_passed` 现在如实反映是否还有阻断问题。
- 修复了 Wave 10 遗留的委派缺陷：`WorkflowService` 与 `DemoService` 的 `start_chapter_generation` 未透传 `auto_remediate`（提交 `1758920`）。

## 验证与限制

见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。安全复核是保守的字符级规则，会拒绝部分合理改写（例如模型把“7×24”写成“7x24”）；被拒时回落确定性修正，不会放行编造。
