# QA 独立终验签署报告：Wave 4 核心能力与技术交付批次（共 5 卡）

**签署日期**：2026-10-27  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 4 批次进入 `in-review` 的 5 张任务卡（`FE-TECH-DEBT-02`、`APP-M2-T022`、`BE-COMPLIANCE-RULES-P3`、`AI-DYNAMIC-PROMPT-CONTEXT`、`INT-APP-SLIM-ROUTING`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-766 至 D-775 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`FE-TECH-DEBT-02`** | App.tsx 巨石组件二次瘦身与路由解耦 | **PASS** | 1. `frontend/web/src/app/App.tsx` 从 695 行二次拆解瘦身至 **394 行**（缩减率 43.3%），单文件行数严格控制在 **400 行** 阈值以内；<br>2. 领域模块清晰分流至 `AppHeaderActions.tsx`、`AppModals.tsx`、`ProjectWorkspaceContent.tsx`、`GlobalPagesContent.tsx`；<br>3. 完整保留单测 AST 函数声明契约与事件监听；<br>4. 前端全量单测 **408 passed, 0 failed**，`tsc -b` **0 error**，Vite 构建 1.60s 成功。 | **建议 PM 标 done** |
| **`APP-M2-T022`** | 平台管理员长任务脱敏视图与操作权限门禁 | **PASS** | 1. 纯逻辑脱敏层 `isPlatformAdminRole` 准确识别平台管理员；<br>2. `maskTaskForPlatformAdmin` 将项目名称替换为 `*** (业务项目已脱敏)`，项目 ID 替换为 `***`，标书文件名由 `sanitizePlatformAdminTitle` 净化；<br>3. 平台管理员视图下 `allowedActions` 强制置空，无重试、取消或跳转业务项目权限；<br>4. `TaskCenterDrawer` 与 `JobsPage` 顶部均渲染 `platform-admin-masked-alert` 警示横幅；<br>5. 专属单测 5 项全绿。 | **建议 PM 标 done** |
| **`BE-COMPLIANCE-RULES-P3`** | PRD P3 核心合规规则 R05/R06/R08/R12/R20 扩充与导出门禁联动 | **PASS** | 1. 完整落地 PRD MVP §5.8 第四批核心合规规则：R05（财务指标）、R06（业绩案例）、R08（交付周期）、R12（SLA 与质保）、R20（报价雷同串标排查）；<br>2. 识别负债率超标、业绩金额不足或缺盖章、工期负偏离、质保低于基线或到达超时、分项报价异常一致，判定为 `blocker`；<br>3. 导出服务联动：正式递交模式（submission）存在 blocker 严格触发 **400 `CHECK_BLOCKER_EXISTS`** 强阻断，内部评审版放行并附合规告警；<br>4. 规则全集扩展至 21 项，专属单测 `test_compliance_rules_p3.py` **6 项全绿**。 | **建议 PM 标 done** |
| **`AI-DYNAMIC-PROMPT-CONTEXT`** | 自适应 Prompt 动态上下文裁剪与 Token 预算控制 | **PASS** | 1. 落地中英加权 Token 估算算法（中文 0.7，英文 1.3，标点 0.3）；<br>2. 落地四级优先级自适应裁剪：Priority 1 核心指令绝不裁剪、Priority 2 高置信度方案片段局部截断提示、Priority 3 条款证据超预算舍弃、Priority 4 参考背景优先丢弃；<br>3. 动态计算不可篡改 16 位 SHA-256 `context_fingerprint` 与详尽 Token 消耗指标，持久化入异步任务与候选成果；<br>4. 涉密项目绑定云端模型强门禁拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**，未对齐变量如实记录至 `missing_variables` 防模型幻觉；<br>5. 专属单测 `test_ai_prompt_budget.py` **10 项全绿**。 | **建议 PM 标 done** |
| **`INT-APP-SLIM-ROUTING`** | 路由分层与平台管理员脱敏长任务全链路联调 | **PASS** | 1. 支持平台管理员脱敏任务查询（`GET /api/v1/jobs?masked=true` 与 `GET /api/v1/jobs/masked`，`operationId="listJobsMasked"`），返回企业掩码（`al***`）与项目掩码（`prj-***`），清空操作动作；<br>2. 平台运维多租户防嗅探：直调具体项目业务接口严格返回 **404 `NOT_FOUND`**；<br>3. 长任务取消与重试细粒度 RBAC 鉴权：负责人重试、编写人取消、越权 403 拦截、非终态重试 409 拦截；<br>4. 前端控制器 `useAppController.ts` 真实发起后端重试 HTTP 调用；<br>5. RFC 7807 统一错误响应，OpenAPI 契约零漂移（0 drift）；<br>6. 专属联调单测 `test_app_routing_and_masked_jobs.py` **4 项全绿**。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/app-slim-and-platform-admin.test.mjs`
- **执行结果**：
  ```text
  ✔ FE-TECH-DEBT-02: App.tsx line count is strictly below 400 lines (4.3466ms)
  ✔ FE-TECH-DEBT-02: Extracted shell & app domain components exist and export properly (1.3056ms)
  ✔ APP-M2-T022: isPlatformAdminRole correctly identifies platform administrator (0.3029ms)
  ✔ APP-M2-T022: sanitizePlatformAdminTitle masks tender file names and project sensitive words (0.3643ms)
  ✔ APP-M2-T022: maskTaskForPlatformAdmin enforces security and ops-view masking invariants (0.9572ms)
  ℹ tests 5, pass 5, fail 0 in 267ms
  ```
- **结论**：5 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 408
  ℹ suites 0
  ℹ pass 408
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 6563.8872
  ```
- **结论**：408 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端 P3 合规规则单测（P3 + P0）
- **命令**：`python -m pytest tests/backend/test_compliance_rules_p3.py tests/backend/test_compliance_rules.py -v`
- **执行结果**：
  ```text
  tests/backend/test_compliance_rules_p3.py::test_r05_financial_metrics_compliance PASSED [  9%]
  tests/backend/test_compliance_rules_p3.py::test_r06_performance_case_sufficiency PASSED [ 18%]
  tests/backend/test_compliance_rules_p3.py::test_r08_delivery_timeline_deviation PASSED [ 27%]
  tests/backend/test_compliance_rules_p3.py::test_r12_sla_warranty_deviation PASSED [ 36%]
  tests/backend/test_compliance_rules_p3.py::test_r20_quotation_collusion_risk_detection PASSED [ 45%]
  tests/backend/test_compliance_rules_p3.py::test_export_gate_blocked_by_p3_compliance_rules PASSED [ 54%]
  tests/backend/test_compliance_rules.py::test_compliance_rules_catalog PASSED [ 63%]
  tests/backend/test_compliance_rules.py::test_r01_tender_number_consistency PASSED [ 72%]
  tests/backend/test_compliance_rules.py::test_r02_qualification_original_commitment PASSED [ 81%]
  tests/backend/test_compliance_rules.py::test_r35_self_designation_and_counterparty PASSED [ 90%]
  tests/backend/test_compliance_rules.py::test_evaluate_p0_rules_returns_seven_rules PASSED [100%]
  ============================= 11 passed in 9.96s ==============================
  ```
- **结论**：11 项全部通过。

### 5. 后端 Prompt 预算管理单测
- **命令**：`python -m pytest tests/backend/test_ai_prompt_budget.py -v`
- **执行结果**：
  ```text
  tests/backend/test_ai_prompt_budget.py::test_token_estimation_chinese_and_english_weighted PASSED [ 10%]
  tests/backend/test_ai_prompt_budget.py::test_priority_1_core_never_truncated_under_tight_budget PASSED [ 20%]
  tests/backend/test_ai_prompt_budget.py::test_priority_adaptive_truncation_p4_dropped_first PASSED [ 30%]
  tests/backend/test_ai_prompt_budget.py::test_priority_2_snippet_partial_truncation PASSED [ 40%]
  tests/backend/test_ai_prompt_budget.py::test_token_budget_usage_statistics_accuracy PASSED [ 50%]
  tests/backend/test_ai_prompt_budget.py::test_context_fingerprint_deterministic_and_tamper_evident PASSED [ 60%]
  tests/backend/test_ai_prompt_budget.py::test_missing_variables_detected_without_hallucination PASSED [ 70%]
  tests/backend/test_ai_prompt_budget.py::test_sensitive_project_blocks_cloud_model PASSED [ 80%]
  tests/backend/test_ai_prompt_budget.py::test_assemble_writing_prompt_plan_end_to_end_integration PASSED [ 90%]
  tests/backend/test_ai_prompt_budget.py::test_start_chapter_generation_records_budget_and_fingerprint PASSED [100%]
  ============================= 10 passed in 1.99s ==============================
  ```
- **结论**：10 项全部通过。

### 6. 后端脱敏任务与联调单测
- **命令**：`python -m pytest tests/backend/test_app_routing_and_masked_jobs.py -v`
- **执行结果**：
  ```text
  tests/backend/test_app_routing_and_masked_jobs.py::test_platform_admin_masked_jobs_view PASSED [ 25%]
  tests/backend/test_app_routing_and_masked_jobs.py::test_platform_admin_security_rbac_boundary PASSED [ 50%]
  tests/backend/test_app_routing_and_masked_jobs.py::test_long_task_retry_and_cancel_role_rbac_matrix PASSED [ 75%]
  tests/backend/test_app_routing_and_masked_jobs.py::test_rfc7807_unified_error_format_compliance PASSED [100%]
  ============================== 4 passed in 3.60s ==============================
  ```
- **结论**：4 项全部通过。

### 7. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 8. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：566 份 Markdown、421 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 478ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `FE-TECH-DEBT-02`：App.tsx 瘦身与架构规范
- **代码健康度**：`App.tsx` 实测 **394 行**，严格控制在 `< 400` 行红线以内；
- **分层解耦**：抽离 `AppHeaderActions`（108 行）、`AppModals`（90 行）、`ProjectWorkspaceContent`（134 行）、`GlobalPagesContent`（132 行），所有子模块均收敛在 `shell/` 与 `app/` 八域子目录中，未在根目录平铺；
- **契约兼容**：既有 AST 静态审查沙箱方法与状态保持完整，408 项前端单测全绿。

### 2. `APP-M2-T022`：平台管理员长任务脱敏与权限隔离
- **敏感信息脱敏**：项目名称脱敏为 `*** (业务项目已脱敏)`，项目 ID 脱敏为 `***`，招标文件文件名被彻底净化，严禁平台管理员跨租户窥探业务信息；
- **权限硬拦截**：`allowedActions` 强制置空，在前端抽屉与页面中隐藏重试/取消/跳转链接，仅展示只读运维信息与 Trace ID 复制；
- **合规横幅展示**：挂载 `platform-admin-masked-alert` 警示横幅，提示脱敏审计状态。

### 3. `BE-COMPLIANCE-RULES-P3`：PRD P3 合规规则与导出门禁
- **规则覆盖**：R05（财务指标）、R06（业绩案例）、R08（交付周期）、R12（SLA 与质保）、R20（报价雷同串标排查）；
- **门禁严格性**：在正式递交（submission）导出时，存在上述任一 blocker 缺陷时，强行返回 400 `CHECK_BLOCKER_EXISTS`；在内部评审模式（internal_review）下放行并附带合规告警。

### 4. `AI-DYNAMIC-PROMPT-CONTEXT`：自适应 Prompt 裁剪与 Token 预算
- **四级优先级裁剪**：P1 核心指令（角色、得分点、字数目标、规范）绝对不裁剪；P2 方案片段超预算时局部截断并保留截断提示；P3 条款证据超限舍弃；P4 参考背景优先丢弃；
- **防伪与防幻觉**：计算 16 位 SHA-256 `context_fingerprint`，未对齐变量如实标入 `missing_variables`，杜绝模型幻觉瞎编；
- **涉密门禁**：项目为 sensitive 时使用云端模型强拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。

### 5. `INT-APP-SLIM-ROUTING`：平台运维脱敏与鉴权联调
- **脱敏端点契约**：打通 `GET /api/v1/jobs?masked=true` 与 `GET /api/v1/jobs/masked`，返回脱敏企业代码与项目 ID；
- **防嗅探隔离**：平台管理员直接请求具体项目业务接口时，系统返回 404 `NOT_FOUND`（而非 403），杜绝跨租户资源嗅探；
- **重试与取消鉴权**：项目负责人可重试，项目成员可取消，只读/越权 403 拦截，非终态重试 409 拦截，RFC 7807 统一错误响应。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 5 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 5 张任务卡标为 `done`**。
