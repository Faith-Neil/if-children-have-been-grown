# AI-COMPLIANCE-CROSS-CHECK 交付报告：AI 合规检查依据交叉核验与差距诊断

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-COMPLIANCE-CROSS-CHECK |
| 代码解释 | [docs/code/AI-COMPLIANCE-CROSS-CHECK.md](../code/AI-COMPLIANCE-CROSS-CHECK.md) |
| 验收 | 13 项专属后端自动化测试全绿（13 passed）；关联回归全部通过；OpenAPI 契约零漂移；工程治理检查通过 |
| 项目进度 | AI 核心推进，AI-COMPLIANCE-CROSS-CHECK 提交 in-review，关联 ISSUE-037、ISSUE-007 保持开启，绝不私自标 done，建议 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据 PRD v1.8 §5.8、§5.11.5、§5.11.6 与用户最新派发指令：
- **目标**：实现正文承诺声明与企业真实证据（RAGFlow / 知识库已核验资料）、招标文件强制条款的多维度交叉核验、防虚构出处追溯与量化差距诊断。
- **交付要点对照**：
  1. **声明与引用智能抽取**：精准提取正文段落中 SLA 指标（99.99%、响应与恢复时限、覆盖时段、巡检频次、RTO/RPO）、资质、人员能力与案例承诺，提取行内引用胶囊，支持 `[证:ID]`、`[片:ID]`、`[cite:ID]` 灵活语法；
  2. **依据交叉比对与差距诊断**：对标招标文件强制条款与企业知识库，输出依据置信度得分（0.0~1.0）、置信等级、针对性差距分析（`gap_description`）与整改建议（`suggestion`）；
  3. **多租户强隔离（`${company_id}::` 前缀与跨租户引用阻断）**：严格校验引用证据归属企业（`evidence_company`）；若在项目正文中援引异企租户证据，严格判定为 `cross_check_discrepancy`，状态标为 `cross_company`，评定置信度 0.0 并阻断（`risk_level="block"`）；
  4. **严格杜绝 AI 虚构依据（防幻觉门禁）**：引用未在企业知识库/资料库中真实存在的依据 ID，严格判定为 `cross_check_discrepancy`，状态标为 `missing`，评定置信度 <= 0.10 并阻断（`risk_level="block"`），绝不容忍凭空捏造证据；
  5. **RAGFlow 原始来源完整溯源**：在核验发现（`ComplianceFinding`）中透传 RAGFlow 原始文档 ID（`document_id`）与分块 ID（`chunk_id`），实现审计全链路追溯；
  6. **负偏离合规强阻断**：承诺指标劣于招标强制要求或引用失效/缺协议证据时，评定置信度 0.0 并阻断（`risk_level="block"`）；
  7. **增量复查与后端 checks 联动**：核验结果持久化至 `incremental_checks`，联动更新章节 `incremental_check_status`（`passed` / `warning` / `failed`），并输出 `discrepancy_count` 指标；
  8. **权限与涉密门禁**：涉密项目强校验本地离线模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）、跨租户 404、非项目成员 403；
  9. **契约保护**：路由挂载 `include_in_schema=False` 保护冻结 OpenAPI 契约，143 个错误码零漂移。

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg/domain/compliance_cross_check.py`：核验服务类、多模态抽取正则、跨租户与防虚构校验、RAGFlow 溯源元数据透传、人员与案例深度核对、置信度算法与差距推导
- `backend/bid-core/icg/domain/workflow_schemas.py`：`ComplianceFinding`（扩展 `document_id`、`chunk_id`、`is_discrepancy`、`discrepancy_type`）、`ComplianceCrossCheckRequest`、`ComplianceCrossCheckResponse`（扩展 `discrepancy_count`）数据模型
- `backend/bid-core/icg/domain/domain.py` / `workflow_orchestrator.py` / `icg/api/workflow.py`：业务门面与路由挂载

### 2.2 自动化测试
- `tests/backend/test_ai_compliance_cross_check.py`：13 项专属测试用例，涵盖高置信度支撑、量化差距诊断、负偏离阻断、无依据声明、失效依据拦截、涉密本地模型守卫、跨租户隔离、HTTP 路由安全、增量复查历史沉淀、跨企业证据引用阻断、RAGFlow 来源溯源、虚构依据防幻觉阻断、差距计数与引用标签灵活性。

---

## 3. 验证命令与结果

### 3.1 专属自动化测试套件
```powershell
pytest tests/backend/test_ai_compliance_cross_check.py -v
```
**运行结果**：
```text
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_high_confidence_with_full_evidence PASSED [  7%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_medium_confidence_gap_general_description_only PASSED [ 15%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_negative_deviation_blocked_with_zero_confidence PASSED [ 23%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_unsupported_claim_without_evidence PASSED [ 30%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_expired_or_invalid_evidence_blocked PASSED [ 38%]
tests/backend/test_ai_compliance_cross_check.py::test_gate_sensitive_project_blocks_cloud_model PASSED [ 46%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_tenant_and_permission_isolation PASSED [ 53%]
tests/backend/test_ai_compliance_cross_check.py::test_http_endpoint_and_openapi_safety PASSED [ 61%]
tests/backend/test_ai_compliance_cross_check.py::test_incremental_check_status_and_checks_integration PASSED [ 69%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_cross_company_evidence_blocked_as_discrepancy PASSED [ 76%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_ragflow_source_traceability PASSED [ 84%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_fabricated_nonexistent_evidence_flagged PASSED [ 92%]
tests/backend/test_ai_compliance_cross_check.py::test_cross_check_discrepancy_count_and_cite_tag_flexibility PASSED [100%]

============================= 13 passed in 2.14s ==============================
```

### 3.2 契约一致性核查
```powershell
python backend/bid-core/export_openapi.py --check
```
**运行结果**：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

### 3.3 检查中心与规则回归
```powershell
pytest tests/backend/test_checks_export_blocker_gate.py tests/backend/test_compliance_rules.py -v
```
**运行结果**：全部 passed。

### 3.4 工程治理核验
```powershell
node scripts/check-project-governance.cjs
```
**运行结果**：治理检查通过，0 错误。

---

## 4. 影响范围与未实现项 / 限制说明

1. **影响范围**：
   - 增强了 `ComplianceCrossCheckService` 的依据交叉核验能力，支持细粒度跨租户阻断、虚构依据识别与 RAGFlow 溯源元数据透传；
   - 保持 HTTP 路由 `include_in_schema=False` 挂载，未对已冻结的外部 OpenAPI 契约引入任何破坏性漂移；
   - 与前端依据核验、增量复查状态、检查中心 Blocker 门禁完全兼容。
2. **环境依赖与限制说明**：
   - 真实 RAGFlow 物理服务连通受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 环境变量门控；在默认离线/CI 研发环境下，采用 Fake/Mock 数据集提供确定性闭环测试；
   - 当前项目保持 `in-review` 状态，符合签署与状态流转纪律，待 QA 与 PD 复核后建议 PM 标 done。
