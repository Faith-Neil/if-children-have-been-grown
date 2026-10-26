为什么有这个文件：记录 BE-COMPLIANCE-RULES-P0 第一批核心合规规则编号落地的交付事实、测试证据与验收记录。

它解决什么问题：作为质量门禁依据，证明 PRD v1.8 MVP §5.8 / §5.8.1 / §5.8.5（核心合规规则编号落地体系：R15/R23/R34/R37）已在 `backend/bid-core/icg/` 上下文分包中落地、统一输出模型 `{rule_id, title, severity, passed, finding_summary, suggestion, issues, details}`、导出前置检查门禁 `run_check` 无缝集成、`/api/v1` 查询与重算端点注册完毕、专属单测 7 项与回归套件 14 项全绿、OpenAPI 契约保持 100% 零漂移一致，并将任务标为 in-review，绝不私自标 done。

# BE-COMPLIANCE-RULES-P0：第一批核心合规规则编号落地交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-COMPLIANCE-RULES-P0 |
| 代码解释 | [BE-COMPLIANCE-RULES-P0](../code/BE-COMPLIANCE-RULES-P0.md) |
| 验收 | 2026-10-23：第一批核心合规规则编号落地（R15/R23/R34/R37）与核验引擎已在 `backend/bid-core/icg/` 分包架构中完全实现；成功支持结构化规则诊断输出（rule_id, title, severity, passed, finding_summary, suggestion, issues, details）；R15 证明材料齐全性（资质/业绩等材料缺失、失效、过期及未确认拦截）；R23 废标红线与关键标星条款响应率（100% 覆盖与非空确认，未响应/被忽略/未映射有效章节赋 blocker）；R34 占位符与“待补/待完善”残留字样排查（正文与条款响应草稿瑕疵阻断 blocking/blocker）；R37 技术/商务偏离表一致性校验（关键条款负偏离强阻断 blocker，正偏离与无偏离前后一致）；集成至 run_check 导出检查门禁，统一赋 rule_id 与 rules 列表；暴露 /api/v1 端点；严禁绕过 RULES_INCOMPLETE 底线；专属单测 7 项全绿，回归套件 14 项全绿，OpenAPI 契约一致性 100% 通过 |
| 项目进度 | 已经 QA 独立终验签署（D-742）与 PD 产品对照核准（D-743），人类 PM 最终确认标为 **done** |
<!-- task-delivery:end -->

## 关联与状态
- **关联 Issue**：[ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-027](../../issues/ISSUE-027.md)
- **依赖任务**：[BE-CHECKS-EXPORT-ALIGN](../tasks/BE-M0.md#be-checks-export-align)、[BE-VOLUME-FINALIZE-GATE](../tasks/BE-M0.md#be-volume-finalize-gate)
- **状态流转**：推进至 `in-review`。严格遵守规范，绝不私自将任务看板标为 `done`，绝不私自关闭 Issue。

## 完成内容与变更清单
1. **结构化合规规则引擎与模型 (`ComplianceRulesEngine`)**：
   - 在 `backend/bid-core/icg/domain/compliance_rules.py` 中实现统一合规规则引擎；
   - 落地统一输出数据结构：`ComplianceRuleResult` 与 `ComplianceRuleIssue`，包含 `rule_id`、`title`、`severity`、`passed`、`finding_summary`、`suggestion`、`issues` 与 `details`；
   - 实现静态规则目录 `CATALOG`，提供规则分类、默认严重度与描述信息。
2. **第一批四大核心 P0 规则落地**：
   - **R15（证明材料齐全性核验）**：识别资质/证书/证明/业绩/授权/财务/纳税等证明类条款，排查未挂接（`EVIDENCE_MISSING`）、证据过期（`EVIDENCE_EXPIRED`）、跨租户或状态未确认（`EVIDENCE_NOT_USABLE`），关键条款赋 blocker、一般条款赋 blocking；
   - **R23（废标红线与关键标星条款 100% 响应率核验）**：核验废标与标星条款状态必须确认（未确认 `REQUIREMENT_PENDING`）、严禁标记为忽略或不适用（`CRITICAL_REQUIREMENT_REJECTED`，blocker）、必须映射到本分册有效章节（`MATRIX_MAPPING_MISSING`，blocker）、必须填写实质有效响应正文且禁止草稿字样（`MATRIX_RESPONSE_MISSING` / `CRITICAL_RESPONSE_INVALID`，blocker）；
   - **R34（占位符与“待补/待完善”残留字样核验）**：使用高性能正则体系扫描已提交章节正文与条款实质响应内容中的占位符（`【待补】`、`待补充`、`【待完善】`、`TODO`、`FIXME`、`{{变量}}` 占位符、AI 对话残留提示），发现即阻断（`CHAPTER_TEXT_PLACEHOLDER` / `REQUIREMENT_RESPONSE_PLACEHOLDER`，blocking/blocker）；
   - **R37（技术/商务偏离表一致性核验）**：核对条款偏离标记（`deviation_type` / `deviation_reason`），关键条款出现负偏离强阻断（`CRITICAL_NEGATIVE_DEVIATION`，blocker），偏离说明不完整时拦截（`DEVIATION_REASON_MISSING`）。
3. **导出检查与编排层集成**：
   - 在 `backend/bid-core/icg/domain/export_service.py` 的 `run_check` 中接入 P0 规则执行结果，自动关联 `rule_id` 并将规则概览注入 `check["rules"]`；
   - 严格保留 `RULES_INCOMPLETE` 底线门禁，系统只要有其余规则未完全实现，严禁假装 complete；
   - 在 `WorkflowService` 中继承 `ComplianceRulesMixin`，并在条款 PATCH 中开放 `deviation_type` 与 `deviation_reason` 偏离表编辑支持。
4. **RESTful API 契约收敛 (`/api/v1`)**：
   - 新增 `POST /api/v1/projects/{project_id}/compliance-rules/evaluate`（触发合规规则重新评估）；
   - 新增 `GET /api/v1/projects/{project_id}/compliance-rules`（读取项目合规规则评估结果）；
   - 新增 `GET /api/v1/compliance-rules/catalog`（读取系统支持规则目录）；
   - 执行 `python backend/bid-core/export_openapi.py` 同步最新 OpenAPI 契约至 `spec/openapi/demo-v1.json`。

## 变更文件清单
- `backend/bid-core/icg/domain/compliance_rules.py`: 新增核心合规规则引擎、四大检测器与领域模型。
- `backend/bid-core/icg/domain/__init__.py`: 导出 `ComplianceRulesEngine`、`ComplianceRulesMixin` 与相关模型。
- `backend/bid-core/icg/domain/export_service.py`: 集成 P0 合规规则核验结果至 `run_check`，赋 `rule_id` 并保留 `RULES_INCOMPLETE` 底线。
- `backend/bid-core/icg/domain/workflow_orchestrator.py`: 混入继承 `ComplianceRulesMixin`，支持 `deviation_type` 与 `deviation_reason`。
- `backend/bid-core/icg/api/compliance.py`: 新增 `/api/v1` 合规规则 evaluate/get/catalog 路由与契约。
- `backend/bid-core/icg/api/__init__.py`: 导出 `include_compliance_routes` 及相关 Pydantic 契约。
- `backend/bid-core/icg_demo/main.py`: 挂载 `include_compliance_routes`。
- `backend/bid-core/icg_demo/workflow_schemas.py`: 扩充 `RequirementPatch` 偏离字段支持。
- `spec/openapi/demo-v1.json`: 同步生成的 OpenAPI 契约。
- `tests/backend/test_compliance_rules_p0.py`: 7 项专属自动化单测用例。
- `docs/code/BE-COMPLIANCE-RULES-P0.md`: 技术实现与架构说明文档。
- `docs/delivery/BE-COMPLIANCE-RULES-P0.md`: 交付报告与测试凭据文档。
- `docs/tasks/BE-M0.md`: 登记 `BE-COMPLIANCE-RULES-P0` 任务定义。
- `docs/TASK_BOARD.md`: 看板更新本卡为 `in-review`。
- `docs/DOCUMENT_INDEX.md`: 登记 D-717 与 D-718 文档索引。

## 自动化测试与验收结果
- **专属测试套件 (`tests/backend/test_compliance_rules_p0.py`)**：
  - `test_r15_proof_material_completeness` PASSED [ 14%]
  - `test_r23_critical_clauses_100_percent_response` PASSED [ 28%]
  - `test_r34_placeholder_and_residual_verification` PASSED [ 42%]
  - `test_r37_deviation_table_consistency` PASSED [ 57%]
  - `test_compliance_rules_catalog_api` PASSED [ 71%]
  - `test_compliance_rules_tenant_and_auth_isolation` PASSED [ 85%]
  - `test_run_check_integrates_p0_compliance_rules` PASSED [100%]
  - 运行命令：`python -m pytest tests/backend/test_compliance_rules_p0.py -v`
  - 结果：**7 passed in 6.76s**
- **关联回归套件测试**：
  - `pytest tests/backend/test_checks_export_blocker_gate.py tests/backend/test_volume_finalize_gate.py -v`
  - 结果：**14 passed in 11.65s**
- **OpenAPI 契约一致性校验**：
  - `python backend/bid-core/export_openapi.py --check`
  - 结果：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **项目治理检查**：
  - `node scripts/check-project-governance.cjs`
  - 结果：通过。

## 限制与未完成事项
- 严格遵守开发规范，本卡状态推进至 `in-review`，绝不私自标为 `done`。
- 当前为第一批 P0 核心规则落地（R15/R23/R34/R37）；其余 40 项次要与推荐性规则保留在 `RULES_INCOMPLETE` 演进清单中，后续迭代推进。
