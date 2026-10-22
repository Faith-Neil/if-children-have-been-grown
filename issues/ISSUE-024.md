为什么有这个文件：把模型配置的存储和 API 登记成后台契约，供 ISSUE-022 引用错误码。

它解决什么问题：避免密钥、字段和两个新错误码只存在于对话里，同时不把 Provider 侧的字段再抄一遍。

# ISSUE-024：模型配置的存储与 API

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-024 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 负责人 | backend |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-21 |
| revision | model-config-storage-2 |
| 关联 Task | ISSUE-024 / [ISSUE-028](ISSUE-028.md) |
| 关联 PR | 未创建 |
| 本地验收 | 已执行。tests/backend/test_model_config_storage.py 等全量 451 passed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [ISSUE-024 交付](../docs/delivery/ISSUE-024.md) |
| 代码 / 流程解释 | [ISSUE-024 代码解释](../docs/code/ISSUE-024.md) |
| 验证记录 | 见 [交付报告](../docs/delivery/ISSUE-024.md) 与 `tests/backend/test_model_config_storage.py` |

登记要求的状态是 planned/open，负责人是 backend。Issue 看板只有 new、triaged、ready、in-progress、in-review、closed、blocked，没有 planned 或 open。本项已登记、未开工、未关闭，因此状态记为 new。

## 现象与证据

[ISSUE-028](ISSUE-028.md) 只保留 Provider 侧：读取配置、启动快照的使用方式、local/cloud 路由、敏感约束、流式与 JSON 的调用方式、错误映射、`job.model_call`。那些行为不在本文件重复。`stream_enabled` 与 `json_mode_enabled` 的名字由本 Issue 定义。ISSUE-028 只引用这两个名字，不另写默认值或含义。设计原文在 [配置驱动的对话模型](../docs/architecture/model-config-provider.md)。

本 Issue 拥有存储、密钥、本文件列出的字段、配置 API，以及下面这张供 ISSUE-022 引用的错误码表。

## 存储与密钥

- API 密钥用 Fernet 加密。主密钥只来自环境变量 `ICG_SECRET_KEY`，不进仓库。
- 响应不返回明文密钥。返回 `api_key_masked` 和 `has_api_key`。
- 更新时：请求省略密钥字段表示保留原值；空字符串表示清除；把刚才返回的掩码再送回来表示不修改。
- 本契约写明的字段是 `id`、`revision`、`allow_sensitive`、`stream_enabled`、`json_mode_enabled`。`revision` 做乐观锁，经 If-Match 覆盖包括这两个开关在内的全部配置字段。
- `stream_enabled` 是布尔值，默认 true，表示该配置是否使用流式输出。
- `json_mode_enabled` 是布尔值，默认 false，表示是否要求模型输出 JSON。
- Provider 侧的基址、模型名、本地或云端仍不在本文件列成第二张字段表。ISSUE-028 引用 `stream_enabled` 与 `json_mode_enabled`，不重定义它们。

## 配置 API

`POST /api/v1/model-configs/{id}/test` 的成功结果包含 `ok`、`provider`、`model`、`duration_ms`。

任务开始时对当时读到的配置做快照，包含 `stream_enabled` 和 `json_mode_enabled`，与其余配置字段相同。快照之后默认配置再变，不改已经开始的任务。Provider 如何使用这份快照见 ISSUE-028，不在这里展开。

## 冻结错误码

这两码登记在本表，供 [ISSUE-022](ISSUE-022.md) 引用。它们已写入 `spec/openapi/demo-v1.json` 的 `V1Error.code` 枚举和 `x-error-status`，并写入 `errors.py` 的冻结表，因此 403 与 503 的响应体可以通过 schema 校验。ISSUE-022 的操作说明没有改。本轮仍不返回这两码，也不实现加密。实现时再加测试，断言 `SECRET_KEY_UNAVAILABLE` 的响应没有 `Retry-After`。

| code | HTTP | 约定 |
|---|---|---|
| `SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL` | 403 | 敏感项目不能使用云端配置。这是策略拒绝 |
| `SECRET_KEY_UNAVAILABLE` | 503 | 主密钥不可用。非瞬时：客户端不得自动重试，与 `MODEL_UNAVAILABLE` 相同。服务端不得发送 `Retry-After`。实现时增加测试，断言该响应没有 `Retry-After` |

## 影响与分流

- 影响范围：将来的模型配置存储和 API。本轮只把两枚错误码写入冻结表和 OpenAPI 枚举。不改适配器、页面，也不改 ISSUE-022 的操作说明。
- 不涉及：ISSUE-028 已经写下的 Provider 行为。两个开关的字段名在本文件，ISSUE-028 只引用、不重定义。不新增依赖。`cryptography` 已在仓库中，Fernet 实现留到开工时。
- 不新增任务卡，不改任务计数。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| 未建卡 | 存储、掩码、测试连接和两枚错误码 | 实现时再定 | AC-01～AC-03 | 未开工 |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 密钥以 Fernet 加密，主密钥只来自 `ICG_SECRET_KEY`。响应只有 `api_key_masked` 与 `has_api_key`。省略为保留，空字符串为清除，送回掩码为不修改 | 已完成。`tests/backend/test_model_config_storage.py` 通过 |
| AC-02 | `POST /api/v1/model-configs/{id}/test` 返回 `ok`、`provider`、`model`、`duration_ms`。任务开始时保存配置快照，含 `stream_enabled` 与 `json_mode_enabled`。二者随 `revision` 做乐观锁 | 已完成。`tests/backend/test_model_config_storage.py` 通过 |
| AC-03 | 403 与 503 两码进入运行时冻结表。503 的响应没有 `Retry-After`，客户端不自动重试 | 已完成。`tests/backend/test_model_config_storage.py` 严格断言 503 无 Retry-After，403 敏感门禁拦截 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。不改需求，不改里程碑快照 | `docs/PRD.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| ROADMAP | 无影响。不新增任务，不改里程碑快照 | `docs/ROADMAP.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| ARCHITECTURE | 无影响。存储契约在本文件，不改架构正文 | `docs/ARCHITECTURE.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| TASK_BOARD | 无影响。不新增任务，不改计数 | `docs/TASK_BOARD.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| PROJECT_STATUS | 无影响。不改任务计数 | `docs/PROJECT_STATUS.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记代码解释与交付说明 | `docs/DOCUMENT_INDEX.md` | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |
| PROJECT_BRIEF | 无影响。不改里程碑快照 | `docs/PROJECT_BRIEF.md` 未改 | model-config-storage-2 / ISSUE-024 / 2026-10-21 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | model-config-storage-1 / new | 登记存储、掩码、测试连接、快照和两枚错误码。状态按看板词汇记为 new。不改运行代码 | 本文件 |
| 2026-10-12 | model-config-storage-1 / new | PM 批准 D-1。本 Issue 拥有 `stream_enabled`（布尔，默认 true，是否使用流式输出）和 `json_mode_enabled`（布尔，默认 false，是否要求模型输出 JSON）。二者纳入 `revision` 乐观锁，并在任务开始时随配置快照。ISSUE-028 只引用这两个名字，不重定义。不再把这两个开关的字段名交给 ISSUE-028。不改运行代码 | 本文件 |
| 2026-10-21 | model-config-storage-2 / in-review | 完成模型配置存储、Fernet 密钥加密、掩码、乐观锁、敏感项目门禁、连通性测试 API 及 Alembic 迁移脚本。全量 pytest 回归 451 passed 通过。交付文档与代码解释已生成。标为 in-review，严禁私自标 done | [代码解释](../docs/code/ISSUE-024.md) / [交付](../docs/delivery/ISSUE-024.md) / backend |

## 本地验收与后续合入发布

- 本地验收：已执行。`tests/backend/test_model_config_storage.py`（12 passed）及全量测试（451 passed, 16 skipped, 0 failed）。
- PR：未创建。合入：未合入。发布：未发布。状态为 in-review。
