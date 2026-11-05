为什么有这个文件：记录工单 6（编辑台 UI 精简）实际改了什么。

它解决什么问题：主路径确认目录 → 开始生成 → 导出可见；工具栏白名单，去掉事实条与重锁挡板。

# TV-M0-T13 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T13](../tasks/TV-M0.md#tv-m0-t13) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| 代码解释 | [TV-M0-T13](../code/TV-M0-T13.md) |

## 实际变更

- 技术分册主路径条：确认目录 / 开始生成 / 导出 / 覆盖视图（次要）。
- 精简工具栏白名单：撤回重做、加粗、下划线、字号、对齐、表格、图片、开始生成；版本降为次级；隐藏事实变量条与段落锁主条、生成候选。
- 目录树：搜索、节状态（未生成/生成中/已生成/待补/需核对）；未取得编辑权改为轻量提示。

## 验收证据

- `node --test tests/unit/technical-editor-ui.test.mjs` → 2 passed。
- `pnpm --dir frontend/web lint` → OK。
- 未宣称：写作助手双模式完整后端（见 TV-M0-T14）。

## 基线同步

TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue 本轮已更新。
