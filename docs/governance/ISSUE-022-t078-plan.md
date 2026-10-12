为什么有这个文件：把 APP-M2-T078 的内存实现范围写清楚，供后台对齐后再写代码。

它解决什么问题：避免把片段发布状态塞进现有 Repository 的整包读写，和 ISSUE-018 按聚合拆分撞在一起。

# APP-M2-T078 内存方案（只规划，未实现）

日期：2026-10-12。关联 [ISSUE-022](../../issues/ISSUE-022.md)。状态：计划，未写代码。T078 仍是 planned。[ISSUE-018](../../issues/ISSUE-018.md) 已登记 MySQL 8 方案，状态 in-review，本轮不实施。后台复核后再改了路径、版本头和发布被拦截时的响应。

## 不改的方法

| 文件 | 保持不动的部分 |
|---|---|
| `backend/bid-core/icg_demo/ports.py` | `Repository.read` 与 `Repository.transaction` 的签名和语义。片段不进这个 Protocol |
| `backend/bid-core/icg_demo/adapters.py` | 现有内存仓库的 `read` 与 `transaction`。不在整包 `DemoState` 提交里写片段 |
| `backend/bid-core/icg_demo/domain.py` | `DemoState` 不增加片段、发布版本或 `kb_sync_status` 字段。现有 `library` 仍只服务已经落地的资料记录 |

`ports.py` 在实现时另外增加一个 `SnippetPublicationStore` Protocol，不改上面两处方法。原因：`Repository.read` 返回整份 `DemoState`，`transaction` 提交整份副本。[持久化方案](../architecture/mysql-8-persistence-plan.md) 第 7 节要先把这种整包访问收成按聚合的窄接口。片段从现在起放在自己的存储里。

## 实现时要新增的文件

| 文件 | 作用 |
|---|---|
| `backend/bid-core/icg_demo/snippet_publication.py` | `SnippetPublicationStore` 的内存实现。独立字典，不经过 `Repository.read` / `transaction` |

这个对象自己持有字典。进程内有效，重启丢失，仍受现有单进程限制。ISSUE-018 落地后，它可以作为片段这个聚合的访问对象。

计划中的 Protocol，每个方法都带 `company_id`。本轮不写进 `ports.py`：

```text
class SnippetPublicationStore(Protocol):
    def list(self, company_id: str) -> list
    def get(self, company_id: str, snippet_id: str) -> dict
    def create(self, company_id: str, payload: dict) -> dict
    def save_draft(self, company_id: str, snippet_id: str, payload: dict, draft_revision: int) -> dict
    def publish(self, company_id: str, snippet_id: str, draft_revision: int) -> dict
    def sync(self, company_id: str, snippet_id: str, published_revision: int) -> dict
```

## 路径

选择 `/api/v1/snippet-publications`，不用 `/api/v1/library/snippets`。

现有资料路由是 `GET/POST /api/v1/library` 和 `PATCH /api/v1/library/{item_id}`，见 `backend/bid-core/icg_demo/workflow_routes.py`。`{item_id}` 会把字面路径段 `snippets` 当成资料 id。把片段放在另一个前缀下，不依赖注册顺序，也不会被这条路由吞掉。因此本轮不为注册顺序另加测试。

## 实现时要改、但只做接入的文件

| 文件 | 改什么 | 不改什么 |
|---|---|---|
| `backend/bid-core/icg_demo/ports.py` | 只增加上面的 Protocol | 不改 `Repository` |
| `backend/bid-core/icg_demo/main.py` | 创建独立存储并挂到应用；增加下面的路由 | 不把片段写入 `repository.transaction` |
| `backend/bid-core/icg_demo/workflow_schemas.py` | 只增加请求和响应模型 | 不在这里保存状态 |
| `spec/openapi/demo-v1.json` | 实现被接受后再由运行中的接口导出 | 本轮的大纲草案不是 T078 的接口 |
| `tests/backend/` 下的新测试 | 公司隔离、版本头、拦截时状态不变 | 本轮不添加 |

`errors.py` 只在双方同意新错误码时才改。在那之前复用已经冻结的码：`VALIDATION_ERROR`（422）、`FORBIDDEN`（403）、`NOT_FOUND`（404）、`VERSION_CONFLICT`（409）、`IF_MATCH_REQUIRED`（428）、`IDEMPOTENCY_KEY_REQUIRED`（428）、`IDEMPOTENCY_CONFLICT`（409）。错误体仍是 `{code, message, details, traceId}`。

不改 `generation_context.py`。那是 T124 的模型输入，要等片段发布和证据抽屉都存在之后另做。

## 接口

公司 id 只来自登录身份，请求体不接受 `company_id`。服务端分配 `snippet_id`，客户端不生成 id。写操作的幂等作用域是 `library:{company_id}`，与现有公司资料相同：同键同指纹重放首次成功结果，同键不同指纹返回 409 `IDEMPOTENCY_CONFLICT`，缺少或格式不符返回 428 `IDEMPOTENCY_KEY_REQUIRED`。

| 方法与路径 | If-Match | 作用 |
|---|---|---|
| `POST /api/v1/snippet-publications` | 不需要。还没有版本 | 创建草稿并返回服务端分配的 id 与 `draft_revision` |
| `GET /api/v1/snippet-publications` | 不需要 | 列出本公司片段，含 `kb_sync_status` |
| `GET /api/v1/snippet-publications/{snippet_id}` | 不需要 | 读取一条，响应里已经带同步状态。不再另设 `GET .../sync`。其他公司的 id 按不存在返回 404 |
| `PUT /api/v1/snippet-publications/{snippet_id}` | `draft_revision` | 保存草稿，不替换已发布正文 |
| `POST /api/v1/snippet-publications/{snippet_id}/publish` | `draft_revision` | 发布。被拦截时返回 200，响应列出原因，存储里的任何字段都不改 |
| `POST /api/v1/snippet-publications/{snippet_id}/sync` | `published_revision` | 重新同步。失败不把状态写成已同步 |

缺少 `If-Match` 的保存、发布和同步返回 428 `IF_MATCH_REQUIRED`。版本不符返回 409 `VERSION_CONFLICT`。

## 字段

`id`、`company_id`、`product`、`snippet_type`、`variables`、`source_group`、`boilerplate_group`、`draft_body`、`published_body`、`draft_revision`、`published_revision`、`kb_sync_status`、`updated_at`。

`kb_sync_status` 取值：`unsynced`、`synced`、`failed`、`blocked`。发布被拦截时的原因只出现在当次 200 响应里，不写回记录。

## 内存结构

```text
SnippetPublicationStore
  records: snippet_id -> 上面的字段
  audits: snippet_id -> 成功的发布与同步记录
```

发布前在存储内部检查：真实报告、写死承诺、未知变量、未发布正文、跨公司引用。任一不通过时返回 200，响应里列出原因，`records` 与 `audits` 都保持调用前的内容。检查通过才替换 `published_body` 并增加 `published_revision`。跨公司读取返回 404，不返回对方正文。

检索如果以后要读已发布片段，只向这个存储要 `published_body`，不向 `Repository.read()` 要。那一步不属于本计划的实现。
