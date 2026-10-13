为什么有这个文件：记录 ISSUE-031 改了哪些基线。

它解决什么问题：避免把一张冻结名单写成产品范围或里程碑计数已经变了。

# ISSUE-031 同步

日期 2026-10-12。revision frozen-names-1。状态 in-review。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改。本卡不改产品规则 |
| ROADMAP | 未改 | 理由同上 |
| ARCHITECTURE | 未改 | 错误码名单在接口约定和代码里 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | 新增 BE-M0-T16，状态 in-review。活计数为 372 项：39 done、8 in-review、7 in-progress、265 planned、49 blocked、4 ready |
| PROJECT_STATUS | 已改 | 活计数与 BE-M0 项数同上 |
| DOCUMENT_INDEX | 已改 | 登记本 Issue、交付、代码说明、验证和本表 |
| docs/reference | 未改 | 只读 |
| spec/openapi/README.md | 已改 | 写明增删错误码必须在同一提交更新 `FROZEN_NAMES` |
| .github | 未改 | 现有 backend 作业会跑契约测试和 QA 脚本 |

BE-M0-T16 为 in-review。ISSUE-031 为 in-review。不标 done，不标 closed。PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照不改。任务看板是准绳。

## 2026-10-13 QA

QA 签署 BE-M0-T16（REV-M0-T34，tip `90b2334`）：`set(ERROR_STATUS)==FROZEN_NAMES`（143）。ISSUE-031 保持 closed。BE-M0-T16 仍 in-review，等 PM。
