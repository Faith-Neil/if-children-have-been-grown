# 代码说明：APP-M2-T106 批量确认（星号 / 废标 / 资格禁用）与置信度高亮

为什么有这个文件：说明 APP-M2-T106 的入口、调用顺序和关键判断。

它解决什么问题：让复审人不读全部代码也能找到本卡行为落在哪里、由哪一层把关。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T106 |
| 交付文件 | `docs/delivery/APP-M2-T106.md` |
| 影响模块 | `frontend/web/src/project/ParseTab.tsx`、`frontend/web/src/project/parse-review-core.ts`、`backend/bid-core/icg/api/workflow.py`、`backend/bid-core/icg/domain/parse_review.py` |
<!-- code-explanation:end -->

## 调用顺序与关键判断
前端 `batchCandidates` 先排除三类关键条目、已确认条目与未解析引用；后台 `POST /api/v1/projects/{id}/requirements/batch-confirm` 再次按类别拒绝并返回不能批量确认的条目，页面不能绕过。`lowConfidence` 读公司阈值。

## 依赖与限制
无。
