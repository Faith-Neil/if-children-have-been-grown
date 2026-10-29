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
| 状态 | done |
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
| 状态 | done |
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

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。


<a id="ai-dynamic-prompt-context"></a>

## AI-DYNAMIC-PROMPT-CONTEXT · 自适应 Prompt 动态上下文裁剪与 Token 预算控制

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 基于模型上下文窗口与 Token 预算，实现四级优先级动态裁剪、加权 Token 估算与防伪指纹计算 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-SNIPPET-RETRIEVAL-MATCH](AI-M0.md#ai-snippet-retrieval-match)、[APP-M2-T124](APP-M2.md#app-m2-t124) |
| PRD / 架构出处 | [PRD v1.8 §5.7.8](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-DYNAMIC-PROMPT-CONTEXT 交付](../delivery/AI-DYNAMIC-PROMPT-CONTEXT.md) |
| 代码解释 | [AI-DYNAMIC-PROMPT-CONTEXT 代码说明](../code/AI-DYNAMIC-PROMPT-CONTEXT.md) |

范围：在 `backend/bid-core/icg/domain/prompt_budget.py` 与 `chapter_generation.py` 中落地自适应 Prompt 动态上下文裁剪与 Token 预算控制引擎：
1. Token 预算分配策略：根据模型上下文窗口（`max_context_tokens`，默认 4096，支持 8192 / 16k / 32k）与预留生成空间（默认 1024）动态计算 Prompt 可用预算；实现中英文加权 Token 估算算法（中文字符 0.7、英文单词 1.3、空白标点 0.3）；
2. 四级优先级动态自适应裁剪：
   - Priority 1（最高核心指令，绝对不裁剪）：角色设定、章节分册目标、得分要点小标题、字数预期、事实约束规范、[证] 引用标记规范；
   - Priority 2（高优先级事实与成熟方案）：高置信度方案片段（精确匹配得分 >= 0.70）与项目已核对事实清单；空间不足时局部截断并附加告示；
   - Priority 3（中优先级条款与有效证据）：招标文件条款与响应要求、已关联公司证据清单；超出预算按相关度截取；
   - Priority 4（低优先级参考背景）：RAGFlow 候选参考切片与低相关片段；预算紧张时自适应优先丢弃；
3. 不可篡改上下文防伪指纹与 Token 指标：基于章节 ID、核心要点、保留切片 ID 列表与项目事实快照计算不可伪造的 16 位 SHA-256 `context_fingerprint`；输出包含 `priority_breakdown` 与 `truncated_items` 的完整 `token_budget_usage`；
4. 涉密隔离与防编造红线：涉密项目（`sensitive=True`）强制使用本地模型配置，企图调用云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；缺失变量如实上报 `missing_variables`，杜绝模型幻觉编造；
5. 服务层深度集成：全面集成入 `assemble_writing_prompt_plan` 与 `ChapterGenerationService.start_chapter_generation`，异步任务与候选成果自动记录指纹与预算指标。

当前条件：自动化回归测试全绿通过（专属测试 10 passed，联合全量 109 passed 3 skipped）。端到端闭环逻辑通过。

可验证验收：
- [x] Token 加权估算：中文字符、英文单词与混合符号加权计算准确；
- [x] Priority 1 核心指令保全：在极端紧缩预算下 P1 核心指令与硬约束绝对不裁剪；
- [x] Priority 4 自适应优先裁剪：预算受限时低优先级 RAGFlow 背景切片优先舍弃并记录原因；
- [x] Priority 2 方案片段局部截断：空间不足但具备缓冲时局部自适应截断并追加清晰告示；
- [x] 完整 Token 使用统计：输出包含四级分解与裁剪条目详情的 `token_budget_usage`；
- [x] 上下文指纹防伪：计算 16 位 SHA-256 `context_fingerprint`，输入或事实微调指纹立即改变；
- [x] 缺失变量识别防幻觉：未对齐变量如实记录至 `missing_variables`，标识 `has_missing_variables=True`；
- [x] 涉密项目本地模型强门禁：敏感项目绑定云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
- [x] 端到端写作计划组装完整性：`assemble_writing_prompt_plan` 返回规范化 Prompt、预算指标与指纹；
- [x] 任务与候选成果记录指纹与预算：`start_chapter_generation` 产出任务与 candidate 均落盘上下文指纹与 Token 指标；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_prompt_budget.py -v` 执行全过（10 passed）；
- [x] 全量 AI 与 RAG 联合测试回归全绿（109 passed, 3 skipped）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。

<a id="ai-outline-generate-expand"></a>

## AI-OUTLINE-GENERATE-EXPAND · 章节写作方案多段落结构化批量生成引擎

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落实多段落结构化切分（[P1]~[Pn]）、得分要点小标题解析、白名单引用核验、多章节独立启动与容错批量生成 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-DYNAMIC-PROMPT-CONTEXT](AI-M0.md#ai-dynamic-prompt-context) |
| PRD / 架构出处 | [PRD v1.8 §5.7.2、§5.7.8](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-OUTLINE-GENERATE-EXPAND 交付](../delivery/AI-OUTLINE-GENERATE-EXPAND.md) |
| 代码解释 | [AI-OUTLINE-GENERATE-EXPAND 代码说明](../code/AI-OUTLINE-GENERATE-EXPAND.md) |

范围：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地章节写作方案多段落结构化批量生成引擎：
1. 结构化段落分块与要点小标题映射（`parse_structured_paragraphs`）：将大模型生成正文解析为带有 `[P1]`~`[Pn]` 编号、段落标签、小标题与引用绑定的结构化段落列表；每一段携带独立 `id`、`paragraph_id`、`order`、`label`、`subheading`、`title`、`text`、`content`、`scoring_point`、`variables` 与 `char_length`；无标签时自适应自动编号；
2. 引用标记提取与防幻觉核验（`extract_paragraph_citations`）：从段落正文中提取 `[证:xxx]` 与 `[片:xxx]` 标记，对照入参白名单严格校验，非法虚构引用标记为 `valid=False`；
3. 多段落 Markdown 回写格式化（`format_structured_chapter_content`）：将结构化段落逆向还原为排版规范的 Markdown 正文，聚合去重小标题；
4. 单章同步生成产物增强：`start_chapter_generation(sync_execute=True)` 自动解析多段落、小标题与引用并落盘入 `candidate`；
5. 跨章节独立批量生成（`batch_generate_chapters`）：支持指定多章节批量独立生成；落实 PRD §5.7.8 关键红线：未确认方案章节（记入 `failed_chapters`，错误码 `PLAN_NOT_CONFIRMED`）绝对不阻塞已确认章节的独立启动；自动汇总各章任务、指纹与 Token 预算统计；
6. 涉密项目本地模型强门禁：敏感项目拦截云端模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
7. 角色权限拦截（只读角色 403 `FORBIDDEN`）与租户隔离（404 `NOT_FOUND`）；
8. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/chapters/batch-generate`（`include_in_schema=False` 保障 OpenAPI 契约 100% 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 11 passed，联合全量 156 passed 2 skipped）。端到端闭环逻辑通过。

可验证验收：
- [x] 多段落结构化解析：包含显式 `[P1]`~`[Pn]` 标签、小标题与引用的正文精准解析；
- [x] 无标签自适应编号：无标签正文自适应分配 `[P1]`~`[Pn]` 并顺序对齐写作要点小标题；
- [x] 行内引用与防幻觉：白名单内真实引用（`valid=True`）与虚构伪造引用（`valid=False`）精确区分；
- [x] Markdown 回写格式化：结构化段落列表逆向回写标准 Markdown 文本；
- [x] 单章同步生成成果丰富：候选成果自动填充 `paragraphs`、`structured_content`、`scoring_subheadings`；
- [x] 批量生成全确认成功：指定多章节全部确认时批量生成成功并汇总任务、指纹与预算；
- [x] 关键红线未确认不阻塞：未确认章节记录 `PLAN_NOT_CONFIRMED`，绝对不阻塞已确认章节生成；
- [x] 涉密项目本地模型门禁：敏感项目绑定云端模型前置拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
- [x] 角色权限与租户隔离：只读角色拦截 403 `FORBIDDEN`，跨租户项目拦截 404 `NOT_FOUND`；
- [x] HTTP 端点集成：`POST /api/v1/projects/{project_id}/chapters/batch-generate` 端到端调用成功；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_outline_generation_expand.py -v` 执行全过（11 passed）；
- [x] 全量 AI 与 RAG 联合测试回归全绿（156 passed, 2 skipped）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。




<a id="ai-outline-auto-tree-build"></a>

## AI-OUTLINE-AUTO-TREE-BUILD · 招标文件解析驱动的大纲树自动规划构建引擎

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落实招标文件需求矩阵自动分类对齐、两卷多层级大纲树与规范编号（卷/章/节/子节）、评分要点挂接与结构化写作要点生成、条款防编造校验、涉密本地模型门禁与定稿就绪检查 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-OUTLINE-GENERATE-EXPAND](AI-M0.md#ai-outline-generate-expand) |
| PRD / 架构出处 | [PRD v1.8 §5.7.1、§5.7.2](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-OUTLINE-AUTO-TREE-BUILD 交付](../delivery/AI-OUTLINE-AUTO-TREE-BUILD.md) |
| 代码解释 | [AI-OUTLINE-AUTO-TREE-BUILD 代码说明](../code/AI-OUTLINE-AUTO-TREE-BUILD.md) |

范围：在 `backend/bid-core/icg/domain/outline_auto_tree.py`、`outline_plan.py`、`outline_orchestrator.py`、`outline_service.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地招标文件解析驱动的大纲树自动规划构建引擎：
1. 结构化大纲树自动衍生与规范编号：基于解析出的招标文件需求矩阵，自动推导构建两卷官方投标大纲层级结构（第一卷 商务标 / 第二卷 技术标 Level 0 卷、第一章 / 1.0 Level 1 章/编、1.1 / 1.2 Level 2 叶子节、1.1.1 Level 3 子节）；
2. 智能条款分类与两册对齐映射：商务资质/财务审计/同类业绩对齐至商务卷，总体架构/高可用双活/实施交付SLA/安全合规对齐至技术卷，偏离表与应答清单对齐至系统类章节，实现 100% 零未映射条款；
3. 评分要点挂接与结构化编写要点生成：为叶子章节自动挂接真实条款 ID（`bound_requirement_ids` 与 `associated_clause_ids`）、分值（`score`）、评分标准（`scoring_criteria`）、星号条款（★）与废标红线，动态加权计算建议目标字数（`target_length`，800~3000 字），合成标准结构化编写要点（`writing_points`）；
4. 条款防编造防幻觉白名单校验：挂接条款严格核验是否存在于解析矩阵中，虚构条款抛出 422 `INVALID_REQUIREMENT_REFERENCE`；
5. 多租户强隔离与 RBAC 权限门禁：跨租户项目拦截 404 `NOT_FOUND`，系统只读角色与项目只读成员拦截 403 `FORBIDDEN`；
6. 涉密项目本地模型门禁：敏感项目（`sensitive=True`）模型规划硬门禁拦截云端模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
7. 预览与单事务原子持久化双模式：支持 `preview=True` 纯内存推导与 `preview=False` 单事务原子更新章节（`state.chapters`）、回写需求矩阵映射（`requirement["chapter_id"]`）、排序与元数据推进；
8. 大纲定稿锁定前置就绪检查：核验大纲完整性、分册覆盖度、零未映射条款与星号条款合规；
9. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/outline/auto-tree-build`（`include_in_schema=False` 保障 OpenAPI 契约 100% 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 11 passed，回归套件 50 passed，AI 全量 56 passed）。端到端闭环逻辑通过。

可验证验收：
- [x] 多层级大纲树自动推导：卷（Level 0）、章（Level 1）、节（Level 2）标准层级衍生与规范编号；
- [x] 需求矩阵智能分类分册对齐：商务资质、技术架构、实施服务、安全合规、偏离表精准对齐，零未映射条款；
- [x] 评分要点挂接与写作指引合成：真实条款 ID 挂接、分值汇总、星号（★）/废标标记识别与结构化 `writing_points` 组装；
- [x] 条款防编造白名单核验：传入虚构未核实条款 ID 精确拦截 422 `INVALID_REQUIREMENT_REFERENCE`；
- [x] 多租户强隔离门禁：跨公司项目操作精确拦截 404 `NOT_FOUND`；
- [x] RBAC 权限门禁：只读角色与项目只读成员拦截 403 `FORBIDDEN`；
- [x] 涉密项目本地模型门禁：敏感项目调用外部云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`，本地模型放行；
- [x] 预览与单事务原子持久化：`preview=True` 纯内存推导，持久化模式原子落盘章节、矩阵映射与版本自增；
- [x] 大纲定稿就绪诊断检查：零未映射条款、空章节与星号条款合规阻断诊断准确；
- [x] HTTP API 端点集成：`POST /api/v1/projects/{project_id}/outline/auto-tree-build` 端到端调用成功；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_outline_auto_tree_build.py -v` 执行全过（11 passed）；
- [x] 大纲与工作流全套回归测试 `pytest tests/backend/test_outline_*.py ...` 执行全过（50 passed）；
- [x] 全量 AI 核心联合测试回归全绿（56 passed）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。


<a id="ai-outline-score-weight-calc"></a>

## AI-OUTLINE-SCORE-WEIGHT-CALC · 大纲评分项分值权重加权与章节优先级智能排序引擎

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落实基于真实招标文件评分项的分值权重加权算法、星号与废标红线综合优先级加权得分、推荐多章节批量生成执行队列、多租户隔离与涉密本地模型门禁 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-OUTLINE-AUTO-TREE-BUILD](AI-M0.md#ai-outline-auto-tree-build) |
| PRD / 架构出处 | [PRD v1.8 §5.7.1、§5.7.8](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-OUTLINE-SCORE-WEIGHT-CALC 交付](../delivery/AI-OUTLINE-SCORE-WEIGHT-CALC.md) |
| 代码解释 | [AI-OUTLINE-SCORE-WEIGHT-CALC 代码说明](../code/AI-OUTLINE-SCORE-WEIGHT-CALC.md) |

范围：在 `backend/bid-core/icg/domain/outline_auto_tree.py`、`outline_plan.py`、`outline_orchestrator.py`、`outline_service.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地大纲评分项分值权重加权与章节优先级智能排序引擎：
1. 真实评分项分值累加与权重加权算法：提取叶子章节关联的真实招标文件条款评分（`score`），累加计算章节分值 `total_score`，计算章节全标权重比 `score_weight`（0.0 ~ 1.0）与所属分册内权重比 `volume_score_weight`（0.0 ~ 1.0），包含全零分值除零保护；
2. 星号条款（★）与一票否决废标红线综合优先级加权判定：
   - 含一票否决废标条款（`has_disqualified`）：`priority="critical"`，加权附加分 `bonus=100.0`，最高优先级排头；
   - 含★关键必保条款（`has_asterisk`）：`priority="critical"`，加权附加分 `bonus=60.0`，前置重点编写；
   - 高分值项（分值>=15分或占比>=15%）：`priority="high"`，加权附加分 `bonus=30.0`；
   - 中分值项（分值>=5分或占比>=5%）：`priority="medium"`，加权附加分 `bonus=15.0`；
   - 基础支撑项：`priority="low"`，附加分 `bonus=0.0`；
   - 综合优先级分值计算：`priority_score = round(sec_score + bonus, 2)`；
3. 多章节批量生成推荐执行队列（`recommended_writing_order`）：按 `(-priority_score, -total_score, section_number)` 倒序构建推荐编写序列，为后续大纲多章节批量生成提供智能编排驱动；
4. 大纲树构建引擎内建集成与单事务持久化：`AutoTreeBuildEngine.build_tree_structure` 自动集成权重计算，`OutlinePlanService.auto_build_outline_tree` 与 `calculate_outline_score_weights` 将权重与优先级字段持久化至 `workflow["outline_plans"][ch_id]` 与 `workflow["recommended_writing_order"]`；
5. 多租户强隔离与 RBAC 权限门禁：跨租户项目严格抛出 404 `NOT_FOUND`，系统只读角色与项目只读成员拦截 403 `FORBIDDEN`；
6. 涉密项目本地模型门禁：敏感项目硬门禁拦截云端外部模型（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）；
7. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/outline/score-weights` 与 `GET /api/v1/projects/{project_id}/outline/recommended-order`（`include_in_schema=False` 保障 OpenAPI 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 8 passed，回归套件 25 passed，AI 全量 64 passed）。端到端闭环逻辑通过。

可验证验收：
- [x] 分值权重加权算法：精确计算章节全标权重比与分册内权重比，除零边界鲁棒；
- [x] 综合优先级梯度判定：一票否决（bonus 100）、★必保（bonus 60）、高分值（bonus 30）、中分值（bonus 15）及综合优先级分 `priority_score`；
- [x] 推荐编写执行队列生成：按优先级分降序生成推荐编写序列，指导批量生成；
- [x] 防编造与溯源保真：分值严格来源于招标文件真实评分条款，严禁虚构分值；
- [x] 多租户强隔离门禁：跨公司项目精确拦截 404 `NOT_FOUND`；
- [x] RBAC 权限门禁：只读角色与项目只读成员拦截 403 `FORBIDDEN`；
- [x] 涉密项目本地模型门禁：敏感项目调用外部云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
- [x] 大纲方案元数据与工作流原子持久化：权重、优先级、推荐队列原子落盘；
- [x] HTTP API 端点集成：POST /outline/score-weights 与 GET /outline/recommended-order 端到端调用成功；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_outline_score_weight.py -v` 执行全过（8 passed）；
- [x] 全套大纲回归测试 `pytest tests/backend/test_ai_outline_*.py ...` 执行全过（25 passed）；
- [x] 全量 AI 核心联合测试回归全绿（64 passed）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。


<a id="ai-outline-batch-generation-pipeline"></a>

## AI-OUTLINE-BATCH-GENERATION-PIPELINE · 基于优先级推荐队列的大纲多章节批量生成流水线调度引擎

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落地基于优先级推荐队列的大纲多章节批量生成流水线调度引擎，实现并发受控分批切片、废标与星标优先调度、未确认章节隔离跳过、全局 Token 预算聚合与单事务原子落盘 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-OUTLINE-SCORE-WEIGHT-CALC](AI-M0.md#ai-outline-score-weight-calc) |
| PRD / 架构出处 | [PRD v1.8 §5.7.1、§5.7.8](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-OUTLINE-BATCH-GENERATION-PIPELINE 交付](../delivery/AI-OUTLINE-BATCH-GENERATION-PIPELINE.md) |
| 代码解释 | [AI-OUTLINE-BATCH-GENERATION-PIPELINE 代码说明](../code/AI-OUTLINE-BATCH-GENERATION-PIPELINE.md) |

范围：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地基于优先级推荐队列的大纲多章节批量生成流水线调度引擎：
1. 优先级自适应排序：依据前序评分权重与推荐编写序列（`recommended_writing_order`），优先执行 critical 废标红线与★关键必保章节，次之 high 高分核心章节，再次 medium/low；
2. 并发门限受控切片：严格按 `concurrency_limit`（1~5 钳制，默认 2）切分 Stage 批次，防止本地模型瞬时并发导致显存崩溃与 Token 预算透支；
3. PRD §5.7.8 关键红线：未确认章节或单章失败绝不阻塞其他章节调度生成（`skipped_unconfirmed_chapters`，流水线状态 `partial_completed`）；
4. 优先级门限过滤：支持 `priority_threshold`（critical/high/medium/low）门限过滤调度；
5. 全局 Token 消耗与耗时仪表盘：汇聚 `duration_ms`、`token_budget_dashboard`（含 `by_chapter` 细粒度统计）与 `priority_execution_summary`；
6. 单事务原子落盘：执行快照原子写入 `workflow["batch_pipeline_runs"]` 与 `workflow["latest_batch_pipeline_run"]`；
7. 多租户强隔离与 RBAC 权限门禁：跨租户项目严格抛出 404 `NOT_FOUND`，系统只读角色与项目只读成员拦截 403 `FORBIDDEN` / `PROJECT_WRITER_REQUIRED`；
8. 涉密项目本地模型硬门禁：涉密项目企图使用云端外部模型严格拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
9. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/outline/batch-pipeline`（`include_in_schema=False` 保障 OpenAPI 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 9 passed，全量 AI 核心套件 73 passed）。

可验证验收：
- [x] 优先级推荐队列排序：废标红线与★星标必保优先排入前置批次；
- [x] 并发切片门限受控：concurrency_limit 1~5 钳制受控分批；
- [x] PRD §5.7.8 关键红线：未确认章节（PLAN_NOT_CONFIRMED）隔离跳过，绝对不阻塞后续章节生成；
- [x] 优先级门限过滤：priority_threshold 参数精确过滤指定层级章节；
- [x] 全局 Token 预算与耗时统计：duration_ms 与 token_budget_dashboard 准确聚合；
- [x] 多租户强隔离门禁：跨公司项目精确拦截 404 `NOT_FOUND`；
- [x] RBAC 权限门禁：只读角色与项目只读成员拦截 403 `FORBIDDEN`；
- [x] 涉密项目本地模型硬门禁：涉密项目调用外部云端模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
- [x] 单事务原子持久化：batch_pipeline_runs 与 latest_batch_pipeline_run 原子落盘；
- [x] HTTP API 端点集成：POST /outline/batch-pipeline 端到端调用成功；
- [x] 专属自动化测试套件 `pytest tests/backend/test_ai_outline_batch_pipeline.py -v` 执行全过（9 passed）；
- [x] 全量 AI 核心联合测试回归全绿（73 passed）；
- [x] OpenAPI 契约校验 `python backend/bid-core/export_openapi.py --check` 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。


<a id="ai-chapter-auto-validation-gate"></a>

## AI-CHAPTER-AUTO-VALIDATION-GATE · 章节生成产物合规性自动即时质检门禁

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落地章节生成产物自动即时质检门禁引擎，实现生成即质检、R34占位符与客套语阻断、R37负偏离阻断、R24签字盖章槽位核验、证据真实性白名单排查、质量健康度评分与评级梯度量化及批量流水线看板汇聚 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-OUTLINE-BATCH-GENERATION-PIPELINE](AI-M0.md#ai-outline-batch-generation-pipeline) |
| PRD / 架构出处 | [PRD v1.8 §5.7.8、§5.10](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-CHAPTER-AUTO-VALIDATION-GATE 交付](../delivery/AI-CHAPTER-AUTO-VALIDATION-GATE.md) |
| 代码解释 | [AI-CHAPTER-AUTO-VALIDATION-GATE 代码说明](../code/AI-CHAPTER-AUTO-VALIDATION-GATE.md) |

范围：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地章节生成产物合规性自动即时质检门禁引擎：
1. 生成即质检（Validation on Generation）：单章独立生成（`start_chapter_generation`）与多章节批量流水线调度（`schedule_batch_pipeline`）在产出候选正文后自动即时触发多维度合规质量核验；
2. R34 占位符与“待补/待完善”残留排查：扫描未替换的草稿标记（`【待定】`、`【待补】`、`TODO`、`XXXX` 等）与 AI 对话客套语句残留，检出即标定阻断缺陷（`code: PLACEHOLDER_RESIDUAL` / `AI_CONVERSATION_RESIDUAL`）；
3. R37 / R28 负偏离与无法满足排查：排查“不满足”、“负偏离”、“无法提供”、“存在差距”等实质性违规表述，检出即标定阻断缺陷（`code: NEGATIVE_DEVIATION_DETECTED`）；
4. R24 签字盖章槽位合规排查：法定承诺与授权证明章节排查显式“未盖公章”、“未签字”或缺少标准公章与法定代表人签字槽位，检出标定阻断缺陷（`code: MANDATORY_SEAL_SIGNATURE_MISSING`）；
5. CITATION_AUTH 引用白名单真实性核验：校验证据编号 `[证:eid]` 是否在已确认白名单中，识别虚构证据并阻断（`code: FABRICATED_OR_INVALID_EVIDENCE_CITATION`）；未匹配知识库候选切片 `[片:sid]` 标定告警（`code: UNVERIFIED_SNIPPET_CITATION`）；
6. 质量健康度评分（0~100）与评级梯度模型：量化计算 `quality_health_score` 与 `quality_health_rating`（`excellent` / `good` / `warning` / `critical`）；
7. 自适应修复建议清单生成：根据检出缺陷代码智能输出针对性改写建议；
8. 实体与异步进度无缝注入：注入候选草稿（`candidate`）与 `demo_job` 异步任务进度（`result_json`）；
9. 批量流水线全局质量看板聚合：持久化汇聚汇总 `validation_summary`（通过数、失败数、阻断数、平均健康分）；
10. 安全物理隔离硬门禁：涉密项目本地模型硬门禁（403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`）、多租户强隔离（404 `NOT_FOUND`）与只读角色门禁（403 `FORBIDDEN`）；
11. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/chapters/{chapter_id}/validate-candidate`（`include_in_schema=False` 保障 OpenAPI 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 12 passed，全量 AI 核心套件 85 passed）。

可验证验收：
- [x] 清洁合规正文 100% 质检通过，评定 100 分 excellent；
- [x] R34 占位符与 AI 对话客套残留字样精准阻断拦截；
- [x] R37 / R28 负偏离与无法满足声明精准阻断拦截；
- [x] R24 法定承诺章节缺少公章/签字槽位精准阻断拦截；
- [x] CITATION_AUTH 虚构证据编号精准阻断拦截，未匹配知识库切片触发告警；
- [x] 质量健康度评分（0~100）与评级梯度（excellent/good/warning/critical）准确量化；
- [x] 自适应修复建议清单准确生成；
- [x] 单章生成自动注入 candidate 实体元数据与 demo_job result_json；
- [x] 批量流水线 schedule_batch_pipeline 自动聚合 validation_summary 质量仪表盘；
- [x] 独立按需合规质检 validate_chapter_content 调用正常；
- [x] 多租户物理强隔离门禁拦截 404 NOT_FOUND，只读系统角色拦截 403 FORBIDDEN；
- [x] 涉密项目调用外部云端大模型硬拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL；
- [x] HTTP API 端点 POST /chapters/{cid}/validate-candidate 端到端调用成功；
- [x] 专属自动化测试套件 pytest tests/backend/test_ai_chapter_validation_gate.py -v 执行全过（12 passed）；
- [x] 全量 AI 核心联合测试回归全绿（85 passed）；
- [x] OpenAPI 契约校验 python backend/bid-core/export_openapi.py --check 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。


<a id="ai-outline-auto-remediation"></a>

## AI-OUTLINE-AUTO-REMEDIATION · 章节合规质检缺陷自动整改建议与局部智能重写引擎

| 字段 | 内容 |
|---|---|
| 状态 | done |
| 估算 | 落地章节合规质检缺陷自动诊断、结构化整改建议合成、违规段落局部智能重写与原地合规保全、多轮自适应收敛迭代（直至健康分>=90）及单章与批量流水线闭环集成 |
| 关联 Issue | [ISSUE-037](../../issues/ISSUE-037.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-CHAPTER-AUTO-VALIDATION-GATE](AI-M0.md#ai-chapter-auto-validation-gate) |
| PRD / 架构出处 | [PRD v1.8 §5.7.8、§5.10](../reference/product/prd-mvp-v1.8.md)；[APP-M2-T126](APP-M2.md#app-m2-t126) |
| 完成时交付 | [AI-OUTLINE-AUTO-REMEDIATION 交付](../delivery/AI-OUTLINE-AUTO-REMEDIATION.md) |
| 代码解释 | [AI-OUTLINE-AUTO-REMEDIATION 代码说明](../code/AI-OUTLINE-AUTO-REMEDIATION.md) |

范围：在 `backend/bid-core/icg/domain/chapter_generation.py`、`domain.py`、`generation_orchestrator.py` 与 `backend/bid-core/icg/api/workflow.py` 中落地章节合规质检缺陷自动整改建议与局部智能重写引擎：
1. 缺陷自动诊断与整改建议计划合成：实现 `diagnose_paragraph_defects` 与 `synthesize_remediation_plan`，针对 R34（占位符/未替换变量/AI客套语）、R37（负偏离）、R24（签字盖章缺失）、CITATION_AUTH（虚构证据）自动合成明确指令与替换预览；
2. 局部智能重写与原地合规保全：严格执行局部最小改动原则，仅改动检出缺陷的违规段落，合格段落 100% 原样保全，段落 `[P1]`~`[Pn]` 连续编号；
3. 多轮自适应收敛迭代：支持 `max_rounds: int = 3`，迭代至阻断项清零且质量健康分达到 `excellent`（>=90 分），并沉淀 `remediation_history`；
4. 单章生成与批量流水线集成：支持 `auto_remediate=True`，在生成检出缺陷时全自动静默整改闭环，并聚合 `total_remediated_chapters` 至全局质量看板；
5. 涉密本地模型硬门禁：涉密项目（`project.sensitive = True`）企图调用外部云模型拦截 403 `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL`；
6. 多租户强隔离与 RBAC 权限门禁：跨租户拦截 404 `NOT_FOUND`，只读角色拦截 403 `FORBIDDEN`；
7. HTTP API 端点集成：注册 `POST /api/v1/projects/{project_id}/chapters/{chapter_id}/remediate-candidate`（`include_in_schema=False` 保障 OpenAPI 零漂移）。

当前条件：自动化回归测试全绿通过（专属测试 12 passed，全量 AI 核心套件 97 passed）。

可验证验收：
- [x] R34 占位符、未填变量宏与 AI 客套语诊断及整改计划合成通过；
- [x] R37 负偏离声明识别与正向承诺反转映射验证通过；
- [x] R24 法定承诺章节缺少盖章签名槽位诊断与整改指引合成通过；
- [x] CITATION_AUTH 虚构证据识别与白名单过滤通过；
- [x] 局部智能重写：合规段落 100% 原样保全，仅改动违规段落验证通过；
- [x] 多轮自适应收敛迭代：阻断清零且健康分达到 90+ (excellent) 验证通过；
- [x] 法定表单章节末尾标准印章签名块整体自动注入通过；
- [x] 单章生成接入 auto_remediate 闭环自动整改通过；
- [x] 大纲批量生成流水线接入 auto_remediate 并汇聚看板通过；
- [x] 涉密项目本地模型硬门禁（拦截外部云模型，403）通过；
- [x] 多租户隔离（404 NOT_FOUND）与 RBAC 只读角色拦截（403）通过；
- [x] HTTP API 端点 POST /remediate-candidate 端到端契约调用通过；
- [x] 专属自动化测试套件 pytest tests/backend/test_ai_outline_auto_remediation.py -v 执行全过（12 passed）；
- [x] 全量 AI 核心联合测试回归全绿（97 passed）；
- [x] OpenAPI 契约校验 python backend/bid-core/export_openapi.py --check 100% 一致；
- [x] 交付文档、代码说明、任务卡与任务看板同步更新。

已获 QA 签署（D-836 PASS）与 PD 验收（D-837 认可），经人类 PM 正式批准标 done。

> 2026-10-28 回归说明：上表“R37 正向承诺反转”“CITATION_AUTH 白名单替换”及【待补】改写行为经核对违反 PRD v1.8 §1.4 原则 3 与 §5.7.4 第 4 条，登记为 [ISSUE-039](../../issues/ISSUE-039.md)，由 [AI-REMEDIATION-NO-FABRICATION](AI-M0.md#ai-remediation-no-fabrication) 撤回。本卡 done 状态与签署记录保留原文。

<a id="ai-remediation-no-fabrication"></a>

## AI-REMEDIATION-NO-FABRICATION · 章节自动整改不编造（按 PRD §5.7.4 规则编排）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时；删除偏离翻转与空泛占位改写；直接转人工问题不进入自动修正；模型改写安全复核；测试按 PRD 重写 |
| 关联 Issue | [ISSUE-039](../../issues/ISSUE-039.md)、[ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-OUTLINE-AUTO-REMEDIATION](AI-M0.md#ai-outline-auto-remediation) |
| PRD / 架构出处 | [PRD v1.8 §1.4、§5.7.4](../reference/product/prd-mvp-v1.8.md)；[实施澄清 A1/A8](../decisions/2026-10-28-prd-amendments-wave11.md) |
| 完成时交付 | [交付](../delivery/AI-REMEDIATION-NO-FABRICATION.md) |
| 代码解释 | [代码说明](../code/AI-REMEDIATION-NO-FABRICATION.md) |

验收：偏离、无依据【待补】、依据外证据不被自动修正并进入人工处理队列；模型改写带入新数字或新引用被拒；只有可自动修正问题时“问题全部解决”，否则如实“待人工处理”。

<a id="ai-kb-rag-pipeline"></a>

## AI-KB-RAG-PIPELINE · 公司知识库同步与检索接入生产链路

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 8小时；客户端对齐 1.0、对账同步、索引过滤与实时复核检索、各调用方接入、状态接口与面板 |
| 关联 Issue | [ISSUE-043](../../issues/ISSUE-043.md)、[ISSUE-037](../../issues/ISSUE-037.md) |
| 依赖 | [AI-RAGFLOW-KB-SYNC](AI-M0.md#ai-ragflow-kb-sync)、[BE-WORKFLOW-DURABILITY](BE-M0.md#be-workflow-durability) |
| PRD / 架构出处 | [PRD v1.8 §1.4、§5.7](../reference/product/prd-mvp-v1.8.md)；B5/B6 拍板 |
| 完成时交付 | [交付](../delivery/AI-KB-RAG-PIPELINE.md) |
| 代码解释 | [代码说明](../code/AI-KB-RAG-PIPELINE.md) |

验收：只有已确认未过期资料与已发布片段入库；改版、撤销、过期后旧文档不被召回；检索命中按资料实时复核并以 [片:id] 引用、不成为 [证]；片段同步状态与知识库真实结果一致；未配置时不伪造。

<a id="ai-kb-rag-eval"></a>

## AI-KB-RAG-EVAL · 知识库检索质量评测与调参（真实 RAGFlow）

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 3小时；合成金标集、评测脚本、真实实例参数扫描与报告 |
| 关联 Issue | [ISSUE-043](../../issues/ISSUE-043.md) |
| 依赖 | [AI-KB-RAG-PIPELINE](AI-M0.md#ai-kb-rag-pipeline) |
| PRD / 架构出处 | [PRD v1.8 §1.4](../reference/product/prd-mvp-v1.8.md) |
| 完成时交付 | `docs/testing/rag-eval-golden-v1.md` |
| 代码解释 | [代码说明](../code/AI-KB-RAG-PIPELINE.md) |

已完成：`scripts/rag_eval.py`、`tests/rag_eval/golden_v1.json`（离线跑通）。待做：真实 RAGFlow 上扫描 `similarity_threshold` × `keywords_similarity_weight`（及重排模型），以同义改写 recall@3 ≥ 0.8、负例误召回 ≤ 0.25 为初定目标，写回默认参数。阻塞：用户侧隧道 2026-10-28 不可达。

结果（2026-10-28）：内置解析见 [内置解析评测](../testing/rag-eval-golden-v1-builtin.md)，据此默认阈值 0.45、关键词权重 0.3（paraphrase recall@3 0.969，负例误召回在 0.45 下为 0）。ICG 结构化流程见 [流程模式评测](../testing/rag-eval-golden-v1-pipeline.md)：21 篇有 7 篇在 LLM 抽取步骤解析失败，召回 literal 0.667 / paraphrase 0.5，低于内置解析；上线前须换稳定的内网抽取模型复测，否则按公司关闭流程。`scripts/rag_eval.py` 新增 `--dataset-id` 接续已在解析的数据集。

<a id="ai-kb-control-plane"></a>

## AI-KB-CONTROL-PLANE · 知识库管控接口与招投标专用摄入流程

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 8小时；四条 ICG 摄入流程与 DSL 生成、/api/v1/kb-admin 全部管控接口与授权审计、历史投标与证书原件、重建迁移、管理页 |
| 关联 Issue | [ISSUE-043](../../issues/ISSUE-043.md) |
| 依赖 | [AI-KB-RAG-PIPELINE](AI-M0.md#ai-kb-rag-pipeline) |
| PRD / 架构出处 | [技术决定](../decisions/2026-10-28-kb-control-plane-and-pipelines.md) |
| 完成时交付 | [技术决定](../decisions/2026-10-28-kb-control-plane-and-pipelines.md) |
| 代码解释 | [技术决定](../decisions/2026-10-28-kb-control-plane-and-pipelines.md) |

验收：`tests/backend/test_kb_admin.py` 11 项；流程部署与数据集绑定在真实 RAGFlow v1.0.0-rc2 上验证；完整解析待嵌入模型可用。

<a id="ai-tender-structured-extraction"></a>

## AI-TENDER-STRUCTURED-EXTRACTION · 招标条款按章节与条目抽取

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | — |
| PRD / 架构出处 | PRD v1.8 §5.2；[技术决定 §4](../decisions/2026-10-28-kb-control-plane-and-pipelines.md) |
| 完成时交付 | [Wave 12 续自测](../testing/2026-10-28-wave-12b-verification.md) |
| 代码解释 | [Wave 12 续自测](../testing/2026-10-28-wave-12b-verification.md) |

原先每个非空行都成为一条条款；现在按章节树与编号条目抽取，合同条款与格式附件不抽，★/▲/废标条目必抽，评分项带分值。`tests/backend/test_tender_extraction.py` 6 项。下一步：扫描件与 .doc/.xls 招标文件经 RAGFlow DeepDOC（tender 流程）解析。

<a id="fe-kb-business-flows"></a>

## FE-KB-BUSINESS-FLOWS · 知识库接入日常业务页面

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 5小时 |
| 关联 Issue | [ISSUE-043](../../issues/ISSUE-043.md) |
| 依赖 | [AI-KB-CONTROL-PLANE](AI-M0.md#ai-kb-control-plane) |
| PRD / 架构出处 | PRD v1.8 §5.4、§5.7 |
| 完成时交付 | [Wave 12 续自测](../testing/2026-10-28-wave-12b-verification.md) |
| 代码解释 | [Wave 12 续自测](../testing/2026-10-28-wave-12b-verification.md) |

写作输入显示知识库候选（[片:id]、仅参考/可挂接提示）；资料库逐条入库状态与“从证书附件识别”；方案片段新建/保存/发布（含拦截原因）与真实同步；知识库管理页解析进度。e2e `knowledge-flows.spec.ts`。

<a id="ai-tender-deepdoc-parse"></a>

## AI-TENDER-DEEPDOC-PARSE · 扫描件与老格式招标文件经 RAGFlow 解析

| 字段 | 内容 |
|---|---|
| 状态 | in-review |
| 估算 | 4小时 |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 依赖 | [AI-TENDER-STRUCTURED-EXTRACTION](AI-M0.md#ai-tender-structured-extraction) |
| PRD / 架构出处 | PRD v1.8 §5.2；[技术决定 §4](../decisions/2026-10-28-kb-control-plane-and-pipelines.md) |
| 完成时交付 | `docs/delivery/AI-TENDER-DEEPDOC-PARSE.md` |
| 代码解释 | `icg/domain/tender_remote.py` 文件头 |

本地解析报 OCR_REQUIRED / FILE_TYPE_UNSUPPORTED 且格式为 PDF、.doc、.docx、.xls、.xlsx、图片时，上传到本公司 `icg-tender` 数据集（开启 ICG 流程时用“招标文件”流程，否则内置 DeepDOC），在 `ICG_TENDER_REMOTE_WAIT`（默认 60 秒）内轮询；未完成则文件标 `parsing_remote`，再次解析时接着查、不重复上传。完成后按分块位置（页码、纵坐标）还原逐页文字，表格 HTML 展平为“ | ”分隔行，交回原条款与事实抽取，再删除 RAGFlow 临时文档。未连接 RAGFlow、解析失败或未识别出文字时如实报 422。测试 `tests/backend/test_tender_remote_parse.py`（5 项，假 RAGFlow 新增版面位置与分页）；真实 RAGFlow 上的扫描件实测未执行。

