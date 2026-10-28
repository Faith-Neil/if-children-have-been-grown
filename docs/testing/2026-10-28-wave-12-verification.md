为什么有这个文件：记录 Wave 12（持久化与知识库）开发自测的命令与结果。

它解决什么问题：让 QA 复跑时知道跑了什么、在哪跑、哪些没跑；本记录不是 QA 签署。

# Wave 12 开发自测记录（2026-10-28）

环境：沙箱，Python 3.11，MySQL 8.4.13（沙箱内本地安装），Node + pnpm 11.20.0，Playwright Chromium。分支 `feat/wave-11-main-path`。

| 检查 | 命令 | 结果 |
|---|---|---|
| 后端全量（内存） | `python -m pytest tests/backend -q` | 879 passed、46 skipped（提交 a6643f2 前） |
| MySQL 标记用例 | `alembic upgrade head && pytest -m mysql tests/backend` | 40 passed |
| 知识库用例（内存 / MySQL） | `pytest tests/backend/test_knowledge_base.py` | 13 passed、1 skipped（真实联调）/ 同 |
| OpenAPI 契约 | `python backend/bid-core/export_openapi.py --check` | 一致 |
| 前端单测 / lint / build | `pnpm test`、`pnpm lint`、`pnpm build` | 289 pass；通过；通过 |
| e2e | `pnpm e2e` | 15 passed、1 failed（`evidence-drawer.spec.ts`，既有 ISSUE-042） |
| 治理检查 | `node scripts/check-project-governance.cjs` | 通过 |
| 评测脚本（离线假服务） | `python scripts/rag_eval.py` | 跑通；假服务按字面二元组打分，数值不代表真实质量 |
| 真实 RAGFlow 评测 | `python scripts/rag_eval.py --live --report ...` | **未执行**：隧道返回 Cloudflare 1033 |

已知：在 MySQL 上跑全量后端用例时，约 50 项因共享库数据互相影响失败（基线同样失败），CI 只跑 `-m mysql`。
