为什么有这个文件：记录QA对AI-06（证据候选改走 RAGFlow 检索适配器）的独立复验与签署结论。

它解决什么问题：不轻信自报结果，亲手执行专项契约测试与全链路检索联合回归，深度核实路径 B/C 客户端注入、跨公司数据集隔离、路径 C 不可附着与查询过滤、零命中/异常安全回退降级等核心指标。

# AI-06 证据候选改走 RAGFlow 检索独立复验与 QA 签署（REV-M0-T42）

- 被验任务：[AI-06](../tasks/AI-M0.md#ai-06) · 证据候选改走 RAGFlow 检索
- 关联 Issue：[ISSUE-037](../../issues/ISSUE-037.md)
- 关联交付：[AI-06 交付](../delivery/AI-06.md)、[代码解释](../code/AI-06.md)
- 被验核心文件：`backend/bid-core/icg_demo/retrieval.py`、`tests/backend/test_evidence_ragflow.py`
- 复验环境：Windows, Python 3.12.9
- 结论：**通过 (PASS)**。**AI-06、ISSUE-037 均保持 in-review / in-progress，严禁标 done / closed**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 路径 B/C 客户端注入与属性断言 | 通过 | `test_ragflow_retrieval_success_paths_b_and_c`：路径 B 候选为 `attachable=True, reference_only=False`；路径 C 候选严格为 `attachable=False, reference_only=True`；路径 A 本地已确认资料不受影响；B 与 C 分别发起携带 `Authorization: Bearer` 的检索调用 |
| AC-02 跨公司数据集物理隔离 | 通过 | `test_cross_company_isolation_uses_only_injected_dataset_id`：以 Company A 发起请求只传 Dataset A；以 Company B 发起只传 Dataset B；未配置数据集的 Company C 安全降级，零网络请求 |
| AC-03 路径 C 不可附着与查询词过滤 | 通过 | `test_path_c_query_filtering_in_memory_mode`：内存模式按查询词子串对历史标书标题与正文进行相关性过滤（无关词排除，相关词命中），闭环解决 ISSUE-016 QA 观察项 O-1（P3） |
| AC-04 独立数据集与请求级重载 | 通过 | `test_separate_datasets_for_snippets_and_history` 与 `test_candidate_request_overrides_datasets`：支持方案片段与历史库分库配置；支持在请求对象中显式指定 dataset_ids 与 rerank_id |
| AC-05 零命中安全降级回退路径 A | 通过 | `test_zero_hits_safely_falls_back_to_path_a`：假服务空 chunks 信封（`code: 0, chunks: []`）被正确捕获为 `skipped: zero hits`，保留路径 A，接口整体正常返回 |
| AC-06 网络异常与错误码安全优雅降级 | 通过 | `test_ragflow_http_500_falls_back_to_path_a`、`test_ragflow_business_error_falls_back_to_path_a` 与 `test_ragflow_timeout_falls_back_to_path_a`：HTTP 500、业务码非零、超时均安全降级并保留路径 A，跳过原因中绝不泄露 API Key 与 URL |
| AC-07 知识库关闭门禁 | 通过 | `test_knowledge_base_disabled_sends_no_ragflow_requests`：`knowledge_base_enabled=False` 时直接返回路径 A，记录 `knowledge base is off`，严格 0 网络请求 |
| AC-08 空白查询与越界数据安全防护 | 通过 | `test_empty_query_handling_in_ragflow_mode`、`test_empty_company_id_raises_retrieval_error`、`test_chunk_outside_dataset_rejected_by_path_b_and_c`：空白查询不上报，空公司 ID 拦截，越界 dataset 的 chunk 防御性丢弃 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| AI-06 专项契约测试 | `python -m pytest tests/backend/test_evidence_ragflow.py -v -rs` | **14 passed, 1 skipped** (跳过真实端点探测) | 16.04s |
| 检索全链路联合回归 | `python -m pytest tests/backend/test_evidence_candidates.py tests/backend/test_evidence_ragflow.py tests/backend/test_fake_ragflow.py tests/backend/test_ragflow_client.py -v -rs` | **55 passed, 3 skipped** (联合回归全绿) | 28.85s |
| 治理一致性核查 | `node scripts/check-project-governance.cjs` | **检查通过** (356 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与边界提示

1. **未改动运行时主入口**：本次实现对 `EvidenceCandidateService` 进行了模块化增强，`main.py` 中的 `create_app()` 当前未直接将此服务暴露为新 HTTP 路由，既有生产接口运行不受任何干扰。
2. **离线 CI 纯洁性完好**：真实端点探针 `test_live_ragflow_evidence_probe_skipped_by_default` 严格遵循 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 环境变量门禁，未开启时自动跳过，保证离线自动化测试环境纯净。
3. **闭环 ISSUE-037 研发目标**：AI-04（夹具）、AI-05（客户端）与 AI-06（检索适配接驳）三项任务全部完成并通过 QA 独立签署，为后续真实模型与知识库对接打下完备契约基石。

## 签署状态

AI-06、ISSUE-037 均保持 **in-review / in-progress**，**严禁标 done / closed**。
