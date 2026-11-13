为什么有这个文件：说明工单 3 覆盖视图与矩阵后台化的代码落点。

它解决什么问题：后续接双库写作时，知道前端确认态已降级为可选覆盖视图。

# TV-M0-T10 代码说明

- `matrix-core.ts`：`coverageSummary`
- `ProjectPages.tsx`（MatrixPage）：技术分册覆盖指标与提示；隐藏整表确认
- `project-header-core.ts` / `ProjectHeader.tsx`：`projectHeaderTabs(technicalOnly)`
- `ProjectWorkspaceContent.tsx`：技术分册 analyze 只渲染 Matrix + Facts
- `technical_matrix.guard_technical_confirm`：可选确认校验文案
