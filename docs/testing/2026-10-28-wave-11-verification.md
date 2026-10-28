为什么有这个文件：记录 Wave 11 开发自测的实际命令、结果与未覆盖范围。

它解决什么问题：让 QA 独立复测时能对照同一组命令，并看清哪些环境本轮没有执行。

# Wave 11 开发自测记录（2026-10-28）

- 分支 `feat/wave-11-main-path`；提交 `1758920`、`06f107d`、`2c8d51c` 及本记录所在的文档提交；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)
- 环境：Linux 沙箱，Python 3.11.15（CI 为 3.13），Node 22.23.4（CI 为 24），pnpm 11.20.0；无 MySQL、无内网模型与 RAGFlow
- 性质：开发自测，不是 QA 签署

## 结果

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `python -m pytest tests/backend -q` | 871 passed、44 skipped（mysql 标记与真实服务门控用例跳过）。基线 tip `4985a9d` 为 849 passed、1 failed（`test_workflow_service_delegation`） |
| Wave 11 专项 | `test_human_queue.py`、`test_volume_cross_review.py`、`test_parse_omissions.py`、`test_ai_outline_auto_remediation.py`、`test_volume_finalize_gate.py`、`test_submission_finalize_gate.py` | 11 + 5 + 4 + 14 + 10 + 1 项全部通过 |
| 会话实时 HTTP | `python tests/backend/session_live_http.py` | 15/15 |
| 错误体与幂等实时 HTTP | `python tests/backend/qa_error_idempotency_live_http.py` | 49/49 |
| T06 贯通冒烟 | `python smoke_t06.py`（`backend/bid-core`） | passed |
| OpenAPI 一致性 | `python backend/bid-core/export_openapi.py --check` | 一致；新增 10 条路径、23 个结构，`V1Error` 枚举 161 个错误码 |
| 前端单测 | `pnpm --dir frontend/web test` | 289 pass、0 fail（新增 `main-path-core.test.mjs` 8 项） |
| 前端类型 / 构建 | `pnpm --dir frontend/web lint`、`build` | 0 error；构建成功 |
| 治理回归 | `node --test tests/governance/*.test.cjs tests/prototype/*.test.cjs tests/workspace-sync/*.test.cjs tests/backend/demo-page.test.cjs` | 35 pass |
| CI 汇总（`2c8d51c`） | offline-check | backend、backend-mysql、frontend、governance 通过；e2e 15 passed、1 failed（`evidence-drawer.spec.ts`，基线同样失败）；[CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468) |
| 浏览器 e2e | `VITE_DEMO=1 pnpm --dir frontend/web e2e` | 本机：`app-shell.spec.ts` 13/13 通过（含修复后的 1280 溢出用例）；`evidence-drawer.spec.ts` 1 项失败，与基线相同，见 [ISSUE-042](../../issues/ISSUE-042.md) |
| MySQL 作业 | CI `backend-mysql` | `06f107d` 首次运行 36 passed、2 failed（表清单未含新表）；`2c8d51c` 修正后全部通过（[CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468)） |

## 未执行或受限

- 关演示（`VITE_DEMO=0`）+ `ICG_REQUIRE_MYSQL=1` 的人工全链路冒烟：本机无 MySQL，未执行。即使执行，也受 [ISSUE-041](../../issues/ISSUE-041.md) 限制（工作流主体不落盘）。
- 真实内网模型与 RAGFlow：未连接；整改循环的模型改写只用测试替身验证安全复核。
- 截图留证：未做。
