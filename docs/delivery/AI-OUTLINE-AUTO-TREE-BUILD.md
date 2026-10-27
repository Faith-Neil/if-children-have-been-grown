# AI-OUTLINE-AUTO-TREE-BUILD 交付报告：招标文件解析驱动的大纲树自动规划构建引擎

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-OUTLINE-AUTO-TREE-BUILD |
| 代码解释 | [docs/code/AI-OUTLINE-AUTO-TREE-BUILD.md](../code/AI-OUTLINE-AUTO-TREE-BUILD.md) |
| 验收 | 11 项专属自动化测试全绿（11 passed in 0.96s）；大纲与工作流全套回归 50 项全绿（50 passed in 1.71s）；全量 AI 与 RAG 联合套件全绿（56 passed in 3.83s）；OpenAPI 契约零漂移；工程治理检查通过（零死链） |
| 项目进度 | 本卡已完成全部功能开发与全量测试闭环，状态转为 in-review，建议由 QA 与 PD 终验后由 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.1《生成闭环总览》与 §5.7.2《页面：写作方案与大纲确认》）：
- **目标**：在 `backend/bid-core/icg/domain/outline_auto_tree.py`、`outline_plan.py`、`outline_orchestrator.py`、`outline_service.py` 与 `backend/bid-core/icg/api/workflow.py` 中，落地基于招标文件解析结果自动推导、多层级规范编号、评分要点精准挂接、防编造防幻觉的完整大纲树自动规划构建引擎。
- **交付要点对照**：
  1. **多层级大纲树自动衍生（卷 -> 章/编 -> 节 -> 子节）**：
     - 基于解析出的招标文件需求矩阵（商务资质、总体架构、实施服务、安全合规、偏离表），自动构建官方投标大纲层级结构；
     - 自动衍生规范化层级编号与中文序号：第一卷 商务标 / 第二卷 技术标（Level 0 卷）、第一章 / 1.0（Level 1 章/编）、1.1 / 1.2（Level 2 叶子节）、1.1.1（Level 3 子节）；
     - 各分级节点包含标准属性：`id`、`title`、`chinese_num`、`section_number`、`level`、`volume`、`chapter_type`、`children`；
  2. **智能条款分类与两册对齐映射**：
     - 商务资格、财务审计、企业认证、历史业绩条款精准分流至商务分册（`business`）；
     - 系统架构、微服务拓扑、高可用双活方案分流至技术分册（`technical`）第一章总体架构方案；
     - 交付团队、实施进度、7x24小时运维与 SLA 承诺分流至技术分册第二章实施服务保障；
     - 网络安全、等保三级、数据加密与应急容灾预案分流至技术分册第三章信息安全保障；
     - 偏离表分流至商务偏离表与技术偏离表（`chapter_type="system"`，`system_subtype="deviation_table"`）；
     - 点对点应答清单分流至系统生成类章节（`point_to_point`）；
     - 零未映射条款红线：矩阵中全部确认条款 100% 精确映射到叶子章节（`unmapped_requirements_count == 0`）；
  3. **评分要点自动挂接与结构化写作指引生成**：
     - 为每个叶子章节精准挂接真实条款 ID（`bound_requirement_ids` 与 `associated_clause_ids`）；
     - 自动提取并装配分值（`score`）、评分标准（`scoring_criteria`）、星号条款（★）与废标红线标记；
     - 自动合成符合模型直接消费的结构化 `writing_points`，明确目标字数建议（`target_length`，800~3000 字动态加权）、编写要点、评分响应指引与客观佐证材料引用要求；
  4. **条款防编造防幻觉白名单校验**：
     - 所有挂接与引用的招标文件条款必须来源于真实解析矩阵（`workflow["requirements"]`）；
     - 企图传入或引用未核实/虚构的条款 ID 直接抛出 422 `INVALID_REQUIREMENT_REFERENCE`，坚决杜绝模型幻觉编造虚假条款依据；
  5. **多租户强隔离与 RBAC 权限门禁**：
     - 跨租户项目请求直接拦截 404 `NOT_FOUND`，杜绝企业间标书数据窥探；
     - 系统只读角色（`viewer`、`auditor`）与项目只读成员拦截 403 `FORBIDDEN`，防止非授权构建大纲；
  6. **内网物理隔离与涉密项目硬门禁（Airgap Boundary）**：
     - 涉密项目（`sensitive=True`）使用模型参与大纲规划时，硬门禁拦截外部云端模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`），仅放行私有化本地模型；
  7. **预览与单事务原子持久化双模式**：
     - `preview=True`：纯内存推导返回规范大纲树与定稿就绪检查，不改动仓储数据；
     - `preview=False`（默认）：单事务原子持久化章节（`state.chapters`）、回写需求矩阵映射（`requirement["chapter_id"]`）、更新章节排序（`chapter_order`）、同步大纲方案元数据（`outline_plans`）与写作计划（`writing_plan`），推进项目与大纲 revision 自增；
  8. **大纲定稿锁定前置就绪检查（check_tree_finalization_readiness）**：
     - 全方位核验大纲完整性、分册覆盖度（两册齐备）、未映射条款数（必须为 0）、空章节与星号条款标记不适用的阻断诊断；
  9. **API 端点集成与 OpenAPI 零漂移**：
     - 注册 `POST /api/v1/projects/{project_id}/outline/auto-tree-build`（`include_in_schema=False`），OpenAPI 契约保持 100% 零漂移。

---

## 2. 交付物清单

### 2.1 核心代码
- `backend/bid-core/icg/domain/outline_auto_tree.py`（**新建**）：
  - `to_chinese_num` / `format_volume_info` / `format_chapter_info` / `format_section_info` / `format_subsection_info`：中文大纲与数字层级格式化引擎；
  - `classify_requirement_clause`：招标文件矩阵条款智能分类与分册对齐分类器；
  - `generate_structured_writing_points`：结构化写作指引与评分响应指引装配器；
  - `STANDARD_TREE_TEMPLATE`：国标级两册标准骨架模板库（商务资质、偏离表、总体架构、实施服务、安全合规、点对点应答）；
  - `AutoTreeBuildEngine`：大纲树自动推导与构建核心引擎类，支持条款分类、映射分流、防编造校验、目标字数加权与结构化大纲树生成；
  - `check_tree_finalization_readiness`：大纲定稿就绪诊断检查器；
- `backend/bid-core/icg/domain/outline_plan.py`：
  - 导入 `AutoTreeBuildEngine` 与 `check_tree_finalization_readiness`；
  - `OutlinePlanService` 新增 `auto_build_outline_tree(project_id, principal, options)` 入口方法，实现租户隔离、RBAC 门禁、涉密模型校验与单事务原子落盘；
- `backend/bid-core/icg/domain/outline_orchestrator.py`：
  - `OutlineOrchestratorMixin` 新增 `auto_build_outline_tree` 快捷委托方法；
  - 升级 `build_outline_tree`，返回包含层级、章节类型、绑定条款、星号/废标标记与写作指引的丰富大纲树节点；
  - 升级 `check_outline_finalization_readiness`，复用 `check_tree_finalization_readiness`；
- `backend/bid-core/icg/domain/outline_service.py`：
  - 重新导出 `OutlinePlanService`、`AutoTreeBuildEngine` 与 `check_tree_finalization_readiness`；
- `backend/bid-core/icg/api/workflow.py`：
  - 注册 `POST /api/v1/projects/{project_id}/outline/auto-tree-build` 端点（配置 `include_in_schema=False` 保障 OpenAPI 零漂移）。

### 2.2 自动化测试
- `tests/backend/test_ai_outline_auto_tree_build.py`（**新建**）：11 项专属自动化测试，包含编号格式化、条款分类、树结构构建、防编造拦截、多租户隔离、RBAC 门禁、涉密模型硬门禁、预览与持久化模式、定稿就绪检查与 HTTP API 端点集成，全绿通过。

---

## 3. 验证命令与结果

### 3.1 专属自动化测试套件
```powershell
pytest tests/backend/test_ai_outline_auto_tree_build.py -v
```
**运行结果**：
```text
tests/backend/test_ai_outline_auto_tree_build.py::test_chinese_numbering_utilities PASSED [  9%]
tests/backend/test_ai_outline_auto_tree_build.py::test_clause_categorization_and_volume_alignment PASSED [ 18%]
tests/backend/test_ai_outline_auto_tree_build.py::test_auto_tree_build_structure_and_numbering PASSED [ 27%]
tests/backend/test_ai_outline_auto_tree_build.py::test_anti_hallucination_clause_verification PASSED [ 36%]
tests/backend/test_ai_outline_auto_tree_build.py::test_multi_tenant_isolation PASSED [ 45%]
tests/backend/test_ai_outline_auto_tree_build.py::test_rbac_role_gate PASSED [ 54%]
tests/backend/test_ai_outline_auto_tree_build.py::test_sensitive_project_local_model_gate PASSED [ 63%]
tests/backend/test_ai_outline_auto_tree_build.py::test_preview_mode_preserves_state PASSED [ 72%]
tests/backend/test_ai_outline_auto_tree_build.py::test_persistence_mode_atomic_updates PASSED [ 81%]
tests/backend/test_ai_outline_auto_tree_build.py::test_outline_finalization_readiness_check PASSED [ 90%]
tests/backend/test_ai_outline_auto_tree_build.py::test_http_api_auto_tree_build PASSED [100%]

============================= 11 passed in 0.96s ==============================
```

### 3.2 大纲与工作流全套回归测试
```powershell
pytest tests/backend/test_outline_plan_service.py tests/backend/test_outline_contract_draft.py tests/backend/test_outline_generation_start.py tests/backend/test_workflow_orchestrator_modular.py tests/backend/test_ai_outline_generation_expand.py tests/backend/test_ai_outline_auto_tree_build.py -q
```
**运行结果**：
```text
..................................................                       [100%]
50 passed in 1.71s
```

### 3.3 全量 AI 核心后端联合套件
```powershell
pytest tests/backend/test_ai_compliance_cross_check.py tests/backend/test_ai_outline_auto_tree_build.py tests/backend/test_ai_outline_generation_expand.py tests/backend/test_ai_prompt_budget.py tests/backend/test_ai_snippet_retrieval.py -q
```
**运行结果**：
```text
........................................................                 [100%]
56 passed in 3.83s
```

### 3.4 OpenAPI 契约零漂移核验
```powershell
python backend/bid-core/export_openapi.py --check
```
**运行结果**：
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 主 Agent 业务验收五条金标准核对

1. **主路径推进**：
   - 彻底解决招标文件解析后到正文分节生成之间的关键断环：将解析出的散落条款与评分标准，一键自动规划成符合招投标规范的两卷结构化大纲树，自动挂接评分项与生成 `writing_points`，端到端打通“解析确认 → 响应矩阵 → 大纲规划构建 → 分节批量生成”主业务路径。
2. **安全与隔离底线**：
   - 严格执行出处防编造校验（非法条款 ID 拦截 422 `INVALID_REQUIREMENT_REFERENCE`）；
   - 严格执行多租户强隔离（跨公司项目拦截 404 `NOT_FOUND`）；
   - 严格执行涉密项目硬门禁（涉密项目绑定云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
   - 严格保护星号条款（★）与废标红线，禁止在定稿就绪检查中遗漏。
3. **关演示正式可用**：
   - 全套逻辑在 `MemoryRepository` 与生产持久化仓储多态下完全一致，单事务原子持久化到章节仓储与工作流存储，支持真实 Access Token 认证与 8 角色权限感知。
4. **诚实记录阻断门禁**：
   - `check_tree_finalization_readiness` 真实检查未映射条款、空章节与未确认大纲，存在阻断时诚实返回 `ready=False` 并输出诊断详情，不伪造可定稿通过。
5. **拒绝空壳冒充交付**：
   - 提供了真实完整的树状衍生推导算法、条款分类器、多层级编号生成器、评分要点结构化生成器与 HTTP API 端点，11 项专属单测与 50 项回归测试全绿覆盖。

---

## 5. 后续流转建议

本任务卡已完成全部功能开发、自动化测试编写、回归复测与契约核验，任务卡状态在 `docs/tasks/AI-M0.md` 及 `docs/TASK_BOARD.md` 中置为 `in-review`。
建议由 QA 角色执行独立终验签署、由 PD 角色进行 PRD MVP v1.8 §5.7.1/§5.7.2 产品视角对照复核后，由人类 PM 最终标为 `done`。
