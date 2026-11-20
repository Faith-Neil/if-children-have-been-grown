# 交付：产品收口为仅技术标（2026-11-08）

依据：[2026-11-08-tech-bid-only-product.md](../decisions/2026-11-08-tech-bid-only-product.md)

## 代码

- `frontend/web/src/project/project-volumes.ts`：固定 `technical_only`，不再因后端 `both` 暴露商务入口。
- `frontend/web/src/editor/EditorPage.tsx`：移除商务分册 `TextArea` 正文路径与 `EditorSlaTools`；统一 `PaperEditor` + `editor-chapter-shell`。
- 写作方案、解析归属、写作档案筛选等 UI 去掉「商务方案」选项。
- `frontend/web/tests/unit/project-volumes.test.mjs` 对齐新口径。

## 文档

- `docs/PRD.md` 活动目标改为仅技术方案路径。
- 新增产品范围决策 `docs/decisions/2026-11-08-tech-bid-only-product.md`。

## 验收

- `pnpm --dir frontend/web build` 通过。
- `node --test frontend/web/tests/unit/project-volumes.test.mjs` 通过。

## 未在本轮删除（刻意保留）

- 后端 `Volume` / `business` 枚举与合成数据兼容。
- `docs/reference/product/prd-mvp-v1.8.md` 档案原文。
- PRD 正文中大量历史「两册」段落（需后续专项清理或标注归档）。
