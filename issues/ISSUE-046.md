为什么有这个文件：登记合规规则编号与 PRD v1.8 规则清单不一致的问题。

它解决什么问题：`compliance_rules.py` 里有约 19 条 `check_rXX` 检查的内容不是 PRD 同编号规则，看板按“有 check_rXX 与测试”把这些规则卡改成了 in-review，规则完成度因此被高估。

# ISSUE-046：合规规则编号与 PRD 规则清单不一致

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-046 |
| 类型 | bug |
| 优先级 | P0 |
| 状态 | closed |
| 登记日期 | 2026-10-31 |
| 最后更新日期 | 2026-11-02 |
| revision | 2 |
| 关联 Task | [BE-ISSUE-046-RULE-REALIGN](../docs/delivery/BE-ISSUE-046-RULE-REALIGN.md)；[APP-M2-T096](../docs/tasks/APP-M2.md#app-m2-t096)（R19 已更正） |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)（已合并进 main） |
| 本地验收 | 2026-11-02：`tests/backend/test_compliance_rules*.py` 46 passed；`export_openapi.py --check` OK |
| 合入 | 分支 `main` @ `7e206e48b557017f9b0ea6df907faa0320fbeb0c`（ISSUE-046 重挂）；PR #6 已合并（2026-11-02） |
| 发布 | 未发布 |

## 处理结果（2026-11-02）

按 PM 决策对 19 条错位规则 **原编号重挂**；旧逻辑改为 `EXT-*`（见 [矩阵](../docs/decisions/2026-11-02-issue-046-realignment-matrix.md)）。相关 APP-M2 规则卡交付已写「编号已对齐」；看板规则卡回到 in-progress 待 QA/产品签署。

## 现象（登记时）

实现 APP-M2-T096（R19 关联投标冲突）时发现，`icg/domain/compliance_rules.py` 的 `check_r19` 曾检查绿色采购。逐条对照约 19 条编号对不上（R01、R02、R04～R06、R08、R10、R12、R13、R15～R18、R20、R26～R28、R32、R34）。详情见 revision 1 表格（Git 历史）。

## 基线

| 基线 | 影响 |
|---|---|
| PRD | 不改；以 PRD v1.8 §5.8.1 为准 |
| TASK_BOARD | 合规规则行与错位卡状态已同步 |
| PROJECT_STATUS | 规则重挂后更新 |
