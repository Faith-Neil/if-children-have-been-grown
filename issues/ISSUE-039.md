为什么有这个文件：登记章节自动整改引擎编造内容、违反“不编造”红线的缺陷及修复。

它解决什么问题：防止系统把“无法满足”自动改成“完全满足”、把【待补】填成空泛承诺、把依据外证据换成别的证据编号。

# ISSUE-039：章节自动整改引擎编造承诺与依据

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-039 |
| 类型 | bug |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [AI-REMEDIATION-NO-FABRICATION](../docs/tasks/AI-M0.md#ai-remediation-no-fabrication)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)（草稿，目标 feat/opencode-ICG） |
| 本地验收 | 开发自测通过（2026-10-28），待 QA 独立复测 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-REMEDIATION-NO-FABRICATION 交付](../docs/delivery/AI-REMEDIATION-NO-FABRICATION.md) |
| 代码 / 流程解释 | [代码说明](../docs/code/AI-REMEDIATION-NO-FABRICATION.md) |
| 验证记录 | [Wave 11 验证](../docs/testing/2026-10-28-wave-11-verification.md) |

## 现象与证据

Wave 10 交付的 AI-OUTLINE-AUTO-REMEDIATION（`backend/bid-core/icg/domain/chapter_generation.py`）在自动整改时：

1. 用 `POSITIVE_RESPONSE_REPLACEMENTS` 把“无法提供”“存在负偏离”“不满足”等确定性替换为“已完整具备并随时提供”“完全响应并优于招标要求”“完全满足”；
2. 把没有依据的【待补】【待定】TODO 替换成“已按招标规范全面落实并具备实施条件”“已全面具备并满足要求”；
3. 把本章依据外的 `[证:xxx]` 替换为白名单里的第一个证据编号；
4. 测试 `test_ai_outline_auto_remediation.py` 把上述行为当作验收通过条件，Wave 10 的 QA/PD 也据此签署。

这直接违反 PRD v1.8 §1.4 原则 3（没有依据就写【待补】）、§5.7.4 第 4 条（缺证据、商务偏离、承诺数值、证据引用问题直接转人工，自动修正永远不改动它们）以及 AGENTS.md 金标准第 2 条。

## 影响与分流

- 影响范围：单章生成 `auto_remediate=True`、批量流水线、`/remediate-candidate` 接口产出的候选正文；若被采纳会进入递交文件，属废标与虚假承诺风险。
- 本次处理范围：删除翻转表；整改只做不编造的确定性修正；改由 PRD §5.7.4 规则编排的章节循环决定处理路径，直接转人工的问题进入人工处理队列；模型改写须通过安全复核。按 PRD 重写 `test_ai_outline_auto_remediation.py` 的断言（现 14 项，含新增“全部可自动修正时收敛”用例）。
- 已签署记录：D-836/D-837 的结论保留原文，不追改；本 Issue 作为其后发现的回归缺陷记录。
- 依赖与阻塞解除条件：无。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-REMEDIATION-NO-FABRICATION | 整改引擎不编造，直接转人工的问题不进入自动修正 | `backend/bid-core/icg/domain/chapter_generation.py`、`backend/bid-core/icg/domain/chapter_loop.py`、`tests/backend/test_ai_outline_auto_remediation.py`、`tests/backend/test_human_queue.py` | AC-01～AC-03 | in-review |

## 验收标准

- AC-01：偏离表述、无依据【待补】、依据外证据编号在任何自动修正后原样保留（证据编号最多改为【待补：依据】），并进入人工处理队列。
- AC-02：模型改写带入新数字、新证据引用或新的直接转人工缺陷时被拒绝，回落到确定性修正。
- AC-03：只有可自动修正的问题时循环以“问题全部解决”停止；否则如实停在“待人工处理”，不以“已通过”冒充。

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 有影响 | 新增实施澄清 A1/A8，见 [PRD 实施澄清](../docs/decisions/2026-10-28-prd-amendments-wave11.md)，在 [PRD](../docs/PRD.md) 正文登记 |
| ROADMAP | 无影响 | 阶段与里程碑不变 |
| ARCHITECTURE | 有影响 | 章节循环模块说明写入 [ARCHITECTURE](../docs/ARCHITECTURE.md) |
| TASK_BOARD | 有影响 | 新增 AI-REMEDIATION-NO-FABRICATION |
| PROJECT_STATUS | 有影响 | 记录缺陷与修复 |
| DOCUMENT_INDEX | 有影响 | 登记本 Issue、交付与代码说明 |
