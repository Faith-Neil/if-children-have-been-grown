为什么有这个文件：记录QA对AI-04（ISSUE-037 假 RAGFlow 检索端点）的独立复验与全量回归签署。

它解决什么问题：相对开发人员自测，亲手独立复跑并确认假 RAGFlow 服务对 Authorization、base_url、成功 chunks、空 chunks、超时与错误码的覆盖完整性，核查全量后台、实时会话与前端测试全绿。

# AI-04 假 RAGFlow 夹具独立复验与 QA 全回归签署（REV-M0-T37）

- 被验 tip：`49bc6f7`（`test: add ISSUE-037 fake RAGFlow fixture for AI-04`）。
- 复验环境：Windows, Python 3.12.9, Node v24.18.0, pnpm v11.20.0; 未设 `ICG_DATABASE_URL` / `ICG_REQUIRE_MYSQL`；真实 RAGFlow 默认跳过。
- 结论：**通过 (PASS)**。**AI-04、ISSUE-037 及 REV-M0-T37 均保持 in-review / in-progress，严禁标 done / closed**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 请求头与基址记录 | 通过 | `test_success_records_bearer_and_effective_base_url`：核验 `call.header("authorization") == "Bearer synthetic-ragflow-key"`；`call.base_url == fake_ragflow.base_url`；`call.method == "POST"`；正文携带 `dataset_ids` 与 `rerank_id` |
| AC-02 Gateway 前缀保留 | 通过 | `test_gateway_prefix_stays_on_recorded_base_url`：基址带 `/gateway` 前缀时，记录的 `base_url` 与 `path` 完整保留该前缀 |
| AC-03 空 chunks 官方信封 | 通过 | `test_empty_chunks_mode_is_code_zero_with_no_chunks`：返回 HTTP 200，`code: 0`，`chunks: []`，`total: 0`；零命中在夹具层面不伪造为错误 |
| AC-04 业务非零错误码 | 通过 | `test_business_error_uses_nonzero_code`：返回 HTTP 200，`code: 102`，`message: "\`dataset_ids\` is required."` |
| AC-05 HTTP 异常状态码 | 通过 | `test_http_error_mode_returns_500`：返回 HTTP 500，`{"message": "synthetic http error"}`，记录请求头中仍有 Authorization |
| AC-06 系统健康检查接口 | 通过 | `test_healthz_returns_documented_ok_body`：`GET /api/v1/system/healthz` 返回 HTTP 200，各组件状态为 `ok` |
| AC-07 未知路径 404 | 通过 | `test_unknown_path_is_404`：非契约路径（如 `/v1/system/healthz`）返回 HTTP 404，`{"message": "not found"}` |
| AC-08 超时挂起与释放 | 通过 | `test_timeout_mode_holds_until_released`：启用 `hold_responses()` 后超时客户端抛出超时异常，释放后恢复正常响应 |
| AC-09 真实服务环境变量门禁 | 通过 | `test_real_ragflow_skip_reason_requires_exact_one`：严格要求 `ICG_RUN_REAL_RAGFLOW_TESTS=1`，其余值均正确生成跳过原因 |
| AC-10 真实服务安全跳过 | 通过 | `test_real_ragflow_health_when_opted_in`：未显式开启时，安全跳过，绝不偷偷访问外部网络 |

## 独立全量回归复跑实测数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| AI-04 假服务专项 | `python -m pytest tests/backend/test_fake_ragflow.py -v -rs` | **9 passed, 1 skipped** | 4.89s |
| 后台全量 Pytest | `python -m pytest tests/backend -q --tb=line` | **395 passed, 14 skipped, 32 warnings** | 257.36s (4分17秒) |
| 会话实时脚本 | `python tests/backend/session_live_http.py` | **15 passed, 0 failed** (TOTAL 15 PASS 15) | 3.2s |
| 导出与版式冒烟 | `python backend/bid-core/smoke_t06.py` | **passed: true** (E1-E7 全部通过) | 5.1s |
| 前端 TypeScript 与构建 | `tsc -b && vite build` (frontend/web) | **Typecheck & Vite build passed** | ~4s |
| 前端全量单测 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **113 passed, 0 failed** | 1.1s |
| CommonJS 治理与原型 | `node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs` | **35 passed, 0 failed** | 46.7s |
| 错误码与幂等 live HTTP | `python tests/backend/qa_error_idempotency_live_http.py` | **49/49 passed** | 3.8s |
| 项目治理一致性检查 | `node scripts/check-project-governance.cjs` | **通过** (340 份 Markdown、397 项任务、37 项 Issue) | 0.8s |

## 观察项与风险提示

- O-1：**真实端点绝不连通**：假服务仅监听 `127.0.0.1` 随机临时端口。未配置 `ICG_RUN_REAL_RAGFLOW_TESTS=1` 时，外部真实知识库访问被安全阻断跳过，符合离线 CI 原则。
- O-2：**产品代码未修改**：本次提交 `49bc6f7` 仅新增了测试夹具 `tests/backend/fake_ragflow.py` 与测试用例 `tests/backend/test_fake_ragflow.py`，未改动 `backend/bid-core` 下的任何运行时业务代码，未改动 OpenAPI 规范。
- O-3：**后续接线边界明确**：空 chunks 在假服务中返回 `code: 0`。真正的“零命中记为跳过，不当成成功候选”属于后续 AI-05（检索客户端）与 AI-06（证据候选路由）的职责范围。
- O-4：**工作区并发准备提示**：复验期间检测到工作区存在未入库的 `ragflow_client.py` 初始草稿文件，但这不影响 tip `49bc6f7` 的纯洁性与独立复验结论。后续 AI-05 开工与签署需由独立卡片承接。

## 状态

AI-04、ISSUE-037、REV-M0-T37 均保持 **in-review / in-progress**，**严禁标 done / closed**。
