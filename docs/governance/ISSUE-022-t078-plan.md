为什么有这个文件：把 APP-M2-T078 的内存实现范围写清楚，供后台对齐后再写代码。

它解决什么问题：避免把片段发布状态塞进现有 Repository 的整包读写，和即将按聚合拆分的 ISSUE-018 撞在一起。

# APP-M2-T078 内存方案（只规划，未实现）

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md)。状态：计划，未写代码。T078 仍是 planned。[ISSUE-018](../../issues/ISSUE-018.md) 已登记 MySQL 8 方案，状态 in-review，本轮不实施。

## 不改的文件

这些文件在实现 T078 时也不改 Repository 的读和写：

| 文件 | 保持不动的部分 |
|---|---|
| `backend/bid-core/icg_demo/ports.py` | `Repository.read` 与 `Repository.transaction` 的签名和语义。不把片段方法加进这个 Protocol |
| `backend/bid-core/icg_demo/adapters.py` | 现有内存仓库的 `read` 与 `transaction`。不在整包 `DemoState` 提交里写片段 |
| `backend/bid-core/icg_demo/domain.py` | `DemoState` 不增加片段、发布版本或 `kb_sync_status` 字段。现有 `library` 仍只服务已经落地的资料记录 |

原因：`Repository.read` 返回整份 `DemoState`，`transaction` 提交整份副本。[持久化方案](../architecture/mysql-8-persistence-plan.md) 第 7 节要先把这种整包访问收成按聚合的窄接口，再谈 MySQL。片段状态如果先写进整包，拆分时还要再拆出来。因此它从现在起就放在自己的存储里，不变成 `DemoState` 的新字段，也不给 `Repository` 增加读写方法。

## 实现时要新增的文件

| 文件 | 作用 |
|---|---|
| `backend/bid-core/icg_demo/snippet_publication.py` | 新的内存存储。独立对象，不经过 `Repository.read` / `transaction` |

这个对象自己持有字典。进程内有效，重启丢失，仍受现有单进程限制。ISSUE-018 落地后，它可以作为片段这个聚合的访问对象，而不用改原来的整包仓库。

## 实现时要改、但只做接入的文件

| 文件 | 改什么 | 不改什么 |
|---|---|---|
| `backend/bid-core/icg_demo/main.py` | 创建独立存储并挂到应用；增加下面的路由，路由直接调用该存储 | 不把片段写入 `repository.transaction` |
| `backend/bid-core/icg_demo/workflow_schemas.py` | 只增加请求和响应模型 | 不在这里保存状态 |
| `spec/openapi/demo-v1.json` | 实现被接受后再由运行中的接口导出。本轮的大纲草案不是 T078 的接口 | 不手改已经导出的资料路由来假装片段已存在 |
| `tests/backend/` 下的新测试 | 发布被拦截、公司隔离、失败不覆盖已发布正文 | 本轮不添加 |

`errors.py` 只在双方同意新错误码时才改。在那之前复用已经冻结的码：`VALIDATION_ERROR`（422）、`FORBIDDEN`（403）、`NOT_FOUND`（404）、`VERSION_CONFLICT`（409）、`IDEMPOTENCY_KEY_REQUIRED`（428）、`IDEMPOTENCY_CONFLICT`（409）。错误体仍是 `{code, message, details, traceId}`。

不改 `generation_context.py`。那是 T124 的模型输入，要等片段发布和证据抽屉都存在之后另做。

## 建议的接口

公司 id 只来自登录身份，请求体不接受 `company_id`。写操作带 `Idempotency-Key` 和 `If-Match`。

| 方法与路径 | 作用 |
|---|---|
| `GET /api/v1/library/snippets` | 列出本公司片段及 `kb_sync_status` |
| `GET /api/v1/library/snippets/{snippet_id}` | 读取一条。其他公司的 id 按不存在返回 404 |
| `PUT /api/v1/library/snippets/{snippet_id}` | 保存草稿，不替换已发布正文 |
| `POST /api/v1/library/snippets/{snippet_id}/publish` | 发布。拦截时列出原因，已发布正文保持原样 |
| `GET /api/v1/library/snippets/{snippet_id}/sync` | 读取同步状态 |
| `POST /api/v1/library/snippets/{snippet_id}/sync` | 重新同步。失败不把状态写成已同步 |

## 字段

`id`、`company_id`、`product`、`snippet_type`、`variables`、`source_group`、`boilerplate_group`、`draft_body`、`published_body`、`draft_revision`、`published_revision`、`kb_sync_status`、`block_reasons`、`updated_at`。

`kb_sync_status` 取值：`unsynced`、`synced`、`failed`、`blocked`。

## 内存结构

```text
SnippetPublicationStore
  records: snippet_id -> 上面的字段
  audits: snippet_id -> 发布与拦截记录
```

发布前在存储内部检查：真实报告、写死承诺、未知变量、未发布正文、跨公司引用。任一不通过时，`published_body` 与 `published_revision` 不变，`kb_sync_status` 改为 `blocked` 或 `failed`，`block_reasons` 写下原因。跨公司读取返回 404，不返回对方正文。

检索如果以后要读已发布片段，只向这个存储要 `published_body`，不向 `Repository.read()` 要。那一步不属于本计划的实现。
