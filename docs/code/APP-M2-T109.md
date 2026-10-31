# 代码说明：APP-M2-T109 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换）

为什么有这个文件：说明 后处理条与合并条目（“已合并 N 条 · 拆分”、多位置切换）在前端的接线方式与纯逻辑所在位置。

它解决什么问题：以后改规则（理由必填、补遗不阻断、版本链条件）时，知道页面与纯函数各在哪里。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T109 |
| 交付文件 | `docs/delivery/APP-M2-T109.md` |
| 影响模块 | `frontend/web/src/project/parse-postprocess-core.ts`、`TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`、`AddendumDiffDrawer.tsx`、`frontend/web/src/shared/types.ts` |
<!-- code-explanation:end -->

## 接线
`merge_status`、`merged_ids`、`sources` 来自 `Requirement`；`POST …/requirements/{id}/split`、`…/merge`、`…/parse/merge-suggestions/{id}/dismiss`、`GET …/parse/post-process`。

合并建议抽屉用建议里的第一条作主条目；拆分请求不带条目列表即全部拆开，理由固定写“人工拆分”（接口理由可选）。

## 约束
页面组件只展示与提交，规则放在 `parse-postprocess-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决，页面校验只是提前提示。`App.tsx` 未改动。

## 依赖与限制
无新依赖。事实（Fact）的合并拆分接口 `splitFact` 后端已有，页面未接入事实表；拆分时不能选只拆其中某几条；没有用真实招标文件验证相似度阈值。
