# 代码说明：APP-M2-T101 招标文件上传与版本链

为什么有这个文件：说明 招标文件上传与版本链在前端的接线方式与纯逻辑所在位置。

它解决什么问题：以后改规则（理由必填、补遗不阻断、版本链条件）时，知道页面与纯函数各在哪里。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T101 |
| 交付文件 | `docs/delivery/APP-M2-T101.md` |
| 影响模块 | `frontend/web/src/project/parse-postprocess-core.ts`、`TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`、`AddendumDiffDrawer.tsx`、`frontend/web/src/shared/types.ts` |
<!-- code-explanation:end -->

## 接线
`file_role` 随上传传给 `files/raw`；`POST …/files/{id}/role`、`POST …/files/{id}/supersede`；版本号、上传人、替代关系来自后端 `TenderFile` 字段。

版本链的后端规则（同类型、其后上传、旧条目标“所在文件已被替代”、人工改过的回到待确认）见 `tender_files.py`；>200 页分批的页码范围只在后端字段 `batches` 记录，页面未展示。

## 约束
页面组件只展示与提交，规则放在 `parse-postprocess-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决，页面校验只是提前提示。`App.tsx` 未改动。

## 依赖与限制
无新依赖。>200 页分批没有在页面展示批次范围；同指纹复用只在解析服务列标“复用”，没有单独的复用详情；没有用真实 RAGFlow 解析验证。
