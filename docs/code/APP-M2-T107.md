# 代码说明：APP-M2-T107 重抽不覆盖与补遗差异

为什么有这个文件：说明 重抽不覆盖与补遗差异在前端的接线方式与纯逻辑所在位置。

它解决什么问题：以后改规则（理由必填、补遗不阻断、版本链条件）时，知道页面与纯函数各在哪里。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T107 |
| 交付文件 | `docs/delivery/APP-M2-T107.md` |
| 影响模块 | `frontend/web/src/project/parse-postprocess-core.ts`、`TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`、`AddendumDiffDrawer.tsx`、`frontend/web/src/shared/types.ts` |
<!-- code-explanation:end -->

## 接线
`GET …/files/{id}/addendum-diff`（`AddendumDiff`）；`AddendumDiffDrawer.tsx` 按 `diff[].op` 着色。

重抽不覆盖人工修改与锁定、仅受影响条目回待确认由后端 `parse_decisions.py` 承担；页面只展示结果。

## 约束
页面组件只展示与提交，规则放在 `parse-postprocess-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决，页面校验只是提前提示。`App.tsx` 未改动。

## 依赖与限制
无新依赖。“三栏与设计稿并排截图”未做；差异视图只在补遗/澄清文件已解析后可用；闸门条件表格驱动用例由既有 T108 覆盖，本卡未新增。
