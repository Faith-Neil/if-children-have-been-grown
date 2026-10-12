为什么有这个文件：记录请求层提交复核时核对了哪些基线，以及哪些句子故意留着。

它解决什么问题：避免为了对齐计数去改仍写着「尚未完成」的产品基线。

# APP-M2-T002 同步

日期 2026-10-12。治理块仍为 g1.1 / 2026-10-11 / ISSUE-007，与 [WORKFLOW](WORKFLOW.md) 一致。APP-M2-T002 与 ISSUE-009 为 in-review。T001 与 ISSUE-014 仍为 in-review。不标 done 或 closed。

本轮只收窄请求层重试，不改任务计数。看板是 362 项：26 done、8 in-review、7 in-progress、268 planned、49 blocked、4 ready。三份基线仍写 7 in-review、50 blocked，那是 ISSUE-010 留下的句子，本轮不改。APP-M2 其余 255 张 planned。AI-02 与 APP-M2-T008 保持 done。AI-01 为 in-review，ISSUE-010 已 closed。BE-M0-T02 与 BE-M0-T03 保持 done。ISSUE-005 保持 in-progress。ISSUE-011 与 ISSUE-012 保持 closed。ISSUE-018、ISSUE-021、ISSUE-022、ISSUE-023、ISSUE-025、ISSUE-026、ISSUE-028、ISSUE-029 保持原状态。APP-M2-T002、ISSUE-009 与 ISSUE-014 保持 in-review。

| 对象 | 实际处理 |
|---|---|
| PRD | 本轮无正文修改。第19行已是「项目共362项：26done、7in-review、7in-progress、268planned、50blocked、4ready。APP-M2中T001与T002为 in-review，T008为 done，T124为 blocked，其余255卡planned」。第21行仍写「整个T001、OIDC和完整资料库仍未完成」 |
| ROADMAP | 本轮无正文修改。第17行已是「当前共362项任务，26done、7in-review、7in-progress、268planned、50blocked、4ready」，并写明 T001 与 T002 为 in-review。第19行仍写「整卡继续in-progress。接下来补实际ProLayout、浏览器路由/返回和全页未保存保护」 |
| ARCHITECTURE | 无正文修改。第21行仍写「布局、浏览器路由和全页离开保护继续本卡」 |
| PROJECT_BRIEF | 本轮无正文修改。第30行已是「当前共362项：26done、7in-review、7in-progress、268planned、50blocked、4ready」。第68行仍写「整卡仍进行中：接下来补实际布局组件、浏览器地址/返回与全页离开保护」 |
| Issue 看板/详情 | ISSUE-009 的请求层段落改为 `MODEL_UNAVAILABLE` 不重试并立刻显示追踪号，状态仍 in-review。看板不改状态 |
| TASK_BOARD | 不改。T002 仍为 in-review。开篇是 26 done、8 in-review、49 blocked |
| PROJECT_STATUS | 补上 `MODEL_UNAVAILABLE` 的 502 不自动重试，并保留向量库已定为 RAGFlow。计数不改 |
| DOCUMENT_INDEX | 更新 D-084、D-141、D-277～D-280 的说明，并加一条变更记录。不新增编号 |
| WORKFLOW | 无规则变化，治理块不升版 |
| OpenAPI | 不改。`x-idempotency.retry` 仍写重试全部 502。客户端按项目经理决定，只重试没有统一错误体的 502 |
| 参考原文 | 不改 `docs/reference/` |
| 后台 | 不改 `backend/` 与 `tests/backend/` |

PR #3 仍待合入。本轮不新建 PR，不合并，不发布。
