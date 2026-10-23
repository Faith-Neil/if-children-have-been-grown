# 为什么有这个文件：说明 RAGFlow 端点对接与检索隔离审查的代码架构、租户隔离与防编造追溯语义。
# 它解决什么问题：对 `ragflow_client.py`、`retrieval.py`、`generation_context.py` 及安全测试门禁进行深度代码审查与机制核验，提供详尽的代码逻辑流与隔离证据。

# AI-M0-RAGFLOW-VERIFY · RAGFlow 端点对接与检索隔离审查代码说明

- 任务 ID：`AI-M0-RAGFLOW-VERIFY`
- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-010](../../issues/ISSUE-010.md)
- 交付报告：[AI-M0-RAGFLOW-VERIFY 交付](../delivery/AI-M0-RAGFLOW-VERIFY.md)
- 核心代码路径：
  - `backend/bid-core/icg_demo/ragflow_client.py`
  - `backend/bid-core/icg_demo/retrieval.py`
  - `backend/bid-core/icg_demo/generation_context.py`
  - `backend/bid-core/icg_demo/compliance_cross_check.py`
  - `tests/backend/fake_ragflow.py`
  - `tests/backend/test_fake_ragflow.py`
  - `tests/backend/test_ragflow_client.py`
  - `tests/backend/test_chapter_generation_rag_flow.py`
  - `tests/backend/test_evidence_ragflow.py`

---

## 1. 架构总览与审查目标

在 AI-M0 里程碑中，系统针对 RAG 检索体系建立了从只读客户端、证据候选路由到上下文组装生成的完整分层链路。本次审查针对三项核心安全与架构原则进行逐行级核实：
1. **端点对接规范性**：客户端协议实现符合官方 API 标准，输入参数严格约束，异常映射完整，密钥隔离零泄露；
2. **多租户/公司强隔离**：严格按 `company_id` 解析与绑定检索数据集，对上游返回切片实施跨数据集阻断防御，杜绝跨租户召回；
3. **防虚构依据与溯源体系**：片段携带唯一 `chunk_id` 与 `document_id` 出处，正文声明与 `.cite`（`[证:ID]` / `[片:ID]`）强绑定，负偏离条款强阻断，未核验证据禁止写入正式正文。

---

## 2. 核心模块代码审计与实现机制

### 2.1 RAGFlow 客户端对接审计 (`backend/bid-core/icg_demo/ragflow_client.py`)

- **配置验证与机密防护**：
  `_validate_base_url` 强制协议必须为 `http` 或 `https`，禁止在 URL 中夹带敏感账号密码，禁止 URL 携带 query 或 fragment。
  API Key 仅从环境变量（默认 `ICG_RAGFLOW_API_KEY`）或显式注入获取。在构建 HTTP 请求头时注入 `Authorization: Bearer <API_KEY>`。所有异常类继承 `RagflowClientError`，其格式化消息仅输出状态码与清洗后的原因文本，绝对不泄露 API Key。
- **端点协议与参数规范**：
  - 检索方法 `retrieve(question, dataset_ids, rerank_id=...)` 强制检验 `question` 必须为非空字符串，`dataset_ids` 必须为非空字符串列表。
  - 请求体 Payload 严格限于官方规范字段：
    ```python
    payload: dict[str, Any] = {
        "question": question.strip(),
        "dataset_ids": [did.strip() for did in dataset_ids],
    }
    if rerank_id is not None and rerank_id.strip():
        payload["rerank_id"] = rerank_id.strip()
    ```
    绝不额外调用未授权的数据集创建、知识库文档上传或解析变更接口，严格遵循只读原则。
- **响应解析与安全异常映射**：
  - HTTP 非 200 状态码：映射为 `RagflowHttpError(status_code, error_msg)`。
  - 非法 JSON 或信封格式缺失：映射为 `RagflowResponseError`。
  - 业务返回码非 0：映射为 `RagflowBusinessError(code, message)`。
  - 网络超时与传输失败：映射为 `RagflowTimeoutError` 与 `RagflowConnectionError`。
  - **零命中关键机制**：当 `code == 0` 且 `chunks` 为空列表时，客户端显式返回 `RagflowRetrievalResult(chunks=[], total=..., skipped=True, skip_reason="zero hits")`，禁止伪装为成功的空候选列表，使得上游能够准确识别并触发降级逻辑。
- **健康检查接口**：
  `health()` 调用 `GET {base_url}/api/v1/system/healthz`，不发送 `Authorization` 头，符合官方无鉴权监控设计。

---

### 2.2 租户与公司强隔离审计 (`backend/bid-core/icg_demo/retrieval.py`)

在 `EvidenceCandidateService` 中，实施了四重公司级强隔离防御：

1. **调用前置租户校验**：
   `collect(request)` 方法首行强制要求：
   ```python
   if not request.company_id.strip():
       raise RetrievalError("company_id is required")
   ```
   没有公司标识的请求立即被阻断。
2. **数据集映射公司限定 (`_resolve_dataset_ids`)**：
   检索数据集解析严格以 `request.company_id` 作为键值查阅 `company_datasets` 或 `company_history_datasets`。若调用方未配置或租户不匹配，解析返回空列表，触发 `RetrievalSkip("RAGFlow dataset not configured")`，绝不跨公司调阅其他租户的数据集。
3. **返回数据越界深度防御 (Defense-in-depth)**：
   在 `_path_b_ragflow` 与 `_path_c_ragflow` 中，即使 RAGFlow 服务端因配置差错或上游漏洞返回了包含其他数据集的片段，本系统实施严格的后置校验：
   ```python
   for chunk in result.chunks:
       if chunk.dataset_id and chunk.dataset_id not in dataset_ids:
           raise RetrievalError("search returned a chunk outside the requested datasets")
   ```
   一旦检测到非授权数据集的 chunk，立即抛出 `RetrievalError` 强行终止，彻底防止跨租户数据泄露。
4. **候选对象公司所有权绑定**：
   所有生成的 `EvidenceCandidate` 候选对象强制设置 `company_id=request.company_id`。路径 A 本地规则检索只匹配 `item.company_id == request.company_id`，路径 C 历史投标不可附着（`attachable=False, reference_only=True`）。

---

### 2.3 事实依据来源追溯与防编造机制 (`generation_context.py` & `compliance_cross_check.py`)

1. **片段级 Provenance 追溯标记**：
   `EvidenceCandidate` 结构体携带 `chunk_id` 与 `document_id`。在 `generation_context.py` 的 `render_model_input` 渲染层中：
   - 已核验企业资料渲染为 `[证]`（附带资料 ID、版本号、有效期）；
   - 检索召回片段渲染为 `[片]`，并打印精确溯源出处：`（chunk_id: <chunk_id>, document_id: <document_id>）`；
   - 路径 C 历史案例明确标注：`【仅供参考，不得作为正式附着证据】`。
2. **正文事实变量防篡改门禁**：
   所有已核验事实以 `{{fact:ID}}` / `{{sla:ID}}` 形式注入 Prompt。
   若大模型输出遗漏变量占位符，触发 `409 FACT_VARIABLE_LOST`；
   若大模型将变量替换为手写字面取值，触发 `409 FACT_LITERAL_REPLACEMENT`；
   若用户或指令企图越过事实表直接改写事实取值，触发 `409 FACT_SOURCE_CHANGE_REQUIRED`。
3. **正文引用与合规交叉核验 (`compliance_cross_check.py`)**：
   - 正文采纳时通过 `[证:ID]` / `[片:ID]` 形成 `.cite` 引用标记；
   - 核验引擎智能抽取 SLA 可用性承诺、响应时间、资质证书、人员认证等强声明，并与行内最近的 `.cite` 引用绑定；
   - 若声明无依据或依据仅为一般描述，置信度下调至 0.15~0.55，并提示补充证明；
   - 若正文承诺劣于招标文件硬性条款（负偏离），或引用已过期/缺失合作协议的证据，置信度直接评定 0.00，标记 `risk="block"` 强力阻断废标隐患；
   - 绝不放行无依据的虚构事实写入正式投标正文。

---

## 3. 真实性保护与环境依赖隔离说明

为了恪守“严禁在无证据时声称生产模型对接已完成”的铁律，系统建立了严格的物理与配置隔离机制：

1. **离线测试门禁 (`ICG_RUN_REAL_RAGFLOW_TESTS=1`)**：
   - 在 `tests/backend/fake_ragflow.py` 中定义 `real_ragflow_skip_reason()` 判定函数：
     ```python
     def real_ragflow_skip_reason() -> str | None:
         if os.environ.get("ICG_RUN_REAL_RAGFLOW_TESTS", "").strip() != "1":
             return "real RAGFlow endpoint tests require ICG_RUN_REAL_RAGFLOW_TESTS=1"
         return None
     ```
   - 在所有测试套件中，标记 `@pytest.mark.live_ragflow` 的真实端点测试用例均通过 `skipif` 自动跳过，确保 CI 及本地纯洁性；
2. **测试替身闭环验证**：
   - `fake_ragflow.py` 提供单机 HTTP 假服务，支持模拟 `chunks`、`empty`、`business_error`、`http_error` 及 `timeout` 五种网络场景，充分验证异常保护分支；
   - `fake_openai_chat.py` 提供 OpenAI 兼容对话假服务，模拟大模型生成与敏感项目门禁；
3. **生产端点接入依赖条件**：
   真实生产环境接入依赖内网真实部署的 RAGFlow 实例（需配置 `ICG_RAGFLOW_BASE_URL` 与 `ICG_RAGFLOW_API_KEY`）及内网私有部署的大模型实例。在尚未部署至物理内网前，生产对接诚实保持 `Blocked` 状态。

---

## 4. 自动化验证证据汇总

执行三项核心测试套件：
```bash
pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_chapter_generation_rag_flow.py
```
**执行结果**：
- `test_fake_ragflow.py`：9 passed, 1 skipped（live 门禁正常生效）
- `test_ragflow_client.py`：25 passed, 1 skipped（live 门禁正常生效）
- `test_chapter_generation_rag_flow.py`：7 passed（端到端章节生成、建议、零命中降级、敏感拦截与防篡改全部通过）
- **合计**：41 passed, 2 skipped, 0 failed（耗时 36.65s）。

执行检索路由与隔离专用测试套件：
```bash
pytest tests/backend/test_evidence_ragflow.py
```
**执行结果**：
- `test_evidence_ragflow.py`：14 passed, 1 skipped（跨租户隔离、越界防御、零命中降级与查询词过滤全绿，耗时 15.17s）。
- **总体验证结论**：55 passed, 3 skipped，测试 100% 绿灯通过。
