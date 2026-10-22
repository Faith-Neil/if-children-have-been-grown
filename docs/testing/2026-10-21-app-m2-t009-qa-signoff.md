为什么有这个文件：记录QA对APP-M2-T009（断点自适应 1280/1440/1680、侧栏持久化记忆与多层级动态面包屑，REV-M0-T51）的独立复测与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行断点与面包屑专项测试、前端全量单测、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查三大标准断点适配（1280px compact 1040px 主内容区无横滚优先、1440px standard、1680px wide 四栏编辑台、useBreakpoint 监听防抖与 Node SSR 降级）、侧栏持久化记忆（localStorage icg_sidebar_collapsed 读写、防崩溃降级与进入项目自动收起）、多层级动态面包屑导航（deriveBreadcrumbs 1~4 级路径推导、上级快速逐级回跳、末级语义化 Leaf 无跳转与 aria-current="page"）、长项目名 16 字符智能截断悬停显示全称以及首屏主包优化（278.49 kB < 295 kB 门禁）。

# APP-M2-T009 断点与侧栏记忆、面包屑独立复测与 QA 签署（REV-M0-T51）

- 被验任务：[APP-M2-T009](../tasks/APP-M2.md#app-m2-t009) · 断点与侧栏记忆、面包屑
- 关联审查任务：REV-M0-T51
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T009 交付](../delivery/APP-M2-T009.md)、[代码解释](../code/APP-M2-T009.md)
- 被验核心文件：`frontend/web/src/shell/responsive.ts`、`frontend/web/src/shell/BreadcrumbNav.tsx`、`frontend/web/src/shell/AppShell.tsx`、`frontend/web/src/app/App.tsx`、`frontend/web/src/shared/styles.css`、`tests/frontend/responsive-layout.test.mjs`、`frontend/web/tests/responsive-layout.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T009 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 三大标准断点与响应式推导 | 通过 | `responsive.ts` 定义 `BREAKPOINT_COMPACT = 1280`、`BREAKPOINT_STANDARD = 1440`、`BREAKPOINT_WIDE = 1680`；`getBreakpointInfo` 纯函数精确计算断点级别、布尔标志位、编辑台推荐列数（紧凑/标准 3 栏，宽屏 4 栏）与主内容区预算（紧凑视口 1040px）；`useBreakpoint` 使用 `requestAnimationFrame` 防抖监听视口变化，并在 Node/SSR 环境下平稳降级为 1440px 标准视口 |
| AC-02 侧栏折叠状态持久化记忆 | 通过 | `readStoredSidebarCollapsed` 与 `writeStoredSidebarCollapsed` 操作 `localStorage`（键名 `icg_sidebar_collapsed`），内置防崩溃 `try...catch` 确保在无痕模式或禁用 Storage 环境下优雅降级；手动切换折叠按钮实时同步至 Storage；组件挂载与路由切换保持用户偏好 |
| AC-03 进入项目空间自动收起侧栏 | 通过 | `onEnterProjectCollapse` 与 `resolveInitialSidebarCollapsed` 决策逻辑经由自动化测试严密覆盖：用户进入具体项目空间时，若未显式指定展开，系统默认自动收起侧边栏以最大化正文编辑区宽度；用户若有显式偏好则尊重用户选择 |
| AC-04 动态多层级语义化面包屑推导 | 通过 | `deriveBreadcrumbs` 动态推导 1~4 级导航轨迹：404 页面（`工作台 > 页面不存在`）、全局页面（`工作台 > 页面名`）、项目空间页（`工作台 > 项目简称 > 页签`）与编辑台分册页（`工作台 > 项目简称 > 编辑台 > 技术分册`）；严格保证所有上级节点具备 `path` 且可点击回跳，末级当前节点具备 `isCurrent: true` 且不带跳转路径 |
| AC-05 长项目名称智能截断与悬停全称 | 通过 | `formatProjectShortName` 纯函数对超过 16 字符的长项目名进行智能安全截断并追加省略号 `…`；`BreadcrumbNav.tsx` 在 DOM 上注入 `title` 属性完整保留原名，悬停即查，彻底防止顶栏被过长项目名挤爆换行 |
| AC-06 无障碍语义与高对比度样式 | 通过 | 外层渲染无障碍 `<nav aria-label="面包屑导航">` 容器；末级当前页渲染为 `<span className="breadcrumb-leaf" aria-current="page">`，字体色彩为高对比度深色 `#1D2129`（WCAG AA 对比度 > 7:1）；上级链接支持悬停过渡与下划线反馈；`.breakpoint-compact` 严格限定 1040px 最大宽度无横向滚动 |
| AC-07 生产构建达标与首屏主包优化 | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 658ms，0 错误 0 告警）；将面包屑导航按需收拢至 `AppShell` 动态切片后，首屏主包 `index-BQx7Z8KQ.js` 由改动前的 289.99 kB 优化至 **278.49 kB**（净降 **11.5 kB**），大幅优于 **295 kB** 门禁红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 断点自适应与面包屑专项测试 | `node --test tests/frontend/responsive-layout.test.mjs frontend/web/tests/responsive-layout.test.mjs` | **15 passed, 0 failed** (纯逻辑 10 项 + AST 断言 5 项) | 0.38s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **193 passed, 0 failed** (包含 15 项断点自适应专项测试) | 1.94s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，耗时 658ms) | 0.66s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-BQx7Z8KQ.js` **278.49 kB**（gzip: 89.73 kB），**大幅低于 <= 295 kB 门禁（净优化 11.5 kB）** | — |
| 工程治理规范核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **包体积逆势优化机制**：在新增断点监听、持久化存储以及动态多层级面包屑后，首屏主包体积非但没有增加，反而从 289.99 kB 降低至 278.49 kB（减少 11.5 kB）。这得益于将 `BreadcrumbNav` 与 Ant Design `Breadcrumb` 组件完全收敛在异步切片 `AppShell` 内，避免了根 Chunk 的依赖扩散。
2. **防崩溃容灾设计完备**：`readStoredSidebarCollapsed` 与 `writeStoredSidebarCollapsed` 对 `localStorage` 访问全程包裹 `try...catch`，在 Safari 无痕浏览、第三方 Cookie/Storage 被禁用的沙盒环境下完全不崩溃，优雅回退到内存状态。
3. **导航回跳不变量严谨**：自动化测试严格验证了面包屑路径链条的结构不变量——上层节点必定为可跳转链接（含有效 `path`），最末节点必定为纯文本叶子节点（标记 `isCurrent: true` 且 `path: undefined`），杜绝了面包屑最后自身循环重载跳转的不良体验。

## 签署状态

APP-M2-T009 / REV-M0-T51 保持 **in-review**，**严禁标 done**。
