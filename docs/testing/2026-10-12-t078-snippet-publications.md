为什么有这个文件：记下 T078 内存发布实际跑过的检查和没跑的部分。

它解决什么问题：避免把本地 pytest 通过写成页面已接通、知识库已同步或服务已发布。

# 2026-10-12 片段发布核对

日期：2026-10-12。任务：[APP-M2-T078](../tasks/APP-M2.md#app-m2-t078)。Issue：[ISSUE-022](../../issues/ISSUE-022.md)。

## 命令

`python3 -m pytest tests/backend/test_snippet_publications.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry tests/backend/test_outline_contract_draft.py -q`

结果：16 passed。

`python3 -m pytest tests/backend -q`

结果：346 passed，2 skipped。跳过原因是 `ICG_DATABASE_URL is unset`。没有因此连接 MySQL。

## 已核对的规则

| 规则 | 结果 |
|---|---|
| 服务端分配 id，请求体不能带 `company_id` | 通过。多送 `company_id` 为 422 `VALIDATION_ERROR` |
| 两条 GET 返回 ETag；详情含 `kb_sync_status`；没有 `GET .../sync` | 通过。详情 ETag 等于 `draft_revision` |
| 其他公司的 id 为 404，响应不含对方正文 | 通过 |
| 保存和发布的 If-Match 核对 `draft_revision`；缺少为 428，不符为 409 | 通过。保存不替换 `published_body` |
| 同步的 If-Match 核对 `published_revision` | 通过 |
| 被拦截的发布返回 200 和五项原因，`records` 与 `audits` 不变，但仍记幂等回执 | 通过。同键重放带 `Idempotent-Replayed` |
| 发布成功才替换 `published_body`、增加 `published_revision` 并记审计 | 通过 |
| 同步失败不把状态写成 `synced` | 通过。未发布和正文含 `[[sync-fail]]` 都写成 `failed` |
| 幂等作用域 `library:{company_id}` | 通过。同一把键不能再创建片段 |
| 片段不进 `DemoState.library` | 通过 |
| 查看人不能发布；缺键不记回执 | 通过 |
| 运行中的 OpenAPI 与去掉草案后的 spec 一致 | 通过。新路径已从运行接口导出 |

## 局限

没有浏览器页面，没有编辑锁，没有 RAGFlow。`[[sync-fail]]` 只模拟知识库拒绝。重启后的丢失没有另起进程验证，存储本身是进程内字典。大纲契约测试仍只核对草案，不调用新的大纲路由。
