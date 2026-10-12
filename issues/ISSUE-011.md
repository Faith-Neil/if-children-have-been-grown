为什么有这个文件：登记在现有模型接口后面增加 OpenAI 兼容对话适配器的变更。

它解决什么问题：避免真实模型调用失败时仍返回演示成功文本，或在未显式配置时替换掉当前替身。

# ISSUE-011：OpenAI 兼容模型适配器

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-011 |
| 类型 | change |
| 优先级 | P1 |
| 状态 | in-review |
| 登记日期 | 2026-10-12 |
| 最后更新日期 | 2026-10-12 |
| revision | openai-adapter-2 |
| 关联 Task | [AI-02](../docs/tasks/AI-M0.md#ai-02) |
| 关联 PR | 未创建 |
| 本地验收 | 开发者已提交复核。2026-10-12 契约测试与全后台回归通过；未连接真实端点。开发者不标 done 或 closed |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [AI-02 交付](../docs/delivery/AI-02.md) |
| 代码 / 流程解释 | [AI-02 代码解释](../docs/code/AI-02.md) |
| 验证记录 | [2026-10-12 验证](../docs/testing/2026-10-12-openai-compatible-model.md) |

## 现象与证据

`ModelProvider` 已要求 `name`、`is_real_model`、`is_local` 和 `suggest(instruction, content)`。原先只有演示替身。公司内网模型预计使用 OpenAI 兼容接口，但端点尚未在 [ISSUE-010](ISSUE-010.md) 决定，托管 CI 也不能访问内网。

本次只增加可替换适配器。默认进程在没有显式配置时仍使用 `DemoModelProvider`。敏感项目继续走既有本地模型门禁。

## 影响与分流

- 影响范围：建议和章节候选使用的模型适配器。数据库、嵌入、重排、向量库不在本次。
- 不新增依赖。HTTP 使用项目里已有的 httpx。
- 密钥只从环境变量读取，仓库不保存密钥、端点密码或真实项目正文。
- 失败进入现有 502 `MODEL_UNAVAILABLE`，不返回假建议，也不改写已提交正文。
- 真实内网联调仍由 ISSUE-010 的访问方式决定。状态是 in-review。开发者不把本 Issue 标为 closed，也不把 AI-02 标为 done。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| AI-02 | 实现 `OpenAICompatibleModelProvider`，默认保持演示替身 | `backend/bid-core/icg_demo/openai_model.py`、`main.py`、契约测试 | AC-01～AC-04 | in-review |

## 验收条目

| 编号 | 可检查的完成条件 | 结果与证据 |
|---|---|---|
| AC-01 | 成功时 POST `{base_url}/v1/chat/completions` 并返回助手文本 | 假传输测试通过，见验证记录 |
| AC-02 | 超时、非 200、畸形 JSON 和空内容失败，且不编造成功文本 | 同上 |
| AC-03 | `is_local` 为 false 时敏感项目被拒绝且不发出请求；为 true 时沿用现有门禁并调用适配器 | 同上；`tests/backend/test_reference_boundaries.py` 仍在全量回归中 |
| AC-04 | 未显式配置时 `create_app()` 仍是演示替身；配置不完整时不退回假成功 | 同上 |

## 六份基线 impact 与同步表

| 基线 | impact：有影响 / 无影响 / 待评估及原因 | 更新路径 / 章节 | revision / Issue ID / 日期 | 同步状态 |
|---|---|---|---|---|
| PRD | 无影响。没有新增用户可见能力或改变验收口径；默认仍是演示建议 | `docs/PRD.md` 未改业务正文 | openai-adapter-1 / ISSUE-011 / 2026-10-12 | 已核对 |
| ROADMAP | 有影响。AI-02 记为 in-review，并说明它不代替模型选型 | `docs/ROADMAP.md` | openai-adapter-2 / ISSUE-011 / 2026-10-12 | 已核对 |
| ARCHITECTURE | 有影响。现有模型口后增加显式启用的兼容适配器，失败语义不变 | `docs/ARCHITECTURE.md` 当前实施段 | openai-adapter-1 / ISSUE-011 / 2026-10-12 | 已核对 |
| TASK_BOARD | 有影响。AI-02 从 done 改回 in-review | `docs/TASK_BOARD.md`、`docs/tasks/AI-M0.md` | openai-adapter-2 / ISSUE-011 / 2026-10-12 | 已核对 |
| PROJECT_STATUS | 有影响。写明适配器已本地验收，真实端点未接通 | `docs/PROJECT_STATUS.md` | openai-adapter-1 / ISSUE-011 / 2026-10-12 | 已核对 |
| DOCUMENT_INDEX | 有影响。登记本 Issue、代码、测试、交付和验证，并把状态改为 in-review | `docs/DOCUMENT_INDEX.md` | openai-adapter-2 / ISSUE-011 / 2026-10-12 | 已核对 |
| PROJECT_BRIEF | 有影响。2026-10-12 排期行把计数改成 342 项并写了 AI-02，原先未登记 | `docs/PROJECT_BRIEF.md` 排期行。0c60842 从 340 项 18 done 改为 342 项 19 done，不回退。与 T008 的 in-review 及 REV-M0-T05 合并后为 343 项 18 done、2 in-review | openai-adapter-2 / ISSUE-011 / 2026-10-12 | 已核对 |

治理块未改。`docs/reference/` 未改。业务库决定在 ISSUE-010，本适配器不连接数据库。

## 处理与复核记录

| 日期 | revision / 状态 | 完成事实、问题与下一步 | 证据 / 复核人 |
|---|---|---|---|
| 2026-10-12 | openai-adapter-1 / 曾标 closed | 适配器、显式配置和契约测试完成。未调用真实端点，未合入，未发布 | [验证记录](../docs/testing/2026-10-12-openai-compatible-model.md) |
| 2026-10-12 | openai-adapter-2 / in-review | 按新规则把 Issue 和 AI-02 从 closed/done 改回 in-review。开发者不标完成；待项目经理在 QA 签字后决定 | 本文与任务看板 |

## 本地验收与后续合入发布

- 本地验收结论与日期：开发者已于 2026-10-12 提交复核，范围限于假 HTTP 契约和现有回归。状态保持 in-review，不标 closed。
- 未覆盖：真实内网端点、并发压测、云端模型和任何数据库。
- PR 状态：未创建。
- 合入提交与日期：未合入。
- 发布版本与日期：未发布。
