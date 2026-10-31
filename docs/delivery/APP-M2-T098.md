为什么有这个文件：记录 APP-M2-T098 项目基本字段和合作方协议（成员复用T14）的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或尚未生效的设置当作已验收。

# APP-M2-T098：项目基本字段和合作方协议（成员复用T14）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T098 |
| 代码解释 | [APP-M2-T098](../code/APP-M2-T098.md) |
| 验收 | 2026-10-31：项目设置的基本信息增加招标人、代理机构、标段、对招标人称呼、开标时间、服务期、项目地点；保存时只有值真的变了的字段才记“已人工修改”（修改人、时间），设置页在字段下显示。合作方保存时校验主体不能为空、不能重复，协议附件编号为空时保存成功但读回标“缺协议”，设置页与概览待办同时提示。成员、参与分册、负责人沿用 APP-M1-T14，不重复计算。引用合作方资料的门禁（缺协议不能被章节引用）是此前已有的 `matrix.py`、R04/R18 逻辑，本卡未改。 验证见 [验证记录](../testing/2026-10-31-t097-t100-project-status-settings.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T098](../tasks/APP-M2.md#app-m2-t098)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §4.3、§5.1.1～5.1.5；本批 T097～T100 共用同一组后台设置接口，文件清单见各卡

## 实际文件
- `backend/bid-core/icg/domain/project_settings.py`：`patch_project` 接收 `basic_info`、记录 `manual_edits`、合作方校验
- `project_settings_groups.py`：`mark_manual_edits`、`validate_partners`、`partner_rows`
- `workflow_schemas.py`：`ProjectPatch.basic_info`、`ProjectPartnerInput.relation_type/work_share`；`project_settings_schemas.py`（新）：`ProjectBasicInfo`、`PartnerRow`、`ProjectSettings`
- `frontend/web/src/project/ProjectSettingsPage.tsx`、`ProjectSettingsGroups.tsx`（`PartnersCard`）、`project-form.ts`（`basicInfoFields`）、`project-settings-core.ts`

## 测试证据
- `tests/backend/test_project_status_settings.py`：`test_manual_edit_marks_only_changed_basic_fields`（含编写人 403）、`test_partner_without_agreement_is_flagged_and_listed_in_todos`（缺协议标记、重复合作方 422、校验失败不覆盖已有）
- `frontend/web/tests/unit/project-settings-core.test.mjs`：人工修改标记、合作方负载
- `frontend/web/e2e/project-status-settings.spec.ts`：设置页显示“缺协议”和“已人工修改”

## 未实现项与限制
- 协议附件编号是自由文本：系统没有附件表可核对编号是否存在，页面也没有协议上传入口（资料库上传是已有流程）；合作方主体 `partner_entity_id` 同样是自由文本，没有对 org_entity 做存在与“合作伙伴”范围校验。
- “重新从解析结果带出”未做：基本信息只能人工填写，解析结果不会自动填入这些字段。
- 预算、最高限价、招标涉及的厂商产品清单、项目大类等 PRD 基本信息未新增字段。
- 人工修改标记只记最近一次修改人和时间，不保留逐次修改历史（审计里有每次保存）。
- “投标主体进入编制中后修改须负责人确认并触发 R02 重核”未做。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。`spec/openapi/demo-v1.json` 未手改，由 CI 产物 `openapi-regenerated` 更新。
