# 代码说明：APP-M2-T135 一键重新检查

为什么有这个文件：说明 APP-M2-T135 的入口、调用顺序和关键判断。

它解决什么问题：让复审人不读全部代码也能找到本卡行为落在哪里、由哪一层把关。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T135 |
| 交付文件 | `docs/delivery/APP-M2-T135.md` |
| 影响模块 | `frontend/web/src/project/ChapterLoopPage.tsx`、`frontend/web/src/project/ManualQueuePage.tsx`、`backend/bid-core/icg/api/chapter_loop.py` |
<!-- code-explanation:end -->

## 调用顺序与关键判断
按钮调用 `POST /api/v1/projects/{pid}/chapters/{cid}/loop/recheck`（带正文版本）；后台自动修可安全修的问题，其余进人工队列；持锁中或版本旧时拒绝。

## 依赖与限制
“全项目一键重新检查”入口不在本卡；分册检查与全文检查走检查页。
