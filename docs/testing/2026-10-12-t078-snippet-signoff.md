为什么有这个文件：记录QA对APP-M2-T078内存片段发布（e6215d4，ISSUE-022）的独立签署。

它解决什么问题：确认进程内发布、拦截原因、ETag/If-Match 与幂等回执仍成立；并写明页面未做，不能标 done。

# APP-M2-T078 内存片段发布 QA签署（REV-M0-T24）

- 被验提交：`e6215d4`（feat: add in-memory snippet publication for T078）；复核基线：`ae38ec3`（含该提交）；关联 APP-M2-T078 / ISSUE-022；数据：仅合成数据。
- 结论：**通过（内存接口切片）**。页面未做，**APP-M2-T078 与本卡均不标 done**，等项目经理设置。

## 验收对照（任务卡 / 交付 / PRD v1.8 §5.5.1、5.5.2）

| 检查 | 结果 | 证据 |
|---|---|---|
| 发布被拦截时列出原因（R31） | 通过 | 被拦截发布返回 200 与五项原因；`records`/`audits` 不变，仍记幂等回执；同键重放带 `Idempotent-Replayed` |
| `kb_sync_status` 显示 | 通过 | 详情含 `kb_sync_status`；两条 GET 返回 ETag（详情 ETag=`draft_revision`）；无 `GET .../sync` |
| 公司隔离 / 版本头 | 通过 | 他司 id 为 404 且不含对方正文；保存与发布 If-Match 核 `draft_revision`（缺 428、不符 409）；同步核 `published_revision` |
| 正例发布与同步失败 | 通过 | 成功才替换 `published_body`、增 `published_revision` 并记审计；未发布或正文含 `[[sync-fail]]` 写成 `failed`，不写成 `synced` |
| 权限反例 | 通过 | 查看人不能发布；缺键不记回执；请求体带 `company_id` 为 422；幂等作用域 `library:{company_id}` |
| 页面读回同源 | 未执行 | 任务卡要求页面读回；本轮仅后台内存接口，交付已载明偏差，故不标 done |
| 不进 DemoState.library | 通过 | 片段走独立字典 `/api/v1/snippet-publications` |

## 套件与 CI

- 聚焦：`pytest tests/backend/test_snippet_publications.py` + 错误体/大纲契约相关项：**18 passed**（Python 3.13.5，`/workspace/qa-venv`）。
- 全量未设库：`pytest tests/backend`：**352 passed，12 skipped**（`ICG_DATABASE_URL` unset）。
- 自 `e6215d4` 至 HEAD：`snippet_publication.py` / `test_snippet_publications.py` **无后续改动**。
- CI [run 38212117391](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38212117391)（head `e6215d4`）：五个 job 全绿（backend / frontend / governance / e2e / backend-mysql）。

## 观察项

- O-1：页面、编辑锁、RAGFlow 同步、跨进程持久化均未做；`[[sync-fail]]` 仅为内存替身。本卡不覆盖这些。
- O-2：APP-M2-T078 / REV-M0-T24 保持 in-review，**不标 done**；T124 仍因 T078 未 done 保持 blocked。
