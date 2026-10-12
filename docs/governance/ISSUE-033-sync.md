为什么有这个文件：记录 ISSUE-033 从登记改为提交复查时改了哪些基线。

它解决什么问题：避免把一张 in-review 卡写成已经由 QA 签完，或写成新增了错误码。

# ISSUE-033 同步

日期 2026-10-12。revision evidence-mount-2。状态 in-review。负责人 backend。不新增错误码。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改 |
| ROADMAP | 未改 | 理由同 PRD |
| ARCHITECTURE | 未改 | 挂接规则在现有流程里 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | BE-M0-T18 改为 in-review。同一次提交另增 BE-M0-T19 planned。BE-M0 现为 19 项，其中 8 项 done |
| PROJECT_STATUS | 已改 | 活计数为 386 项：50 done、11 in-review、7 in-progress、265 planned、48 blocked、5 ready |
| DOCUMENT_INDEX | 已改 | 补交付、代码解释和验证记录 |
| 错误码与 OpenAPI | 已改契约字段，未改错误码 | 冻结模型 `EvidenceMountFields` 仍在。运行时资料和项目请求体增加挂接字段。未跑 `export_openapi.py`。冻结名单仍是 143 个名字 |
| 依赖与 CI | 未改 | 不改工作流 |

BE-M0-T13 已依据 QA ae38ec3，PM 17:16 确认 done。ISSUE-018 仍为 in-progress。APP-M2-T114 已 done（QA f521950，PM 17:13 确认）。APP-M2-T078 已 done（QA 19c4862，PM 17:20 确认）。本卡不标 done，本 Issue 不标 closed。QA 重签之前不能标 done。

## 规格增量

日期 2026-10-12。revision evidence-mount-spec-1 写入冻结模型。evidence-mount-2 接通运行时。不改 `frozen_error_codes.py`，不新增错误码。不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑快照。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| spec/openapi/demo-v1.json | 已改 | 冻结模型 `EvidenceMountFields` 保留。资料列表和条款 PATCH 的 `x-issue-033` 改为已实现。运行时比较前去掉该标记和冻结模型 |
| 错误码 | 未改 | 仍是 143 个。过期用 409 `EVIDENCE_EXPIRED`，reference 或缺协议用 409 `EVIDENCE_NOT_USABLE`，受限且无 ACL 或非管理员用 403 `FORBIDDEN` |

未合入，未发布。不标 done，不标 closed。
