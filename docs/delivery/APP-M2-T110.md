为什么有这个文件：记录 APP-M2-T110 冲突待选定页签（并列取值、理由必填）的前端与测试交付。

它解决什么问题：说明页面实际做到什么、哪些没做，避免把未运行的测试或未连接的服务当作已验收。

# APP-M2-T110：冲突待选定页签（并列取值、理由必填）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T110 |
| 代码解释 | [APP-M2-T110](../code/APP-M2-T110.md) |
| 验收 | 2026-10-31：冲突抽屉按卡片并列各方取值、文件、页码与原文，可点来源定位左侧原文；项目负责人选定一方，或标“不构成冲突”，两者都必须写理由（页面与后台同样拒绝空理由）；“已按补遗处理”的冲突不阻断确认，可“核对无误”或“撤销补遗替代”；未定位到原条款的补遗条目须选择被替代的原条款；已被新取值取代的历史决定折叠在“历史记录”。验证见 [验证记录](../testing/2026-10-31-wp4-parse-postprocess-frontend.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T110](../tasks/APP-M2.md#app-m2-t110)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.1.1～5.1.5、§5.2.1～5.2.4；后端见提交 `229d05f`

## 实际文件
- 接口：`GET …/parse/conflicts`（`listConflicts`）与 `POST …/parse/conflicts/{id}/decision`（`chooseConflict`，action 为 choose、not_conflict、revert、assign_target、confirm）；`ConflictCards.tsx`，纯逻辑在 `parse-postprocess-core.ts` 的 `buildDecision`、`blockingCount`。
- 前端：`frontend/web/src/project/` 下 `TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`（新）、`AddendumDiffDrawer.tsx`（新）、`parse-postprocess-core.ts`（新）；`shared/types.ts`
- 测试：“处理冲突必须写理由”“已按补遗处理不阻断”用例；`tests/backend/test_parse_decisions.py` 前 6 项（并列取值、理由必填、确认被阻断、新取值另记冲突、人工改过的事实重跑不冲突、不构成冲突须理由）；e2e 冲突卡理由校验

## 说明
旧的 `PATCH …/conflicts/{id}` 不再由页面调用。顶部“冲突待选定”计数仍取工作区里状态为 pending 的冲突，与 `blockingCount` 口径一致。

## 未实现项与限制
- 没有批量处理（PRD 要求逐条）；只有项目负责人可处理，其他角色只读；没有用真实招标文件产生冲突后在浏览器里走完整流程（e2e 只覆盖入口与理由校验，且本机未运行）。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，以上后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。
