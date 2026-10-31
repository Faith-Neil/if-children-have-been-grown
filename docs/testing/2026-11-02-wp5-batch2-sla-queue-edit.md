为什么有这个文件：记录 APP-M2-T134（队列单段编辑）与 APP-M2-T122（需复核传播）及 T119 判定汇总的验证方式、结果与局限。

它解决什么问题：说明本机跑了什么、哪些只能在 CI 运行，防止把未运行的验证写成通过。

# WP-5 第二批：队列单段编辑与服务承诺需复核传播验证（2026-11-02）

## 环境
本机无网络，没有 fastapi、pydantic、pytest、pnpm；只能运行 Node 单测、`py_compile` 与治理检查。

## 结果
| 验证 | 命令 / 位置 | 关联任务卡 | 结果 |
|---|---|---|---|
| 新增前端单测 | `cd frontend/web && node --test --experimental-strip-types tests/unit/main-path-core.test.mjs tests/unit/sla-propagation.test.mjs` | T134、T122 | 通过（预检与请求体、接线、传播文案与提醒级别） |
| 前端全量单测 | `cd frontend/web && node --test --experimental-strip-types tests/unit/*.test.mjs` | T134、T122 | 400 项中 396 通过、4 失败；失败项为已知预存在失败（editor-deep-linkage、project-volumes、responsive-layout、volume-finalize-glue） |
| 后端语法 | `python3 -m py_compile` 逐个改动文件 | T134、T122 | 通过（仅语法，不是运行） |
| 项目治理检查 | `node scripts/check-project-governance.cjs` | 全部 | 通过 |
| 后端用例 | `tests/backend/test_human_queue.py`（新增 5 项，改 2 处断言）、`tests/backend/test_sla_propagation.py`（新增 7 项） | T134、T122 | 未执行（本机无 pytest），由 CI 执行 |
| 类型检查与构建 | `pnpm` 的 tsc 与 vite 构建 | T134、T122 | 未执行，由 CI 执行 |
| 端到端 | `frontend/web/e2e/queue-paragraph-edit.spec.ts`、`sla-propagation.spec.ts` | T134、T122 | 未执行，由 CI 的 Playwright 执行 |
| openapi | `spec/openapi/demo-v1.json` | T134、T122 | 未手改；新增 `editHumanIssueParagraph`、`getSlaPropagation`，`listHumanQueue` 的 `permissions.edit`、`paragraph_text`、`chapter_revision` 由 CI 重新导出；`test_operation_ids`、`test_v1_lease` 等在同步前会失败 |

## 局限
- 后端与 e2e 用例从未运行过，可能有只有 pytest、Playwright 才能发现的问题（例如固定数据下问题所在段落序号、`quote` 前缀匹配）；CI 失败时以 CI 日志为准修正。
- 没有调用真实模型或真实 RAGFlow；单段编辑内容完全来自人工输入。
- T119 的故障等级、服务时段三方值模型未做；T120 导出本身未改；T211～T213 未动。
