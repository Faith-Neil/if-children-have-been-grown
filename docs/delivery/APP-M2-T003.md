为什么有这个文件：交付前端通用状态组件（骨架屏、空态、错误、无权限、已过期、只读）的实现、测试与验证结果。

它解决什么问题：统一全站状态呈现规范，支持错误码/追踪号一键复制，实现 403 上下文保护，且文字对比度严格符合 WCAG 4.5:1。

# APP-M2-T003：通用状态组件封装交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T003 |
| 代码解释 | [代码解释](../code/APP-M2-T003.md) |
| 验收 | 前端 127 项测试全部通过（新增 14 项专项）、`pnpm --dir frontend/web build` 成功且无体积反弹，WCAG 4.5:1 对比度通过 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 APP-M2-T001（已 done）。下一任务：APP-M2-T004 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-16
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T001](../tasks/APP-M2.md#app-m2-t001)（done）
- 分支：`main`
- 本地验收状态：本地验证通过，已按流程标至 `in-review`，等待 QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了统一通用状态组件的封装，全面覆盖设计规范 §6.1 和任务要求中的六大状态：

1. **`frontend/web/src/status/status-views.ts`（新增）**：
   - 实现纯函数逻辑：`extractErrorInfo`（统一解析 `ApiError`、v1 错误体、旧版错误体、标准 `Error` 与字符串）、`copyText`（安全剪贴板复制及降级策略）、`contrastRatio`（WCAG 2.1 相对亮度与对比度计算）；
   - 定义状态缺省解析器：`resolveEmptyState`、`resolveForbidden`、`resolveExpired`、`resolveReadonly`；
   - 固化符合 WCAG 4.5:1 的色彩令牌 `STATUS_CONTRAST_TOKENS`（如高对比度深橙棕色 `#9a5608` 与深褐色 `#5c3504`）。

2. **`frontend/web/src/status/StatusViews.tsx`（新增）**：
   - **`SkeletonView` / `PageSkeleton`**：支持 `page`、`table`（5 行）、`cards`（3 张）、`detail` 四种变体；包含 10 秒超时长任务提醒（“仍在加载，可离开本页，任务在后台继续”）；
   - **`EmptyState` / `EmptyView`**：支持 `empty`、`filtered`（默认清除筛选按钮）、`search`（动态注入搜索关键词）三种模式及主行动引导按钮；
   - **`ErrorView` / `ErrorState`**：展示统一错误体（`code` 红色标签、`message` 说明），提供 `traceId` / `requestId` 一键复制（带图标、Tooltip 及 2 秒反馈状态切换），支持 `onRetry` 动作，支持 `page`、`block`、`inline` 三种版式；
   - **`Forbidden403` / `NoPermission`**：展示 403 无权限访问提示，保留当前上下文（项目名称、用户角色、请求路径标签），提供“当前内容及未保存文字仍保留在下方，写入口已关闭”的安心保护说明，并提供返回工作台引导；
   - **`ExpiredWarning` / `StaleBanner`**：提供版本过期黄色警告条（文字使用 `#9a5608`，对比度 > 4.8:1），支持当前保存版本与后台最新版本对比显示，并提供“重新运行”/“核对最新版本”动作；
   - **`ReadonlyBanner` / `ReadOnlyBanner`**：提供中性蓝灰色的只读会话保护横幅，展示只读原因（如“项目已取消”、“只读成员模式”）、受限范围与角色标签。

3. **`frontend/web/src/shared/styles.css`（修改）**：
   - 增加 `.icg-status-skeleton`、`.icg-status-empty`、`.icg-status-error`、`.icg-status-forbidden`、`.icg-status-expired`、`.icg-status-readonly` 等样式类，确保 ProLayout 混入主题下文字对比度符合 WCAG AA 4.5:1 规范。

4. **`frontend/web/src/app/App.tsx` 与 `SupportPages.tsx`（修改）**：
   - 在应用入口接入统一的 `Forbidden403`、`ReadonlyBanner` 与 `EmptyState` 组件。

5. **`tests/frontend/status-views.test.mjs` 与 `frontend/web/tests/status-views.test.mjs`（新增）**：
   - 新增 14 项完整的前端测试，全面覆盖逻辑算法、错误抽取、剪贴板交互、AST 结构声明与无障碍属性断言。

## 代码解释

详细调用链、状态机、错误降级机制与设计决策参见 [APP-M2-T003 代码解释](../code/APP-M2-T003.md)。

## 验收结果

### 1. 自动化测试套件执行
在仓库根目录执行：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行结果：
- **总测试数**：127 项
- **通过数**：127 项
- **失败数**：0 项
- **耗时**：约 1.5 秒
- 专项测试验证了：
  - WCAG 4.5:1 对比度公式与各颜色令牌验证通过；
  - `ApiError`、v1 错误、旧版错误与空值错误提取通过；
  - 剪贴板复制及异常降级逻辑通过；
  - 空态（empty / filtered / search）文案与动作推导通过；
  - 403 权限上下文标签与未保存保留说明推导通过；
  - 过期版本号对比与只读范围解析通过；
  - AST 断言六大组件及别名导出完整无遗漏；
  - 复制按钮 `data-testid="copy-trace-button"` 与无障碍属性 `aria-label="复制请求编号"` 正确声明。

### 2. 构建与体积审计
在仓库根目录执行：
```bash
pnpm --dir frontend/web build
```
执行结果：
- TypeScript 类型检查完全通过（`tsc -b` 无报错）；
- Vite 生产环境打包耗时 4.71 秒；
- 产物体积无异常反弹：
  - `index.js`：289.96 kB（gzip: 92.19 kB，较变更前 318.42 kB 保持稳定并略有优化）；
  - `index.css`：24.25 kB（gzip: 5.65 kB）；
  - 路由级代码拆分（Route-level Code Splitting）完好，未打破各页面的延迟加载。

## 项目进度

- 本卡状态由 `planned` 标为 `in-review`。
- 绝不私自将任务标为 `done`，等待主 Agent、QA 与项目经理审查。
- 看板现况：APP-M2 中 T001、T002、T008、T078、T114 为 done，T003 为 in-review，T124 为 ready，其余 planned。
- 下一业务组件任务：[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)（业务小组件：LevelTag、AiTag、DirectTag、Cite、SourceBar）。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无变化。状态规范与 §2.3 / 5.12 契合 |
| ROADMAP | 同步记录 APP-M2-T003 提交 in-review |
| ARCHITECTURE | 无变化。组件库符合前端现有 ProLayout 与状态分层架构 |
| Issue 看板/详情 | ISSUE-007 保持 in-progress；记录 APP-M2-T003 完成开发并提交 in-review |
| TASK_BOARD / PROJECT_STATUS | 更新 TASK_BOARD.md 中 APP-M2-T003 状态为 in-review 并链接交付文档 |
| tasks/APP-M2.md | 更新 APP-M2-T003 状态为 in-review 并注明已提交交付与代码解释 |

## 风险与后续

1. **实际浏览器剪贴板权限**：在未获授权或非安全环境（HTTP 且非 localhost）中，现代浏览器可能限制剪贴板写入；组件已实现降级保护并不引发页面崩溃；
2. **后续组件消费**：后续任务（如 APP-M2-T004 业务小组件、APP-M2-T005 ProTable 封装）可直接引入 `StatusViews.tsx` 作为缺省状态骨架与错误边界。
