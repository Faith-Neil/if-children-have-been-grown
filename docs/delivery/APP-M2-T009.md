为什么有这个文件：交付断点自适应系统（1280 / 1440 / 1680）、侧栏折叠状态持久化记忆与多层级动态面包屑导航的封装实现、单元测试与构建验证结果。

它解决什么问题：
1. 落地 1280px 紧凑桌面（主内容区 1040px，表格无横滚优先）、1440px 标准桌面、1680px 宽屏工作台（四栏编辑台）的三大标准断点响应系统与 `useBreakpoint` Hook；
2. 实现侧栏持久化记忆：进入项目空间默认自动收起侧边栏以最大化编辑写作可用宽度，用户手动切换折叠/展开持久化存储至 `localStorage`（`icg_sidebar_collapsed`），路由切换或刷新页面后保持偏好记忆；
3. 实现动态多层级面包屑（Breadcrumbs）：依据路由与上下文推导 1~4 级面包屑（工作台 -> 项目名称 -> 页签/编辑台 -> 分册），长项目名智能截断悬停显示全称，上层节点支持快速逐级点击跳转回退，末级呈现语义化当前页；
4. 严格落实包体积与构建优化：首屏主包 Bundle 体积由 289.99 kB 优化至 278.49 kB（净优化 11.5 kB，优于 295 kB 门禁）。

# APP-M2-T009：断点与侧栏记忆、面包屑交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T009 |
| 代码解释 | [代码解释](../code/APP-M2-T009.md) |
| 验收 | 前端全量 193 项测试全部通过（含 15 项断点自适应与面包屑专项测试）、`pnpm --dir frontend/web build` 成功通过且产物体积达标（index 主包 278.49 kB < 295 kB 门禁，构建耗时 926ms）；1280/1440/1680 断点计算、侧栏持久化记忆与进入项目自动收起、长项目名截断悬停全称、多层级面包屑逐级回跳均通过自动化验证 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（已 done）、APP-M2-T001（已 done）。下一任务：按看板推进 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)（done）
- 契约接口：PRD v1.8 §2.3、§5.12、§7.2 与设计规范 §3.1、§3.4、§7.3、§9.6 布局与导航规范
- 分支：`feat/opencode-ICG`
- 本地验收状态：本地自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了断点适配、侧栏持久化记忆与动态面包屑的全面实现：

1. **`frontend/web/src/responsive.ts`（新增）**：
   - 定义三大标准断点常量：`BREAKPOINT_COMPACT = 1280`、`BREAKPOINT_STANDARD = 1440`、`BREAKPOINT_WIDE = 1680`；
   - 纯函数 `getBreakpointInfo(width)`：计算断点级别（`tier`: `sub-compact` / `compact` / `standard` / `wide`）、布尔标志位、编辑台推荐列数（3 栏 / 4 栏）与主内容区预估宽度（紧凑视口 1040px 优先保障表格无横滚）；
   - 自定义 Hook `useBreakpoint()`：监听视口变化并利用 `requestAnimationFrame` 防抖刷新，SSR/Node 环境优雅降级为 1440 标准视口；
   - 侧栏持久化：定义 `SIDEBAR_COLLAPSED_STORAGE_KEY = 'icg_sidebar_collapsed'`，实现 `readStoredSidebarCollapsed`、`writeStoredSidebarCollapsed`（内置防崩溃 `try...catch`），实现 `resolveInitialSidebarCollapsed` 与 `onEnterProjectCollapse` 决策；
   - 动态面包屑推导：实现 `formatProjectShortName`（长名智能截断与省略号）、`deriveBreadcrumbs`（依据 404/全局/项目/编辑台分册动态推导 1~4 级导航轨迹，严格保证上层节点具备 `path`，末级节点标记 `isCurrent: true` 且无路径）。

2. **`frontend/web/src/BreadcrumbNav.tsx`（新增）**：
   - 封装 Ant Design Breadcrumb 组件；
   - 外层包裹无障碍 `<nav aria-label="面包屑导航" className="topbar-breadcrumb-nav">`；
   - 上层链接具备安全点击跳转回调与平滑样式过渡；末级当前页渲染为 `<span className="breadcrumb-leaf" aria-current="page">`；
   - 悬停展示 `fullTitle` 完整文本，避免长项目名在顶栏换行挤占。

3. **`frontend/web/src/AppShell.tsx`（修改）**：
   - 集成 `useBreakpoint()`，在 ProLayout 根节点上注入 `breakpoint-${breakpoint.tier}` 类名与 `data-breakpoint` 属性；
   - 支持 `breadcrumbs` 属性，并将 `BreadcrumbNav` 按需渲染在懒加载的外壳切片中，优化首屏主 Chunk 体积。

4. **`frontend/web/src/App.tsx`（修改）**：
   - 侧栏 `collapsed` 状态结合 `readStoredSidebarCollapsed` 与路由初始值初始化；
   - 手动切换通过 `handleCollapseChange` 实时写回 `localStorage`；
   - 进入项目（`openProject` / `loadTab`）时通过 `onEnterProjectCollapse` 自动收起侧栏，最大化写作区；
   - 顶栏动态调用 `deriveBreadcrumbs` 并将 `breadcrumbs` 传至 `AppShell`。

5. **`frontend/web/src/styles.css`（修改）**：
   - 增加 `.breakpoint-compact` 下 `.workspace-content` 与 `.project-content:not(.fullbleed)` 的 `max-width: 1040px` 规则；
   - 增加 `.topbar-breadcrumb-nav`、`.breadcrumb-leaf`（`#1D2129` 高对比度）与链接悬停样式。

6. **测试套件（新增）**：
   - `tests/frontend/responsive-layout.test.mjs`：10 项专属纯逻辑单测，全面覆盖三大断点临界值、编辑台 3/4 栏推导、1040px 宽度预算、Storage 读写与异常降级、项目名称截断、404 与多层级面包屑推导及回跳不变量；
   - `frontend/web/tests/responsive-layout.test.mjs`：5 项 TypeScript AST 静态结构断言，全面验证模块导出、无障碍语义、属性传递与 CSS 规则。

## 测试与构建验证

### 1. 自动化单元测试验证
执行指令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
输出结果：
```text
ℹ tests 193
ℹ suites 0
ℹ pass 193
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1904.3051
```
全量 193 项前端单测全部通过（包含 15 项断点适配与面包屑专项测试）。

### 2. 生产构建与首屏体积审计
执行指令：
```bash
pnpm --dir frontend/web build
```
输出结果：
```text
dist/index.html                                0.94 kB │ gzip:   0.57 kB
dist/assets/index-BPLaGusP.css                29.65 kB │ gzip:   6.72 kB
dist/assets/AppShell-BCTy1JWJ.js             223.69 kB │ gzip:  73.43 kB
dist/assets/index-BQx7Z8KQ.js                278.49 kB │ gzip:  89.73 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip:  90.01 kB
dist/assets/jsx-runtime-DNp14iXa.js          437.98 kB │ gzip: 144.54 kB
✓ built in 926ms
```
- **门禁预算**：<= 295 kB；
- **实际体积**：首屏主包 `index-BQx7Z8KQ.js` 为 **278.49 kB**（Gzip 后 **89.73 kB**）；
- **优化幅度**：相比前期 289.99 kB 降低了 **11.5 kB**，未出现任何体积膨胀。

### 3. 项目治理检查
执行指令：
```bash
node scripts/check-project-governance.cjs
```
输出结果：
```text
治理检查通过：376 份 Markdown、397 项任务、37 项 Issue。
```

## 交付与后续安排

- 任务看板与索引：已同步登记至 `docs/DOCUMENT_INDEX.md`，并在 `docs/tasks/APP-M2.md` 将 `APP-M2-T009` 更新为 `in-review`。
- 绝不私自标 `done`，绝不私自关闭 Issue。
- 交付成果已备好供主 Agent 与 QA 团队独立复查。
