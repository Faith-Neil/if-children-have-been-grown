为什么有这个文件：记录 APP-M2-T109 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换）的前端与测试交付。

它解决什么问题：说明页面实际做到什么、哪些没做，避免把未运行的测试或未连接的服务当作已验收。

# APP-M2-T109：后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T109 |
| 代码解释 | [APP-M2-T109](../code/APP-M2-T109.md) |
| 验收 | 2026-10-31：解析页条目卡片对主条目显示“已合并 N 条”标签与“拆分”按钮，被并入的条目不单列；有多个来源位置时显示“切换位置”并在左侧原文预览间循环定位；后处理条增加“合并建议”入口，抽屉列相似条目，项目负责人写理由后“合并”或“不合并”，数字不同的合并由后台拒绝。验证见 [验证记录](../testing/2026-10-31-wp4-parse-postprocess-frontend.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T109](../tasks/APP-M2.md#app-m2-t109)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.1.1～5.1.5、§5.2.1～5.2.4；后端见提交 `229d05f`

## 实际文件
- 接口：`merge_status`、`merged_ids`、`sources` 来自 `Requirement`；`POST …/requirements/{id}/split`、`…/merge`、`…/parse/merge-suggestions/{id}/dismiss`、`GET …/parse/post-process`。
- 前端：`frontend/web/src/project/` 下 `TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`（新）、`AddendumDiffDrawer.tsx`（新）、`parse-postprocess-core.ts`（新）；`shared/types.ts`
- 测试：“已合并 N 条与拆分后的显示”“多位置切换”用例；`tests/backend/test_parse_decisions.py` 的 `test_summary_counts_merged_duplicates`、`test_split_then_merge_back`、`test_split_unmerged_item_is_rejected`、`test_merge_with_different_numbers_is_rejected`、`test_merged_member_cannot_be_edited_until_split`；e2e 合并建议入口

## 说明
合并建议抽屉用建议里的第一条作主条目；拆分请求不带条目列表即全部拆开，理由固定写“人工拆分”（接口理由可选）。

## 未实现项与限制
- 事实（Fact）的合并拆分接口 `splitFact` 后端已有，页面未接入事实表；拆分时不能选只拆其中某几条；没有用真实招标文件验证相似度阈值。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，以上后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。
