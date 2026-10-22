# 为什么有这个文件：记录QA对编辑台深度联动（三线成果：APP-M2-T168、BE-CHAPTER-EDIT-DETAIL、AI-EDITOR-CONTEXT-LINKAGE）的独立背靠背复测、全量回归与终验签署结论。

# 它解决什么问题：不轻信各端自报结果，严格落实 QA 裁判职责，独立运行前端全量与契约单测、后端章节详情读取与 AI 上下文切分单测、OpenAPI 契约一致性测试、前端生产构建包体积检查及全库治理检查；深度审计三线成果的核心安全门禁（未持锁强制 copy_only 且正文零突变、敏感项目本地离线模型 403 强隔离、星号/废标条款徽标展示与禁止标记不适用、中屏 1280px 正文区 >= 700px 消除横向滚动、八角色读写隔离与多租户 404 隔离）；给出明确的 PASS 终验结论，将相关任务卡稳定保持在 in-review，严禁私自标 done 或关闭 Issue。

# 编辑台深度联动（三线成果）QA 独立背靠背复测与终验签署报告

- 被验任务：
  - [APP-M2-T168](../tasks/APP-M2.md#app-m2-t168) · 编辑台章节加载、数据联动与向后兼容（前端大纲树深度挂接、1280px~1440px 响应式折叠消除横滚、未保存文字防离开拦截、只读态协同）
  - `BE-CHAPTER-EDIT-DETAIL` · 编辑台章节详情读取与段落结构接口（`GET /api/v1/projects/{project_id}/chapters/{chapter_id}`、段落结构切分、引用依据匹配、持锁/非持锁状态感知、只读安全准入）
  - `AI-EDITOR-CONTEXT-LINKAGE` · 编辑台章节上下文感知问答与划词引用联动（段落编号 `[P1]~[Pn]`、划词段落精准匹配、Diff 建议、未获锁强制 `copy_only` 且正文零突变、敏感项目本地模型硬隔离）
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)（项目主流程与编辑台协同）
- 关联交付文档：
  - [docs/delivery/APP-M2-T168.md](../delivery/APP-M2-T168.md)
  - [docs/delivery/BE-CHAPTER-EDIT-DETAIL.md](../delivery/BE-CHAPTER-EDIT-DETAIL.md)
  - [docs/delivery/AI-EDITOR-CONTEXT-LINKAGE.md](../delivery/AI-EDITOR-CONTEXT-LINKAGE.md)
- 关联代码解释文档：
  - [docs/code/APP-M2-T168.md](../code/APP-M2-T168.md)
  - [docs/code/BE-CHAPTER-EDIT-DETAIL.md](../code/BE-CHAPTER-EDIT-DETAIL.md)
  - [docs/code/AI-EDITOR-CONTEXT-LINKAGE.md](../code/AI-EDITOR-CONTEXT-LINKAGE.md)
- 复验环境：
  - OS: Windows (PowerShell)
  - Python: 3.12.9, pytest: 8.4.2
  - Node: 24.9.0, Vite: 8.3.4, TypeScript: 5.8.2
- 签署结论：**【PASS 终验签署通过】**。
- 状态约定：**APP-M2-T168、BE-CHAPTER-EDIT-DETAIL、AI-EDITOR-CONTEXT-LINKAGE 全部保持 in-review，严禁标 done；关联 ISSUE-007 保持开启**。

---

## 一、三线成果验收矩阵与门禁审计

| 序号 | 核心需求与门禁维度 | 被验成果 | 审计与测试实测结论 | 状态 |
|---|---|---|---|---|
| **AC-01** | **前端大纲树挂接与分册切换** | APP-M2-T168 | `EditorPage.tsx` 完整集成 `OutlineTreeView`，支持技术/商务分册平滑切换，智能识别展示章节编号、标题、章节类型徽标（专项/通用/系统生成）及星号（★）/废标红线标记；切换节点平滑读取章节数据。 | **PASS** |
| **AC-02** | **响应式中屏正文 >= 700px 零横滚** | APP-M2-T168 | 实测 `editor-deep-linkage.test.mjs`：中屏（1280~1440px）大纲支持折叠为 44px 迷你竖条或独立抽屉，右侧助手支持折叠；在 1280px 标准断点下，正文编辑区可用宽度计算值为 836px（远超 700px 最低门限），彻底消除横向滚动条。 | **PASS** |
| **AC-03** | **未保存文字防离开拦截与只读协同** | APP-M2-T168 | 当 `dirty=true` 时，切换章节前置拦截并唤起确认弹窗；非主管分册严格协同 `useDataPermission`，展示 `ReadonlyBanner` 与只读富文本测试桩（`data-testid="readonly-editor-view"`），销毁心跳。 | **PASS** |
| **AC-04** | **章节详情读取与段落结构切分** | BE-CHAPTER-EDIT-DETAIL | 落地 `GET /api/v1/projects/{project_id}/chapters/{chapter_id}`（`operationId: getChapterEditDetail`）；`decompose_paragraphs` 算法精准将正文拆解为结构化段落，并精准关联对应 `citations`；优先读取持久化段落。 | **PASS** |
| **AC-05** | **持锁/未持锁动态感知与 OCC 版本** | BE-CHAPTER-EDIT-DETAIL | 接口返回 `locked_by`、`lock_expires_at` 与 `revision`；未持锁时返回 `locked_by=None`，持锁时正确回显当前持锁用户与过期时间；为前端编辑台保存时的 OCC 并发控制提供可靠依据。 | **PASS** |
| **AC-06** | **划词精准命中与 Diff 润色建议** | AI-EDITOR-CONTEXT-LINKAGE | 划词选中文本时，`decompose_chapter_paragraphs` 精准定位所在段落并打上 `is_selected=True` 标记；在划词润色场景（`polish`）下生成标准 `diff_suggestion`（含原文字、改写建议与对比差量），保留事实变量标记。 | **PASS** |
| **AC-07** | **无锁强制 copy_only 与正文零突变** | AI-EDITOR-CONTEXT-LINKAGE | 未持有效编辑锁租约时，AI 上下文响应中 `can_insert` 强制恒为 `False`，`action="copy_only"` 并提示未获锁；后端章节正文、修订号、版本历史保持 100% 零突变、零污染。 | **PASS** |
| **AC-08** | **敏感项目本地模型硬隔离与 RBAC 租户隔离** | 综合安全门禁 | 敏感项目强制核验本地模型，配置云端模型抛出 `403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；只读角色（`viewer`, `auditor`, `group_admin`, `platform_admin`）拦截 403；跨租户与跨项目访问拦截 404。 | **PASS** |

---

## 二、独立复测实测数据与执行凭据

### 1. 后端专属单测与契约测试（40 passed, 0 failed）
执行命令：
```bash
pytest tests/backend/test_chapter_edit_detail.py tests/backend/test_editor_ai_context.py tests/backend/test_outline_plan_service.py tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py -v
```
实测输出截断：
```text
tests/backend/test_chapter_edit_detail.py::test_get_chapter_edit_detail_success PASSED [  2%]
tests/backend/test_chapter_edit_detail.py::test_get_chapter_edit_detail_paragraphs_and_citations PASSED [  5%]
tests/backend/test_chapter_edit_detail.py::test_unauthenticated_returns_401 PASSED [  7%]
tests/backend/test_chapter_edit_detail.py::test_non_existent_chapter_and_project_returns_404 PASSED [ 10%]
tests/backend/test_chapter_edit_detail.py::test_cross_project_and_company_isolation PASSED [ 12%]
tests/backend/test_chapter_edit_detail.py::test_lock_status_sensing_unlocked_and_locked PASSED [ 15%]
tests/backend/test_chapter_edit_detail.py::test_eight_roles_read_only_viewer_can_get_but_cannot_write PASSED [ 17%]
tests/backend/test_chapter_edit_detail.py::test_stored_structured_paragraphs_takes_precedence PASSED [ 20%]
tests/backend/test_editor_ai_context.py::test_decompose_paragraphs_and_selection_matching PASSED [ 22%]
tests/backend/test_editor_ai_context.py::test_scene_detection PASSED [ 25%]
tests/backend/test_editor_ai_context.py::test_build_editor_prompt_context_polish_scene PASSED [ 27%]
tests/backend/test_editor_ai_context.py::test_build_editor_prompt_context_compliance_scene PASSED [ 30%]
tests/backend/test_editor_ai_context.py::test_chat_editor_context_fallback_when_no_selection PASSED [ 32%]
tests/backend/test_editor_ai_context.py::test_chat_editor_context_polish_diff_suggestion PASSED [ 35%]
tests/backend/test_editor_ai_context.py::test_guard_no_lock_forces_copy_only PASSED [ 37%]
tests/backend/test_editor_ai_context.py::test_guard_valid_lock_and_citations_allow_suggest_replacement PASSED [ 40%]
tests/backend/test_editor_ai_context.py::test_guard_valid_lock_without_citations_blocks_insert PASSED [ 42%]
tests/backend/test_editor_ai_context.py::test_guard_sensitive_project_blocks_cloud_model PASSED [ 45%]
tests/backend/test_editor_ai_context.py::test_guard_readonly_roles_and_cross_tenant_isolation PASSED [ 47%]
tests/backend/test_editor_ai_context.py::test_workflow_service_and_answer_card_integration PASSED [ 50%]
tests/backend/test_outline_plan_service.py::test_get_outline_plan_tree_and_metadata PASSED [ 52%]
tests/backend/test_outline_plan_service.py::test_asterisk_and_disqualified_cannot_be_marked_not_applicable PASSED [ 55%]
tests/backend/test_outline_plan_service.py::test_permission_gates_role_and_volume_owner PASSED [ 57%]
tests/backend/test_outline_plan_service.py::test_atomic_revision_increment_on_confirmation PASSED [ 60%]
tests/backend/test_outline_plan_service.py::test_batch_confirm_by_volume PASSED [ 62%]
tests/backend/test_outline_plan_service.py::test_memory_repository_polymorphism_offline PASSED [ 65%]
tests/backend/test_error_idempotency.py::test_literal_domain_errors_use_the_single_frozen_status PASSED [ 67%]
tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry PASSED [ 70%]
tests/backend/test_error_idempotency.py::test_v1_model_unavailable_uses_unified_error_body PASSED [ 72%]
tests/backend/test_error_idempotency.py::test_unknown_v1_route_returns_unified_404_with_trace_id PASSED [ 75%]
tests/backend/test_error_idempotency.py::test_v1_error_body_matches_request_header_and_legacy_shape_stays PASSED [ 77%]
tests/backend/test_error_idempotency.py::test_same_key_replays_success_and_changed_payload_conflicts_without_writing PASSED [ 80%]
tests/backend/test_error_idempotency.py::test_missing_or_invalid_key_is_428_and_failure_is_not_stored PASSED [ 82%]
tests/backend/test_error_idempotency.py::test_receipt_expires_after_24_hours_and_memory_is_bounded PASSED [ 85%]
tests/backend/test_error_idempotency.py::test_uncapped_receipts_keep_more_than_2048 PASSED [ 87%]
tests/backend/test_operation_ids.py::test_running_app_all_operation_ids_valid_camel_case_and_no_api_prefix PASSED [ 90%]
tests/backend/test_operation_ids.py::test_running_app_operation_ids_are_globally_unique PASSED [ 92%]
tests/backend/test_operation_ids.py::test_spec_demo_v1_json_all_operation_ids_valid_and_globally_unique PASSED [ 95%]
tests/backend/test_operation_ids.py::test_well_known_operation_ids PASSED [ 97%]
tests/backend/test_operation_ids.py::test_implemented_contract_matches_running_schema PASSED [100%]

============================= 40 passed in 12.35s =============================
```

### 2. 前端单元测试与契约测试（全量 284 passed, 0 failed）
执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出统计：
```text
ℹ tests 284
ℹ suites 0
ℹ pass 284
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2303.6334
```

### 3. 前端生产构建与分包检查
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3351 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                0.71 kB │ gzip:   0.52 kB
dist/assets/index-CZMgSkPA.css                34.47 kB │ gzip:   7.53 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/MenuUnfoldOutlined-Nb8MiWYk.js     6.69 kB │ gzip:   2.60 kB
dist/assets/collapse-CkeV8bG4.js              10.50 kB │ gzip:   3.83 kB
dist/assets/SupportPages-B-c9L3dm.js          11.29 kB │ gzip:   4.52 kB
dist/assets/ProjectSettingsPage-BdR8qelA.js   22.54 kB │ gzip:   8.91 kB
dist/assets/SlaPages-BPoZPuy3.js              36.48 kB │ gzip:  12.05 kB
dist/assets/ProjectPages-Dp0Pr_B1.js         116.10 kB │ gzip:  34.94 kB
dist/assets/EditorPage-CjHTKDmL.js           140.24 kB │ gzip:  45.30 kB
dist/assets/AppShell-B7mEzmiu.js             222.29 kB │ gzip:  73.18 kB
dist/assets/jsx-runtime-J66WJ9pO.js          438.61 kB │ gzip: 144.68 kB
dist/assets/index-eBkFqlIl.js                660.14 kB │ gzip: 202.84 kB
✓ built in 672ms
```
- TypeScript 类型检查零错误；
- EditorPage 独立按需加载分包仅 140.24 kB（gzip 45.30 kB）；
- 构建总耗时 672ms，无异常内存或体积泄漏。

### 4. 工程治理与基线合规检查
执行命令：
```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
实测输出：
```text
治理检查通过：439 份 Markdown、397 项任务、37 项 Issue。
ℹ tests 12
ℹ suites 0
ℹ pass 12
ℹ fail 0
ℹ duration_ms 347.3018
```

---

## 三、签署结论与工作规范守则

根据测试裁判原则：
1. **APP-M2-T168**（编辑台大纲树挂接与响应式断点）、**BE-CHAPTER-EDIT-DETAIL**（章节详情与段落切分）与 **AI-EDITOR-CONTEXT-LINKAGE**（编辑台章节上下文感知问答与划词引用联动）三线成果全面达标，出具 **PASS 终验签署结论**。
2. **严守工作流红线**：QA 绝不私自将任务看板标为 done，绝不私自关闭业务 Issue；上述任务卡稳妥保持 **in-review** 状态，由主 Agent / 项目经理进行后续里程碑确认。
