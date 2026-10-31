# 代码说明：APP-M2-T110 冲突待选定页签（并列取值、理由必填）

为什么有这个文件：说明 冲突待选定页签（并列取值、理由必填）在前端的接线方式与纯逻辑所在位置。

它解决什么问题：以后改规则（理由必填、补遗不阻断、版本链条件）时，知道页面与纯函数各在哪里。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T110 |
| 交付文件 | `docs/delivery/APP-M2-T110.md` |
| 影响模块 | `frontend/web/src/project/parse-postprocess-core.ts`、`TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`、`AddendumDiffDrawer.tsx`、`frontend/web/src/shared/types.ts` |
<!-- code-explanation:end -->

## 接线
`GET …/parse/conflicts`（`listConflicts`）与 `POST …/parse/conflicts/{id}/decision`（`chooseConflict`，action 为 choose、not_conflict、revert、assign_target、confirm）；`ConflictCards.tsx`，纯逻辑在 `parse-postprocess-core.ts` 的 `buildDecision`、`blockingCount`。

旧的 `PATCH …/conflicts/{id}` 不再由页面调用。顶部“冲突待选定”计数仍取工作区里状态为 pending 的冲突，与 `blockingCount` 口径一致。

## 约束
页面组件只展示与提交，规则放在 `parse-postprocess-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决，页面校验只是提前提示。`App.tsx` 未改动。

## 依赖与限制
无新依赖。没有批量处理（PRD 要求逐条）；只有项目负责人可处理，其他角色只读；没有用真实招标文件产生冲突后在浏览器里走完整流程（e2e 只覆盖入口与理由校验，且本机未运行）。
