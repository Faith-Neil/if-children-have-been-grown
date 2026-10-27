为什么有这个文件：把模型选型和兼容适配器分成可单独验收的任务。

它解决什么问题：避免在端点和数据库还没决定时，把演示替身或一个适配器说成生产模型已经接入。

# AI-M0：模型接入准备

日期：2026-10-13。AI 表示模型接入任务，独立于前端 FE 计划和 APP 页面计划。

<a id="ai-01"></a>

## AI-01 · 登记模型、向量、业务库和内网访问待决项

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 记录选项本身不依赖外部接口；用户决定的等待时间不计入实现 |
| 关联 Issue | [ISSUE-010](../../issues/ISSUE-010.md)，并回链 [ISSUE-005](../../issues/ISSUE-005.md) |
| 依赖 | [FE-M0-T02](FE-M0.md#fe-m0-t02)。不依赖尚未选定的端点或数据库 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 当前实施段；[ISSUE-005](../../issues/ISSUE-005.md) DG-06 |
| 完成时交付 | [登记交付](../delivery/AI-01.md)；运行时见 [ISSUE-028 交付](../delivery/ISSUE-028.md) |
| 代码解释 | 假服务见 [代码解释](../code/AI-01.md)；运行时见 [ISSUE-028 代码解释](../code/ISSUE-028.md) |

范围：列出对话模型、嵌入、重排、向量库、业务库和内网验证的可选项，以及需要用户回答的问题。项目经理对 PostgreSQL 16 与 pgvector 的意见只记为建议，用户没有采纳。

当前条件：2026-10-12 用户决定业务库为 MySQL 8，对话模型由配置页提供，嵌入与向量库用 RAGFlow 自带能力，生产生成只在内网（user decision, relayed by PM）。ISSUE-010 已 closed。本卡为 in-review。托管 CI 不能访问公司内网。CI 使用测试目录里的假对话服务；连真实地址须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。配置读取与运行时路由已通过 ISSUE-028 接入。

可验证验收：

- [x] 选项和未决问题已写入 ISSUE-010，建议与决定分开。
- [x] 用户已作出选择，路线图和架构的决定用词已更新。PRD 不新增验收。PRD、路线图和 brief 的任务计数未改。
- [x] CI 使用假的 OpenAI 兼容服务，记录请求头和实际 `base_url`。连真实地址的测试须 `ICG_RUN_REAL_MODEL_TESTS=1`，默认跳过。
- [ ] 选定后的真实端点或库有独立验收，不由本登记代替。
- [x] 敏感项目使用非本地模型返回 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`（由 409 改为 403，见 ISSUE-028 与 `test_model_config_provider.py`）。

<a id="ai-02"></a>

## AI-02 · OpenAI 兼容对话适配器

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 在现有模型和 HTTP 库上增加一个适配器 |
| 关联 Issue | [ISSUE-011](../../issues/ISSUE-011.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) 的 `ModelProvider`。不依赖 ISSUE-010 的最终端点 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 模型替换口；敏感项目本地门禁保持原行为 |
| 完成时交付 | [交付](../delivery/AI-02.md) |
| 代码解释 | [代码解释](../code/AI-02.md) |

范围：实现 `OpenAICompatibleModelProvider`。`name` 为 `openai-compatible`，`is_real_model` 为 true，`is_local` 来自配置。`suggest` 调用 `POST {base_url}/v1/chat/completions`。配置来自环境变量。演示替身仍是 `create_app()` 的默认实现；只有显式打开配置开关才选择真实适配器。

当前条件：不连接真实端点。密钥不入库。不新增依赖。

可验证验收：

- [x] 假 HTTP 覆盖成功、超时、非 200、畸形 JSON，以及 `is_local` 真假与敏感项目门禁。
- [x] 失败走现有 502 `MODEL_UNAVAILABLE`，不返回假成功，不改已提交正文。
- [x] `tests/backend/test_reference_boundaries.py` 包含在全后台回归中。
- [x] 交付、代码解释、验证记录和基线同步已登记。真实内网调用不在本卡。

项目经理于 10-12 12:10 在 QA 签署后确认。状态为 done。合入和发布仍未发生。ISSUE-010 已 closed，真实端点仍未验收。

<a id="ai-03"></a>

## AI-03 · 检索层内存骨架

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 在现有协议旁增加内存检索口，不接外部服务 |
| 关联 Issue | [ISSUE-016](../../issues/ISSUE-016.md) |
| 依赖 | [BE-M0-T01](BE-M0.md#be-m0-t01) 的替换口。向量库已定为 RAGFlow 自带，本卡仍不连接它 |
| PRD / 架构出处 | [前端架构](../ARCHITECTURE.md) 当前实施段。业务库为 MySQL 8，本卡不连接它 |
| 完成时交付 | [交付](../delivery/AI-03.md) |
| 代码解释 | [代码解释](../code/AI-03.md) |

范围：定义 `EmbeddingProvider.embed`、`RerankProvider.rerank` 和 `VectorStore.upsert/search`。搜索按 `company_id`、`status` 和 `type` 过滤。三者都只提供内存实现。`EvidenceCandidateService` 产出路径 A（已确认资料上的规则）、路径 B（嵌入、按公司检索、重排）和路径 C（历史投标，仅供参考且不可附着）。B 或 C 失败，或知识库关闭时，保留 A 并记录跳过原因。

当前条件：不连接 MySQL，不连接 RAGFlow，不新增依赖，不挂到 `create_app`。向量库选型已在 ISSUE-010 关闭，不由本卡实现。

可验证验收：

- [x] 三个协议和内存实现可用，搜索必须同时给出公司、状态和类型。
- [x] 合成数据覆盖跨公司隔离，历史投标不可附着，失败或知识库关闭时回退到 A。
- [x] `tests/backend/test_reference_boundaries.py` 包含在全后台回归中。
- [x] 交付、代码解释、验证记录和基线同步已登记。真实库不在本卡。

项目经理依据 QA 签署 2fe6198（REV-M0-T16）确认。状态为 done。ISSUE-016 为 closed。合入和发布仍未发生。真实库不在本卡。

<a id="ai-04"></a>

## AI-04 · CI 假 RAGFlow 检索服务

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 只加测试夹具，不改运行代码 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)。设计保持 [ISSUE-029](../../issues/ISSUE-029.md) closed |
| 依赖 | [AI-03](AI-M0.md#ai-03) 的内存口仍在。本卡不连接它，也不替换它 |
| PRD / 架构出处 | [RAGFlow 检索适配器](../architecture/ragflow-retrieval-adapter.md)。产品字段以 [PRD v1.8](../reference/product/prd-mvp-v1.8.md) 与 [字典 v1.9](../reference/product/kb-data-dictionary-v1.9.md) 为准，不另造 |
| 完成时交付 | [交付](../delivery/AI-04.md) |
| 代码解释 | 不改 `backend/bid-core`。假服务见 [代码解释](../code/AI-04.md) |

范围：在 `tests/backend/` 提供只监听 `127.0.0.1` 的假 RAGFlow。`POST /api/v1/retrieval` 记下 `Authorization: Bearer` 和实际 `base_url`。可选 `GET /api/v1/system/healthz`。模式覆盖成功 chunks、空 chunks、非 0 业务 `code`、HTTP 错误，以及可释放的超时停住。真实地址须 `ICG_RUN_REAL_RAGFLOW_TESTS=1`，默认跳过。

当前条件：不实现 `RagflowRetrievalClient`，不改 `retrieval.py`，不加依赖。数据集生命周期和 `kb_sync` 不在本卡。零命中在适配器里记为跳过，不记为成功的空列表；本卡只让夹具返回空 chunks，不做这条映射。重排仍是 RAGFlow 的 `rerank_id`，不新增重排依赖。

可验证验收：

- [x] 假服务记录 `Authorization` 和实际 `base_url`，包括路径前缀。
- [x] 成功体为 `{"code":0,"data":...}`，并另有空 chunks、非 0 业务码和 HTTP 错误。
- [x] 真实连接默认跳过。交付、代码解释、验证记录和基线同步已登记。
- [ ] 零命中记为跳过，以及客户端与 `retrieval.py` 接线。留给 AI-05、AI-06。

不标 done。ISSUE-037 为 in-progress。合入和发布仍未发生。

<a id="ai-05"></a>

## AI-05 · RAGFlow 检索客户端

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 在已有 httpx 上增加一个只读检索客户端 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md) |
| 依赖 | [AI-04](AI-M0.md#ai-04) 的假服务。不依赖数据集创建或 `kb_sync` |
| PRD / 架构出处 | [RAGFlow 检索适配器](../architecture/ragflow-retrieval-adapter.md) 的检索与错误节 |
| 完成时交付 | [交付](../delivery/AI-05.md) |
| 代码解释 | [代码解释](../code/AI-05.md) |

范围：实现 `RagflowRetrievalClient`。`POST {base_url}/api/v1/retrieval`，请求头 `Authorization: Bearer`。基址与密钥只从环境注入。正文只带调用方注入的 `question`、`dataset_ids` 和 `rerank_id`。不创建数据集，不上传，不解析，不改 `kb_sync_status`。

当前条件：客户端已实现。不改 `EvidenceCandidateService`。`code` 为 0 且 chunks 为空时返回跳过，不返回成功的空列表。非 0 业务码、HTTP 错误和超时是检索失败，不能当成命中。密钥不进日志。不加依赖，不用本仓库新的重排库。

可验证验收：

- [x] 假服务覆盖成功 chunks、空 chunks 记为跳过、非 0 业务码、HTTP 错误和超时。
- [x] 只发送注入的 `dataset_ids` 与 `rerank_id`。不调用数据集或同步接口。
- [x] 不改 `retrieval.py`。交付、代码解释和基线同步已登记。真实内网不在本卡。

已由人类 PM 依据 QA 复测签署（D-742）与 PD 产品验收（D-743）正式确认为 done。

<a id="ai-06"></a>

## AI-06 · 证据候选改走 RAGFlow 检索

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 在现有证据候选后面换上检索客户端，保留路径 A |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md) |
| 依赖 | [AI-05](AI-M0.md#ai-05) 的客户端，以及 [AI-03](AI-M0.md#ai-03) 的三条路径 |
| PRD / 架构出处 | [RAGFlow 检索适配器](../architecture/ragflow-retrieval-adapter.md) 的证据候选节。路径 C 按查询词过滤来自 ISSUE-016 的 QA P3 |
| 完成时交付 | [AI-06 交付](../delivery/AI-06.md)；[AI 端到端流水线交付](../delivery/AI-GENERATION-PIPELINE.md) |
| 代码解释 | [AI-06 代码解释](../code/AI-06.md)；[AI 端到端流水线代码解释](../code/AI-GENERATION-PIPELINE.md) |

范围：路径 B、路径 C 改为调用 `RagflowRetrievalClient`。只传入该公司注入的 dataset id。路径 A 仍是已确认资料上的规则，不经过 RAGFlow。路径 C 仍不可附着，并按查询词过滤。B 或 C 失败，或零命中时，保留 A 并记录跳过原因。知识库关闭时不调用 RAGFlow。

当前条件：已完成编码与自动化验证，提交复核。不建数据集，不改 `kb_sync`。重排只传 `rerank_id`。不把内存口从测试里删掉。不进入 `create_app`。

可验证验收：

- [x] 假 RAGFlow 覆盖跨公司只使用注入的 dataset id、历史投标不可附着、零命中或失败时回退到 A。
- [x] 路径 C 按查询词过滤。知识库关闭时没有检索请求。
- [x] 交付、代码解释、验证记录和基线同步已登记。真实库不在本卡。
- [x] 检索能力与动态模型配置端到端闭环接入章节生成 (`WorkflowService.generate`) 与章节建议 (`DemoService.suggest`)，详见 [AI 端到端流水线交付](../delivery/AI-GENERATION-PIPELINE.md)。

已由人类 PM 依据 QA 复测签署（D-742）与 PD 产品验收（D-743）正式确认为 done。

<a id="ai-editor-context-linkage"></a>

## AI-EDITOR-CONTEXT-LINKAGE · 编辑台章节上下文感知问答与划词引用联动

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 编辑台右侧助手与中间正文深度联动，支持划词润色与合规诊断 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-06](AI-M0.md#ai-06) 的检索与证据候选能力，以及 [APP-M2-T179](APP-M2.md#app-m2-t179) 助手门禁规范 |
| PRD / 架构出处 | [PRD v1.8 §5.11.3～5.11.6、§5.7.8](../reference/product/prd-mvp-v1.8.md) |
| 完成时交付 | [AI-EDITOR-CONTEXT-LINKAGE 交付](../delivery/AI-EDITOR-CONTEXT-LINKAGE.md) |
| 代码解释 | [AI-EDITOR-CONTEXT-LINKAGE 代码解释](../code/AI-EDITOR-CONTEXT-LINKAGE.md) |

范围：实现编辑台章节正文上下文感知与划词引用联动。支持传入 `chapter_id`, `chapter_title`, `selected_text`，正文切分为带编号段落 `[P1]`, `[P2]...` 并精准标定划词命中段落。支持两类场景：划词优化/润色建议（`polish`，输出 Diff 建议与改写片段，强制保护事实变量）与章节合规性/完整度问答（`compliance_qa`，条款覆盖诊断）。四道安全门禁守卫：未获独占编辑锁时强制 `can_insert=False`、`action="copy_only"` 且章节正文零突变；持有有效锁且具有溯源依据放行 `suggest_replacement` 建议；敏感项目强制本地离线模型（403）；只读角色（403）与跨租户隔离（404）。

当前条件：已完成编码与自动化验证，提交复核。专属单测 12 passed，联合套件 73 passed 全部绿灯。

可验证验收：
- [x] 正文结构化切分段落 `[P1]`, `[P2]...`，选中文本精准命中，无选中文本时无损兜底。
- [x] 划词润色场景输出 Diff 建议产物，保留事实与 SLA 变量标记。
- [x] 章节合规性问答注入招标文件条款要求与公司证据清单。
- [x] 自动搜集 `[证]` 与 `[片]` 依据并计算唯一 SHA-256 溯源指纹与 `context_fingerprint`。
- [x] 未获锁时强制 `can_insert=False`，章节正文/修订号/版本历史零修改。
- [x] 敏感项目强阻断云端模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）。
- [x] 系统只读角色与项目只读成员拦截 403 `FORBIDDEN`，跨租户隔离 404 `NOT_FOUND`。
- [x] 交付、代码解释、验证记录和基线同步已登记。

已由人类 PM 依据 QA 复测签署（D-742）与 PD 产品验收（D-743）正式确认为 done。

<a id="ai-compliance-cross-check"></a>

## AI-COMPLIANCE-CROSS-CHECK · AI 合规检查依据交叉核验与差距诊断

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 正文声明与引用智能抽取，对标 RAGFlow 证据与招标文件条款进行置信度推导与差距诊断 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [APP-M2-T185](APP-M2.md#app-m2-t185) 采纳建议回写，以及 [AI-EDITOR-CONTEXT-LINKAGE](AI-M0.md#ai-editor-context-linkage) 上下文感知 |
| PRD / 架构出处 | [PRD v1.8 §5.8、§5.11.5、§5.11.6](../reference/product/prd-mvp-v1.8.md) |
| 完成时交付 | [AI-COMPLIANCE-CROSS-CHECK 交付](../delivery/AI-COMPLIANCE-CROSS-CHECK.md) |
| 代码解释 | [AI-COMPLIANCE-CROSS-CHECK 代码解释](../code/AI-COMPLIANCE-CROSS-CHECK.md) |

范围：实现 AI 合规检查依据交叉核验与差距诊断核心引擎。多维度抽取正文段落中声明（SLA 可用性、响应恢复时限、覆盖时段、巡检频次、RTO/RPO、资质认证、人员能力、业绩案例及服务承诺）并精准绑定行内 `[证:ID]`、`[片:ID]`、`[cite:ID]` 引用胶囊。实现全维度交叉核验场景比对与置信度推导（充分证据 0.95 high、一般描述 0.55 medium warning 并提供针对性差距诊断与补传建议、未标引用 0.15~0.40 low/unsupported）。对标招标文件硬性条款检出负偏离直接评定 0.00 unsupported block 并阻断废标隐患；对标证据有效性（过期、缺失合作协议）直接评定 0.00 unsupported block；严防跨租户泄露，异企租户证据引用严格评定 0.00 unsupported block 并标识 `cross_company` 阻断；严格落实防虚构/幻觉红线，未入库依据引用直接识别为 0.10 unsupported block。完整透传 RAGFlow 来源文档与分块溯源元数据（`document_id` / `chunk_id`），输出量化差距指标 `discrepancy_count` 与 `is_discrepancy` 标签。核验结果沉淀至 `workflow['incremental_checks']`，联动更新 `chapter.incremental_check_status` 并构建 `CheckIssue`。严格落实涉密项目本地模型门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）、非成员权限拦截（403 `FORBIDDEN`）、跨租户隔离（404 `NOT_FOUND`）与 OpenAPI 契约零漂移（`include_in_schema=False`）。

当前条件：已完成深化编码与自动化验证，提交复核。专属单测 13 passed 全部绿灯。

可验证验收：
- [x] 多维度声明（SLA、资质、人员、案例、承诺）抽取与行内引用区间精准绑定（支持 `[证:ID]`、`[片:ID]`、`[cite:ID]`）。
- [x] 充分证据高置信度（0.95 high）比对通过，透传 RAGFlow `document_id` 与 `chunk_id` 溯源证据。
- [x] “正文承诺 99.99% 但证据仅为一般描述”识别为 0.55 medium warning，并输出差距诊断与补传建议，标识 `is_discrepancy=True`。
- [x] 正文承诺劣于招标文件硬性条款识别为 0.00 unsupported block 负偏离阻断。
- [x] 引用过期证据或缺失合作协议识别为 0.00 unsupported block 阻断。
- [x] 跨租户异企证据引用严格阻断（0.00 unsupported block，`cross_company` 状态）。
- [x] 引用未入库虚构/幻觉依据严格阻断（0.10 unsupported block，`missing` 状态）。
- [x] 后端 checks 服务联动与增量复查状态更新（`passed` / `warning` / `failed`）及 `discrepancy_count` 统计。
- [x] 涉密项目拦截云端模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）。
- [x] 跨租户 404 与非项目成员 403 严格隔离。
- [x] HTTP 端点 `include_in_schema=False` 保护 143 个冻结错误码无变更。
- [x] 交付、代码解释、测试文件和基线同步已登记。

状态保持 in-review，建议由 QA 与 PD 验收后由 PM 标 done。




<a id="ai-m0-ragflow-verify"></a>

## AI-M0-RAGFLOW-VERIFY · RAGFlow 端点对接与检索隔离审查

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 针对端点对接规范、多租户强隔离、防虚构出处追溯与离线测试门禁进行代码与架构审计 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-010](../../issues/ISSUE-010.md) |
| 依赖 | [AI-04](AI-M0.md#ai-04)、[AI-05](AI-M0.md#ai-05)、[AI-06](AI-M0.md#ai-06) |
| PRD / 架构出处 | [RAGFlow 检索适配器](../architecture/ragflow-retrieval-adapter.md)；[PRD v1.8 §5.8、§5.11](../reference/product/prd-mvp-v1.8.md) |
| 完成时交付 | [AI-M0-RAGFLOW-VERIFY 交付](../delivery/AI-M0-RAGFLOW-VERIFY.md) |
| 代码解释 | [AI-M0-RAGFLOW-VERIFY 代码说明](../code/AI-M0-RAGFLOW-VERIFY.md) |

范围：全面核查 RAGFlow 检索适配层（`ragflow_client.py`、`retrieval.py`、`generation_context.py`、`compliance_cross_check.py`）。核实客户端只读规范与异常安全映射；核实多租户/公司数据集绑定与越界防御；核实事实依据来源追溯（`document_id` / `chunk_id` / `.cite` 引用）与防虚构机制；核实真实外部模型测试受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护与当前生产端点 blocked 依赖条件。

当前条件：自动化回归测试全绿通过（41 passed 2 skipped + 14 passed 1 skipped），端到端闭环逻辑通过。生产环境对接诚实记录为 blocked 并明确环境依赖。

可验证验收：
- [x] 客户端严格遵循 POST /api/v1/retrieval 规范，输入非空校验，只传 question/dataset_ids/rerank_id，异常安全映射，零命中（code 0 且 chunks 为空）标记 skipped=True。
- [x] 检索过程具备公司/租户强隔离语义（CandidateRequest.company_id 强制校验，数据集绑定 company_id，返回 chunk 越界严格抛出 RetrievalError 阻断）。
- [x] 事实依据来源追溯与防编造追溯语义成立（chunk_id 与 document_id 挂载入 Prompt，事实变量防篡改 409 保护，.cite 引用精准关联知识库 ID，负偏离条款与无效证据 risk=block 强阻断）。
- [x] 真实 RAGFlow 测试受环境变量 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护，默认在假服务环境下测试端到端闭环逻辑；生产对接依赖诚实说明为 blocked。
- [x] 自动化测试 `pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_chapter_generation_rag_flow.py` 执行全过（41 passed, 2 skipped）。
- [x] 专用检索测试 `pytest tests/backend/test_evidence_ragflow.py` 执行全过（14 passed, 1 skipped）。
- [x] 交付报告、代码说明与任务看板同步完成。

已由人类 PM 依据 QA 复测签署（D-742）与 PD 产品验收（D-743）正式确认为 done。

<a id="ai-ragflow-kb-sync"></a>

## AI-RAGFLOW-KB-SYNC · RAGFlow 知识库摄入与同步闭环（D4-AI）

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落实用户拍板 B5/B6，补齐知识库摄入闭环，实现多租户强隔离、文档上传、解析轮询与优雅降级 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-M0-RAGFLOW-VERIFY](AI-M0.md#ai-m0-ragflow-verify) |
| PRD / 架构出处 | [PRD v1.8 §5.8、§5.11](../reference/product/prd-mvp-v1.8.md)；用户 2026-10-26 拍板 B5/B6 |
| 完成时交付 | [AI-RAGFLOW-KB-SYNC 交付](../delivery/2026-10-26-ragflow-kb-sync.md) |
| 代码解释 | [AI-RAGFLOW-KB-SYNC 代码说明](../code/2026-10-26-ragflow-kb-sync.md) |

范围：落实用户拍板 B5（招标/投标私有内网隔离、严禁向公网发请求）与 B6（私有化部署、Windows/Linux 兼容），打通知识库片段摄入与同步闭环（`dataset/kb_sync`）。扩展客户端 `create_dataset`（带租户命名空间前缀）、`list_datasets`（租户隔离过滤）、`get_dataset`（所有权核验）、`upload_document`（multipart上传）、`trigger_parse`（触发内置解析）与 `get_document_status`（解析生命周期轮询）。扩展领域服务 `RagflowConfigService.sync_knowledge_base`，支持从方案片段发布存储及企业资料库结构化摄入、智能对齐或自动创建租户隔离数据集、将 run 映射为规范的 `kb_sync_status`（`synced` / `failed` / `unsynced`）并回写存储。实现非本公司跨租户同步 404 拦截、网络异常优雅降级，以及 `@pytest.mark.live_ragflow` 真实环境门控。保持 143 个冻结错误码与 OpenAPI 契约 100% 零漂移。

当前条件：自动化回归测试全绿通过（专属测试 9 passed 1 skipped，联合全量 67 passed 4 skipped）。端到端闭环逻辑通过。真实生产端点诚实记录为 blocked 并明确环境依赖。

可验证验收：
- [x] 客户端支持带 `${company_id}::` 命名空间前缀的数据集创建与所有权检查；
- [x] 客户端 `httpx.Client` 强制配置 `trust_env=False`，避免系统代理劫持内网请求；
- [x] 领域服务 `sync_knowledge_base` 完整闭环，方案片段发布后摄入知识库并回写 `kb_sync_status` 为 `synced`；
- [x] 非本公司方案片段跨租户同步严格抛出 404 `NOT_FOUND`；
- [x] 上游网络/服务端 500 异常时优雅降级并返回失败状态，不引起主服务崩溃；
- [x] 真实 RAGFlow 测试受 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 保护，默认在假服务环境下闭环；
- [x] 专属测试套件 `pytest tests/backend/test_ragflow_kb_sync.py -v` 执行全过（9 passed, 1 skipped）；
- [x] 全量 RAGFlow 测试 `pytest tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py tests/backend/test_evidence_ragflow.py tests/backend/test_ragflow_config_api.py tests/backend/test_ragflow_kb_sync.py tests/backend/test_chapter_generation_rag_flow.py` 全绿（67 passed, 4 skipped）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已由人类 PM 依据 QA 复测签署（D-742）与 PD 产品验收（D-743）正式确认为 done。

<a id="ai-snippet-retrieval-match"></a>

## AI-SNIPPET-RETRIEVAL-MATCH · 方案片段智能检索与上下文精准匹配

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 针对章节与评分项实现方案片段高精度检索、项目事实变量抽取对齐与出处防伪溯源 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-010](../../issues/ISSUE-010.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-RAGFLOW-KB-SYNC](AI-M0.md#ai-ragflow-kb-sync)、[AI-06](AI-M0.md#ai-06) |
| PRD / 架构出处 | [PRD v1.8 §5.8、§5.11](../reference/product/prd-mvp-v1.8.md)；[资料库字典 v1.9](../reference/product/kb-data-dictionary-v1.9.md) |
| 完成时交付 | [AI-SNIPPET-RETRIEVAL-MATCH 交付](../delivery/AI-SNIPPET-RETRIEVAL-MATCH.md) |
| 代码解释 | [AI-SNIPPET-RETRIEVAL-MATCH 代码说明](../code/AI-SNIPPET-RETRIEVAL-MATCH.md) |

范围：在 `backend/bid-core/icg/domain/snippet_retrieval.py` 与 `infra/retrieval.py` 中实现方案片段高精度检索与上下文精准匹配服务。
1. 多租户强隔离：严格限制只召回当前会话 `company_id` 下已发布的方案片段（`published_revision > 0`），严禁跨租户越界召回，跨租户项目访问拦截 404；
2. 相关度匹配与变量提取：根据章节标题、评分项要点及提示词上下文，计算片段文本匹配度（字块 2-gram 重合度、关键词命中与向量余弦相似度综合加权）；自动抽取片段中声明的项目事实变量占位符（如 `{{project_name}}`, `{{service_period}}`, `{{sla_availability}}`, `{{fact:...}}`, `{{sla:...}}` 及中英文别名），并从项目事实表和 SLA 承诺中对齐填充；未对齐变量如实标入 `missing_variables` 告警；
3. 出处防虚构与 .cite 关联：每个召回片段生成标准引用标记（`[片:snippet_id]`）、16 位不可篡改 SHA-256 防伪指纹与完整来源元数据，严禁虚构依据；提供 `format_snippets_for_prompt` 规范化 Prompt 装配；
4. 涉密项目本地模型门禁与离线隔离：涉密项目（`sensitive=True`）若配置或调用云端模型，强门禁拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；针对自建内网 RAGFlow 或本地 Qwen 客户端，设置 `trust_env=False` 严防网络代理劫持；
5. RAGFlow 联动与优雅降级：支持多路检索并验证 `${company_id}::` 租户数据集隔离，外部服务异常时优雅降级为本地高精度检索；
6. 契约安全：路由端点挂载 `include_in_schema=False` 保护冻结 OpenAPI 契约 100% 零漂移。

当前条件：自动化回归测试全绿通过（专属测试 11 passed，联合全量 89 passed 3 skipped）。端到端闭环逻辑通过。

可验证验收：
- [x] 多租户强隔离：只召回本公司已发布片段，未发布草稿与跨租户片段 100% 隔离；
- [x] 越权隔离：跨租户项目访问拦截 404 NOT_FOUND；
- [x] 相关度精准匹配与加权排序：字块 2-gram、关键词加权与向量余弦相似度联合打分（0.0 ~ 1.0）；
- [x] 事实变量自动对齐替换：支持 project_name、service_period、sla_availability、fact:ID、sla:KEY 等精准填充；
- [x] 缺失变量识别：未对齐变量标入 missing_variables 并保留占位符，标识 has_missing_variables=True；
- [x] 出处防虚构与 .cite 溯源：标准 [片:ID] 标签、16 位 SHA-256 防伪指纹与 Prompt 上下文装配；
- [x] 涉密项目本地模型强门禁：敏感项目绑定云端模型拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
- [x] 优雅降级：RAGFlow 超时或异常时本地检索正常返回；
- [x] RAGFlow 越界召回拦截：非本租户数据集分块触发 RetrievalError 阻断；
- [x] HTTP 端点 POST /api/v1/projects/{project_id}/snippets/match 认证与租户隔离安全；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_snippet_retrieval.py -v` 执行全过（11 passed）；
- [x] 全量 AI 与 RAG 联合测试回归全绿（89 passed, 3 skipped）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

状态保持 in-review，建议由 QA 与 PD 终验后由 PM 标 done。
