# 任务交付：React-Router 现代化路由体系与可信守卫落地（D5）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-REACT-ROUTER |
| 代码解释 | [React-Router 现代化路由体系与可信守卫实现说明](../code/2026-10-26-frontend-react-router.md) |
| 验收 | 1. 专属单元测试：`frontend/web/tests/unit/react-router.test.mjs`：11 passed；<br>2. 前端全量单测回归：`pnpm --dir frontend/web test`：395 passed（100% 全绿通过）；<br>3. TypeScript 严格类型检查：`pnpm --dir frontend/web lint`：0 错误、0 警告；<br>4. 项目工程治理脚本核验：`node scripts/check-project-governance.cjs`：校验通过。 |
| 项目进度 | 已经 QA 独立终验签署（D-742）与 PD 产品对照核准（D-743），人类 PM 最终确认标为 **done** |
<!-- task-delivery:end -->

## 1. 任务背景与目标

依据 2026-10-26 用户审计与官方拍板 **决策 B2**（确定引入 React-Router）：将此前前端简易的字符串手动路由分发解耦为现代化的结构化 React-Router 体系。

本任务目标：
1. 在 `frontend/web/src/app/routes-core.ts` 与 `routes.tsx` 设计并实现结构化路由配置：
   - 基础路径：`/login`（登录页）、`/projects`（项目列表工作台，兼顾 `/workbench`）、`/projects/:projectId`（项目工作区分页：招标文件/响应矩阵/生成方案/检查中心/整本导出）、`/projects/:projectId/editor/:chapterId`（编辑器深链接）、`/library`（方案片段知识库）、`/writing-archive`（写作档案与规范，兼顾 `/writing`）、`/admin`（公司管理/合规配置，兼顾 `/admin/rules`）；
2. 实现可信路由守卫（Route Guard）：
   - 认证守卫（`AuthGuard`）：未认证自动拦截跳转 `/login`，越权拦截展示语义化 `Forbidden403` 界面；
   - 脏状态保护守卫（`DirtyGuard`）：保留编辑器中未保存离开的拦截确认体验；
3. 将 `frontend/web/src/app/App.tsx` 中的路由挂载对接至 React-Router，保留既有顶栏、模态弹窗（`ModelConfigModal`, `RagflowConfigModal`）及侧边导航联动；
4. 编写专属单元测试，确保前端 379+ 测试全部绿色并通过类型检查。

---

## 2. 完成内容与变更清单

| 文件路径 | 变更类型 | 说明 |
|---|---|---|
| `frontend/web/src/app/routes-core.ts` | 新增 | 纯逻辑层：导出 `APP_ROUTES` 常量、路径构造器（`buildProjectPath`, `buildEditorChapterPath`, `buildGlobalPath`）与标题推导纯函数 `getRouteTitle`，零 JSX 依赖 |
| `frontend/web/src/app/routes.tsx` | 新增 | 视图与守卫层：实现可信路由认证与 RBAC 八角色守卫组件 `AuthGuard`、脏数据离开保护组件 `DirtyGuard` |
| `frontend/web/src/app/app-route.ts` | 修改 | 扩展 `AppRoute` 模型，新增 `/login` 与章节编辑器深链接 `{ kind: 'project', chapterId }`，配置现代路径别名映射 |
| `frontend/web/src/shell/route-guard.ts` | 修改 | 路由权限核验前置放行 `/login` 与根路径，保留严格的 8 角色鉴权拦截 |
| `frontend/web/src/editor/EditorPage.tsx` | 修改 | 扩展支持 `initialChapterId?: string` 属性，实现章节深链接直接定位与双向选择 |
| `frontend/web/src/main.tsx` | 修改 | 全局装配 `<BrowserRouter>` 上下文容器，驱动 HTML5 History 路由 |
| `frontend/web/src/app/App.tsx` | 修改 | 响应式联动 `location.pathname`，无缝对接 React-Router，保留全套顶栏、弹窗及侧栏联动 |
| `frontend/web/tests/unit/react-router.test.mjs` | 新增 | 覆盖常量定义、深层路径构造、别名映射、标题推导、八角色越权拦截、跨公司隔离与脏状态拦截的 11 项专属权威单测 |
| `docs/code/2026-10-26-frontend-react-router.md` | 新增 | 专属代码解释、架构分层与时序图文档 |
| `docs/delivery/2026-10-26-frontend-react-router.md` | 新增 | 本交付归档文档 |
| `docs/TASK_BOARD.md` | 修改 | 登记本任务卡并推至 `in-review` |
| `docs/DOCUMENT_INDEX.md` | 修改 | 登记 D-734 与 D-735 |

---

## 3. 验收依据与测试证据

### 3.1 专属单测证据
运行命令：
```bash
node --test frontend/web/tests/unit/react-router.test.mjs
```
测试结果：
- `APP_ROUTES defines all official paths according to Decision B2` (pass)
- `buildProjectPath correctly formats project and tab routes with URI encoding` (pass)
- `buildEditorChapterPath formats deep link into chapter editor` (pass)
- `buildGlobalPath maps navigation domain IDs to canonical paths` (pass)
- `getRouteTitle derives informative Chinese titles for all route kinds` (pass)
- `parseAppPath accurately parses modern and legacy route paths` (pass)
- `routeAfterLogin redirects from login or root to user home path, preserves deep link` (pass)
- `AuthGuard blocks platform_admin from business data routes` (pass)
- `AuthGuard allows project_lead and bid_writer to access legitimate routes` (pass)
- `AuthGuard rejects cross-company project access` (pass)
- `DirtyGuard intercepts navigation when editor is dirty until confirmed` (pass)
**11 passed, 0 failed**。

### 3.2 全量前端单测回归
运行命令：
```bash
pnpm --dir frontend/web test
```
测试结果：
**395 passed, 0 failed**，全套套件 100% 保持绿色！

### 3.3 TypeScript 严格检查
运行命令：
```bash
pnpm --dir frontend/web lint
```
测试结果：
`$ tsc -b --noEmit`，**0 错误、0 警告**。
