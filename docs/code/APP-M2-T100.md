# 代码说明：APP-M2-T100 分册格式、闭环及导出设置（分工复用T14）

为什么有这个文件：说明 分册格式、编制方式、密封/暗标/页码/封面、递交文件名、完整值类别在后台与前端的接线方式和规则所在位置。

它解决什么问题：以后改状态流转、设置校验或占用口径时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T100 |
| 交付文件 | `docs/delivery/APP-M2-T100.md` |
| 影响模块 | `project_settings_groups.py`、`export_naming.py`、`project_settings_schemas.py`、`frontend/web/src/project/ProjectSettingsGroups.tsx`（`VolumeFormatCard`、`FullValueCard`）、`project-settings-core.ts`（`volumeSettingsPayload`、`fullValuePayload`、`canConfirmFullValue`） |
<!-- code-explanation:end -->

## 接线
- `project_settings_groups.py`：`validate_volume_settings`、`save_volume_settings`（`PUT …/volume-settings`，`updateVolumeSettings`）、`validate_full_value`、`save_full_value`（`PUT …/submit-full-value`，`updateSubmitFullValue`）
- `export_naming.py`：递交版优先用分册设置的 `submit_file_name`
- `project_settings_schemas.py`：`VolumeSettingInput`、`FullValueUpdate` 等
- `frontend/web/src/project/ProjectSettingsGroups.tsx`（`VolumeFormatCard`、`FullValueCard`）、`project-settings-core.ts`（`volumeSettingsPayload`、`fullValuePayload`、`canConfirmFullValue`）

## 约束
- 所有写入走 `WorkflowService._write`（Idempotency-Key、If-Match、审计）；动作名 `project.update:<组>`，在 `_authorize` 里按 `project.update` 要求项目负责人，编写人、只读成员被拒。
- 设置数据存在项目工作流（`status`、`basic_info`、`manual_edits`、`rule_overrides`、`volume_settings`、`submit_full_value`），不新增数据库列。
- `workflow_orchestrator.py` 只加取消只读守卫和阶段推导的调用，仍不超过 350 行；新逻辑在 `project_lifecycle.py`、`project_settings_groups.py`。
- 前端页面组件只展示与提交，规则在 `project-settings-core.ts`、`project-header-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决。`App.tsx` 未改动。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
