为什么有这个文件：记录 APP-M2-T114 挂证据抽屉这一轮实际做成了什么。

它解决什么问题：避免把本地浏览器通过写成已经具备审计列、批量匹配或已经发布。

# APP-M2-T114：EvidenceDrawer 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T114 |
| 代码解释 | [挂证据抽屉](../code/APP-M2-T114.md) |
| 验收 | 前端单测 97 项通过，其中挂证据 4 项。`pnpm --dir frontend/web build` 通过。浏览器端到端 14 项通过，含本卡 1 项。见 [核对](../testing/2026-10-12-app-m2-t114-evidence-drawer.md)。缺协议和受限只在单测。Excel 与并排设计稿未做 |
| 项目进度 | 并入 BE-M0-T16 与 REV-M0-T18、T19 后看板 374 项：41 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。本卡 in-review，未标 done。T124 仍 blocked。未合入，未发布 |
<!-- task-delivery:end -->

## 关联与状态

- 日期、里程碑、Issue、任务卡：2026-10-12，APP-M2，[ISSUE-007](../../issues/ISSUE-007.md)。[任务卡](../tasks/APP-M2.md#app-m2-t114)。
- 分支、提交、PR：`codex/repository-foundation`。接口以冻结提交 `73fde1e` 的 `spec/openapi/demo-v1.json` 为准。其后没有再改这份 JSON。PR 未创建。
- 本地验收状态：in-review。抽屉已接到响应矩阵。不标 done。
- 合入 / 发布状态：未合入，未发布。

## 完成内容与变更文件

- `frontend/web/src/evidence-drawer.ts`：分组、可勾选判断、打开时的增减和版本过期。
- `frontend/web/src/EvidenceDrawer.tsx`：要求原文、结构化资料、方案片段、历史标书参考、已挂列表。
- `frontend/web/src/ProjectPages.tsx`：矩阵打开抽屉，保存 `PATCH` 的 `evidence_ids`。状态列仍是条款状态。证据失效单独成标签。
- `frontend/web/src/types.ts`：资料上的可选版本、相关度、来源层级、协议、受限和原文位置。
- `frontend/web/src/styles.css`：证据失效行左侧色条。
- `frontend/web/tests/evidence-drawer.test.mjs` 与 `frontend/web/e2e/evidence-drawer.spec.ts`。

冻结契约没有 `listEvidenceCandidates` 和 `attachEvidence`。保存沿用已有的条款更新。`LibraryItem` 允许额外字段，所以页面能读到协议或受限标记；新建资料的请求体不允许这些字段，演示里补不出来。字典里的 `matrix_evidence` 审计列（引用版本、挂接人、挂接时间、匹配方式）后台没有单独存储，本轮只对照打开抽屉时的编号列表。

偏差：任务卡还提到与 03 并排截图和真实 Excel。那两项属于矩阵表格和导出卡，本轮没有做，所以不能标 done。批量智能匹配按钮仍禁用。

## 代码解释

入口、分组和保存见 [代码解释](../code/APP-M2-T114.md)。

## 验收结果

命令与结果见 [核对](../testing/2026-10-12-app-m2-t114-evidence-drawer.md)。`frontend/web` 没有 lint 脚本。类型检查含在 `pnpm build` 的 `tsc -b` 里。

## 项目进度

T114 从 planned 改为 in-review。rebase 时上游已加入 BE-M0-T16，以及已本地验收的 REV-M0-T18、REV-M0-T19。看板为 374 项：41 done、9 in-review、7 in-progress、264 planned、49 blocked、4 ready。APP-M2 其余 253 张卡仍 planned。T124 仍 blocked，因为 T078 未标 done，T114 也未标 done。ISSUE-007 仍 in-progress。ISSUE-022 仍 in-review。ISSUE-031 与 BE-M0-T16 仍 in-review。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无影响。开发仍按已登记的 v1.8。本轮不改任务计数，也不改里程碑快照 |
| ROADMAP | 无影响。没有新增或取消任务。本轮不改任务计数 |
| ARCHITECTURE | 无影响。没有新模块或新接口。挂接仍是现有条款更新 |
| Issue 看板/详情 | ISSUE-007 仍 in-progress。ISSUE-022 仍 in-review，并写明 T114 已 in-review 但未 done，T124 仍 blocked |
| TASK_BOARD / PROJECT_STATUS | T114 改为 in-review。并入 BE-M0-T16 与两张 QA 卡后为 374 项、41 done、9 in-review、264 planned。三份基线计数不改 |
| DOCUMENT_INDEX | 登记交付、代码解释、核对和同步表 |

## 风险与后续

演示登录不能造出缺协议或受限资料，这两条只由单测挡住。过期、未确认和历史标书在浏览器里核对过。他人先保存时，第一次保存被后台版本拒绝，抽屉留在原地；再次保存才显示“本行已被他人修改”。本地通过不是合入，也不是发布。
