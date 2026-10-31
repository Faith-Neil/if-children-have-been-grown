为什么有这个文件：记录 WP-4 前端（APP-M2-T101、T102、T107、T109、T110）的验证方式、结果与局限。

它解决什么问题：说明本机跑了什么、哪些只能在 CI 运行，防止把未运行的验证写成通过。

# WP-4 解析后处理前端验证（2026-10-31）

## 环境
本机无网络，没有 fastapi、pydantic、pytest、pnpm；只能运行 Node 单测、`py_compile` 与治理检查。

## 结果
| 验证 | 命令 / 位置 | 结果 |
|---|---|---|
| 新增前端单测 | `cd frontend/web && node --test tests/unit/parse-postprocess-core.test.mjs` | 6 项通过 |
| 前端全量单测 | `cd frontend/web && node --test tests/*.test.mjs tests/**/*.test.mjs` | 552 通过、4 失败；失败的 4 项（editor-deep-linkage、project-volumes、responsive-layout、volume-finalize-glue）为改动前就存在的失败，与本次无关 |
| 页面文件语法 | TypeScript `transpileModule` 逐文件检查 `ConflictCards`、`TenderTab`、`ParseTab`、`MergeSuggestionsDrawer`、`AddendumDiffDrawer` | 无语法诊断（不是类型检查） |
| 项目治理检查 | `node scripts/check-project-governance.cjs` | 通过（701 份 Markdown、455 项任务、46 项 Issue） |
| 后端用例 | `tests/backend/test_parse_decisions.py`、`test_parse_postprocess.py`、`test_tender_files.py` | 未执行（本机无 pytest），由 CI 执行 |
| 类型检查与构建 | `pnpm` 的 tsc 与 vite 构建 | 未执行，由 CI 执行 |
| 端到端 | `frontend/web/e2e/parse-postprocess.spec.ts`（2 项） | 未执行，由 CI 的 Playwright 执行 |

## 局限
- 未连接真实 RAGFlow，也未调用真实模型，换服务重试、扫描件解析与相似度合并没有实跑。
- e2e 用合成文本文件，冲突卡只在后台产生冲突时检查并列取值与理由校验；没有强制构造冲突，因此“选定一方”的完整流程没有浏览器证据。
- 页面没有做类型检查，可能存在仅 tsc 才能发现的类型错误，以 CI 结果为准。
