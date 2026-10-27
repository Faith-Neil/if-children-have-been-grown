# QA 独立终验签署报告：Wave 3 核心能力与技术交付批次（共 4 卡）

**签署日期**：2026-10-27  
**验收负责人**：QA｜成长测试 QA subagent  
**验收目标**：对 Wave 3 批次进入 `in-review` 的 4 张任务卡（`APP-M2-T021`、`BE-COMPLIANCE-RULES-P2`、`AI-SNIPPET-RETRIEVAL-MATCH`、`INT-TASK-CENTER-GLUE`）进行独立全量测试复测、质量门禁审计、业务主路径核验与终验签署。  
**前置交付物查验**：已逐项核验 D-756 至 D-763 全部交付文档（delivery）与代码说明（code），内容与实测完全一致。

---

## 一、QA 终验签署汇总表

| 任务卡 ID | 任务名称 | 验收结论 | 核心通过证据 | 是否建议 PM done |
| :--- | :--- | :---: | :--- | :---: |
| **`APP-M2-T021`** | 任务中心页基础 + 顶栏任务角标与抽屉 | **PASS** | 1. 顶栏 `<TaskBadge />` 动态角标仅统计当前登录公司租户下运行中与排队中任务（`calculateActiveTaskCount` 租户强隔离）；<br>2. 抽屉 `<TaskCenterDrawer />` 与主页 `<JobsPage />` 四分类筛选（全部、进行中、已完成、异常失败）与计数完全生效；<br>3. 落实 Layout First 原则与色彩隔离体系：AI 任务专属紫（`#722ed1`）与业务主蓝（`#1e4db7`）；<br>4. 权限按钮硬控制（`canPerformTaskAction`）：仅失败任务允许重试，仅运行/排队中允许取消；<br>5. 前端专属单测 7 项全绿，全量单测 **403 passed, 0 failed**，`tsc -b` **0 error**。 | **建议 PM 标 done** |
| **`BE-COMPLIANCE-RULES-P2`** | PRD P2 核心合规规则引擎扩充与导出门禁联动 | **PASS** | 1. 完整落地 PRD MVP §5.8 第三批核心合规规则：R07（原厂授权与授权链）、R11（拟派人员与社保）、R14（强制必备附件）、R25（旧标书与其他公司残留）、R31（敏感信息与真实巡检报告残留）；<br>2. 识别原厂授权缺失/过期/授权链断裂、人员社保断缴/不一致、缺少 5 大必备附件、旧标书占位残留、明文身份证/银行卡/口令，判定为 `blocker`；<br>3. 导出服务联动：正式递交模式（submission）存在 blocker 严格触发 **400 `CHECK_BLOCKER_EXISTS`** 强阻断，内部评审版放行并附合规告警；<br>4. 专属单测 `test_compliance_rules_p2.py` **6 项全绿**。 | **建议 PM 标 done** |
| **`AI-SNIPPET-RETRIEVAL-MATCH`** | 方案片段智能检索与上下文精准匹配 | **PASS** | 1. 多租户强隔离：严格限定只召回当前会话 `company_id` 下已发布的方案片段，跨租户与未发布草稿物理阻断；<br>2. 多模态加权检索（2-gram 字符碎片 + 核心关键词加权 + 余弦向量相似度）排序精准；<br>3. 变量自动对齐填充：项目事实与 SLA 别名映射，未对齐变量如实标入 `missing_variables`，绝不凭空捏造；<br>4. 标准 `[片:ID]` 引用胶囊与 16 位不可篡改 SHA-256 防伪指纹；<br>5. 涉密项目绑定云端模型强门禁拦截 **403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`**；<br>6. 专属单测 `test_ai_snippet_retrieval.py` **11 项全绿**。 | **建议 PM 标 done** |
| **`INT-TASK-CENTER-GLUE`** | 异步任务中心与长任务流式通知前后端联调 | **PASS** | 1. 长任务异步启动返回 **202 Accepted + Location** 响应头，正确持久化入 `demo_job` 表（状态 `pending`/`queued`）；<br>2. SSE 实时推流（`/api/v1/jobs/{id}/events`）支持 `Last-Event-ID` 断点续传，前端胶水层解包 `JobEvent`，终态优雅断开；<br>3. 平滑降级至轮询 `GET /api/v1/jobs/{id}`，返回标准 `JobStatus`；<br>4. 角色权限防线：只读角色取消拦截 403，非项目负责人/管理员重试拦截 403，进行中重试拦截 409；<br>5. 多租户隔离：跨公司访问长任务严格返回 **404 `NOT_FOUND`** 防信息嗅探；<br>6. 专属联调单测 `test_task_center_glue.py` **7 项全绿**。 | **建议 PM 标 done** |

---

## 二、自动化复测与质量门禁凭证清单

本 QA subagent 在签署前，在真实生产配置与关演示约束下独立运行了全套权威测试：

### 1. 前端专属单元测试套件
- **命令**：`node --test frontend/web/tests/unit/task-center.test.mjs`
- **执行结果**：
  ```text
  ✔ 1. 顶栏角标计数 (calculateActiveTaskCount)：统计运行中+排队中任务并保障多租户隔离 (1.2789ms)
  ✔ 2. 任务状态谓词判定 (isTaskRunning, isTaskCompleted, isTaskFailed, isTaskCancelled) (0.1644ms)
  ✔ 3. 数据归一化 (normalizeTask)：双结构兼容、字段派生与百分比钳位 (1.6803ms)
  ✔ 4. 四分类筛选与统计 (computeTaskCounts & filterTasks) (1.234ms)
  ✔ 5. 操作权限校验防线 (canPerformTaskAction) (0.5515ms)
  ✔ 6. AI 任务色彩隔离红线验证 (resolveProgressStrokeColor & isAiJob) (0.5134ms)
  ✔ 7. 时间与耗时格式化友好渲染 (formatTaskTime & resolveJobStatusMeta) (2.0695ms)
  ℹ tests 7, pass 7, fail 0 in 211ms
  ```
- **结论**：7 项全部通过。

### 2. 前端全量权威单元测试套件
- **命令**：`pnpm --dir frontend/web test`
- **执行结果**：
  ```text
  ℹ tests 403
  ℹ suites 0
  ℹ pass 403
  ℹ fail 0
  ℹ cancelled 0
  ℹ skipped 0
  ℹ todo 0
  ℹ duration_ms 4890.7907
  ```
- **结论**：403 项全部通过，0 失败。

### 3. 前端 TypeScript 严格静态编译检查
- **命令**：`pnpm --dir frontend/web lint` (`tsc -b --noEmit`)
- **执行结果**：退出码 0，**0 error, 0 warning**。

### 4. 后端合规规则单测（P2 + P0）
- **命令**：`python -m pytest tests/backend/test_compliance_rules_p2.py tests/backend/test_compliance_rules.py -v`
- **执行结果**：
  ```text
  tests/backend/test_compliance_rules_p2.py::test_r07_original_manufacturer_authorization PASSED [  9%]
  tests/backend/test_compliance_rules_p2.py::test_r11_personnel_and_social_security PASSED [ 18%]
  tests/backend/test_compliance_rules_p2.py::test_r14_mandatory_attachments_verification PASSED [ 27%]
  tests/backend/test_compliance_rules_p2.py::test_r25_entity_name_and_legacy_residuals PASSED [ 36%]
  tests/backend/test_compliance_rules_p2.py::test_r31_sensitive_data_and_real_inspection_residuals PASSED [ 45%]
  tests/backend/test_compliance_rules_p2.py::test_export_gate_blocked_by_p2_compliance_rules PASSED [ 54%]
  tests/backend/test_compliance_rules.py::test_compliance_rules_catalog PASSED [ 63%]
  tests/backend/test_compliance_rules.py::test_r01_tender_number_consistency PASSED [ 72%]
  tests/backend/test_compliance_rules.py::test_r02_qualification_original_commitment PASSED [ 81%]
  tests/backend/test_compliance_rules.py::test_r35_self_designation_and_counterparty PASSED [ 90%]
  tests/backend/test_compliance_rules.py::test_evaluate_p0_rules_returns_seven_rules PASSED [100%]
  ============================= 11 passed in 6.78s ==============================
  ```
- **结论**：11 项全部通过。

### 5. 后端方案片段检索单测
- **命令**：`python -m pytest tests/backend/test_ai_snippet_retrieval.py -v`
- **执行结果**：
  ```text
  tests/backend/test_ai_snippet_retrieval.py::test_multi_tenant_isolation_only_published_own_company_recalled PASSED [  9%]
  tests/backend/test_ai_snippet_retrieval.py::test_cross_tenant_project_access_rejected PASSED [ 18%]
  tests/backend/test_ai_snippet_retrieval.py::test_relevance_matching_and_scoring PASSED [ 27%]
  tests/backend/test_ai_snippet_retrieval.py::test_variable_extraction_and_project_facts_alignment PASSED [ 36%]
  tests/backend/test_ai_snippet_retrieval.py::test_missing_variables_detection PASSED [ 45%]
  tests/backend/test_ai_snippet_retrieval.py::test_cite_tag_and_anti_tamper_fingerprint PASSED [ 54%]
  tests/backend/test_ai_snippet_retrieval.py::test_sensitive_project_blocks_cloud_model PASSED [ 63%]
  tests/backend/test_ai_snippet_retrieval.py::test_retriever_degrades_gracefully_when_ragflow_fails PASSED [ 72%]
  tests/backend/test_ai_snippet_retrieval.py::test_http_endpoint_match_snippets PASSED [ 81%]
  tests/backend/test_ai_snippet_retrieval.py::test_fact_and_sla_alias_variations_alignment PASSED [ 90%]
  tests/backend/test_ai_snippet_retrieval.py::test_ragflow_cross_tenant_chunk_rejected PASSED [100%]
  ============================= 11 passed in 1.44s ==============================
  ```
- **结论**：11 项全部通过。

### 6. 后端任务中心前后端联调单测
- **命令**：`python -m pytest tests/backend/test_task_center_glue.py -v`
- **执行结果**：
  ```text
  tests/backend/test_task_center_glue.py::test_long_task_creation_and_demo_job_persistence PASSED [ 14%]
  tests/backend/test_task_center_glue.py::test_job_sse_events_streaming_and_resume PASSED [ 28%]
  tests/backend/test_task_center_glue.py::test_job_polling_and_terminal_completion PASSED [ 42%]
  tests/backend/test_task_center_glue.py::test_job_cancel_action_and_permissions PASSED [ 57%]
  tests/backend/test_task_center_glue.py::test_job_retry_action_and_permissions PASSED [ 71%]
  tests/backend/test_task_center_glue.py::test_tenant_and_multi_company_strong_isolation PASSED [ 85%]
  tests/backend/test_task_center_glue.py::test_persisted_demo_job_transparent_adaptation PASSED [100%]
  ============================== 7 passed in 5.07s ==============================
  ```
- **结论**：7 项全部通过。

### 7. OpenAPI 契约一致性校验
- **命令**：`python backend/bid-core/export_openapi.py --check`
- **执行结果**：`[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.`
- **结论**：契约零漂移通过。

### 8. 项目工程治理检查与单测
- **命令 1**：`node scripts/check-project-governance.cjs` -> **治理检查通过：554 份 Markdown、417 项任务、38 项 Issue，0 错误**。
- **命令 2**：`node --test tests/governance/*.test.cjs` -> **12 passed, 0 fail in 485ms**。

---

## 三、业务主路径与关键门禁深入核验

### 1. `APP-M2-T021`：任务中心与顶栏角标
- **多租户隔离**：顶栏徽标角标计数通过 `calculateActiveTaskCount(tasks, companyId)` 严格过滤仅属于当前公司租户的任务，未出现跨租户任务计数混淆；
- **四分类与状态机**：全部（all）、进行中（running/pending/queued）、已完成（completed/succeeded）、异常失败（failed）四分类筛选与计数逻辑完备；
- **色彩隔离体系**：AI 任务（`generate_chapter`、`generate_outline` 等）明确标识 AI 紫色（`#722ed1`），常规业务任务标识业务蓝色（`#1e4db7`）；
- **操作权限硬防线**：`canPerformTaskAction` 严格限制重试（仅失败任务）与取消（仅进行中任务）。

### 2. `BE-COMPLIANCE-RULES-P2`：PRD P2 合规规则与导出门禁
- **规则覆盖**：R07（原厂授权与授权链）、R11（拟派人员与社保）、R14（5大必备法定附件）、R25（旧标书与其他公司残留）、R31（敏感信息与真实巡检报告残留）；
- **阻断行为与门禁**：在正式递交（submission）模式下，存在上述 blocker 缺陷时，强拦截返回 400 `CHECK_BLOCKER_EXISTS`；在内部评审模式（internal_review）下，放行并附带合规告警。

### 3. `AI-SNIPPET-RETRIEVAL-MATCH`：方案片段智能检索与上下文精准匹配
- **召回租户强隔离**：严格限定当前会话 `company_id` 下已发布的方案片段（`status == "published"` 且 `published_revision > 0`），未发布草稿与跨租户片段 100% 隔离；
- **变量替换与防编造**：项目事实与 SLA 变量对齐填充，未对齐变量如实标入 `missing_variables`，响应体给出 `has_missing_variables: true`，严禁编造数据；
- **出处溯源与防伪**：生成 `[片:ID]` 标签，动态计算 16 位 SHA-256 不可篡改防伪指纹；
- **涉密本地模型门禁**：项目 sensitive 时若使用云端模型，强门禁拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`。

### 4. `INT-TASK-CENTER-GLUE`：异步任务中心与流式前后端联调
- **长任务生命周期**：创建异步任务返回 202 + Location 响应头，状态正确写入 `demo_job` 表（`pending`/`queued`）；
- **SSE 推流与续传**：支持 `Last-Event-ID` 断点续传，前端胶水层解包 `JobEvent`，终态优雅断开；
- **断线降级**：客户端断线后自动降级为 HTTP 轮询 `GET /api/v1/jobs/{id}`；
- **跨租户强隔离**：跨公司访问长任务严格返回 404 `NOT_FOUND`，防止未授权租户探测任务信息；
- **RBAC 角色权限**：只读角色取消长任务拦截 403，普通编写人重试长任务拦截 403，仅项目负责人或管理员允许重试。

---

## 四、纪律遵从与流转建议

根据 `AGENTS.md` 签署纪律：
1. 本 QA subagent 保持客观中立，严禁自行在 `docs/TASK_BOARD.md` 标 `done`；
2. 上述 4 张任务卡在看板中均保持 `in-review` 状态；
3. 本 QA 签署报告作为官方复测凭据，**正式建议主 Agent 提请人类 PM（项目经理）复核并统一在任务看板中将上述 4 张任务卡标为 `done`**。
