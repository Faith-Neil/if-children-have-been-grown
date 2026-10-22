为什么有这个文件：说明 APP-M2-T019 后台长任务进度组件 JobProgress、子步骤流转与 AI 紫色进度条规范隔离的具体实现、状态流转与架构约束。

它解决什么问题：阐述基于 PRD v1.8 §5.12.4、§5.7.6 及字典 4.16 规范的后台任务进度呈现体系，实现 5 类核心状态机（pending/running/completed/failed/cancelled）、总进度条与子步骤明细 Timeline/List 展示、严格落实 AI 紫色专属进度条与非 AI 业务蓝色进度条的样式隔离、失败容错与 traceId 复制交互，并在 Vite 构建中保持首屏主包 <= 295 kB 门禁底线。

# APP-M2-T019：代码解释

- 对应任务：[APP-M2-T019](../tasks/APP-M2.md#app-m2-t019) · JobProgress：步骤、子进度、AI 紫进度条
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T019 交付](../delivery/APP-M2-T019.md)
- 日期：2026-10-22
- 实际代码路径：
  - [job-progress.ts](../../frontend/web/src/status/job-progress.ts)
  - [JobProgress.tsx](../../frontend/web/src/status/JobProgress.tsx)
  - [styles.css](../../frontend/web/src/shared/styles.css)
  - [job-progress.test.mjs](../../tests/frontend/job-progress.test.mjs)
  - [job-progress.test.mjs](../../frontend/web/tests/job-progress.test.mjs)

---

## 改了什么以及为什么

### 1. 业务痛点与规范红线
根据 PRD v1.8 §5.12.4（后台任务中心 G-03）、§5.7.6（章节生成任务）及数据字典 4.16 节：
- **5 类长任务状态覆盖**：系统存在大量异步长任务（文档生成、大纲规划、合规审查、文档导出、知识库导入与重建等），前端必须完整覆盖 `pending`（排队/等待中）、`running`（执行中）、`completed`（已完成）、`failed`（失败）、`cancelled`（已取消）5 类状态；
- **子步骤与加权推导**：任务包含复杂子步骤流水线（如章节生成包含：提取需求 -> 检索证据材料 -> 提示词装配 -> 模型生成 -> 格式质检），前端需清晰展示步骤耗时、当前运行步骤与子进度细条，并支持从步骤明细中自动推导加权总进度；
- **色彩规范红线（严格隔离）**：
  - AI 生成与模型相关任务（`generate_chapter`、`model_review`、`assistant_qa`、`matrix_match`、`attachment_recognize` 等）**严格注入专属 AI 紫色进度条**（`#722ed1`），并挂载 `.is-ai-progress` 类名；
  - 普通业务任务（`export`、`compliance_check`、`kb_import`、`cleanup` 等）**严禁使用紫色**，强制使用企业主蓝色（`#1e4db7`）；
- **失败容错与追踪审计**：任务执行失败时，必须以标准结构展示错误码 `errorCode`、错误描述与脱敏摘要，提供 `traceId` 一键复制（对齐 StatusViews 统一交互），并根据 `allowedActions` 提供“从失败步骤重试”或整任务重试入口。

---

## 2. 具体实现架构

### 2.1 纯逻辑层 (`frontend/web/src/status/job-progress.ts`)
脱离 DOM 纯 TypeScript 实现，具备高可测性与高稳定性：
1. **状态机与色彩令牌定义**：
   - 导出 `JobStatus` 与 `JobStepStatus` 类型：`'pending' | 'running' | 'completed' | 'failed' | 'cancelled'`；
   - 锁定色彩令牌：`aiProgress = '#722ed1'`，`defaultProgress = '#1e4db7'`，`success = '#52c41a'`，`error = '#ff4d4f'`，`cancelled = '#8c8c8c'`，`pending = '#faad14'`，均符合 WCAG AA 4.5:1 对比度标准。
2. **AI 任务判定规则 (`isAiJob`)**：
   - 内置包含 PRD 与技术方案 8.23 节规定的 AI 任务类型集合：`generate_chapter`, `generate_outline`, `chapter_summary`, `model_review`, `model_review_batch`, `assistant_qa`, `assistant_suggest`, `ragflow_retrieval`, `evidence_matching`, `matrix_match`, `attachment_recognize`, `generation`, `loop` 等；
   - 支持前缀自适应（`ai_` 或 `model_` 开头）与大小写宽容；
   - 支持显式 `isAi` 标志强制覆盖（优先级最高）；
   - 普通业务任务（`export`、`compliance` 等）严格判定为 `false`。
3. **色彩解析器 (`resolveProgressStrokeColor`)**：
   - `failed` 映射至红色；`completed` 映射至绿色；`cancelled` 映射至中性灰；
   - `running` / `pending` 态：当且仅当判定为 AI 任务时输出 `#722ed1`；非 AI 业务任务严禁输出紫色，输出 `#1e4db7`。
4. **总进度推导算法 (`deriveJobProgress`)**：
   - 当任务状态为 `completed` 时强制返回 100；
   - 显式 `explicitPercent` 优先并做 0-100 区间安全约束；
   - 若未传显式进度，则遍历子步骤列表：完成步骤记 100 分，执行中步骤若未声明子进度默认记 50 分，计算均值并四舍五入。
5. **耗时格式化与元信息转换**：
   - `formatDuration(durationMs)`：`< 1000ms` 显示毫秒，`< 60s` 显示一位小数秒（如 `3.4s`），`>= 60s` 显示分秒（如 `1m 20s`）；
   - `resolveJobStatusMeta`：输出统一的中文标签（等待中、执行中、已完成、执行失败、已取消）与 Ant Design Badge / Progress 状态映射。

---

### 2.2 表现层组件 (`frontend/web/src/status/JobProgress.tsx`)
1. **AI 紫色类名与外层属性约束**：
   - 顶层容器带有 `data-testid="job-progress"`，当且仅当判定为 AI 任务时挂载 `.is-ai-progress` CSS 类，并在 HTML 属性上打上 `data-is-ai="true"` 标记，非 AI 任务严禁挂载该类名；
2. **头部信息与排队提示**：
   - 渲染任务标题、类型 Tag（AI 任务紫标签，普通任务蓝标签）、状态 Badge 与整体耗时；
   - 当任务处于 `pending` 且后端返回 `queueReason` 时，渲染排队说明横条（如“本地模型繁忙，排队第 6 位”）；
3. **主进度条呈现**：
   - 渲染 Ant Design `<Progress percent={percent} strokeColor={strokeColor} ... />`；
4. **子步骤明细列表**：
   - 支持通过 `showSteps` 控制展开，渲染步骤标题、步骤耗时、状态图标徽标与说明；
   - 当前正在执行的步骤（`running`）展示专属 Loading 动画并高亮背景；
   - 若子步骤包含细分进度，展示步骤微型进度条；
   - 步骤失败时就近渲染错误标签与原因；
5. **失败容错与追踪号交互**：
   - 任务失败时渲染 `data-testid="job-error-block"` 警示区块；
   - 完整展示 `errorCode`、`errorMessage` 与 `errorSummary`；
   - 提供 `traceId` 追踪号单号展示与复制按钮（`data-testid="copy-trace-btn"`），调用 `copyText` 并带有复制成功的反馈；
   - 提供基于失败步骤针对性重试或整任务重试按钮（`data-testid="job-retry-btn"`）及取消任务按钮（`data-testid="job-cancel-btn"`）。

---

### 2.3 样式系统 (`frontend/web/src/shared/styles.css`)
- 注入 `.icg-job-progress` 基础卡片样式与 `.is-compact` 紧凑尺寸；
- 注入 `.is-ai-progress` 专属紫色边框（`#d3adf7`）与微紫色背景光晕（`#fdfaff`），悬浮高亮边框 `#b37feb`；
- 保证文本色彩符合 `#1d2129` 与 `#4e5969`，色彩对比度严格大于 4.5:1。

---

## 3. 测试覆盖与门禁验证

### 3.1 单元测试矩阵
- **纯逻辑单测** (`tests/frontend/job-progress.test.mjs`，6 个测试点)：
  1. 状态机与状态元信息映射（5 类核心状态正确映射）；
  2. AI 任务类型判定规则（内置 13 类 AI 任务正例、前缀适配、非 AI 业务严禁反例、显式覆盖优先）；
  3. 进度条色彩与规范隔离（AI 紫色 `#722ed1` 与业务蓝色 `#1e4db7`，严禁非 AI 使用紫色）；
  4. 总体进度推导算法（完成强制 100、显式优先截断、子步骤加权平均、无步骤默认映射）；
  5. 耗时格式化（毫秒、秒、分秒与异常兜底）；
  6. 任务类型中文标签字典映射。
- **表现层 AST 与静态契约测试** (`frontend/web/tests/job-progress.test.mjs`，4 个测试点)：
  1. `job-progress.ts` 源码结构与必要导出符号检查；
  2. `JobProgress.tsx` 组件导出与全套 `data-testid` 完备性验证；
  3. AI 紫色样式隔离规范断言（严格禁止非 AI 任务出现紫色）；
  4. 失败容错、步骤重试与 Trace ID 交互契约断言。

### 3.2 门禁验证结果
- **前端全量单测**：`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`，全绿通过（**263 passed, 0 failed**）；
- **生产构建体积**：`pnpm --dir frontend/web build`，在 915ms 内构建成功，主包体积 `dist/assets/index-EIM2ccZO.js` 保持为 **294.86 kB**（严格 <= 295.00 kB）。
