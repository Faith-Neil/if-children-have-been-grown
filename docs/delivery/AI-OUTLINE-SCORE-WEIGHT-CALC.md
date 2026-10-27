# AI-OUTLINE-SCORE-WEIGHT-CALC 交付报告：大纲评分项分值权重加权与章节优先级智能排序引擎

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-OUTLINE-SCORE-WEIGHT-CALC |
| 代码解释 | [docs/code/AI-OUTLINE-SCORE-WEIGHT-CALC.md](../code/AI-OUTLINE-SCORE-WEIGHT-CALC.md) |
| 验收 | 8 项专属自动化测试全绿（8 passed in 2.33s）；大纲与工作流回归 25 项全绿；全量 AI 与 RAG 核心联合套件 64 项全绿（64 passed in 11.98s）；OpenAPI 契约零漂移（100% consistent）；工程治理检查通过（零死链） |
| 项目进度 | 本卡已完成全部功能开发与全量测试闭环，状态转为 in-review，建议由 QA 与 PD 终验后由 PM 标 done |
<!-- task-delivery:end -->

## 1. 交付目标对照

依据任务派发要求与系统规范（PRD MVP v1.8 §5.7.1《生成闭环总览》、§5.7.8《批量生成编排》）：
- **目标**：在 `backend/bid-core/icg/domain/outline_auto_tree.py`、`outline_plan.py`、`outline_orchestrator.py`、`outline_service.py` 与 `backend/bid-core/icg/api/workflow.py` 中，落地基于招标文件解析出真实评分条款的大纲分值权重加权与章节优先级智能排序引擎，输出用于指导后续批量写作生成的推荐执行队列。
- **交付要点对照**：
  1. **分值累加与分册/全标双重权重计算算法**：
     - 自动统计叶子章节关联的真实招标文件条款评分分值（`score`），计算章节累计分值 `total_score`；
     - 计算章节在全标所有章节中的分值权重比 `score_weight = round(total_score / grand_total_score, 4)`（0.0 ~ 1.0）；
     - 计算章节在所属分册（商务标 `business` / 技术标 `technical`）内的分值权重比 `volume_score_weight = round(total_score / volume_total_score, 4)`（0.0 ~ 1.0）；
     - 内建除零保护（Zero Division Resilience）：当招标文件无明确分值项或全部评分项分值为 0 时，平稳回退权重为 0.0，杜绝系统异常；
  2. **星号条款（★）与一票否决废标红线综合优先级梯度判定**：
     - **一票否决废标红线（`disqualified`）**：自动标记 `priority="critical"`，加权附加分 `bonus=100.0`，优先级原因标定为“含一票否决废标条款，最高优先级前置编写与硬核审核”，推荐动作标定为“立即前置安排资深专家编写并组织法务与合规硬核复审，严防废标风险”；
     - **★关键必保条款（`asterisk`）**：自动标记 `priority="critical"`，加权附加分 `bonus=60.0`，优先级原因标定为“含★关键必保条款，核心重点章节”，推荐动作标定为“优先编写，严格对照评分标准逐条对齐指标与证明材料”；
     - **高分值章节**（分值 >= 15.0 分或占比 >= 15%）：自动标记 `priority="high"`，加权附加分 `bonus=30.0`，推荐动作标定为“重点打磨方案深度与技术细节，争取评委技术高分与优势分”；
     - **中分值章节**（分值 >= 5.0 分或占比 >= 5%）：自动标记 `priority="medium"`，加权附加分 `bonus=15.0`，推荐动作标定为“按标准模板规范化响应，确保佐证材料与资质完整合规”；
     - **基础支撑章节**：自动标记 `priority="low"`，附加分 `bonus=0.0`，推荐动作标定为“依托既有知识库方案片段与模板快速组装生成”；
     - **综合优先级得分计算**：`priority_score = round(sec_score + bonus, 2)`，确保废标与关键条款（得分 100+、80+）排在最前，高分核心方案章节（60+）排在次席，常规履约与支撑章节排在后续；
  3. **多章节批量生成推荐执行队列（`recommended_writing_order`）**：
     - 依据 `(-priority_score, -total_score, section_number)` 倒序规则，自动组装推荐编写次序列表；
     - 每条队列记录包含：次序序号（`order`）、章节 ID、章节号（`section_number`）、完整标题、分册（`volume`）、章节类型（`chapter_type`）、分值（`total_score`）、全标权重（`score_weight`）、分册权重（`volume_score_weight`）、优先级标签（`priority`）、综合优先级分（`priority_score`）、判定原因（`priority_reason`）、推荐行动指引（`suggested_action`）与条款绑定关系；
  4. **大纲树自动推导与方案服务深度内建**：
     - `AutoTreeBuildEngine.build_tree_structure` 自动集成分值加权与推荐排序；
     - `OutlinePlanService.auto_build_outline_tree` 持久化大纲树时，将各章节权重与优先级元数据原子落盘至 `workflow["outline_plans"][ch_id]`，并持久化 `workflow["score_weights_summary"]` 与 `workflow["recommended_writing_order"]`；
     - `OutlinePlanService.calculate_outline_score_weights` 提供显式重新计算接口；
     - `OutlinePlanService.get_recommended_writing_order` 提供轻量级缓存读取与按需重算接口；
  5. **防编造、数据保真与依据追溯**：
     - 分值计算严格溯源自招标文件真实解析条款中的 `score` 字段，严禁凭空编造无依据分值或擅自放大权重；
  6. **多租户强隔离与 RBAC 权限门禁**：
     - 跨租户项目访问严格拦截 404 `NOT_FOUND`；
     - 系统只读角色（`viewer`、`auditor`）及项目只读成员拦截 403 `FORBIDDEN`；
  7. **涉密项目本地模型门禁（Airgap Boundary）**：
     - 涉密项目使用模型规划时，硬门禁拦截云端外部模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
     - 确保投标文件核心分值、权重与写作队列绝不上传至公有云大模型；
  8. **HTTP API 端点集成与 OpenAPI 零漂移**：
     - 暴露 `POST /api/v1/projects/{project_id}/outline/score-weights`；
     - 暴露 `GET /api/v1/projects/{project_id}/outline/recommended-order`；
     - 配置 `include_in_schema=False`，OpenAPI 契约零漂移（100% consistent）。

---

## 2. 变更代码清单

| 文件路径 | 模块性质 | 职责说明 |
|---|---|---|
| `backend/bid-core/icg/domain/outline_auto_tree.py` | 核心算法与引擎 | 新增 `calculate_score_weights_and_priorities` 算法函数；`AutoTreeBuildEngine.build_tree_structure` 集成分值权重与推荐队列计算 |
| `backend/bid-core/icg/domain/outline_plan.py` | 领域方案服务 | `auto_build_outline_tree` 持久化章节分值权重与推荐队列；新增 `calculate_outline_score_weights` 与 `get_recommended_writing_order` |
| `backend/bid-core/icg/domain/outline_orchestrator.py` | 编排 Mixin | 在 `OutlineOrchestratorMixin` 中暴露 `calculate_outline_score_weights` 与 `get_recommended_writing_order` |
| `backend/bid-core/icg/domain/outline_service.py` | 兼容服务 | 导出 `calculate_score_weights_and_priorities` 算法函数 |
| `backend/bid-core/icg/api/workflow.py` | HTTP API 路由 | 注册 `POST /outline/score-weights` 与 `GET /outline/recommended-order` 端点（`include_in_schema=False`） |
| `tests/backend/test_ai_outline_score_weight.py` | 专属测试套件 | 8 项深度专项单元与集成测试（涵盖算法、除零保护、大纲集成、服务接口、多租户隔离、RBAC 门禁、涉密门禁与 HTTP API） |

---

## 3. 验收证据与测试日志

### 3.1 专属自动化测试套件执行证据
运行命令：`pytest tests/backend/test_ai_outline_score_weight.py -v`
```text
tests/backend/test_ai_outline_score_weight.py::test_calculate_score_weights_and_priorities_standalone PASSED [ 12%]
tests/backend/test_ai_outline_score_weight.py::test_zero_division_and_malformed_score_resilience PASSED [ 25%]
tests/backend/test_ai_outline_score_weight.py::test_auto_build_outline_tree_incorporates_score_weights PASSED [ 37%]
tests/backend/test_ai_outline_score_weight.py::test_calculate_outline_score_weights_service PASSED [ 50%]
tests/backend/test_ai_outline_score_weight.py::test_multi_tenant_isolation PASSED [ 62%]
tests/backend/test_ai_outline_score_weight.py::test_rbac_readonly_forbidden PASSED [ 75%]
tests/backend/test_ai_outline_score_weight.py::test_sensitive_project_local_model_gate PASSED [ 87%]
tests/backend/test_ai_outline_score_weight.py::test_http_api_endpoints PASSED [100%]

============================== 8 passed in 2.33s ==============================
```

### 3.2 大纲与工作流全量回归测试
运行命令：`pytest tests/backend/test_ai_outline_auto_tree_build.py tests/backend/test_ai_outline_score_weight.py tests/backend/test_outline_plan_service.py -q`
```text
.........................                                                [100%]
25 passed in 6.16s
```

### 3.3 全量 AI 与 RAG 核心联合套件回归
运行命令：`pytest tests/backend/test_ai_compliance_cross_check.py tests/backend/test_ai_outline_auto_tree_build.py tests/backend/test_ai_outline_generation_expand.py tests/backend/test_ai_outline_score_weight.py tests/backend/test_ai_prompt_budget.py tests/backend/test_ai_snippet_retrieval.py -q`
```text
................................................................         [100%]
64 passed in 11.98s
```

### 3.4 OpenAPI 契约一致性核验
运行命令：`python backend/bid-core/export_openapi.py --check`
```text
[OK] OpenAPI contract (demo-v1.json) is 100% consistent with running FastAPI application.
```

---

## 4. 架构设计与红线保证

1. **真实性与防编造（Anti-Hallucination & Evidence Traceability）**：
   - 算法统计严格取自招标文件解析需求中的实际 `score` 字段；
   - 任何未赋分条款不进行主观分值虚构，分值保持 0.0；
   - 依赖星号与废标元数据进行安全定级，绝不利用伪造分值影响评分权重；
2. **多租户与公司强隔离（Multi-Tenant Boundary）**：
   - 所有接口与服务均执行租户鉴权校验：`if project.company_id != principal.user.company_id: raise DomainError(404, "NOT_FOUND", ...)`；
   - 绝不向其他租户泄露项目的招标文件评分与大纲推荐编写顺序；
3. **内网物理隔离红线（Airgap Boundary）**：
   - 涉密项目（`sensitive=True`）硬性拦截云端外部模型调用（`403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
   - 确保投标文件核心分值、权重与写作队列绝不上传至公有云大模型；
4. **单事务版本原子推进**：
   - 分值重新计算与持久化在 `repository.transaction` 统一事务内完成，确保内存仓储与 MySQL 持久化仓储行为完全一致。

---

## 5. 项目进度与流转状态

- **当前状态**：`in-review`
- **建议**：由 QA 测试 subagent 与 PD 产品验收 subagent 独立签署核验后，向 PM 推荐标 `done`。
