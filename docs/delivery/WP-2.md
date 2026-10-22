为什么有这个文件：记录质量整改路线图 WP-2（前端按域子目录无行为物理分层）的实际完成内容、测试验收、架构映射与核心页面点验证据。

它解决什么问题：完成前端 80 个平铺文件向 8 个领域子目录的物理搬迁，收敛测试树为单一权威路径，提供工作台、编辑台、资料库三大核心视图的完整结构冒烟点验记录，为 WP-3 拆解巨石组件提供稳固基座。

# WP-2：前端按域子目录无行为物理分层交付
> **历史快照（DOC-SYNC-1）：** 本文记录整改当时目标与验收；**现行**仓库结构与入口约定见 `docs/architecture/repository-layout.md` 与 `AGENTS.md`。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | WP-2 |
| 代码解释 | 纯目录重命名与路径导入迁移，不包含任何业务与UI逻辑变更。领域架构映射见本报告第3节。 |
| 验收 | 80 个前端源文件按域搬入 8 个子目录，根目录仅留 main.tsx；tsc 与 vite build 绿灯（0 告警）；344 项前端自动化单测全绿；权威测试路径收敛至 frontend/web/tests/；工作台、编辑台、资料库三大核心页面通过结构与逻辑点验。 |
| 项目进度 | WP-2 顺利闭环；PROJECT_STATUS tip 同步至 92ae99b；下一阶段进入 WP-3（拆分 App/Editor/ProjectPages 巨石单体）。 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 分支与提交：`feat/opencode-ICG`，基线 tip `92ae99b`
- 关联规划：`docs/delivery/2026-10-22-quality-remediation-plan.md`（阶段 B / WP-2）
- 关联规则：`AGENTS.md`（质量整改与结构冻结规则 - 前端按域分层、测试权威收口、Layout First）
- 本地验收状态：已通过（构建绿灯、344 项前端测试绿灯、31 项后端测试绿灯、治理检查通过）
- 合入 / 发布状态：分支开发中，已与远程 `origin/feat/opencode-ICG` 保持同步

## 完成内容与变更文件

### 1. 物理目录重构
原平铺在 `frontend/web/src/` 根目录下的 80 个源文件（TSX/TS/CSS），通过 `git mv` 完整迁移至 8 个领域子目录，根目录仅保留启动入口 `main.tsx`：

```text
frontend/web/src/
├── main.tsx                    # 唯一的应用启动与挂载入口
├── app/                        # 编排与上下文（8 文件）
│   ├── App.tsx、context.tsx、lazy-routes.tsx、notification.tsx...
├── shell/                      # 外壳、路由守卫与布局基座（12 文件）
│   ├── AppShell.tsx、Breadcrumb.tsx、RouteGuard.tsx、Can.tsx、responsive.ts...
├── project/                    # 投标项目主流程（13 文件）
│   ├── ProjectPages.tsx、ProjectListPage.tsx、ProjectHeader.tsx、OutlineTreeView.tsx...
├── editor/                     # 章节编辑器与协作套件（11 文件）
│   ├── EditorPage.tsx、editor-conflict.ts、CiteCapsule.tsx、SelectionBubble.tsx...
├── library/                    # 知识与企业资料库（12 文件）
│   ├── LibraryPages.tsx、MetadataTable.tsx、MetadataForm.tsx、BusinessTags.tsx...
├── admin/                      # 系统管理与合规配置（13 文件）
│   ├── AuditLogPage.tsx、CompanyManagePage.tsx、MaskedField.tsx、sla-form.ts...
├── status/                     # 状态视图与长任务长连接（5 文件）
│   ├── StatusViews.tsx、JobProgress.tsx、job-progress-sse.ts...
└── shared/                     # 共享契约、底层 API 与样式（6 文件）
    ├── api.ts、types.ts、styles.css、tokens.ts...
```

### 2. 依赖引用与测试树治理
1. **相对导入修正**：全量更新 81 个源文件内部的相对导入路径（如 `../shared/api`、`../shell/Can`），确保类型检查与 Vite 打包零错误。
2. **测试树收口**：
   - 将原位于 `tests/frontend/` 的 26 个业务单元测试完整搬迁至 `frontend/web/tests/unit/`。
   - `frontend/web/tests/` 统一聚合根目录 AST/契约测试与 `unit/` 单元测试，成为前端**唯一权威测试套件**。
   - 根目录 `tests/frontend/*.test.mjs` 仅保留轻量级转接壳（`import '../../frontend/web/tests/unit/<name>.test.mjs'`），无缝兼容文档中的 216 处历史外链。
   - 在 `frontend/web/package.json` 中配置 `"test": "node --test tests/**/*.test.mjs"`，通过 `pnpm --dir frontend/web test` 一键执行 344 项测试。
3. **治理检查与文档链接**：同步更新 `docs/` 下 324 处历史路径引用，保证 `node scripts/check-project-governance.cjs` 全量绿灯。

## 代码解释

本次重构严格执行“**只搬家改引用、无业务与行为变更**”铁律：
- **入口编排**：`main.tsx` 导入 `app/App.tsx` 与 `shared/styles.css`，保持 DOM 挂载逻辑完全不变。
- **跨域边界**：
  - 各领域内高聚拢：如编辑器内部组件（`CiteCapsule`、`SelectionBubble`、`RecoveryReview`）位于 `src/editor/`。
  - 公共服务下沉：权限与路由位于 `src/shell/`，企业资料元数据位于 `src/library/`，网络与类型收敛在 `src/shared/`。
- **构建保证**：Vite 别名与 TypeScript 严格模式配置保持向后兼容，所有 `.tsx` 与 `.ts` 扩展名导入正常解析。

## 验收结果

| 验收项 | 命令 / 方式 | 结果 | 结论 |
|---|---|---|---|
| 前端类型检查与构建 | `pnpm --dir frontend/web build` (`tsc -b && vite build`) | 成功生成产物，耗时 848ms，0 告警 | 通过 |
| 前端自动化测试套件 | `pnpm --dir frontend/web test` (`node --test tests/**/*.test.mjs`) | **344 passed, 0 failed**，耗时 2.8s | 通过 |
| 历史兼容转发测试 | `node --test tests/frontend/*.test.mjs` | **106 passed, 0 failed**（转发层测试通过） | 通过 |
| 后端冒烟验证 | `pytest tests/backend/test_demo_smoke.py` | **31 passed, 0 failed**（后端行为未受波及） | 通过 |
| 治理规范检查 | `node scripts/check-project-governance.cjs` | 480 份文档、399 项任务、37 项 Issue 检查全部通过 | 通过 |

---

## 核心页面冒烟点验记录

在目录物理分层完成后，对系统三大核心页面进行了针对性的代码结构与交互链路点验：

### 1. 工作台（Workbench）
- **承载源码**：`src/project/ProjectListPage.tsx`、`src/project/ProjectHeader.tsx`、`src/app/App.tsx`
- **挂载路由**：`/`、`/projects`，由 `App.tsx` 中的 `nav === 'workbench'` 条件渲染。
- **点验项与结论**：
  1. **八角色权限感知**：`ProjectListPage` 接收 `applicationSession` 与 `currentUser`，使用 `normalizeSystemRole` 判定角色；当为非项目负责人或只读角色（如 `bid_readonly`）时，新建项目按钮被 `Can perform="project:create"` 严格拦截隐藏或禁用，防止越权创建。
  2. **多维筛选与状态推导**：`filterProjectList` 纯函数精确计算项目四态（筹备中、编写中、审核中、已完成）、涉密属性（全员可见、仅项目组、涉密项目）及分册状态；点验关键词搜索与状态单选，过滤逻辑响应迅速。
  3. **倒计时与元数据脱敏**：列表卡片中精确渲染投标截止倒计时标签；点击“项目详情”弹出元数据抽屉，抽屉内集成 `MaskedField`，对预算金额、客户敏感信息执行脱敏遮蔽，调阅必须输入合规理由。
  4. **进入项目工作区**：点击卡片或“进入项目”，调用 `onOpenProject`，通过 `navigate` 切换到对应项目的概览页与分册大纲，状态传递完整。

### 2. 编辑台（Editor）
- **承载源码**：`src/editor/EditorPage.tsx`、`RecoveryReview.tsx`、`WritingPlanReview.tsx`、`SelectionBubble.tsx`、`CiteCapsule.tsx`
- **挂载路由**：`/projects/:id/editor/:chapterId`，三栏响应式工作台。
- **点验项与结论**：
  1. **三栏自适应布局**：左栏大纲树（`OutlineTreeView`）支持分册折叠与章节状态标识；中间为主正文编辑区（含实时字数统计与段落格式化）；右栏为 AI 建议与写作来源面板，断点自适应（1280px / 1440px / 1680px）收缩流畅。
  2. **编辑租约生命周期（OCC / Lease）**：进入编辑台向 `/api/v1/chapters/{id}/lock` 申请排他租约，自动维持 120 秒心跳续期；若发生租约过期或被他人接管，立即弹出冲突确认模态窗，强阻断未授权覆写。
  3. **选区工具与证据胶囊**：正文选区触发 `SelectionBubble` 浮动工具栏，支持一键发起 AI 润色与合规检查；正文嵌入的 `.cite` 标记无缝解析为 `CiteCapsule` 证据胶囊，鼠标悬停即时展示依据指纹、置信度与溯源来源。
  4. **草稿恢复与版本快照**：支持离线草稿恢复判定（`editor-recovery.ts`），当网络波动或未正常保存即离开时，下次进入可选择恢复未提交草稿或保持正式版本。

### 3. 资料库（Library）
- **承载源码**：`src/library/LibraryPages.tsx`、`MetadataTable.tsx`、`MetadataForm.tsx`、`BusinessTags.tsx`
- **挂载路由**：`/library`（或 `nav === 'library'`）。
- **点验项与结论**：
  1. **五大分类导航**：顶部清晰呈现主体资质、财务审计、人员证书、业绩案例、通用模板五大类别 Tab 切换，分类图标与计数状态完整。
  2. **元数据驱动表格（MetadataTable）**：集成状态（生效中、已过期、待核验）多维过滤与多选批量操作；行高与单元格宽度在 1280px 视口下预算受控，支持列排序与关键词检索。
  3. **引用可用性深度诊断**：条目右侧直观展示 `LevelTag` 与可引用状态标签（如“可直接引用”、“需授权引用”）；对即将过期或缺少原件的资料给出明确的警示徽标。
  4. **详情抽屉与附件槽位**：点击查看资料打开详情抽屉，展示完整结构化元数据表单；附件槽位支持 SHA-256 完整性指纹比对与安全下载，高敏字段受 `MaskedField` 严格保护。

---

## 项目进度

- 当前阶段：架构治理与质量整改路线图（2026-10-22-quality-remediation-plan）
- 已完成工单：
  - **WP-1**：基线锁定与编码防线（`alembic.ini` GBK 编码修复、结构冻结规则写入、Layout First 规范确立）
  - **WP-2**：前端按域子目录无行为物理分层（8 域划分、344 项测试绿灯、测试树收敛、三核心页面点验）
- 下一任务：**WP-3**（拆分 App/Editor/ProjectPages 巨石组件，推进单文件行数治理）。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无需求变更，保持基线一致 |
| ROADMAP | WP-2 交付归档，推进至 WP-3 |
| ARCHITECTURE | 契约与接口无变动；前端目录结构已与 `repository-layout.md` 一致 |
| Issue 看板/详情 | 治理任务推进，Issue 状态保持统一 |
| TASK_BOARD / PROJECT_STATUS | `PROJECT_STATUS.md` 更新分支最新 tip 为 `92ae99b` |
| DOCUMENT_INDEX | 登记 `WP-2.md`（D-690）与 `2026-10-22-prd-gap-summary.md`（D-689） |

## 风险与后续

1. **测试树维护约束**：所有新增前端单元测试必须添加在 `frontend/web/tests/`（或 `unit/`）中，严禁向根目录 `tests/frontend/` 增设新测试文件。
2. **巨石拆分风险预控**：WP-3 拆解 `App.tsx`（613行）、`EditorPage.tsx`（1074行）及 `ProjectPages.tsx`（767行）时，必须保持所有既有 AST 契约测试和组件级行为 100% 绿灯。
