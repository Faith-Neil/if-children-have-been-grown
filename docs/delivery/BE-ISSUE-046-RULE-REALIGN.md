# BE-ISSUE-046-RULE-REALIGN · 合规规则 PRD 编号重挂

| 项目 | 内容 |
|---|---|
| Task ID | BE-ISSUE-046-RULE-REALIGN |
| 状态 | in-review |
| Issue | [ISSUE-046](../../issues/ISSUE-046.md)（closed 2026-11-02） |
| 合入 | 分支 `main` @ `7e206e48b557017f9b0ea6df907faa0320fbeb0c`（基于 `cfdf5ad`） |

## 完成内容

- 19 条错位 `check_rXX` 按 [矩阵](../decisions/2026-11-02-issue-046-realignment-matrix.md) 重挂为 PRD 语义；原实现迁入 `EXT-*` 并在 `evaluate_p*` 中可选执行。
- 新增 `icg/domain/compliance_prd_checks.py`；`compliance_rules.py` 保留 `_legacy_misaligned_rXX` 供 EXT 包装。
- 测试：`tests/backend/test_compliance_rules*.py` 46 passed（2026-11-02 本机）。

## 验收

| 项 | 结果 |
|---|---|
| pytest compliance 套件 | 46 passed |
| `python export_openapi.py --check` | OK |
| 治理检查 | 见同步表 |

## 缺口（诚实记录）

- R05/R20 为 PRD 二期/MVP stub（info 通过，无阻断逻辑）。
- R28 引擎内为占位，完整模型评审仍在章节循环。
- R18 依赖 `workflow.similarity_hits` 人工/任务写入，非全自动查重。

## ISSUE-046：编号对齐状态

**编号已对齐**（2026-11-02）。
