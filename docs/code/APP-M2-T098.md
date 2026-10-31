# 代码说明：APP-M2-T098 项目基本字段和合作方协议（成员复用T14）

为什么有这个文件：说明 基本字段人工修改标记、合作方协议校验与缺协议标记在后台与前端的接线方式和规则所在位置。

它解决什么问题：以后改状态流转、设置校验或占用口径时，知道规则在哪个文件、前端哪里只是展示。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T098 |
| 交付文件 | `docs/delivery/APP-M2-T098.md` |
| 影响模块 | `backend/bid-core/icg/domain/project_settings.py`、`project_settings_groups.py`、`workflow_schemas.py`、`frontend/web/src/project/ProjectSettingsPage.tsx`、`ProjectSettingsGroups.tsx`（`PartnersCard`）、`project-form.ts`（`basicInfoFields`）、`project-settings-core.ts` |
<!-- code-explanation:end -->

## 接线
- `backend/bid-core/icg/domain/project_settings.py`：`patch_project` 接收 `basic_info`、记录 `manual_edits`、合作方校验
- `project_settings_groups.py`：`mark_manual_edits`、`validate_partners`、`partner_rows`
- `workflow_schemas.py`：`ProjectPatch.basic_info`、`ProjectPartnerInput.relation_type/work_share`；`project_settings_schemas.py`（新）：`ProjectBasicInfo`、`PartnerRow`、`ProjectSettings`
- `frontend/web/src/project/ProjectSettingsPage.tsx`、`ProjectSettingsGroups.tsx`（`PartnersCard`）、`project-form.ts`（`basicInfoFields`）、`project-settings-core.ts`

## 约束
- 所有写入走 `WorkflowService._write`（Idempotency-Key、If-Match、审计）；动作名 `project.update:<组>`，在 `_authorize` 里按 `project.update` 要求项目负责人，编写人、只读成员被拒。
- 设置数据存在项目工作流（`status`、`basic_info`、`manual_edits`、`rule_overrides`、`volume_settings`、`submit_full_value`），不新增数据库列。
- `workflow_orchestrator.py` 只加取消只读守卫和阶段推导的调用，仍不超过 350 行；新逻辑在 `project_lifecycle.py`、`project_settings_groups.py`。
- 前端页面组件只展示与提交，规则在 `project-settings-core.ts`、`project-header-core.ts` 的纯函数里（可用 `node --test` 验证）；后台是最终裁决。`App.tsx` 未改动。

## 依赖与限制
无新依赖。限制见交付文档“未实现项与限制”。
