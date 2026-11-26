为什么有这个文件：解释 TV-M0-T23 未挂载池防丢与全局项目事实表的代码。

# TV-M0-T23 代码说明

| 文件 | 说明 |
|---|---|
| [technical_outline.py](../../backend/bid-core/icg/domain/technical_outline.py) | `replace_outline` 同步 `response_tasks` 与 `unassigned_requirements`；删节/非叶化的孤儿需求退回未挂载池而非静默丢弃；`confirm_directory` 未挂载非空且未放行返回 `409 UNASSIGNED_REQUIREMENTS` |
| [technical_fact_sheet.py](../../backend/bid-core/icg/domain/technical_fact_sheet.py) | `build_global_fact_sheet`（人工保存优先，模型读标事实/通用事实/拟派团队补齐）、`update_global_fact_sheet`、`freeze_global_fact_sheet`（确认目录时冻结 `global_fact_sheet_snapshot`）、`prompt_fact_sheet_json`（注入 Prompt 的精简字典） |
| [api/workflow.py](../../backend/bid-core/icg/api/workflow.py) | 事实表读取/保存接口、目录确认携带未挂载放行参数 |
| [workflow_schemas.py](../../backend/bid-core/icg/domain/workflow_schemas.py) | 未挂载池、事实表字段的响应模型 |
| [outline-tree.ts](../../frontend/web/src/project/outline-tree.ts) | 挂载/卸载纯函数、未挂载池收集 |
| [OutlineTreeView.tsx](../../frontend/web/src/project/OutlineTreeView.tsx) | 各节挂载计数徽标、未挂载池展示与重挂交互、确认前强提醒 |
| [EditorPage.tsx](../../frontend/web/src/editor/EditorPage.tsx) | 全局事实表核对编辑入口与确认警告 |
