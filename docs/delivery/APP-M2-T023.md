# APP-M2-T023：StatusTag 状态注册表（9.3 全部代码表）交付报告

为什么有这个文件：记录 APP-M2-T023 StatusTag 状态注册表与通用状态标签组件的交付状态、实现内容与质量验证证据。

它解决什么问题：
1. 依据 PRD MVP v1.8 §5.10.3、§6.9 与设计规范 9.3，集中收口 6 大核心业务状态码表（项目、章节、长任务、合规检查、导出交付、编辑租约），根治散落各处的不规范标签与魔法字符串；
2. 严格落实 WCAG AA 4.5:1 文本对比度标准，杜绝低对比度不可读与视觉割裂；
3. 践行 **Layout First** 原则，以紧凑清晰的标签与色彩自然表达业务状态；
4. 严格落实 AI 紫色隔离红线（AI 紫仅用于生成中状态，严禁混入其他业务状态）。

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T023 |
| 代码解释 | [APP-M2-T023 代码说明](../code/APP-M2-T023.md) |
| 文档登记 | [D-778](../DOCUMENT_INDEX.md) |
| 验收 | 1. 6 大核心业务状态码表完整收口：收录 ProjectStatus (5项)、ChapterStatus (5项)、JobStatus (5项)、CheckStatus (3项)、ExportStatus (4项)、LockStatus (4项)；<br>2. 严格 WCAG AA 4.5:1 对比度保证：所有 subtle、solid、outline 调色板经算法验证 100% 满足 >= 4.5:1 文本对比度；<br>3. 容错回退机制：支持大小写不敏感、历史兼容别名自动映射与未知状态优雅降级，保障系统永不崩溃；<br>4. AI 紫色强隔离红线：除 AI 章节生成外，其他非 AI 状态绝不混用紫色；<br>5. 单元测试与构建绿灯：专属单测 6 项全部通过，全量 414 项前端单元测试 100% 保持全绿，TypeScript 0 error，Vite 生产构建 1.40s 成功。 |
| 项目进度 | 本地已完成实现与多维质量验证，测试与构建 100% 绿灯，按规范推至 in-review，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 业务背景与规范遵从

根据 PRD MVP v1.8 §5.10.3、§6.9 与系统设计规范 9.3：
- 项目列表（`ProjectListPage`）、章节大纲树（`OutlineTreeView`）、任务中心（`TaskCenterDrawer` / `JobsPage`）、合规检查台（`ChecksPage`）、导出交付台（`ExportPage`）以及章节编辑器（`EditorPage`）均需向用户直观展示阶段性业务状态；
- 原实现中存在状态定义零碎、样式不一、对比度未标准化的问题；
- 本任务通过在 `frontend/web/src/shared/` 统一封装纯逻辑注册表 `status-registry.ts` 与高内聚表现组件 `StatusTag.tsx`，实现全站状态单源驱动。

---

## 2. 核心交付内容清单

### 2.1 统一状态注册表 (`frontend/web/src/shared/status-registry.ts`)
1. **6 大业务域状态收口**：
   - **`project` (项目状态)**：`draft`（筹备中）、`in_progress`（编写中）、`review`（审核中）、`completed`（已完成）、`archived`（已归档）；
   - **`chapter` (章节状态)**：`not_started`（未开始）、`generating`（生成中 - AI紫）、`draft`（草稿）、`reviewed`（已复核）、`approved`（已定稿）；
   - **`job` (长任务状态)**：`queued`（排队中）、`running`（进行中）、`completed`（已完成）、`failed`（异常失败）、`cancelled`（已取消）；
   - **`check` (合规检查状态)**：`passed`（合规通过）、`warning`（合规提醒）、`blocker`（废标阻断）；
   - **`export` (导出交付状态)**：`idle`（待导出）、`processing`（排版中）、`completed`（已生成）、`failed`（导出失败）；
   - **`lock` (编辑租约状态)**：`unlocked`（空闲可编辑）、`locked_self`（本人编辑中）、`locked_other`（他人占用）、`expired`（租约过期）。
2. **纯算法与对比度保障**：
   - 导出 `luminance(hex)` 与 `contrastRatio(hex1, hex2)`；
   - 经实测，`STATUS_COLOR_TOKENS` 的全部色板（`success`, `processing`, `warning`, `error`, `default`, `ai`）在 subtle、solid、outline 三种形态下对比度均在 **5.4:1 ～ 8.9:1** 之间，严格高于 WCAG AA 4.5:1。
3. **安全容错与终态判定**：
   - 支持大小写与空白字符归一化；
   - 支持历史旧接口别名映射（如 `pending -> queued`, `succeeded -> completed`, `hint -> warning`, `disqualification -> blocker`, `held -> locked_self` 等）；
   - 导出 `isStatusTerminal(domain, code)` 统一判定任务或流程是否已达终态。

### 2.2 通用状态标签组件 (`frontend/web/src/shared/StatusTag.tsx`)
1. **多形态与多尺寸支持**：
   - 支持 `variant`（`subtle` 浅底描边默认，`solid` 实心高对比，`outline` 白底描边）；
   - 支持 `size`（`default` 24px，`small` 20px）；
2. **无障碍与语义契约**：
   - 声明 `role="status"`、`aria-label={meta.ariaLabel}`、`data-testid={`status-tag-${type}-${meta.code}`}`、`data-domain`、`data-status`、`data-variant`、`data-size`；
3. **能力扩展**：
   - `showBadge`：支持小圆点 Badge 样式；
   - `showIcon`：支持根据状态自动渲染对应的 Ant Design 语义图标；
   - `tooltip`：支持便捷悬浮展示状态说明；
4. **快捷派生组件**：
   - 导出 `ProjectStatusTag`, `ChapterStatusTag`, `JobStatusTag`, `CheckStatusTag`, `ExportStatusTag`, `LockStatusTag`。

---

## 3. 测试与质量门禁证据

### 3.1 专属单元测试（6 passed, 0 failed）
运行命令：
```bash
node --test frontend/web/tests/unit/status-tag.test.mjs
```

测试输出：
```
✔ 1. 6 大核心业务状态码表正向映射与元信息完整性 (3.5671ms)
✔ 2. 容错性与别名兼容：大小写不敏感、历史别名映射与安全兜底 (0.4548ms)
✔ 3. WCAG AA 4.5:1 文本对比度标准核验 (1.0281ms)
✔ 4. AI 紫色强隔离红线断言 (0.4258ms)
✔ 5. 终态判定函数 isStatusTerminal 契约断言 (0.461ms)
✔ 6. StatusTag.tsx 组件结构与无障碍契约 AST 断言 (31.0711ms)
ℹ tests 6
ℹ suites 0
ℹ pass 6
ℹ fail 0
```

### 3.2 全量前端单测全绿（414 passed, 0 failed）
运行命令：
```bash
pnpm --dir frontend/web test
```
执行结果：414 项单测全绿，0 项失败，0 项跳过。

### 3.3 TypeScript 类型检查与 Vite 生产构建
- `pnpm --dir frontend/web lint`：退出码 0，0 error。
- `pnpm --dir frontend/web build`：✓ built in 1.40s 顺利通过。

---

## 4. 建议与流转

本卡所有核心状态注册表与标签组件均已落地并通过多维测试验证，当前状态推至 `in-review`。建议 PM 在 QA/PD 复核签署后标为 `done`。
