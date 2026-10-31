为什么有这个文件：记录 APP-M2-T097～T100（项目状态、倒计时与设置）的验证方式、结果与局限。

它解决什么问题：说明本机跑了什么、哪些只能在 CI 运行，防止把未运行的验证写成通过。

# 项目状态、倒计时与设置验证（2026-10-31）

## 环境
本机无网络，没有 fastapi、pydantic、pytest、pnpm；只能运行 Node 单测、`py_compile` 与治理检查。

## 结果
| 验证 | 命令 / 位置 | 关联任务卡 | 结果 |
|---|---|---|---|
| 新增前端单测 | `cd frontend/web && node --test tests/unit/project-settings-core.test.mjs` | T097～T100 | 通过（倒计时 3 天边界、页签权限、状态按钮、人工修改标记、合作方、规则覆盖、分册设置、完整值、占用提示） |
| 前端全量单测 | `cd frontend/web && node --test tests/*.test.mjs tests/**/*.test.mjs` | T097～T100 | 560 通过、4 失败；失败的 4 项（editor-deep-linkage、project-volumes、responsive-layout、volume-finalize-glue）为改动前就存在的失败 |
| 后端语法 | `python3 -m py_compile` 逐个改动文件 | T097～T100 | 通过（仅语法，不是运行） |
| 项目治理检查 | `node scripts/check-project-governance.cjs` | 全部 | 通过 |
| 后端用例 | `tests/backend/test_project_status_settings.py`（14 项） | T097～T100 | 未执行（本机无 pytest），由 CI 执行 |
| 类型检查与构建 | `pnpm` 的 tsc 与 vite 构建 | T097～T100 | 未执行，由 CI 执行 |
| 端到端 | `frontend/web/e2e/project-status-settings.spec.ts` | T097、T098 | 未执行，由 CI 的 Playwright 执行 |
| openapi | `spec/openapi/demo-v1.json` | T097～T100 | 未手改；新增接口 `getProjectSettings`、`transitionProjectStatus`、`updateRuleOverrides`、`updateVolumeSettings`、`updateSubmitFullValue` 由 CI 重新导出 |

## 局限
- 后端用例从未运行过，可能有只有 pytest 才能发现的问题；CI 失败时以 CI 日志为准修正。
- 未连接真实 RAGFlow，也未调用真实模型；递交版导出走合成数据。
- 规则覆盖、分册格式（除递交文件名）、完整值类别只保存、不生效，见各卡交付文档。
