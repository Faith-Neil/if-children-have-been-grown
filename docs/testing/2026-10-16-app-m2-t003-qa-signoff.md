为什么有这个文件：记录QA对APP-M2-T003（通用状态组件封装）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手复跑前端全量单测、验证生产环境打包与包体积审计，深度核验 6 类组件在各变体、一键复制、上下文保护与 WCAG 4.5:1 色彩对比度上的合规性。

# APP-M2-T003 通用状态组件封装独立复验与 QA 签署（REV-M0-T40）

- 被验任务：[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003) · 通用状态组件封装
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T003 交付](../delivery/APP-M2-T003.md)、[代码解释](../code/APP-M2-T003.md)
- 被验核心文件：`frontend/web/src/status/StatusViews.tsx`、`frontend/web/src/status/status-views.ts`、`frontend/web/src/shared/styles.css`、`frontend/web/tests/status-views.test.mjs`、`tests/frontend/status-views.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T003 保持 in-review，严禁标 done**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 6 类状态组件完备性 | 通过 | `StatusViews exports all six core status views and their approved aliases`：导出 `SkeletonView/PageSkeleton`、`EmptyState/EmptyView`、`ErrorView/ErrorState`、`Forbidden403/NoPermission`、`ExpiredWarning/StaleBanner`、`ReadonlyBanner/ReadOnlyBanner` |
| AC-02 ErrorView 统一错误体与 traceId 复制 | 通过 | `ErrorView supports error body code, message, traceId copy button, and retry action`：解析 ApiError/v1/旧版错误体，呈现 red Tag code、message；包含 `data-testid="copy-trace-button"` 与 `aria-label="复制请求编号"`，具备 2 秒复制反馈切换；支持 page/inline/block 布局与 onRetry 重试 |
| AC-03 SkeletonView 变体与超时提醒 | 通过 | `SkeletonView supports table 5 rows, cards 3, detail, and 10s timeout notice`：支持 page、table(默认5行)、cards(默认3张)、detail 四种变体；10 秒后展示“仍在加载，可离开本页，任务在后台继续”超时提示 Alert |
| AC-04 EmptyState 筛选与搜索模式 | 通过 | `EmptyState supports filtered and search modes with actionable buttons`：支持 empty/filtered/search 模式；filtered 模式自动生成“清除筛选”引导；search 模式动态呈现“没有找到名称包含‘xxx’的项目或资料” |
| AC-05 Forbidden403 上下文保护 | 通过 | `Forbidden403 preserves context tags, retained notice, and returns to workbench or safe route`：展示 403 提示，保留当前项目名称、用户角色、请求路径标签，并展示“当前内容及未保存文字仍保留在下方，写入口已关闭”保护提示 |
| AC-06 ExpiredWarning 版本比对 | 通过 | `ExpiredWarning alerts on stale revision with WCAG high contrast warning styling`：版本过期警告条展示当前已保存版本与后台最新版本比对，支持“重新运行”与重跑动作 |
| AC-07 ReadonlyBanner 只读会话保护 | 通过 | `ReadonlyBanner provides non-editable session protection and displays scope and role`：中性蓝灰横幅展示“当前页面处于只读状态，所有修改、保存与生成入口已关闭，仅供查阅”，附带范围与角色标签 |
| AC-08 WCAG 4.5:1 对比度审计 | 通过 | `WCAG 4.5:1 text contrast compliance for all status view colors`：告警文字 `#9a5608` 白底对比度 4.88:1（黄色背景上 4.80:1），告警描述 `#5c3504` 对比度 8.78:1，主要正文 `#1d2129` 对比度 14.9:1，次要说明 `#4e5969` 对比度 6.44:1，主色 `#1e4db7` 对比度 7.55:1，错误色 `#d9363e` 对比度 4.62:1，全部满足 WCAG AA 4.5:1 |
| AC-09 纯逻辑与剪贴板解耦测试 | 通过 | `extractErrorInfo safely extracts code, message, traceId, status, and details` 与 `copyText copies to clipboard or returns gracefully in node environment`：纯逻辑与 Node 无 DOM 环境解耦，测试 100% 通过 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 前端全量单测 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **127 passed, 0 failed** (含 14 项通用状态组件专项断言) | 1.89s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build`，无报错无告警) | 1.40s |
| 产物体积审计 | 检查 `frontend/web/dist/assets/` | `index.js` **289.96 kB** (gzip: 92.19 kB)，按需加载分包完好，体积较变更前略有缩减 | — |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (350 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **样式与 ProLayout 协同**：`.icg-status-expired` 与 `.icg-status-readonly` 样式使用高对比度色彩覆盖了 Ant Design 默认浅黄色，彻底解决了历史上浅黄文字可读性差的缺陷。
2. **渐进式替换策略**：在 `App.tsx` 和 `SupportPages.tsx` 中已接入统一的 `EmptyState`，既有复杂工作区页面后续可逐步无缝替换为这套六类组件。
3. **无障碍属性完备**：骨架屏提供 `role="status"` 和 `aria-busy="true"`，空态提供 `aria-label`，复制按钮提供 `aria-label="复制请求编号"`，符合屏幕阅读器无障碍标准。

## 签署状态

APP-M2-T003 保持 **in-review**，**严禁标 done**。
