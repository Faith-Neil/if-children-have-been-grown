为什么有这个文件：说明片段发布实际怎么从请求走到内存字典。

它解决什么问题：避免只看到路由路径，却不知道版本、拦截和回执分别写在哪里。

# APP-M2-T078：代码解释

- 对应任务、Issue、交付文档：APP-M2-T078，[ISSUE-022](../../issues/ISSUE-022.md)，[交付](../delivery/APP-M2-T078.md)。
- 日期、实际代码路径、提交 / PR：2026-10-12。`backend/bid-core/icg_demo/snippet_publication.py`。PR 未创建。

## 改了什么以及为什么

片段草稿、已发布正文、修订和同步状态放在 `MemorySnippetPublicationStore` 自己的字典里。`Repository.read`、`Repository.transaction` 和 `DemoState` 的定义没有改。幂等回执仍写入既有的 `workflow_receipts`，作用域是 `library:{company_id}`，这样和公司资料共用同一把键。

## 入口和调用顺序

`create_app` 调用 `include_snippet_routes`。公司 id 只取登录用户，请求体多送 `company_id` 会得到 422 `VALIDATION_ERROR`。

1. 创建：`POST /api/v1/snippet-publications`。服务端用 `new_id("snippet")` 分配 id。不核对 If-Match。
2. 列表和详情：两条 GET 都返回 ETag。详情的 ETag 是 `draft_revision`，供随后保存和发布的 If-Match 使用。列表的 ETag 是本公司列表的指纹。详情里的 `kb_sync_status` 就是同步状态，没有 `GET .../sync`。
3. 保存草稿：`PUT` 的 If-Match 必须等于 `draft_revision`。只改草稿字段并加一，不替换 `published_body`。
4. 发布：`POST .../publish` 的 If-Match 也核对 `draft_revision`。
5. 同步：`POST .../sync` 的 If-Match 核对 `published_revision`。

写操作先要编写人或项目经理角色，再要合法的 `Idempotency-Key`，然后才核对版本。缺少键是 428 `IDEMPOTENCY_KEY_REQUIRED`。缺少 If-Match 是 428 `IF_MATCH_REQUIRED`。版本不符是 409 `VERSION_CONFLICT`。查看人写操作是 403 `FORBIDDEN`。其他公司的 id 是 404 `NOT_FOUND`，响应里没有对方正文。

## 数据与状态

`records` 保存字段。`audits` 只追加成功的发布和同步。进程内有效，重启丢失。知识库没有连接。正文里的 `[[sync-fail]]` 让同步失败，状态写成 `failed`，不会写成 `synced`。

发布通过时，`published_body` 换成当前草稿，`published_revision` 加一，`kb_sync_status` 写成 `unsynced`，并记一条审计。

## 关键判断与异常

发布前在存储内部检查五项：没有来源组却提到报告、承诺旁边有固定数字、未声明的 `{{变量}}`、空正文或引用了尚未发布的本公司片段、引用了其他公司或不存在的片段。任一项不通过都返回 200，`blocked` 为 true，`reasons` 列出原因。这次调用不改 `records` 和 `audits`。因为它是 200，幂等层仍把这次结果记成回执。同键同指纹重放这一次 200，并带 `Idempotent-Replayed: true`。同键不同指纹是 409 `IDEMPOTENCY_CONFLICT`。失败不记回执。

## 验证与限制

核对记录在 [2026-10-12 片段发布](../testing/2026-10-12-t078-snippet-publications.md)。没有页面，没有 MySQL，没有真实知识库。`generation_context.py` 没有改，模型输入仍不读这些片段。项目经理确认内存发布层为 done（QA 19c4862，PM 17:20 确认）。页面未做，不挡住 done。本说明不改行为。
