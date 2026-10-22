为什么有这个文件：说明橙色标签对比只改了文字色。

它解决什么问题：避免以后把浅底或绿红标签也改掉，或再加一个颜色库。

# ISSUE-036：代码解释

- 对应 Issue、交付文档：[ISSUE-036](../../issues/ISSUE-036.md)，[交付](../delivery/ISSUE-036.md)。
- 日期、实际代码路径：2026-10-12。`frontend/web/src/shared/styles.css`、`frontend/web/e2e/app-shell.spec.ts`。不新增任务卡。PR 未新开。

## 改了什么以及为什么

Ant Design 5 的预设标签用色板第 7 级做文字、第 1 级做浅底。橙色约 3.34:1，金色约 2.76:1，warning 色 `#faad14` 更低。页面已经用 `#9a5608` 写警告图标。标签改成同一个字色后，在橙色浅底 `#fff7e6` 上约 5.31:1，在金色浅底 `#fffbe6` 上约 5.45:1。

选择器是 `.ant-tag.ant-tag-orange`、`.ant-tag.ant-tag-gold`、`.ant-tag.ant-tag-warning`。运行时样式带哈希类，普通选择器压不住，所以文字色使用 `!important`。底色和边框仍是预设浅色，标签仍能看出警告。

`statusColor` 对非确认、非退回的条款返回 `orange`。顶栏“示例数据”、待确认项目、编辑台待办、SLA 待确认和未量化、支撑页“尚未实现”、写作计划待核对，都走这三类颜色之一。不改组件调用。

## 验证与限制

概览页可见的橙色标签纳入已有对比检查，门槛仍是 4.5:1。没有逐页打开 SLA 金色标签。没有新依赖。见 [核对](../testing/2026-10-12-issue-036-orange-contrast.md)。
