为什么有这个文件：记录QA对ISSUE-033规格增量（32b184c）的契约复签。

它解决什么问题：确认冻结契约映射符合项目经理批准方案，并写明运行时仍待后端。

# ISSUE-033 规格增量契约复签（REV-M0-T26）

- 被验提交：`32b184c`（spec: ISSUE-033 evidence fields is_restricted and mount guards）；复核基线：`ab3fbb7`（含该提交）；关联 ISSUE-033 / BE-M0-T18；数据：仅合成数据。
- 结论：**规格通过**。运行时未接通。**ISSUE-033 保持 in-progress，不标 closed；BE-M0-T18 仍 planned；本卡不标 done**。

## 验收对照（PM 批准映射）

| 检查 | 结果 | 证据 |
|---|---|---|
| 对外字段 `is_restricted`（不用 `restricted`） | 通过 | `EvidenceMountFields.properties` 含 `is_restricted`，无 `restricted`；`x-implemented: false` |
| `agreement_present` 派生、只读、不入库 | 通过 | `readOnly: true`；描述含「派生」「不入库」「agreement_attachment_id」 |
| 有效期 `valid_to`/`is_long_term` 对照 `bid_deadline_at` | 通过 | 描述与 `x-issue-033.compare_deadline` 均为 `bid_deadline_at`；不对照今天；expiring 允许挂；unknown 不 409 |
| PATCH 复用三码，不新增错误码 | 通过 | 规则写 409 `EVIDENCE_EXPIRED`、409 `EVIDENCE_NOT_USABLE`、403 `FORBIDDEN`；`V1Error.code` 仍 143；`set(ERROR_STATUS)==FROZEN_NAMES` |
| 冻结名字未擅自改动 | 通过 | 契约枚举长度 143；实现契约与 `create_app().openapi()` 一致 |

## 套件与 CI

- `pytest tests/backend/test_evidence_mount_contract.py tests/backend/test_error_idempotency.py`：**10 passed**（Python 3.13，`/workspace/qa-venv`）。
- CI [run 38228282444](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38228282444)（head `32b184c`）：五个 job 全绿。

## 观察项

- O-1：运行时尚未返回这些字段，也不按规则拒绝；等后端 ISSUE-033 实现后再行为验。
- O-2：本卡与 ISSUE-033 / BE-M0-T18 **不标 done**。
