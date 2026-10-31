# 代码说明：APP-M2-T105 条目卡片编辑与逐条确认

为什么有这个文件：说明 APP-M2-T105 的入口、调用顺序和关键判断。

它解决什么问题：让复审人不读全部代码也能找到本卡行为落在哪里、由哪一层把关。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T105 |
| 交付文件 | `docs/delivery/APP-M2-T105.md` |
| 影响模块 | `frontend/web/src/project/ParseTab.tsx`、`frontend/web/src/project/parse-review-core.ts`、`frontend/web/src/project/PdfLocator.tsx`、`backend/bid-core/icg/domain/parse_review.py` |
<!-- code-explanation:end -->

## 调用顺序与关键判断
`ParseTab.editItem` 打开条目编辑，保存走 `PATCH` 条目接口；后台 `parse_review` 写入人工修改并置人工锁，重抽时跳过有人工锁的条目；点条目后 `PdfLocator` 按条目页码与坐标跳页高亮。

## 依赖与限制
乱码条目须对照原页补录（`needsReentry`），不能直接确认。与 02d 的并排截图未存档。
