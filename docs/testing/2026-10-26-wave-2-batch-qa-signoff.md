# QA 独立终验签署报告：Wave 2 核心能力与技术债批次（共 4 卡）

**签署日期**：2026-10-26  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：Wave 2 新一批进入 `in-review` 的 4 张任务卡（`FE-TECH-DEBT-01`、`BE-COMPLIANCE-RULES-P1`、`AI-COMPLIANCE-CROSS-CHECK`、`INT-MODEL-CONFIG-MODAL`）进行独立测试复测、门禁核验与终验签署。  
**前置交付物查验**：已核验 D-746 至 D-753 全部交付与代码说明文档，无缺失。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`FE-TECH-DEBT-01`** | EditorPage 巨石二次瘦身与模块解耦 | **PASS** | 1. `EditorPage.tsx` 代码从 1090 行二次瘦身至 **497 行**（净减 593 行，缩减率 54.4%），所有拆分模块均受控在 500 行内；<br>2. 抽离 `useEditorLock`、`useSelectionBubble`、`useEditorOperations`、`EditorDiffDrawer`、`EditorSlaTools`、`EditorAuxiliaryDrawers`；<br>3. 前端全量单测 **396 passed, 0 failed**，`tsc -b` **0 error**；<br>4. AST 契约与三态渲染完美保持。 | **建议 PM 标 done** |
| **`BE-COMPLIANCE-RULES-P1`** | PRD P1 核心合规规则引擎扩充与导出门禁联动 | **PASS** | 1. 完整实现 PRD MVP §5.8 第二批核心合规规则：R03（资质/信誉）、R04（联合体协议）、R09（工期/SLA）、R10（质保期/响应时限）；<br>2. 识别证书过期、资质缺失、失信名单、联合体协议缺失、服务期未承诺/负偏离、质保期低于基线及跨章节冲突，判定为 blocker；<br>3. 联动导出服务，递交版强阻断 400 `CHECK_BLOCKER_EXISTS`，内部评审版放行并附合规告警；<br>4. 专属单测 `test_compliance_rules_p1.py` **5 项全绿**。 | **建议 PM 标 done** |
| **`AI-COMPLIANCE-CROSS-CHECK`** | AI 合规检查依据交叉核验与差距诊断 | **PASS** | 1. 精准抽取段落 SLA 指标、资质、人员、案例声明与 `[证:ID]`、`[片:ID]`、`[cite:ID]` 引用；<br>2. 输出量化置信度得分（0.0~1.0）、置信等级与具备针对性的差距诊断建议；<br>3. 严守 `${company_id}::` 多租户强隔离，跨租户引用置信度归零并强阻断；<br>4. 严守防虚构出处底线，引用未入库假证据置信度降至 <= 0.10 并强阻断；<br>5. 透传 RAGFlow `document_id` 与 `chunk_id` 来源元数据；<br>6. 专属测试 `test_ai_compliance_cross_check.py` **13 项全绿**。 | **建议 PM 标 done** |
| **`INT-MODEL-CONFIG-MODAL`** | 模型配置弹窗前后端联调与涉密本地隔离守卫 | **PASS** | 1. `ModelConfigModal.tsx` 弹窗支持 Local Qwen 与云端模型切换、base_url、API Key 掩码及即时连通性测试；<br>2. 涉密项目绑定云端模型时，后端严格拦截抛出 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` 并返回 RFC 7807 统一错误体；<br>3. 内网模型与 RAGFlow HTTP 客户端配置 `trust_env=False`，防止操作系统 VPN/透明代理劫持内网请求；<br>4. 专属单测 `test_model_config_glue.py` **3 项全绿**。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在本次签署前，在真实仓库环境下独立重新执行了全套权威自动化测试套件：

### 1. 前端权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 396
  ℹ suites 0
  ℹ pass 396
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 4800.6136
  ```
- **结论**：396 项全部通过，0 失败。

### 2. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 3. 后端 Wave 2 专属专项自动化测试
- **命令**：`python -m pytest tests/backend/test_compliance_rules_p1.py tests/backend/test_model_config_glue.py tests/backend/test_ai_compliance_cross_check.py -v`
- **执行结果**：
  ```text
  tests/backend/test_compliance_rules_p1.py::test_r03_qualification_validity_and_credit PASSED
  tests/backend/test_compliance_rules_p1.py::test_r04_consortium_agreement_verification PASSED
  tests/backend/test_compliance_rules_p1.py::test_r09_service_period_and_sla_commitment PASSED
  tests/backend/test_compliance_rules_p1.py::test_r10_warranty_period_and_response_time PASSED
  tests/backend/test_compliance_rules_p1.py::test_export_gate_blocked_by_p1_compliance_rules PASSED
  tests/backend/test_model_config_glue.py::test_model_configs_crud_and_direct_test_alias PASSED
  tests/backend/test_model_config_glue.py::test_ragflow_config_route_aliases PASSED
  tests/backend/test_model_config_glue.py::test_sensitive_project_model_binding_gate_and_rfc7807 PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_high_confidence_with_full_evidence PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_medium_confidence_gap_general_description_only PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_negative_deviation_blocked_with_zero_confidence PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_unsupported_claim_without_evidence PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_expired_or_invalid_evidence_blocked PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_gate_sensitive_project_blocks_cloud_model PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_tenant_and_permission_isolation PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_http_endpoint_and_openapi_safety PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_incremental_check_status_and_checks_integration PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_cross_company_evidence_blocked_as_discrepancy PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_ragflow_source_traceability PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_fabricated_nonexistent_evidence_flagged PASSED
  tests/backend/test_ai_compliance_cross_check.py::test_cross_check_discrepancy_count_and_cite_tag_flexibility PASSED
  ============================= 21 passed in 18.47s =============================
  ```
- **结论**：21 项用例全部通过，耗时 18.47s。

### 4. 后端全量关键主链路大回归自动化测试
- **命令**：`python -m pytest tests/backend/test_smoke_non_demo_pipeline.py tests/backend/test_compliance_rules.py tests/backend/test_compliance_rules_p1.py tests/backend/test_deprecated_demo_api.py tests/backend/test_ragflow_kb_sync.py tests/backend/test_volume_finalize_gate.py tests/backend/test_checks_export_blocker_gate.py tests/backend/test_model_config_glue.py tests/backend/test_ai_compliance_cross_check.py -v`
- **执行结果**：
  ```text
  ================== 62 passed, 1 skipped in 85.83s (0:01:25) ===================
  ```
- **结论**：62 项全部通过，1 项 skipped（无内网探针环境变量时的物理探针跳过，符合诚实原则）。

### 5. OpenAPI 契约一致性门禁
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移。

### 6. 项目工程治理检查与治理单元测试
- **命令 1**：`node scripts/check-project-governance.cjs`  
  **结果 1**：`治理检查通过：544 份 Markdown、414 项任务、38 项 Issue。`
- **命令 2**：`node --test tests/governance/*.test.cjs`  
  **结果 2**：`12 passed, 0 fail in 443ms`。

---

## 三、逐卡独立验收核查与审计

### 1. `FE-TECH-DEBT-01`：EditorPage 巨石二次瘦身与模块解耦
- **代码健康度**：原 `EditorPage.tsx`（1090 行）拆分为：
  - `EditorPage.tsx` 主页面：497 行（严格低于 600 行红线）；
  - `useEditorLock.ts`：119 行；
  - `useSelectionBubble.ts`：106 行；
  - `useEditorOperations.ts`：286 行；
  - `EditorDiffDrawer.tsx`：171 行；
  - `EditorSlaTools.tsx`：97 行；
  - `EditorAuxiliaryDrawers.tsx`：146 行。
- **架构规范**：严格限定在 `frontend/web/src/editor/` 八域目录内，未在 `src` 根目录平铺。
- **契约完整性**：既有 AST 静态审查反射方法（`localError`、`run`、`viewVersions`、`handleRevisionConflict` 等）与 DOM 契约（`data-testid`）完整保持，396 项单元测试全部绿灯。
- **结论**：**PASS**。

### 2. `BE-COMPLIANCE-RULES-P1`：PRD P1 核心合规规则引擎扩充
- **规则覆盖**：
  - R03（资质/信誉）：覆盖截止时间过期校验、资质缺失校验、被执行人/失信黑名单语义识别；
  - R04（联合体协议）：覆盖独立投标放行、联合体投标协议缺失阻断、成员营业执照/资质缺失阻断；
  - R09（工期/SLA）：覆盖工期应答缺失阻断、工期负偏离阻断；
  - R10（质保期/响应时限）：覆盖质保低于基线阻断、响应超时阻断、跨章节（技术分册 vs 商务分册）质保承诺冲突阻断。
- **导出门禁联动**：所有识别出的 blocker 缺陷结构化写入 `ComplianceRuleIssue`，在导出递交版时严格触发 400 `CHECK_BLOCKER_EXISTS`，内部评审版放行并附合规告警。
- **分包合规**：代码全部收敛于 `backend/bid-core/icg/domain/compliance_rules.py`，不侵入 `icg_demo`。
- **结论**：**PASS**。

### 3. `AI-COMPLIANCE-CROSS-CHECK`：依据交叉核验与差距诊断
- **声明与引用抽取**：智能正则覆盖 SLA 可用性、响应/恢复时限、时段覆盖、巡检频次、RTO/RPO，以及资质、团队人员、业绩案例；支持 `[证:ID]`、`[片:ID]`、`[cite:ID]` 多类标签语法。
- **量化置信度与差距诊断**：
  - 充分依据支撑：置信度 0.95，风险级别 info；
  - 一般文字描述缺乏量化数据：置信度 0.55，风险级别 warning，输出具体差距描述与整改建议；
  - 负偏离条款：置信度 0.0，风险级别 block；
  - 缺少依据标注：置信度 0.15~0.40，风险级别 warning。
- **安全与防伪造红线**：
  - **多租户强隔离**：异企租户证据引用判定为 `cross_company`，置信度 0.0，强阻断；
  - **防虚构出处追溯**：引用未入库假 ID 判定为 `missing`，置信度 <= 0.10，强阻断；
  - **RAGFlow 元数据溯源**：在 `ComplianceFinding` 中透传 `document_id` 与 `chunk_id`；
  - **涉密项目守卫**：项目为 sensitive 时尝试绑定云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。
- **契约安全**：路由配置 `include_in_schema=False`，OpenAPI 契约零漂移。
- **结论**：**PASS**。

### 4. `INT-MODEL-CONFIG-MODAL`：模型配置弹窗前后端联调
- **交互与功能**：`ModelConfigModal.tsx` 实现清晰简洁的 Layout First 设计，支持本地/云端单选切换、API Key 掩码保护与连通性测试。
- **涉密守卫**：敏感项目绑定云端模型时抛出 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，返回 RFC 7807 统一错误体。
- **网络防劫持**：内网模型与 RAGFlow HTTP 客户端配置 `trust_env=False`，杜绝宿主机 VPN 代理劫持。
- **结论**：**PASS**。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
