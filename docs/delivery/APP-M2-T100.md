为什么有这个文件：记录 APP-M2-T100 分册格式、闭环及导出设置（分工复用T14）的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或尚未生效的设置当作已验收。

# APP-M2-T100：分册格式、闭环及导出设置（分工复用T14）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T100 |
| 代码解释 | [APP-M2-T100](../code/APP-M2-T100.md) |
| 验收 | 2026-10-31：每个分册可保存编制方式（系统编制/系统外编制）、内部截止时间（晚于项目投标截止时间给警告）、单独密封、页码方式（每册从 1 起/连续）、暗标、封面模板、递交文件名。递交文件名含 {编写人} 变量或本项目成员姓名时保存返回 422；导出递交版时分册设置的递交文件名优先于命名规则。递交版需填完整值的敏感字段类别（身份证件号码、手机号、银行账号）只有项目负责人可勾选，必须关联本项目的招标要求作为依据，记录确认人和时间。 验证见 [验证记录](../testing/2026-10-31-t097-t100-project-status-settings.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T100](../tasks/APP-M2.md#app-m2-t100)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §4.3、§5.1.1～5.1.5；本批 T097～T100 共用同一组后台设置接口，文件清单见各卡

## 实际文件
- `project_settings_groups.py`：`validate_volume_settings`、`save_volume_settings`（`PUT …/volume-settings`，`updateVolumeSettings`）、`validate_full_value`、`save_full_value`（`PUT …/submit-full-value`，`updateSubmitFullValue`）
- `export_naming.py`：递交版优先用分册设置的 `submit_file_name`
- `project_settings_schemas.py`：`VolumeSettingInput`、`FullValueUpdate` 等
- `frontend/web/src/project/ProjectSettingsGroups.tsx`（`VolumeFormatCard`、`FullValueCard`）、`project-settings-core.ts`（`volumeSettingsPayload`、`fullValuePayload`、`canConfirmFullValue`）

## 测试证据
- `tests/backend/test_project_status_settings.py`：`test_volume_settings_save_read_back_and_warn_on_late_internal_deadline`、`test_submit_file_name_rejects_writer_variable_and_writer_name`（含编写人 403、重复分册、非法时间）、`test_volume_file_name_is_used_for_the_submission_export`、`test_full_value_categories_need_basis_and_only_the_lead_can_confirm`（无依据、依据不存在、非法类别、编写人 403、清空）
- `frontend/web/tests/unit/project-settings-core.test.mjs`：分册设置与完整值校验

## 未实现项与限制
- **除递交文件名外，分册格式设置目前只保存、不生效**：编制方式、单独密封、页码方式、暗标、封面模板没有被导出、写作方案确认或检查读取（导出页码与封面沿用 T197 的既有逻辑）；系统外编制也未放宽“未指定负责人不能确认写作方案”的门禁。
- **完整值类别只保存、不生效**：导出代码目前没有按类别决定递交版是否显示完整身份证件号码、手机号、银行账号（内部稿掩码是已有逻辑），所以 PRD 5.9.1 第 8 条的“未勾选类别在递交版同样掩码”尚未由本设置驱动。
- 分册的新增、删除、改名、类型（技术/商务/资格/报价/其他）、“删除前须转移章节”“已定稿不能删除”未做，分册仍只有技术、商务两册。
- 生成闭环（本项目关闭章节模型评审、章节生成顺序）未做；合标负责人沿用 T14 的团队设置。
- 递交文件名只拦编写人变量和本项目成员姓名，不会识别其他可能暴露编写人的内容。
- 完整值依据的招标要求没有检查该条款是否真的提到“填写完整证件号码”。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。`spec/openapi/demo-v1.json` 未手改，由 CI 产物 `openapi-regenerated` 更新。
