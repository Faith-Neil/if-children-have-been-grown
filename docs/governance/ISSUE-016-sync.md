# ISSUE-016 基线同步记录

日期：2026-10-12。治理版本：g1.1。任务：AI-03。范围：检索口与三条证据候选的内存实现。不连接 MySQL，不选定向量库。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无。没有新的用户操作或验收口径 | 不改需求正文 | 维持现有实施视图 |
| ROADMAP.md | 有。新增一张 in-review 卡，计数必须跟着变 | 在 AI-02 与 T008 已 done 的 343 项（20 done、1 in-review、7 in-progress）之后改为 344 项：20 done、2 in-review、7 in-progress、266 planned、49 blocked。页面顺序不变。AI-03 不标 done | 2026-10-12 进度说明 |
| ARCHITECTURE.md | 有。架构上多了检索替换口 | 当前实施段写明内存实现，业务库虽已定为 MySQL 8 但未连接，向量库仍待决 | 2026-10-12 说明 |
| issues/index.md / ISSUE-016.md | 有。新变更已提交复核 | 状态为 in-review。登记时下一编号改为 ISSUE-017；其后 ISSUE-017 与 ISSUE-020 已被其他提交占用，本轮不改编号。ISSUE-014 仍保留给前端。ISSUE-010 仍 blocked | in-review；未合入、未发布 |
| TASK_BOARD.md / tasks/AI-M0.md | 有。新增 AI-03 | 看板和任务卡为 in-review。AI-M0 为 3 项、1/3：AI-02 已 done，AI-03 不标 done。交付和代码解释已链接 | in-review |
| PROJECT_STATUS.md | 有。必须区分内存骨架和未选的向量库 | 进度中并列写出，并写明不连接 MySQL | 2026-10-12 |
| DOCUMENT_INDEX.md | 有。Issue、代码、测试、交付和验证都要能找到 | 登记 D-213～D-220。D-206～D-212 仍是 ISSUE-014 的布局条目 | 2026-10-12 |
| 产品参考 PRD/字典 | 无。检索口不修改参考原文 | 未修改 `docs/reference/` | 保持原文 |
| 业务数据库 | 无实现。ISSUE-010 已决定 MySQL 8，本卡不连接它 | 不新增驱动、迁移或向量库。单元测试仍用内存 | 内存实现 |
| PROJECT_BRIEF.md | 有。排期行的任务总数变了 | 在项目经理确认 AI-02 与 T008 之后的 343 项（20 done、1 in-review、7 in-progress）之后改为 344 项（20 done、2 in-review、7 in-progress）。原因是新增 AI-03，且不回退先前句子。排期写明 AI-03 只使用内存检索，T001 保持 in-review，T008 保持 done | 2026-10-12；已登记 |
| backend/bid-core/README.md | 有。原句仍写数据库未选定 | 改为业务库已决定为 MySQL 8 但未连接，并说明检索口不进入 `create_app` | 2026-10-12 |
| FE-M0-T04 | 无门禁变化 | 写明 AI-03 不解除该卡 | 仍 blocked |
| 本轮错误体旁路 | 无新错误码。不改 PRD、ROADMAP、ARCHITECTURE、TASK_BOARD、PROJECT_STATUS、PROJECT_BRIEF | `cba6282` 已冻结 `{code, message, details, traceId}`。适配器在 `POST /api/v1/projects/{id}/generate` 失败时已是 502 `MODEL_UNAVAILABLE`，`traceId` 等于 `X-Request-ID`。只在既有适配器测试加一条，不改 `errors.py`，不改 `spec/openapi/demo-v1.json` 码表。rebase 后保留 ISSUE-017、ISSUE-020 与 REV-M0-T07。看板现为 352 项：21 done、5 in-review、7 in-progress、266 planned、49 blocked、4 ready。本轮不改这些基线正文 | 2026-10-12；仍 in-review |
| DOCUMENT_INDEX.md 追加 | 有。要能找到这条旁路测试 | D-203 改为 31 项并写明 v1 冻结错误体；D-216 写上复跑次数。变更日志追加一行。不重开 ISSUE-011 | 2026-10-12 |

开发者提交的契约不能当作任务 done、Issue closed、PR 已合入或服务已发布。向量库、嵌入和重排仍等 ISSUE-010。只有项目经理在 QA 签字后把 AI-03 标为 done。

## QA 签署后关闭

日期：2026-10-12。依据 QA 签署 2fe6198（REV-M0-T16）。ISSUE-016 改为 closed，AI-03 改为 done。未合入，未发布。不改检索代码。路径 C 不按查询词过滤仍留到 RAGFlow 适配器实现。

| 文档 | 本次影响 | 实际处理 | 版本与状态 |
|---|---|---|---|
| PRD.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| ROADMAP.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| PROJECT_BRIEF.md | 无 | 不改正文，不改里程碑计数 | 2026-10-12 |
| ARCHITECTURE.md | 有 | 检索口仍只在内存。状态改为 closed / done | 2026-10-12 |
| TASK_BOARD.md | 有 | AI-03 改为 done。看板 371项39done、6in-review、7in-progress、266planned、49blocked、4ready | 2026-10-12 |
| PROJECT_STATUS.md | 有 | 同上计数，并写明 ISSUE-016 已 closed | 2026-10-12 |
| DOCUMENT_INDEX.md | 有 | 更新当前行并追加变更记录。不改历史行 | 2026-10-12 |
| issues/index.md | 有 | ISSUE-016 改为 closed，验收证据链接签署记录 | closed |
| issues/ISSUE-017.md | 无 | 不改。DevOps 拥有 ISSUE-017 与 OPS-M0-T02 | closed |
| backend/bid-core | 无 | 不改 retrieval.py | done |

未合入，未发布。没有重跑 pytest：本轮不改后台代码。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：247 份 Markdown、371 项任务、29 项 Issue。」检查程序未修改。看板手写摘要与任务表一致：371项39done、6in-review、7in-progress、266planned、49blocked、4ready。
