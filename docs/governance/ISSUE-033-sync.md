为什么有这个文件：记录 ISSUE-033 登记时改了哪些基线。

它解决什么问题：避免把一张 planned 卡写成已经改了挂接接口。

# ISSUE-033 同步

日期 2026-10-12。revision evidence-mount-1。状态 new。负责人 backend。无接口改动。字典对照和错误码选择本轮不做。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 未改 | 里程碑快照不改 |
| ROADMAP | 未改 | 理由同 PRD |
| ARCHITECTURE | 未改 | 本轮不改运行结构 |
| PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| TASK_BOARD | 已改 | 新增 BE-M0-T18，状态 planned。BE-M0 现为 18 项，其中 7 项 done |
| PROJECT_STATUS | 已改 | 活计数为 378 项：44 done、9 in-review、7 in-progress、265 planned、49 blocked、4 ready |
| DOCUMENT_INDEX | 已改 | 登记本表和 ISSUE-033 |
| 错误码与 OpenAPI | 未改 | 规格增量由 AI bot 另交。本轮不定错误码 |
| 依赖与 CI | 未改 | 不改工作流。排在 BE-M0-T13 之后 |

BE-M0-T13 仍为 in-review。ISSUE-018 仍为 in-progress。APP-M2-T114 仍为 in-review。本卡不标 done，本 Issue 不标 closed。实现后由 QA 重签。

## 规格增量

日期 2026-10-12。revision evidence-mount-spec-1。ISSUE-033 改为 in-progress。BE-M0-T18 仍为 planned。不改后台应用代码，不改 `frozen_error_codes.py`，不新增错误码。不改 PRD、ROADMAP、PROJECT_BRIEF 的任务计数。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| spec/openapi/demo-v1.json | 已改 | 冻结模型 `EvidenceMountFields`。资料列表和条款 PATCH 增加 `x-issue-033`。运行时比较前去掉该标记和冻结模型 |
| spec/openapi/README.md | 已改 | 写明字段名、派生协议和三个已有错误码 |
| 错误码 | 未改 | 仍是 143 个。过期用 409 `EVIDENCE_EXPIRED`，reference 或缺协议用 409 `EVIDENCE_NOT_USABLE`，受限且无 ACL 或非管理员用 403 `FORBIDDEN` |
| TASK_BOARD / BE-M0-T18 | 已改说明 | 卡片仍 planned。ISSUE-033 改为 in-progress |
| PROJECT_STATUS | 未改计数 | 不改任务状态计数 |
| PRD / ROADMAP / PROJECT_BRIEF | 未改 | 里程碑快照不改 |
| DOCUMENT_INDEX | 已改 | 更新当前行并追加变更记录 |

未合入，未发布。不标 done，不标 closed。`python3 -m pytest tests/backend/test_evidence_mount_contract.py tests/backend/test_outline_contract_draft.py tests/backend/test_error_idempotency.py::test_openapi_declares_v1_error_body_status_table_and_retry -q` 为 8 passed、1 warning。`python3 -m pytest tests/backend -q` 为 352 passed、12 skipped、1 warning。12 项跳过都是 `ICG_DATABASE_URL is unset`。错误码枚举仍是 143。`node scripts/check-project-governance.cjs` 通过，输出为「治理检查通过：279 份 Markdown、378 项任务、33 项 Issue。」检查程序未修改。
