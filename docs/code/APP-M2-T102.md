# 代码说明：APP-M2-T102 解析进度页（JobProgress 接入）

为什么有这个文件：说明 解析进度页（JobProgress 接入）在前端的接线方式与纯逻辑所在位置。

它解决什么问题：以后改规则（理由必填、补遗不阻断、版本链条件）时，知道页面与纯函数各在哪里。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T102 |
| 交付文件 | `docs/delivery/APP-M2-T102.md` |
| 影响模块 | `frontend/web/src/project/parse-postprocess-core.ts`、`TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`、`AddendumDiffDrawer.tsx`、`frontend/web/src/shared/types.ts` |
<!-- code-explanation:end -->

## 接线
`ParseRequest.service` 与 `TenderFile.parse_service_label`、`parse_duration_ms`、`reused`；前端 `retryBody`、`durationLabel`。

进度订阅与取消、重试沿用 T020，本卡不改。

## 约束
页面组件只展示与提交，规则放在 `parse-postprocess-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决，页面校验只是提前提示。`App.tsx` 未改动。

## 依赖与限制
无新依赖。换服务重试按文件重新解析，不比较两次结果；RAGFlow 未连接时如实显示后台失败原因；本机未连真实 RAGFlow，换服务重试没有实跑。
