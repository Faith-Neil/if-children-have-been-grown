# 为什么有这个文件：记录 AI-M0 RAGFlow 端点对接、租户强隔离与防编造追溯语义审查核验的实际证据与结论。
# 它解决什么问题：对 AI-04、AI-05、AI-06 及端到端生成链路进行系统化审查，核实外部端点对接规范、租户强隔离语义与事实防编造追溯机制，诚实记录生产依赖阻断与离线复现条件。

# AI-M0-RAGFLOW-VERIFY · RAGFlow 端点对接与检索隔离审查交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | AI-M0-RAGFLOW-VERIFY |
| 代码解释 | 详见 [代码说明](../code/AI-M0-RAGFLOW-VERIFY.md) |
| 验收 | 自动化套件核验：`pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_chapter_generation_rag_flow.py` 执行通过（41 passed, 2 skipped, 36.65s）；`pytest tests/backend/test_evidence_ragflow.py` 执行通过（14 passed, 1 skipped, 15.17s）；端点对接规范、公司租户强隔离、越界防御与防编造追溯机制全部核验通过；真实端点由 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护，生产对接诚实说明外部依赖与复现条件 |
| 项目进度 | 本审查核验任务卡推进至 in-review，AI-04、AI-05、AI-06 保持 in-review；生产环境对接保持 blocked；关联 ISSUE-037 保持 in-progress；严禁私自标 done |
<!-- task-delivery:end -->

---

## 关联与状态

- 日期：2026-10-23
- 里程碑：AI-M0 模型接入准备
- 关联任务卡：[AI-M0-RAGFLOW-VERIFY](../tasks/AI-M0.md#ai-m0-ragflow-verify)、[AI-04](../tasks/AI-M0.md#ai-04)、[AI-05](../tasks/AI-M0.md#ai-05)、[AI-06](../tasks/AI-M0.md#ai-06)
- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-010](../../issues/ISSUE-010.md)
- 本地验收状态：自动化测试全绿通过，端点对接规范与隔离防编造逻辑核验完成，待 QA 团队与主 Agent 复核。
- 合入 / 发布状态：未合入，未发布；生产环境依赖待内网接入。

---

## 核心核验内容与审计发现

### 1. 端点对接规范核验 (`ragflow_client.py`)
- **入参与方法边界**：
  - `RagflowRetrievalClient` 仅实现 `POST /api/v1/retrieval`（检索）与 `GET /api/v1/system/healthz`（健康检查）；
  - 入参严格校验：`question` 必为非空字符串，`dataset_ids` 必为非空字符串列表，可选 `rerank_id`；
  - 严禁且无任何接口越权调用数据集管理、文件上传、文档解析或同步状态修改，恪守只读客户端边界；
- **凭据与机密隔离**：
  - API Key 仅通过环境变量（默认 `ICG_RAGFLOW_API_KEY`）或显式注入，统一添加 `Authorization: Bearer <API_KEY>` 请求头；
  - 异常类 `RagflowClientError`、`RagflowHttpError` 等在输出信息中严格清洗，密钥不在日志、URL 或异常栈中泄露；
- **异常层次与零命中规范**：
  - HTTP 错误映射为 `RagflowHttpError`，业务返回码非 0 映射为 `RagflowBusinessError`，超时映射为 `RagflowTimeoutError`；
  - 当服务端返回 `code == 0` 且 `chunks == []` 时，明确封装为 `skipped=True` 与 `skip_reason="zero hits"`，杜绝被上层静默当成成功的空候选列表。

### 2. 公司 / 租户强隔离机制核验 (`retrieval.py`)
- **强制输入公司绑定**：
  - `CandidateRequest` 必须携带非空 `company_id`，否则在入口抛出 `RetrievalError("company_id is required")`；
- **数据集映射限定**：
  - `_resolve_dataset_ids` 严格以当前请求的 `company_id` 查表匹配注入的数据集 ID，未授权或未配置的公司直接跳过，禁止跨公司调阅；
- **返回切片越界纵深防御**：
  - 即使上游服务因误配返回了属于其他数据集的 chunk，在 `_path_b_ragflow` 与 `_path_c_ragflow` 中执行显式越界检查：
    `if chunk.dataset_id and chunk.dataset_id not in dataset_ids: raise RetrievalError(...)`，强行阻断跨租户污染；
- **候选分类与附着属性**：
  - 路径 A 仅筛选当前公司已确认非历史资料；
  - 路径 B 为当前公司可附着切片（`attachable=True, reference_only=False`）；
  - 路径 C 强制不可附着（`attachable=False, reference_only=True`），仅供人工参考。

### 3. 事实依据追溯与防虚构语义核验 (`generation_context.py` & `compliance_cross_check.py`)
- **出处信息保真注入**：
  - `render_model_input` 将证据切片以 `[片] 检索证据片段（chunk_id: ..., document_id: ...）` 精准出处注入 Prompt；
  - 路径 C 明确渲染 `【仅供参考，不得作为正式附着证据】`；
- **事实变量强保护**：
  - 必须保留的占位符变量若被大模型擅自改写为字面值，抛出 `409 FACT_LITERAL_REPLACEMENT`；若变量遗漏，抛出 `409 FACT_VARIABLE_LOST`；若指令企图越过事实表改写数值，抛出 `409 FACT_SOURCE_CHANGE_REQUIRED`；
- **正文引用与合规交叉核验**：
  - 正文采纳时通过 `[证:ID]` / `[片:ID]` 形成 `.cite` 引用标记；
  - `compliance_cross_check.py` 对标 RAGFlow 证据与招标文件硬性条款：
    - 正文承诺劣于招标文件硬性条款，评定 0.00 unsupported 并在合规检查中标记 `risk="block"` 强阻断；
    - 引用已过期或缺失合作协议的证据，评定 0.00 unsupported 强阻断；
    - 空泛承诺无依据评定 0.15~0.55 low/medium 并要求补充证明；
    - 严禁编造无依据事实直接成为正式投标正文。

---

## 真实性与 Blocked 处理分析

根据质量审查约定与合作项目准则，本报告郑重作出如下说明：
1. **真实环境依赖与当前 Blocked 状态**：
   - 生产级大模型与真实 RAGFlow 依赖内网专有物理环境（专用 GPU 推理服务器与内网知识库集群），当前测试环境无物理外网/内网连通；
   - 生产端点对接当前客观处于 **Blocked** 状态，依赖以下外部环境前置条件：
     - 提供可访问的内网 `ICG_RAGFLOW_BASE_URL` 与有效 `ICG_RAGFLOW_API_KEY`；
     - 提供具备真实资质、人员、案例切片解析的向量数据集；
     - 部署内网离线大模型推理端点并配置至系统；
   - **严禁谎报已接入生产模型**，严禁在无证据时声称“生产模型对接已完成”；
2. **测试门禁保护规范**：
   - 真实端点探测用例严格受环境变量 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护，默认自动跳过；
   - 本地开发与 CI 依赖 `fake_ragflow` 夹具实现五种状态（chunks、empty、business_error、http_error、timeout）端到端闭环验证，确保测试结果真实、可复现、零污染。

---

## 自动化测试核验执行证据

### 1. 核心端到端与假服务测试套件
```bash
pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_chapter_generation_rag_flow.py
```
**实际控制台输出**：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 43 items

tests\backend\test_fake_ragflow.py .........s                            [ 23%]
tests\backend\test_ragflow_client.py .........................s          [ 83%]
tests\backend\test_chapter_generation_rag_flow.py .......                [100%]

======================= 41 passed, 2 skipped in 36.65s ========================
```
- 说明：2 项 skipped 均为 `@pytest.mark.live_ragflow` 真实端点探测，受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护自动跳过，符合规范。

### 2. 候选检索与隔离专用测试套件
```bash
pytest tests/backend/test_evidence_ragflow.py
```
**实际控制台输出**：
```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\徐佳馨\if-children-have-been-grown
configfile: pytest.ini
plugins: anyio-4.14.2
collected 15 items

tests\backend\test_evidence_ragflow.py ..............s                   [100%]

======================= 14 passed, 1 skipped in 15.17s ========================
```
- 说明：1 项 skipped 为真实端点跳过；其余 14 项（租户隔离、零命中降级、越界拦截、查询词过滤）全部通过。

---

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。核心逻辑对齐 PRD v1.8 §5.8、§5.11，不改动验收基线 |
| ROADMAP | 无影响。不改变阶段排期 |
| ARCHITECTURE | 无影响。现有分层架构与适配器契约完全吻合 |
| Issue 看板/详情 | 有影响。核验 ISSUE-037、ISSUE-010，保持开启，记录复验证据 |
| TASK_BOARD / PROJECT_STATUS | 有影响。登记 `AI-M0-RAGFLOW-VERIFY` 为 in-review，说明外部环境依赖与证据 |
| DOCUMENT_INDEX | 有影响。登记本交付报告与代码说明文档 |

---

## 风险与后续建议

1. **真实端点物理接入待排期**：后续在内网集成测试阶段，需由运维提供内网 RAGFlow 服务并配置 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 进行网络与物理连通性冒烟验收；
2. **知识库解析同步流水线对接**：文档上传与解析异步任务目前由离线或外部完成，后续需推进知识库文件解析完成状态（`kb_sync_status`）与检索可用性的联动。
