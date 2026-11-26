为什么有这个文件：记录目录编辑「未挂载池」防丢机制与全局项目事实表交付。

# TV-M0-T23 交付

| 项 | 内容 |
|---|---|
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done |
| Issue | [ISSUE-054](../../issues/ISSUE-054.md) |
| 代码 | [TV-M0-T23](../code/TV-M0-T23.md) |

## 实际变更

- 需求与目录节点保持解耦：删除章节或叶子节点非叶化时，孤儿 `requirement_id` 自动退回 `unassigned_requirements`（未挂载池），支持重新挂载到目标章节或一键归入「其他服务承诺」兜底节。
- `replace_outline` 同步维护 `response_tasks`：未挂载需求仍保留显式任务，不静默丢失。
- `confirm_directory` 门禁：未挂载池非空且未显式放行时返回 `409 UNASSIGNED_REQUIREMENTS`；前端确认弹窗强提醒并展示未挂载清单。
- 新增全局项目事实表（Global Fact Sheet）：项目名、甲方名、服务期、质保期、SLA 响应、驻场人数、项目经理、目标产品型号列表、技术路线；目录确认阶段可核对编辑，确认时冻结为 `global_fact_sheet_snapshot` 作为全书唯一事实基准。
- 前端 `OutlineTreeView` 显示各节挂载计数与未挂载池，`EditorPage` 提供事实表核对编辑入口与确认警告。

## 验收证据

- 后端未挂载池/事实表单测：2 passed；前端 outline 单测：8 passed。
- `export_openapi.py` 已重新导出契约，`--check` 一致。

## 局限

- 未挂载池的 409 可被显式放行参数覆盖（按设计保留人工兜底）。
- 只用合成数据验证；未做真实招标文件端到端验收。

## 同步

PRD、ROADMAP、ARCHITECTURE：无改动，按 [ISSUE-054](../../issues/ISSUE-054.md) 的 Wave 2 设计执行。
