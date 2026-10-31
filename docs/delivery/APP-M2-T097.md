为什么有这个文件：记录 APP-M2-T097 项目概览（待办、分册、状态操作）的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或尚未生效的设置当作已验收。

# APP-M2-T097：项目概览（待办、分册、状态操作）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T097 |
| 代码解释 | [APP-M2-T097](../code/APP-M2-T097.md) |
| 验收 | 2026-10-31：项目负责人可登记递交（须已有成功导出的递交版）、开标、结果（中标/未中标/废标/流标）或在递交前取消项目（须写原因，不可撤销）；不合规的流转后台返回 409 INVALID_STATUS_TRANSITION。取消后一切经 `WorkflowService._write` 的写入返回 409 PROJECT_CANCELLED，设置页整体只读，概览显示“已取消”。投标截止倒计时不超过 3 天（含恰好 3 天）显示红色。导出页签在没有导出权限时不显示。概览待办追加后台给出的真实待办（合作方缺协议、分册无负责人、分册内部截止临近、距投标截止不足 3 天、拟派人员占用），每项可一键跳转。 验证见 [验证记录](../testing/2026-10-31-t097-t100-project-status-settings.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T097](../tasks/APP-M2.md#app-m2-t097)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §4.3、§5.1.1～5.1.5；本批 T097～T100 共用同一组后台设置接口，文件清单见各卡

## 实际文件
- `backend/bid-core/icg/domain/project_lifecycle.py`（新）：状态流转、取消只读守卫、占用冲突
- `backend/bid-core/icg/domain/project_settings_groups.py`（新）：待办 `project_todos`、设置读回 `project_settings`
- `backend/bid-core/icg/domain/workflow_orchestrator.py`：`_write` 加取消只读守卫；`workspace` 返回 `project_status`；阶段推导抽为 `workspace_stage`（仍为 336 行，上限 350）
- `icg/api/workflow.py`：`POST /api/v1/projects/{p}/status`（`transitionProjectStatus`）、`GET …/settings`（`getProjectSettings`）
- `errors.py`、`frozen_error_codes.py`：`INVALID_STATUS_TRANSITION`、`PROJECT_CANCELLED`（均 409）
- `frontend/web/src/project/project-header-core.ts`（倒计时红色、`tabAllowedByPermissions`）、`ProjectSettingsGroups.tsx`（状态卡）、`OverviewTab.tsx`、`project-settings-core.ts`（新）

## 测试证据
- `tests/backend/test_project_status_settings.py`：`test_cancel_makes_project_read_only_and_cannot_be_undone`、`test_status_flow_submit_open_result_follows_the_state_diagram`、`test_submit_needs_a_successful_submission_export_and_only_the_lead_changes_status`（含编写人、只读成员权限反例）、`test_stale_version_and_replay_for_status_change`（旧版本与重复请求）、`test_overview_todos_cover_volume_owner_and_internal_deadline`
- `frontend/web/tests/unit/project-settings-core.test.mjs`（倒计时 3 天边界、页签、状态按钮）；`project-header-list.test.mjs` 的颜色断言由 orange 改为 red
- `frontend/web/e2e/project-status-settings.spec.ts`

## 未实现项与限制
- 项目表没有状态列：登记类状态存在项目工作流里，草稿、待确认、编制中、已导出由工作台阶段推出；“解析中”“检查中”“可导出”不单列，项目列表接口和列表页的状态筛选、6 张统计卡、复制为新项目、列表内取消入口未改（属项目列表卡）。
- 取消只读只拦经 `_write` 的写入；不经 `_write` 的写入（编辑台正文锁与提交、资料库、旧 `/api/chapters` 路由）未拦截，前端除设置页外各页签也没有整体置灰。
- “已递交触发人员占用、已开标释放、中标转履约占用”只做了提示口径（已开标/已结束/已取消的项目不再计入占用），没有占用台账，也没有“中标转履约占用”。
- 倒计时 3 天为写死常量，未做公司可配置；列表“3 天内置顶”沿用 `isUrgent` 的口径（现为 ≤3 天），未单独验证置顶排序。
- 页签只收紧导出页签（与会话 `project.export` 路由一致）；合规检查页签对只读成员仍可见，因为只读成员需要查看检查结果。
- 概览待办未包含“证书在截止时间前过期”“原厂专项授权需提前申请”“定稿后已修改待复核”“分册已定稿等待交叉复核”；分册内部截止待办只在填了内部截止时间后出现。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。`spec/openapi/demo-v1.json` 未手改，由 CI 产物 `openapi-regenerated` 更新。
