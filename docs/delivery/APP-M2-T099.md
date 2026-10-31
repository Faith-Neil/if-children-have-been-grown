为什么有这个文件：记录 APP-M2-T099 项目设置：拟派人员、SLA 取值、规则覆盖的实际交付和测试证据。

它解决什么问题：说明做到什么、没做什么，避免把未运行的测试或尚未生效的设置当作已验收。

# APP-M2-T099：项目设置：拟派人员、SLA 取值、规则覆盖

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T099 |
| 代码解释 | [APP-M2-T099](../code/APP-M2-T099.md) |
| 验收 | 2026-10-31：保存或读取拟派人员时，同公司其他在投项目（未开标、未结束、未取消）已拟派同一人则返回占用提示并显示在拟派人员卡上，只提示不锁定。项目设置的 SLA 取值组显示所选模板、取值项数、超出能力项数、待重新核对项数，并跳转服务承诺矩阵（项目内改写仍在矩阵页，不回写资料库，此前已有）。项目级规则覆盖（证明材料有效天数、有效期覆盖服务期、本单位人员、社保月数）可保存、读回，保存时校验规则名、取值范围和依据的招标要求，整组替换、仅项目负责人可写。 验证见 [验证记录](../testing/2026-10-31-t097-t100-project-status-settings.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T099](../tasks/APP-M2.md#app-m2-t099)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §4.3、§5.1.1～5.1.5；本批 T097～T100 共用同一组后台设置接口，文件清单见各卡

## 实际文件
- `project_lifecycle.py`：`occupancy_conflicts`；`staff_proof_rules.py`：拟派人员读写返回 `occupancy`
- `project_settings_groups.py`：`validate_rule_overrides`、`save_rule_overrides`（`PUT …/rule-overrides`，`updateRuleOverrides`）、设置读回的 `sla` 摘要
- `frontend/web/src/project/ProposedStaffCard.tsx`、`proposed-staff-core.ts`（`occupancyMessages`）、`ProjectSettingsGroups.tsx`（`SlaSummaryCard`、`RuleOverridesCard`）

## 测试证据
- `tests/backend/test_project_status_settings.py`：`test_staff_occupancy_is_a_hint_and_released_after_open_or_cancel`、`test_settings_sla_is_none_without_template_and_hidden_from_other_companies`、`test_rule_overrides_validate_and_replace_as_a_whole`（非法取值、重复、不存在的依据、编写人 403、失败不改已存的）
- `frontend/web/tests/unit/project-settings-core.test.mjs`：规则覆盖校验、占用提示文字

## 未实现项与限制
- **项目级规则覆盖目前只保存、不生效**：合规检查引擎（`compliance_rules.py` 的 R03、R11 等）尚未读取这些覆盖值，所以 PRD 验收③“覆盖规则生效后合规检查结果随之变化”未满足；页面上已明示。
- 占用提示按“同公司、其他项目、状态未收口”判断，没有比较时间段是否重叠，也没有 `conflict_status`（已知悉）字段；跨公司占用不提示。
- SLA 取值的改写、超出能力判定是此前已有的矩阵页功能，本卡只在设置页读回摘要，没有在设置页内编辑取值。
- 拟派人员的 R12 人员占用冲突检查规则（T217）不在本卡。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。`spec/openapi/demo-v1.json` 未手改，由 CI 产物 `openapi-regenerated` 更新。
