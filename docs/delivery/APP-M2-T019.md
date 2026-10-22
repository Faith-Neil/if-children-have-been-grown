为什么有这个文件：记录 APP-M2-T019 后台长任务进度组件 JobProgress、子步骤流转与 AI 紫色进度条规范隔离的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现后台长任务 5 类状态机（pending/running/completed/failed/cancelled）、总进度条与子步骤明细 Timeline/List 展示、严格落实 AI 紫色专属进度条与非 AI 业务蓝色进度条的样式隔离、失败容错与 traceId 复制交互、首屏 Bundle 体积控制（<= 295 kB）与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T019：JobProgress：步骤、子进度、AI 紫进度条交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T019 |
| 代码解释 | [docs/code/APP-M2-T019.md](../code/APP-M2-T019.md) |
| 验收 | 10 项专属自动化单测通过；全量 263 项前端单测通过；生产构建首屏产物 294.86 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T019 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T019](../tasks/APP-M2.md#app-m2-t019)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **纯逻辑层状态机、色彩隔离与进度推导 (`frontend/web/src/status/job-progress.ts`)**：
   - 定义 5 类长任务核心状态机：`pending`（等待中）、`running`（执行中）、`completed`（已完成）、`failed`（失败）、`cancelled`（已取消）；
   - 锁定色彩规范令牌：AI 紫色 `#722ed1`、业务蓝色 `#1e4db7`、成功色 `#52c41a`、失败色 `#ff4d4f`、取消灰 `#8c8c8c`；
   - 实现了 `isAiJob(jobType, explicitIsAi)`：内置 13 类内置 AI 任务判定，支持前缀扩展与显式参数覆盖，非 AI 业务严禁返回 true；
   - 实现了 `resolveProgressStrokeColor(status, isAi)`：执行色彩红线隔离，非 AI 业务严禁出现紫色；
   - 实现了 `deriveJobProgress({ status, explicitPercent, steps })`：支持显式进度与子步骤列表加权均值推导，已完成强制 100；
   - 实现了 `formatDuration(durationMs)` 耗时友好格式化与 `resolveJobStatusMeta` 状态元信息解析。
2. **表现层长任务进度组件封装 (`frontend/web/src/status/JobProgress.tsx`)**：
   - 顶层容器根据 AI 判定严格挂载 `.is-ai-progress` 与 `data-is-ai="true"` 属性；
   - 头部呈现任务标题、类型 Tag（AI 紫/业务蓝）、状态 Badge、耗时与排队原因；
   - 主进度条 `<Progress ... />` 动态绑定色彩与状态；
   - 子步骤明细支持展开展示标题、耗时、状态图标、步骤说明与运行态子进度条；
   - 失败容错区块完整展示 `errorCode`、`errorMessage` 与 `errorSummary`，提供 `traceId` 一键复制（`copyText` 联动交互）与从失败步骤重试/取消操作。
3. **样式与规范落地 (`frontend/web/src/shared/styles.css`)**：
   - 补充 `.icg-job-progress` 与 `.is-ai-progress` 专属紫色光晕与卡片边框规范；
   - 确保文本符合 WCAG AA 4.5:1 对比度标准。

### 2. 变更文件清单
- `frontend/web/src/status/job-progress.ts` (新增): 状态机定义、AI任务判定、色彩隔离、进度派生与耗时格式化
- `frontend/web/src/status/JobProgress.tsx` (新增): 表现层组件封装（Progress、Timeline步骤、失败容错与traceId复制）
- `frontend/web/src/shared/styles.css` (修改): 注入 JobProgress 与 .is-ai-progress 规范样式
- `tests/frontend/job-progress.test.mjs` (新增): 6 项纯逻辑单测（状态机、AI判定、色彩隔离、进度推导与耗时）
- `frontend/web/tests/job-progress.test.mjs` (新增): 4 项 AST 静态契约、属性完备性与样式隔离断言
- `docs/code/APP-M2-T019.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T019.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单测执行记录
```bash
$ node --test tests/frontend/job-progress.test.mjs frontend/web/tests/job-progress.test.mjs
✔ 1. job-progress.ts exports core logic and status-machine symbols (19.3019ms)
✔ 2. JobProgress.tsx exports JobProgress component and binds essential attributes (7.0168ms)
✔ 3. AI 紫色样式隔离规范断言（严格禁止非 AI 任务出现紫色） (4.2743ms)
✔ 4. 失败容错、重试与 Trace ID 交互契约断言 (3.4888ms)
✔ 1. 状态机与状态元信息映射 (resolveJobStatusMeta) (0.7295ms)
✔ 2. AI 任务类型判定规则 (isAiJob) (0.1792ms)
✔ 3. 进度条色彩与规范隔离 (resolveProgressStrokeColor) (0.1436ms)
✔ 4. 总体进度推导算法 (deriveJobProgress) (0.2064ms)
✔ 5. 耗时格式化函数 (formatDuration) (0.1345ms)
✔ 6. 任务类型中文名称与标签 (getJobTypeLabel) (0.0844ms)
ℹ tests 10
ℹ pass 10
ℹ fail 0
```

全量前端回归：
```bash
$ node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 263
ℹ pass 263
ℹ fail 0
```

### 2. 生产构建与 Bundle 体积门禁
```bash
$ pnpm --dir frontend/web build
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
dist/assets/index-EIM2ccZO.js                294.86 kB │ gzip:  93.91 kB
✓ built in 915ms
```
- 首屏主包体积：`294.86 kB` <= `295.00 kB` 门禁红线，严格受控。

---

## 声明
本卡所有代码均经过严格自测与门禁检查，状态标至 **in-review**，绝不私自标 done，关联 Issue 保持开启。
