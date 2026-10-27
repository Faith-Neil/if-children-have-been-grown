为什么有这个文件：记录 APP-M2-T021 任务中心页基础 + 顶栏任务角标与抽屉的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现后台长任务全局状态感知、顶栏角标实时统计（运行中+排队中）、抽屉与中心页四分类筛选（全部、运行中、已完成、异常失败）、AI 专属紫色与常规业务蓝色样式隔离、失败重试与进行中取消操作权限控制，以及 403 项前端自动化单测保持 100% 绿色的证据链。

# APP-M2-T021：任务中心页基础 + 顶栏任务角标与抽屉交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T021 |
| 代码解释 | [docs/code/APP-M2-T021.md](../code/APP-M2-T021.md) |
| 文档登记 | [D-756](../DOCUMENT_INDEX.md) |
| 验收证据 | 7 项专属自动化单测通过；全量 403 项前端单元测试 100% 保持绿色；TypeScript 静态编译 0 error；Vite 生产构建成功；工程治理检查通过 |
| 项目进度 | 前端核心能力推进，APP-M2-T021 状态推至 `in-review`，关联 ISSUE-007 保持开启，严禁自行标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-26
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T021](../tasks/APP-M2.md#app-m2-t021)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)、[APP-M2-T019](../tasks/APP-M2.md#app-m2-t019)、[APP-M2-T020](../tasks/APP-M2.md#app-m2-t020)
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心功能实现
1. **纯逻辑层模型与算法 (`frontend/web/src/shell/task-center.ts`)**：
   - 定义宽容兼容的输入类型 `RawTaskInput`，支持 `shared/Job`、`status/JobProgressData` 与扩展字段；
   - 实现了 `normalizeTask` 归一化算法：状态统一（`queued` -> `pending`, `succeeded` -> `completed`）、百分比 0-100 钳位（已完成强制 100%）、子步骤耗时计算、`allowedActions` 派生；
   - 实现了 `calculateActiveTaskCount`：统计当前公司运行中 (`running`) 与排队中 (`pending`/`queued`) 任务数，严格落实多租户隔离；
   - 实现了 `computeTaskCounts` 与 `filterTasks`：支持全部（`all`）、进行中（`running`）、已完成（`completed`）、异常失败（`failed`）四分类切换与关键词多维检索；
   - 实现了 `canPerformTaskAction`：操作权限硬防线（仅失败任务允许 `retry`，仅进行中/排队中任务允许 `cancel`）。
2. **状态 Hook 与顶栏徽标 (`frontend/web/src/shell/useTaskBadge.ts`, `TaskBadge.tsx`)**：
   - 封装 `useTaskBadge` Hook，集中管理抽屉可见性、四分类页签状态与过滤任务列表；
   - 落地 `TaskBadge` 组件：顶栏展示 `<CheckSquareOutlined />` 带有数字角标，具备悬停提示与无障碍属性。
3. **任务中心抽屉与卡片 (`frontend/web/src/shell/TaskCenterDrawer.tsx`)**：
   - 贯彻 **Layout First** 克制设计原则，460px 宽度抽屉；
   - 顶栏配备“查看全部任务”链接跳转主页面；
   - 包含四分类带有各自分类计数 Badge 的选项卡（Tabs）；
   - 任务卡片呈现任务标题、类型 Tag、状态 Badge、所属项目、当前执行步骤、百分比进度条（复用 JobProgress 色彩隔离：AI 专属紫 `#722ed1` 与业务蓝 `#1e4db7`）；
   - 失败区块展示错误信息、错误码与带有复制按钮的 `Trace ID`；
   - 动作支持失败任务“重试”、进行中任务“取消”与“前往页面”。
4. **任务中心完整页面升级 (`frontend/web/src/app/SupportPages.tsx` -> `JobsPage`)**：
   - 升级 `/jobs` 路由对应的 `JobsPage`，提供四分类 Tabs、统计角标、进度条色彩隔离与重试/取消/前往项目交互。
5. **主应用集成 (`frontend/web/src/app/App.tsx`)**：
   - 顶栏引入 `TaskBadge`；
   - 挂载 `TaskCenterDrawer`，实现任务取消（`POST /api/v1/jobs/{id}/cancel`）与重试状态响应。

### 2. 变更文件清单
- `frontend/web/src/shell/task-center.ts` (新增): 任务中心纯逻辑、四分类筛选、租户隔离与权限算法
- `frontend/web/src/shell/useTaskBadge.ts` (新增): 顶栏任务角标与抽屉状态管理 Hook
- `frontend/web/src/shell/TaskBadge.tsx` (新增): 顶栏任务中心入口按钮与状态角标组件
- `frontend/web/src/shell/TaskCenterDrawer.tsx` (新增): 任务中心抽屉与任务卡片组件
- `frontend/web/src/status/TaskDrawer.tsx` (修改): 兼容层委托至 TaskCenterDrawer
- `frontend/web/src/app/SupportPages.tsx` (修改): 升级 JobsPage 支持四分类筛选与动作
- `frontend/web/src/app/App.tsx` (修改): 顶栏接入 TaskBadge、TaskCenterDrawer 与重试/取消回调
- `frontend/web/src/shared/styles.css` (修改): 注入任务中心卡片与悬浮光晕样式
- `frontend/web/tests/unit/task-center.test.mjs` (新增): 7 项专属纯逻辑单元测试
- `docs/code/APP-M2-T021.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T021.md` (新增): 任务交付文档

---

## 验收证据

### 1. 专属单元测试
```bash
$ node --test frontend/web/tests/unit/task-center.test.mjs
✔ 1. 顶栏角标计数 (calculateActiveTaskCount)：统计运行中+排队中任务并保障多租户隔离 (0.739ms)
✔ 2. 任务状态谓词判定 (isTaskRunning, isTaskCompleted, isTaskFailed, isTaskCancelled) (0.1615ms)
✔ 3. 数据归一化 (normalizeTask)：双结构兼容、字段派生与百分比钳位 (0.9277ms)
✔ 4. 四分类筛选与统计 (computeTaskCounts & filterTasks) (1.0368ms)
✔ 5. 操作权限校验防线 (canPerformTaskAction) (0.3105ms)
✔ 6. AI 任务色彩隔离红线验证 (resolveProgressStrokeColor & isAiJob) (0.1728ms)
✔ 7. 时间与耗时格式化友好渲染 (formatTaskTime & resolveJobStatusMeta) (1.6563ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
```

### 2. 全量前端单元测试（403 项单测 100% 保持绿色）
```bash
$ pnpm --dir frontend/web test
...
ℹ tests 403
ℹ suites 0
ℹ pass 403
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 4653.6958
```

### 3. TypeScript 静态类型编译
```bash
$ pnpm --dir frontend/web lint
$ tsc -b --noEmit
# 0 error，执行代码退出码为 0
```

### 4. 生产构建打包
```bash
$ pnpm --dir frontend/web build
$ tsc -b && vite build
✓ 3408 modules transformed.
✓ built in 1.37s
```

### 5. 工程治理规范检查
```bash
$ node scripts/check-project-governance.cjs
治理检查通过：546 份 Markdown、414 项任务、38 项 Issue。
```

---

## 状态同步与 PM 审核建议

- `docs/tasks/APP-M2.md` 中 `APP-M2-T021` 状态已同步更新为 `in-review`；
- `docs/TASK_BOARD.md` 中 `APP-M2-T021` 状态已同步推至 `in-review`；
- `docs/DOCUMENT_INDEX.md` 已登记 `D-756` 与 `D-757`；
- 建议 PM 在 QA 独立复验及 PD 产品对照无误后，正式核准标 `done`。
