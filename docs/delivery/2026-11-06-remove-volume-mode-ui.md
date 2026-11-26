# 改码说明：去掉分册/模式选择（2026-11-06）

依据：`E:\杂项\2026-11-06-remove-volume-mode-cursor-brief.md`  
分支：`feat/iss-047-technical-volume-mvp`（未合 PR）

## 做了什么

1. **新建项目**：`CreateProjectModal` 去掉 `volume_mode` 初始值/控件；`App.tsx` 创建请求仍**写死** `volume_mode: 'technical_only'`（API 兼容，不给用户选）。
2. **设置**：去掉「只写技术标 / 分册模式」文案；技术方案路径下隐藏「参与分册」勾选；负责人改称「技术方案负责人」。
3. **概览**：原「分册进度」改为「技术方案进度」，去掉定稿徽标。
4. **导出**：移除 `VolumeFinalizePanel` 入口与定稿徽章；技术方案路径不再展示生成范围单选；递交门禁前端不再依赖 finalize。
5. **文案**：用户可见「技术分册」→「技术方案」（及关联「商务方案 / 方案」表述）。
6. **主路径核对**：`confirm_directory` 写入 `outline_revision`，避免技术方案确认目录后 `generation/start` 因缺修订号 409。

## 改动文件

### 前端源码
- `frontend/web/src/app/App.tsx`
- `frontend/web/src/app/context.tsx`
- `frontend/web/src/project/CreateProjectModal.tsx`
- `frontend/web/src/project/project-volumes.ts`
- `frontend/web/src/project/OverviewTab.tsx`
- `frontend/web/src/project/ProjectPages.tsx`
- `frontend/web/src/project/ProjectSettingsPage.tsx`
- `frontend/web/src/project/ProjectSettingsGroups.tsx`
- `frontend/web/src/project/ParseTab.tsx`
- `frontend/web/src/project/OmissionsDrawer.tsx`
- `frontend/web/src/project/OutlineTreeView.tsx`
- `frontend/web/src/project/ManualQueuePage.tsx`
- `frontend/web/src/project/ChapterLoopPage.tsx`
- `frontend/web/src/project/ExportNamingCard.tsx`
- `frontend/web/src/project/export-checks-core.ts`
- `frontend/web/src/project/volume-api.ts`
- `frontend/web/src/project/VolumeFinalizePanel.tsx`（文案；导出页已不再挂载）
- `frontend/web/src/project/project-team.ts`
- `frontend/web/src/editor/EditorPage.tsx`
- `frontend/web/src/editor/WritingPlanReview.tsx`
- `frontend/web/src/editor/writing-input.ts`
- `frontend/web/src/shell/data-permission.ts`
- `frontend/web/src/shell/responsive.ts`
- `frontend/web/src/shell/route-guard.ts`
- `frontend/web/src/shell/can-directive.ts`
- `frontend/web/src/library/WritingArchivePage.tsx`
- `frontend/web/src/library/writing-archive-core.ts`
- `frontend/web/src/library/metadata-table.ts`
- `frontend/web/src/library/LibraryAttachments.tsx`
- `frontend/web/src/admin/AuditLogPage.tsx`
- `frontend/web/src/admin/audit-log-core.ts`

### 后端（目录确认修订号）
- `backend/bid-core/icg/domain/technical_outline.py`

### 测试
- `frontend/web/tests/unit/project-volumes.test.mjs`
- `frontend/web/tests/unit/main-path-core.test.mjs`
- `frontend/web/tests/unit/checks-export.test.mjs`
- `frontend/web/tests/unit/volume-finalize-glue.test.mjs`
- `frontend/web/tests/unit/data-permission.test.mjs`
- `frontend/web/tests/unit/responsive-layout.test.mjs`
- `frontend/web/tests/unit/writing-archive-page.test.mjs`
- `frontend/web/tests/unit/merge-checklist.test.mjs`
- `frontend/web/tests/unit/project-team.test.mjs`
- `frontend/web/tests/unit/routing-gate.test.mjs`

## 验收对照

| 项 | 结果 |
|----|------|
| 新建无分册/模式控件 | 通过 |
| 设置/概览/导出无分册定稿入口与「只写技术标」文案 | 通过 |
| API 仍写死 `technical_only` | 通过（`App.tsx`） |
| 确认目录写 `outline_revision` | 通过（后端） |
| 未合 PR | 是 |

请 PM 在工作台复验：新建 → 上传解析 → 确认目录 → 开始生成。
