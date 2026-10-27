为什么有这个文件：说明 APP-M2-T021 任务中心页基础 + 顶栏任务角标与抽屉的具体实现、模块架构与交互设计。

它解决什么问题：
1. 统一管理异步长任务（文档生成、解析、导出、合规审查、模型评审等）的运行状态与全局感知；
2. 顶栏实时展示“运行中 + 排队中”任务徽标，落实公司级多租户隔离；
3. 抽屉与任务中心页面实现全部（all）、运行中（running/pending/queued）、已完成（completed/succeeded）、异常失败（failed）四分类与计数；
4. 严格贯彻 Layout First 设计原则与 JobProgress 的 AI 专属紫色（#722ed1）和常规业务蓝色（#1e4db7）色彩隔离体系；
5. 提供任务失败重试（retry）与进行中取消（cancel）安全操作权限防线。

# APP-M2-T021：代码解释

- 对应任务：[APP-M2-T021](../tasks/APP-M2.md#app-m2-t021) · 任务中心页基础 + 顶栏任务角标与抽屉
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T021 交付](../delivery/APP-M2-T021.md)
- 文档登记：[D-757](../DOCUMENT_INDEX.md)
- 日期：2026-10-26
- 代码路径：
  - [task-center.ts](../../frontend/web/src/shell/task-center.ts)
  - [useTaskBadge.ts](../../frontend/web/src/shell/useTaskBadge.ts)
  - [TaskBadge.tsx](../../frontend/web/src/shell/TaskBadge.tsx)
  - [TaskCenterDrawer.tsx](../../frontend/web/src/shell/TaskCenterDrawer.tsx)
  - [TaskDrawer.tsx](../../frontend/web/src/status/TaskDrawer.tsx)
  - [SupportPages.tsx](../../frontend/web/src/app/SupportPages.tsx)
  - [App.tsx](../../frontend/web/src/app/App.tsx)
  - [styles.css](../../frontend/web/src/shared/styles.css)
  - [task-center.test.mjs](../../frontend/web/tests/unit/task-center.test.mjs)

---

## 1. 业务背景与架构约束

系统在 APP-M2-T019 与 APP-M2-T020 中已完成 `JobProgress` 长任务进度条组件及 SSE 实时订阅与轮询回退，但在全局顶栏（Header）中缺少直观的状态角标，任务抽屉也为极简旧版，无法支撑复杂的异步任务流。

### 硬约束与规范遵从
1. **八域分层（严格禁止平铺）**：
   - 核心纯逻辑收敛在 `frontend/web/src/shell/task-center.ts`；
   - 状态 Hook 放在 `frontend/web/src/shell/useTaskBadge.ts`；
   - 表现层组件放在 `frontend/web/src/shell/TaskBadge.tsx` 与 `frontend/web/src/shell/TaskCenterDrawer.tsx`；
   - 任务中心完整页升级在 `frontend/web/src/app/SupportPages.tsx`（`JobsPage`）；
   - 严禁触碰 `backend/` 与 `FE-M0-T04～T10`。
2. **Layout First 克制设计**：
   - 避免冗余或说明书式的文字标签；
   - 通过卡片阴影、外边框色调、状态徽标（Badge）与紧凑进度条清晰呈现任务生命周期。
3. **AI 色彩隔离红线**：
   - AI 任务（`generate_chapter`、`generate_outline`、`model_review` 等）严格采用紫色（Tag color: `purple`，Progress stroke: `#722ed1`，边框 `#d3adf7`）；
   - 普通业务（`export`、`compliance`、`kb_import` 等）严格使用企业主蓝色（Tag color: `blue`，Progress stroke: `#1e4db7`），严禁使用紫色。
4. **多租户隔离**：
   - 顶栏徽标计数与列表筛选严格绑定当前会话的 `company_id`，杜绝跨租户任务信息泄漏。

---

## 2. 模块详细设计与调用时序

### 2.1 纯逻辑层 (`frontend/web/src/shell/task-center.ts`)
脱离 DOM 与 React 依赖，具备纯逻辑单元测试性：
- `RawTaskInput`：宽松兼容的联合输入类型，无缝吸纳 `Job`（shared）、`JobProgressData`（status）及任意后台返回字典；
- `normalizeTask(raw)`：
  - 自动识别 ID、项目 ID、项目名称；
  - 规范化状态（`queued`/`pending` -> `pending`，`succeeded`/`completed` -> `completed`）；
  - 百分比钳位在 0～100（已完成强制为 100%）；
  - 自动推导子步骤耗时与标题；
  - 根据状态与输入派生 `allowedActions`（进行中默认包含 `cancel`，失败默认包含 `retry`）；
- `calculateActiveTaskCount(tasks, companyId)`：
  - 过滤匹配当前公司；
  - 累加状态为 `running`、`pending`、`queued` 的工单数量；
- `computeTaskCounts(tasks, companyId)`：
  - 产出 `{ all, running, completed, failed }` 四分类数字字典；
- `filterTasks(tasks, filter, options)`：
  - 支持按分类标签（`all`、`running`、`completed`、`failed`）、所属项目与关键词全文搜索；
- `canPerformTaskAction(task, action)`：
  - 严格校验 `task.allowedActions.includes(action)`；
  - 仅在失败态允许 `retry`，仅在运行/等待态允许 `cancel`。

### 2.2 响应式状态 Hook (`frontend/web/src/shell/useTaskBadge.ts`)
```typescript
export function useTaskBadge({ tasks, companyId, initialFilter, initialOpen }: UseTaskBadgeOptions): UseTaskBadgeResult {
  // 维护 drawerOpen, filter, searchQuery 状态
  // useMemo 缓存 normalizedTasks
  // useMemo 缓存 activeCount 与 counts
  // useMemo 缓存 filteredTasks
}
```

### 2.3 顶栏徽标 (`frontend/web/src/shell/TaskBadge.tsx`)
- 使用 Ant Design `<Button type="text">` + `<Badge count={activeCount} size="small" overflowCount={99}>`；
- 图标采用 `<CheckSquareOutlined />`；
- 配备清晰的 Tooltip（“任务中心 (X 项任务进行中)”）与无障碍 `aria-label`。

### 2.4 任务抽屉 (`frontend/web/src/shell/TaskCenterDrawer.tsx`)
- 抽屉宽度 460px；
- 顶部提供“查看全部任务”链接（跳转至 `/jobs` 页面）；
- 四选项卡（全部、进行中、已完成、异常失败），每个 Tab 上挂载对应数量的彩色 Badge；
- 任务卡片呈现（`TaskCenterCard`）：
  - 头部：任务标题、类型 Tag（AI紫 / 业务蓝）、状态 Badge、耗时与创建时间；
  - 项目元数据：展示项目名称与图标；
  - 步骤明细：若存在当前步骤，显示步骤名与运转状态（LoadingOutlined spin / Check / Close）；
  - 进度条：使用 `<Progress size="small" percent={progress} strokeColor={strokeColor} />`；
  - 失败区块：包含错误码、错误提示与带有复制按钮的 `Trace ID`；
  - 底部动作：
    - 失败任务展示“重试”按钮（`<Button danger type="primary">`）；
    - 运行中任务展示“取消”按钮（`<Button danger type="text">`）；
    - 带有“前往页面”跳转链接。

### 2.5 任务中心页面升级 (`frontend/web/src/app/SupportPages.tsx` -> `JobsPage`)
- 升级旧版同步任务简单说明页为功能完备的后台任务管理主页面；
- 提供相同的四分类 Tab 切换；
- 以元数据表格（Table）形式呈现：任务类型、标题/说明、状态、进度条（色彩隔离）、创建时间、耗时与重试/取消/前往项目动作。

### 2.6 主应用胶水 (`frontend/web/src/app/App.tsx`)
- 顶栏引入 `<TaskBadge tasks={jobs} companyId={user?.company_id} onClick={() => setTaskDrawer(true)} />`；
- 挂载 `<TaskCenterDrawer>`，并在用户点击取消时调用 `POST /api/v1/jobs/{id}/cancel`，本地响应式变更状态；
- 用户点击重试时重新刷新任务列表。

---

## 3. 验证与质量保证

1. **专属单测覆盖 (`frontend/web/tests/unit/task-center.test.mjs`)**：
   - 7 项单测覆盖角标统计、多租户隔离、状态判定、归一化、四分类筛选、重试/取消权限与 AI 色彩隔离；
   - 100% 保持通过。
2. **TypeScript 编译检查**：
   - 运行 `pnpm --dir frontend/web lint`（`tsc -b --noEmit`），0 error。
3. **全量前端回归**：
   - 运行 `pnpm --dir frontend/web test`，全量 403 项单测 100% 全部通过。
4. **生产打包构建**：
   - 运行 `pnpm --dir frontend/web build`，生产构建用时 1.37s，全部 Chunks 生成正常。
