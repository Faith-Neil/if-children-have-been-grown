# APP-M2-T020：JobProgress SSE 订阅流、断线重连与轮询回退机制交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T020 |
| 代码解释 | [docs/code/APP-M2-T020.md](../code/APP-M2-T020.md) |
| 验收 | 7 项专属自动化单测全绿；全量 334 项前端单测全绿；生产构建 1.03s 顺利通过；工程治理检查通过 |
| 项目进度 | 前端 M2 推进，APP-M2-T020 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 1. 任务背景与交付目标

依据 PRD v1.8 §5.12.4、§5.7.6 与原交接文档规范：
- **目标**：实现后台长任务进度条组件 `JobProgress` 的实时流式订阅与高可用容灾架构。
- **核心要求**：
  1. 挂接 SSE 订阅（`/api/v1/jobs/{id}/events`），支持解析流式推送的进度与步骤详情；
  2. 断线阶梯重试：遇断开自动按 1s -> 2s -> 4s 指数退避重连 3 次；
  3. 平滑轮询回退：3 次重试失败后，无缝降级为 2 秒定时轮询（`GET /api/v1/jobs/{id}`），并在进度条上方呈现明确的黄色警示 Tag：“实时流已断开，已切换为定时刷新”；
  4. 终态断开：任务进入 `succeeded`、`completed`、`failed`、`cancelled` 终态时，立即关闭 SSE 连接并清理所有定时器，彻底防止内存泄漏；
  5. 严格遵守红线要求：不触碰 `ProjectPages.tsx` 与 `EditorPage.tsx`。

---

## 2. 变更文件与实现清单

1. **`frontend/web/src/status/job-progress-sse.ts`（新增）**：
   - 实现了 `parseSseLine` 与 `parseSseMessage` 标准 SSE 消息解析算法；
   - 实现了 `calculateBackoffDelay` 指数退避延迟算法（1s -> 2s -> 4s）；
   - 实现了 `isJobTerminalStatus` 终态快速判断；
   - 实现了 `JobStreamSubscriptionManager` 控制器，集成连接、3次阶梯重试、轮询降级与终态注销；
   - 封装了声明式 React Hook `useJobProgressSse`。
2. **`frontend/web/src/status/JobProgress.tsx`（修改）**：
   - 扩充 `JobProgressProps` 支持 `isFallbackPolling`、`connectionStatus` 与 `fallbackMessage`；
   - 渲染包含 `data-testid="job-stream-fallback-tag"` 的降级警告 Tag（“实时流已断开，已切换为定时刷新”）；
   - 导出包装组件 `JobProgressWithSse`，开箱即用支持自动订阅；
   - 重新导出所有流式核心符号。
3. **`tests/frontend/job-progress-sse.test.mjs`（新增）**：
   - 编写 7 项专属自动化单测，覆盖 SSE 解析、指数退避、终态判定、模拟推送、3次断线重试、轮询降级、终态释放。
4. **`frontend/web/tests/job-progress.test.mjs`（修改）**：
   - 新增第 5 项契约测试，断言 `JobProgressWithSse` 导出、降级 Tag testid 与降级文案。

---

## 3. 验收证据与测试输出

### 3.1 专属自动化单测
```
node --test tests/frontend/job-progress-sse.test.mjs
✔ 1. SSE 文本与多行消息解析 (parseSseLine & parseSseMessage) (1.5051ms)
✔ 2. 指数退避延迟算法计算 (calculateBackoffDelay) (0.137ms)
✔ 3. 任务终态判定集合 (isJobTerminalStatus & TERMINAL_JOB_STATUSES) (0.1366ms)
✔ 4. SSE 模拟订阅与正常进度推送更新 (23.4737ms)
✔ 5. 断线 3 次阶梯指数退避重连与重试计数 (108.7832ms)
✔ 6. 超过 3 次重试后平滑回退至定时轮询模式 (61.0202ms)
✔ 7. 任务进入终态 (completed / failed / cancelled) 自动关闭连接与定时器 (16.1286ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
```

### 3.2 任务模块全量单测回归
```
node --test tests/frontend/job-progress.test.mjs frontend/web/tests/job-progress.test.mjs tests/frontend/job-progress-sse.test.mjs
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
```

### 3.3 全局前端单测全量回归
```
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 334
ℹ suites 0
ℹ pass 334
ℹ fail 0
ℹ duration_ms 3040.799
```

### 3.4 生产构建验证
```
pnpm --dir frontend/web build
$ tsc -b && vite build
✓ built in 1.03s
产物体积受控，主包 414.52 kB，无多余依赖与告警。
```

---

## 4. 边界与红线遵从说明

- **严格红线隔离**：未修改 `ProjectPages.tsx` 与 `EditorPage.tsx`，与并发任务零冲突。
- **任务状态治理**：绝不私自标记任务为 `done`，当前更新为 `in-review`，关联 Issue 保持开启，等待 QA 验收签署。
