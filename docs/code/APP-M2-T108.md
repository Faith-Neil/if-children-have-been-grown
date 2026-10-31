# 代码说明：APP-M2-T108 “确认解析结果”闸门（悬停列未满足项）

为什么有这个文件：说明 APP-M2-T108 的入口、调用顺序和关键判断。

它解决什么问题：让复审人不读全部代码也能找到本卡行为落在哪里、由哪一层把关。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T108 |
| 交付文件 | `docs/delivery/APP-M2-T108.md` |
| 影响模块 | `frontend/web/src/project/ParseTab.tsx`、`frontend/web/src/project/parse-review-core.ts`、`backend/bid-core/icg/domain/parse_review.py` |
<!-- code-explanation:end -->

## 调用顺序与关键判断
后台 `parse_review.gates` 返回闸门计数（2026-10-30 补 `PARSE_INCOMPLETE`：确认接口早已拒绝未解析完的文件，但悬停列表漏列这一项）；前端 `unmetGates` 生成悬停文字，`canConfirm` 为假时按钮置灰；后台确认接口同样按闸门拒绝，前端状态不作为放行依据。

## 依赖与限制
无。
