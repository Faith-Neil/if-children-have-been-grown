# 代码说明：APP-M2-T118 挂证据候选的三路显示

为什么有这个文件：说明三路证据候选在后台与前端的接线方式和规则所在位置。

它解决什么问题：以后改候选规则、可挂接判断或抽屉展示时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T118 |
| 交付文件 | `docs/delivery/APP-M2-T118.md` |
| 影响模块 | `matrix.py`、`api/evidence_candidates.py`、`api/__init__.py`、`app/main.py`、`frontend/web/src/project/matrix-core.ts`、`MatrixMatchDrawer.tsx` |
<!-- code-explanation:end -->

## 接线
- `MatrixMixin._requirement_candidates` 对单条条款返回 structured / snippets / history 和 `kb_status`；资料库项按 `_attachable` 判断可否挂接，历史标书与知识库 `reference_only` 命中归入历史路，知识库抛错记为 unavailable。
- `list_evidence_candidates`（只读）整理为统一候选：`route`、`version`、`source`、`cite_reason`、`blocked_reason`、`attachable`、`content_preview`；片段与历史 `attachable` 固定为 false；`can_attach` 来自 `project_access.writable`。条款不存在 404，已并入的条款 409 `REQUIREMENT_MERGED`，他人项目由 `demo._project` 返回 404。
- 挂接仍走 `PATCH …/requirements/{id}`，其中 `tender_orchestrator.patch_requirement` 继续拒绝历史标书和未确认资料（409 `EVIDENCE_NOT_USABLE`），页面勾选不是最终裁决。

## 约束
- 候选只读，不写状态、不挂接、不新增错误码。
- `ResponseBody` 为 extra=allow 的严格响应模型，operationId `listEvidenceCandidates` 全局唯一。
- 前端 `candidateSelectable` 只让“资料库规则匹配 + 后台判可挂接 + 调用人有权限 + 未挂接”的候选可选。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
