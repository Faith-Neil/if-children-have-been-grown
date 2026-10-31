为什么有这个文件：记录 APP-M2-T118（三路证据候选）与 APP-M2-T136（异常中断与重试）的验证方式、结果与局限。

它解决什么问题：说明本机跑了什么、哪些只能在 CI 运行，防止把未运行的验证写成通过。

# WP-5 第一批：三路证据候选与循环异常重试验证（2026-11-01）

## 环境
本机无网络，没有 fastapi、pydantic、pytest、pnpm；只能运行 Node 单测、`py_compile` 与治理检查。

## 结果
| 验证 | 命令 / 位置 | 关联任务卡 | 结果 |
|---|---|---|---|
| 新增前端单测 | `cd frontend/web && node --test --experimental-strip-types tests/unit/chapter-loop-core.test.mjs tests/unit/matrix-core.test.mjs` | T118、T136 | 通过（中断标签与重试文案、三路分组、可选规则、知识库状态文案） |
| 前端全量单测 | `cd frontend/web && node --test --experimental-strip-types tests/unit/*.test.mjs` | T118、T136 | 394 通过、4 失败；失败的 4 项（editor-deep-linkage、project-volumes、responsive-layout、volume-finalize-glue）暂存本批改动后同样失败，为改动前就存在的失败 |
| 后端语法 | `python3 -m py_compile` 逐个改动文件 | T118、T136 | 通过（仅语法，不是运行） |
| 项目治理检查 | `node scripts/check-project-governance.cjs` | 全部 | 通过 |
| 后端用例 | `tests/backend/test_human_queue.py`（新增 4 项）、`tests/backend/test_matrix.py`（新增 5 项） | T136、T118 | 未执行（本机无 pytest），由 CI 执行 |
| 类型检查与构建 | `pnpm` 的 tsc 与 vite 构建 | T118、T136 | 未执行，由 CI 执行 |
| 端到端 | `frontend/web/e2e/matrix.spec.ts`（扩展三组标题断言） | T118 | 未执行，由 CI 的 Playwright 执行 |
| 端到端（T136） | 无 | T136 | 未写：浏览器里无法确定性触发循环异常 |
| openapi | `spec/openapi/demo-v1.json` | T118、T136 | 未手改；新增 `listEvidenceCandidates`，`recheckChapter` 响应新增 `interrupted`、`error`，由 CI 重新导出 |

## 局限
- 后端用例从未运行过，可能有只有 pytest 才能发现的问题（例如知识库对象 monkeypatch 的位置）；CI 失败时以 CI 日志为准修正。
- 未连接真实 RAGFlow，也未调用真实模型；循环中断由测试注入异常触发，不代表真实模型故障的表现。
- 已并入条款的候选查询、生成后循环中断记录没有单独用例。
