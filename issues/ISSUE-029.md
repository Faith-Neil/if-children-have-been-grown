为什么有这个文件：把 RAGFlow 检索适配器收成一份待复核的设计。

它解决什么问题：避免在内存检索还没换成真实客户端时，把官方路径写成已经调用。

# ISSUE-029：RAGFlow 检索适配器设计

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-029 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | ragflow-adapter-design-1 |
| 关联 Task | [AI-01](../docs/tasks/AI-M0.md#ai-01)；现有内存口是 [AI-03](../docs/tasks/AI-M0.md#ai-03) / [ISSUE-016](ISSUE-016.md) |
| 关联 PR | 未创建 |
| 本地验收 | 设计已写。没有客户端。见 [核对](../docs/testing/2026-10-12-issue-010-decisions.md) |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-01 交付](../docs/delivery/AI-01.md) |
| 代码 / 流程解释 | 无运行代码。设计见 [适配器设计](../docs/architecture/ragflow-retrieval-adapter.md) |
| 验证记录 | [2026-10-12 决定核对](../docs/testing/2026-10-12-issue-010-decisions.md) |

## 现象与证据

[ISSUE-010](ISSUE-010.md) 已关闭：嵌入与向量库用 RAGFlow 自带能力。AI-03 仍是内存实现，不进入 `create_app`。

路径依据 <https://ragflow.io/docs/http_api_reference>，含 “Migrate to 1.0” 说明，不钉 Git 提交。HTTP 使用已有的 `httpx==0.28.1`。不加依赖。

重排产品未在用户决定里选定。本设计提议使用检索接口的 `rerank_id`，模型在 RAGFlow 内配置。这不是第二项已关闭的选型。

## 影响与分流

- 影响范围：以后的路径 B/C。路径 A 仍不经过 RAGFlow。B 或 C 失败时保留 A。
- 公司隔离靠我们保存的 dataset id。RAGFlow 令牌不是 `company_id`。
- `CANCEL` 映射为 `kb_sync_status=failed`，不映射为 `blocked`，以免和 T078 的 200 受阻发布混淆。
- CI 使用记录 `Authorization` 和 `base_url` 的假 RAGFlow。真实连接默认跳过。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-03 | 内存口保持不变 | `backend/bid-core/icg_demo/retrieval.py` | 本轮不改代码 | in-review |
| AI-01 | 设计可复核 | `docs/architecture/ragflow-retrieval-adapter.md` | 路径表和状态映射已写明 | in-review |

开发者不把本 Issue 标 closed。

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 官方路径、检索字段和健康检查已列出 | 已写入设计。未调用 |
| AC-02 | 不新增依赖，不改检索代码 | 本轮不改 `requirements.txt` 与 `retrieval.py` |
| AC-03 | 重排仍标明为提案，不是已关闭的用户决定 | 设计与 ISSUE-017 草案一致 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。不改任务计数，不增加页面验收 | `docs/PRD.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |
| ROADMAP | 无任务计数变化。决定用词随 ISSUE-010 | `docs/ROADMAP.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。写明向量库为 RAGFlow，适配器未实现 | `docs/ARCHITECTURE.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |
| TASK_BOARD | 无新任务。AI-03 仍 in-review | `docs/TASK_BOARD.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。写明检索仍是内存 | `docs/PROJECT_STATUS.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue 与设计 | `docs/DOCUMENT_INDEX.md` | ragflow-adapter-design-1 / ISSUE-029 / 2026-10-12 | 已核对 |

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | ragflow-adapter-design-1 / in-review | 设计已提交。等待复核。不标 closed | [设计](../docs/architecture/ragflow-retrieval-adapter.md) |

## 本地验收与后续合入发布

- 本地验收：设计核对完成。没有连接 RAGFlow。
- PR：未创建。合入：未合入。发布：未发布。
