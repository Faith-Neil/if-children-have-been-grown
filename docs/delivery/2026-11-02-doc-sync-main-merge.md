# 文档同步：main 合入元数据（2026-11-02）

| 项目 | 内容 |
|---|---|
| 类型 | 治理交付（非 TASK done） |
| 合入 | 分支 `main` @ `cfdf5ad972339db229c3e7c43482086b4ba3dd4b`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 已合并（2026-11-02）；未发布生产 |

## 范围

- Wave 11 / Kiro 活跃 in-review 交付合入字段统一（T133、T144、T111、AI-REMEDIATION、BE-WORKFLOW-STATE-PERSIST、T260/T166/T020/T096 等，见各 delivery「合入」段）。
- `docs/testing/2026-10-31-t166-issue-linkage.md`、`t020-parse-job-progress.md`、`t096-related-bid.md` 回填 `cfdf5ad` 五项 CI success。
- `docs/PROJECT_STATUS.md`、`docs/DOCUMENT_INDEX.md`、本文件与 ISSUE-046 决策矩阵登记。

## 验证

- `node scripts/check-project-governance.cjs`（收尾）
- ISSUE-046 规则重挂：`python -m pytest tests/backend/test_compliance_rules*.py`（46 passed，2026-11-02 本机 bid-core 环境）

## 后续（2026-11-02）

- 代码合入：`7e206e4` `fix(compliance): realign 19 PRD rule IDs per ISSUE-046`（推送 `main` 后须复跑 GitHub offline-check 五项）。
- 文档：`BE-COMPLIANCE-RULES-P1～P5` ISSUE-046 免责声明；[规则单卡索引](2026-11-02-issue-046-rule-card-index.md)；看板 done 100 / tip `7e206e4`。
