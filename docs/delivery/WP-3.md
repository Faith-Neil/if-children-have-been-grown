为什么有这个文件：记录质量整改路线图 WP-3（拆前端巨石单体组件）的实际完成内容、测试验收、代码解释与视觉克制（Layout First）落地说明。

它解决什么问题：针对 App.tsx、ProjectPages.tsx、EditorPage.tsx 三大单体巨石，在 100% 保持既有行为与 AST 契约的前提下，按领域抽取 13 个细粒度子组件（单文件规模均控制在 21~348 行），杜绝冗余标签与界面说明书化。

# WP-3：前端巨石组件拆分解耦交付
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-3 |
| 代码解释 | 从 App.tsx、ProjectPages.tsx、EditorPage.tsx 解耦拆出 13 个独立领域子组件，架构映射与模块设计详见本交付第3节。 |
| 验收 | tsc 与 vite build 绿灯（0 告警）；344 项权威前端测试全绿（0 失败）；工程治理检查 484 份 Markdown 0 错误；13 个新文件行数均在 21~348 行健康区间；严格落实 Layout First 视觉克制规范。 |
| 项目进度 | WP-3 顺利闭环；下一阶段进入 WP-4（后端 database.py / workflow.py 分包与去 demo 化）。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 C / WP-3）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则 - 前端按域分层、测试权威收口、Layout First）
- 本地验收状态：已通过（生产构建通过、344 项前端测试全绿、治理检查通过）
- 合入 / 发布状态：分支持续演进，与远程保持同步

---

## 完成内容与变更文件

### 1. 拆解产物概览（13 个新增独立领域组件）

所有新增组件严格划分到各自所属领域子目录，单文件行数均维持在 **21 ~ 348 行** 的健康维护区间：

| 领域目录 | 新增组件文件 | 对应提取自 | 行数 | 职责说明 |
|---|---|---|---|---|
| `src/app/` | [`LoginScreen.tsx`](file:///frontend/web/src/app/LoginScreen.tsx) | `App.tsx` | 70 行 | 登录全屏界面：合成账号切换、系统品牌介绍与登录提交 |
| `src/project/` | [`CreateProjectModal.tsx`](file:///frontend/web/src/project/CreateProjectModal.tsx) | `App.tsx` | 66 行 | 新建投标项目弹窗：名称、编号、截止时间与涉密属性输入表单 |
| `src/status/` | [`TaskDrawer.tsx`](file:///frontend/web/src/status/TaskDrawer.tsx) | `App.tsx` | 70 行 | 后台任务抽屉：长任务状态 Tag、实时进度条与页面跳转入口 |
| `src/project/` | [`SourceLink.tsx`](file:///frontend/web/src/project/SourceLink.tsx) | `ProjectPages.tsx` | 21 行 | 招标文件条款页码定位与锚点链接小组件 |
| `src/project/` | [`OriginalPreview.tsx`](file:///frontend/web/src/project/OriginalPreview.tsx) | `ProjectPages.tsx` | 110 行 | 原文预览卡片：原文文件与页码切换、条款引用高亮、原件安全下载 |
| `src/project/` | [`ConflictCards.tsx`](file:///frontend/web/src/project/ConflictCards.tsx) | `ProjectPages.tsx` | 85 行 | 抽取事实冲突决策卡片列表：单选候选值与选定理由填写 |
| `src/project/` | [`OverviewTab.tsx`](file:///frontend/web/src/project/OverviewTab.tsx) | `ProjectPages.tsx` | 146 行 | 项目工作区概览页（OverviewPage）：步骤进度、待办任务、分册正文提交率与最近导出 |
| `src/project/` | [`TenderTab.tsx`](file:///frontend/web/src/project/TenderTab.tsx) | `ProjectPages.tsx` | 223 行 | 招标文件页（TenderPage）：多格式文件上传拖拽、解析触发、原件下载与异常文件移除 |
| `src/project/` | [`ParseTab.tsx`](file:///frontend/web/src/project/ParseTab.tsx) | `ProjectPages.tsx` | 348 行 | 招标解析页（ParsePage）：原文条款多维分类、确认/修改/排除模态窗、冲突与事实抽屉联动 |
| `src/project/` | [`FactsTab.tsx`](file:///frontend/web/src/project/FactsTab.tsx) | `ProjectPages.tsx` | 185 行 | 项目事实表（FactsPage）：必备事实列表、SLA 矩阵引用核对、事实修改与确认依据提交 |
| `src/editor/` | [`EditorAssistantPanel.tsx`](file:///frontend/web/src/editor/EditorAssistantPanel.tsx) | `EditorPage.tsx` | 184 行 | 编辑器右栏助手（EditorAssistantPanel）：对话助手 Tab、整章建议卡片、问题列表与写作来源 |
| `src/editor/` | [`EditorDiffModal.tsx`](file:///frontend/web/src/editor/EditorDiffModal.tsx) | `EditorPage.tsx` | 61 行 | 编辑器差异对比确认弹窗（EditorDiffModal）：当前正文与建议内容双栏对比与采纳 |
| `src/editor/` | [`EditorVersionsDrawer.tsx`](file:///frontend/web/src/editor/EditorVersionsDrawer.tsx) | `EditorPage.tsx` | 61 行 | 编辑器历史版本抽屉（EditorVersionsDrawer）：正文版本时间线与核对恢复为草稿 |

### 2. 主体单体重构与行数瘦身

- **`frontend/web/src/app/App.tsx`**：
  - 成功剥离内联渲染的 `LoginScreen`、`CreateProjectModal`、`TaskDrawer`；
  - 严格保留全部 17 项内部核心状态函数（`loadSession`, `login`, `followPath`, `openProject`, `reload`, `mutate`, `libraryMutate`, `reportDirty`, `arrived`, `writeAddress`, `askLeave`, `requestPath`, `loadTab`, `showMissing`, `loadNav`, `navigate`, `report`），100% 满足 `app-orchestration.test.mjs` 和 `evidence-orchestration.test.mjs` 的 AST 动态闭包执行机制。
- **`frontend/web/src/project/ProjectPages.tsx`**：
  - 代码量由 **768 行锐减至 643 行（净降 139+ 行）**；
  - 成功拆出 `OverviewTab`、`TenderTab`、`ParseTab`、`FactsTab`、`SourceLink`、`OriginalPreview`、`ConflictCards`；
  - 保留 `MatrixPage`、`ChecksPage`、`ExportPage` 作为页面统一出口，完美兼容 `checks-export.test.mjs` 对 blocker 告警横幅、导出门禁 radio、导出历史表格 testid 的 AST 静态文本断言。
- **`frontend/web/src/editor/EditorPage.tsx`**：
  - 成功拆离右侧对话助手面板 `EditorAssistantPanel`、差异对比弹窗 `EditorDiffModal` 与版本历史抽屉 `EditorVersionsDrawer`；
  - 严格保持正文编辑区三态权限守卫（只读浏览态、未持锁态、持锁编辑态）、实时字数与目标诊断进度条、OCC 409 版本冲突合并弹窗、大纲树联动与断点自适应等 4 套自动化专项测试的 AST 契约。

---

## 视觉与交互原则（Layout First 践行说明）

在组件拆解与重构过程中，全面执行 `AGENTS.md` 规定的 **Layout First** 铁律（*Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining*）：
1. **杜绝说明书式界面**：新抽离的 `CreateProjectModal`、`TaskDrawer`、`EditorAssistantPanel` 等组件中，未新增任何多余的解释性副标题、长篇提示文字或重复性小徽标。
2. **依托布局传递意图**：
   - 在 `EditorAssistantPanel` 中，依靠 Tab（对话助手 / 问题 / 写作来源）、输入卡片与操作按钮的视觉高亮自然呈现流程，而非堆叠使用说明；
   - 在 `TaskDrawer` 中，仅保留核心状态 Tag 与操作按钮，让任务队列与进度条自解释；
   - 在 `TenderTab` 与 `ParseTab` 中，通过原件预览左栏与条款右栏的左右对比布局，自然引导用户完成“对照原文 - 确认要求”的交互流。

---

## 验收结果

| 验收项 | 验证命令 | 实际结果 | 结论 |
|---|---|---|---|
| 前端类型检查与生产构建 | `pnpm --dir frontend/web build` (`tsc -b && vite build`) | 成功打包，耗时 855ms，0 错误 0 告警 | 通过 |
| 权威前端自动化单测套件 | `pnpm --dir frontend/web test` (`node --test tests/**/*.test.mjs`) | **344 passed, 0 failed**，耗时 3.2s | 通过 |
| 工程治理规则校验 | `node scripts/check-project-governance.cjs` | 484 份 Markdown、399 项任务、37 项 Issue 检查全部通过 | 通过 |
| 拆解单文件规模门禁 | 静态代码行数统计 | 13 个新增组件行数均在 21~348 行之间，符合 < 400 行指标 | 通过 |

---

## 项目进度

- 当前阶段：架构治理与质量整改路线图（2026-10-22-quality-remediation-plan）
- 已完成工单：
  - **WP-1**：基线锁定与编码防线
  - **WP-2**：前端按域子目录无行为物理分层
  - **WP-3**：拆分 App/Editor/ProjectPages 巨石单体组件（13 个领域子组件独立拆离，全量 344 单测绿灯）
- 下一任务：**WP-4**（后端 database.py / workflow.py 限界上下文分包与去 demo 化，优先切片 infra 仓储与 mysql_gate）。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无需求变更，保持基线一致 |
| ROADMAP | WP-3 交付归档，推进至 WP-4 |
| ARCHITECTURE | 前端模块化拆解符合 `repository-layout.md` 与分域分层架构 |
| Issue 看板/详情 | 治理任务持续推进，各 Issue 状态对齐 |
| TASK_BOARD / PROJECT_STATUS | 同步 WP-3 完成状态 |
| DOCUMENT_INDEX | 登记 `WP-3.md`（D-691） |

## 风险与后续

1. **WP-4 后端分包边界**：后端拆解 `database.py`（101KB）与 `workflow.py`（92KB）时，必须通过 `icg_demo` 保留平滑兼容 re-export 层，确保 606 项 pytest 单测与 15 项会话冒烟持续绿灯。
2. **测试树单一性持续维护**：继续严守 `AGENTS.md` 结构冻结规则，所有新测试统一归入 `frontend/web/tests/`。
