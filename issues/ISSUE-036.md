为什么有这个文件：登记前端橙色和警告色状态标签对比不足。

它解决什么问题：避免浅底上的橙色标签文字看不清，也不占用已保留的 ISSUE-034 与 ISSUE-035。

# ISSUE-036：橙色状态标签对比度

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-036 |
| 类型 | bug |
| 优先级 | P3 |
| 状态 | in-review |
| 负责人 | frontend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | orange-tag-contrast-1 |
| 关联 Task | 不新增任务卡。已有页面上的橙色、金色和 warning 标签，不改 APP-M2 卡片状态。见 [任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | 未新开。随 [PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 提交，未合入 |
| 本地验收 | 计算对比和概览页可见橙色标签已核对。见 [核对](../docs/testing/2026-10-12-issue-036-orange-contrast.md)。不标 closed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [交付](../docs/delivery/ISSUE-036.md) |
| 代码 / 流程解释 | [代码解释](../docs/code/ISSUE-036.md) |
| 验证记录 | [核对](../docs/testing/2026-10-12-issue-036-orange-contrast.md) |

不新增任务卡。这是已有 `frontend/web` 标签的对比修正，不新开 APP 卡，也不把任何任务标 done。ISSUE-034 与 ISSUE-035 保留，本号不用它们。

## 现象与证据

Ant Design 预设 `Tag color="orange"` 的文字色是色板第 7 级 `#d46b08`，底是第 1 级 `#fff7e6`，对比约 3.34:1，低于正文 4.5:1。金色预设 `#d48806` 在 `#fffbe6` 上约 2.76:1。`color="warning"` 使用警告色 `#faad14`，在浅底上更低。

页面里这些标签用于待确认、待核对、示例数据、尚未实现、超出能力，以及 SLA 未量化（金色）。具体位置：`App.tsx`、`ProjectPages.tsx` 的 `statusColor`、`EditorPage.tsx`、`SlaPages.tsx`、`SupportPages.tsx`、`WritingPlanReview.tsx`。项目里已有正文橙色 `.orange{color:#9a5608}`，标签没有跟这个色。

## 影响与分流

- 影响范围：`frontend/web` 里橙色、金色和 warning 状态标签的文字色。不改绿、红、蓝标签，不改按钮，不改后台。
- 本次处理：样式覆盖文字色为 `#9a5608`。浅底保留，标签仍能看出是警告色。不新增依赖。
- 依赖：无。ISSUE-033 的挂证据缺口不在本 Issue。不关闭 ISSUE-033。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| 无新增任务卡 | 提高已有橙色、金色和 warning 标签文字对比 | `frontend/web/src/styles.css`；`frontend/web/e2e/app-shell.spec.ts` | AC-01～AC-02 | in-review |

不新增任务卡，因为没有新页面或新接口。交付、核对和代码解释回链本 Issue。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 橙色、金色和 warning 标签文字在各自浅底上达到 4.5:1 | 本地计算：`#9a5608` 在 `#fff7e6` 上 5.31:1，在 `#fffbe6` 上 5.45:1。概览页可见橙色标签由浏览器核对。见 [核对](../docs/testing/2026-10-12-issue-036-orange-contrast.md)。不标 closed |
| AC-02 | 不新增依赖，只改 `frontend/web` 的样式和已有对比检查 | 已改 `styles.css` 与 `app-shell.spec.ts`。未改 `package.json` |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。没有新需求，也不改里程碑快照 | 无 | orange-tag-contrast-1 / ISSUE-036 / 2026-10-12 | 已核对 |
| ROADMAP | 无影响。没有新阶段 | 无 | 同上 | 已核对 |
| ARCHITECTURE | 无影响。没有新模块或接口 | 无 | 同上 | 已核对 |
| TASK_BOARD | 无影响于任务状态。不新增任务卡。同一提交另把 APP-M2-T114 与 REV-M0-T22 标为 done | `docs/TASK_BOARD.md` 开篇计数 | 同上 | 已核对 |
| PROJECT_STATUS | 无影响于本缺陷的产品阶段。开篇计数随看板更新 | `docs/PROJECT_STATUS.md` | 同上 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、交付、代码解释、核对和同步表 | `docs/DOCUMENT_INDEX.md` | 同上 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | orange-tag-contrast-1 / in-review | 已把橙色、金色和 warning 标签文字改为 `#9a5608`。等待复核。不标 closed | [核对](../docs/testing/2026-10-12-issue-036-orange-contrast.md) |

## 本地验收与后续合入发布

- 本地验收结论与日期：对比计算与概览页可见橙色标签已在 2026-10-12 核对。状态保持 in-review，不标 closed。
- 未覆盖：没有逐页点开 SLA 金色标签和“尚未实现”页。样式选择器覆盖这三类标签，浅底按 Ant Design 默认色板计算。
- PR 状态：[PR #3](https://github.com/Faith-Neil/if-children-have-been-grown/pull/3) 待合入。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
