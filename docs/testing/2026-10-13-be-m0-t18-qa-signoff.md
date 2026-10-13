为什么有这个文件：记录QA对BE-M0-T18 / ISSUE-033（挂证据运行时规则）的正式签署。

它解决什么问题：相对 REV-M0-T26（仅规格），确认运行时拒绝过期/缺协议/受限，并复用既有错误码。

# BE-M0-T18 / ISSUE-033 挂证据运行时 QA签署（REV-M0-T35）

- 被验 tip：`90b2334`；运行时接通含 `af51151` 及后续 merge。
- 环境：未设数据库连接串；仅合成数据。
- 结论：**通过**。**BE-M0-T18 / ISSUE-033 / 本卡均不标 done / closed**。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| AC-01 过期 vs 长期 | 通过 | `test_evidence_mount.py`：过期非长期 → 409 `EVIDENCE_EXPIRED`；`is_long_term` 可挂接；对照项目截止（非「今天」） |
| AC-02 reference / 缺协议 | 通过 | `reference` 与缺 `agreement_attachment_id` 的 partner → 409 `EVIDENCE_NOT_USABLE`，说明不同 |
| AC-03 `is_restricted` | 通过 | 旧字段名 `restricted` → 422；无权 → 403 `FORBIDDEN`；授权/管理员可挂 |
| AC-04 不新增错误码 | 通过 | 名单仍 143；`set(ERROR_STATUS)==FROZEN_NAMES` |
| 字段与字典 | 通过 | 运行时用 `is_restricted`（非 `restricted`）；`agreement_present` 由 `project_partner.agreement_attachment_id` 派生；`valid_to`/`is_long_term` 对照项目截止 |
| 专项 + 无库全量 | 通过 | `test_evidence_mount.py` + contract；全量 **381 passed，13 skipped** |

## 独立复跑命令

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend/test_evidence_mount.py tests/backend/test_evidence_mount_contract.py -q --tb=line
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend -q --tb=line
node scripts/check-project-governance.cjs
```

## 观察项

- O-1：合作方/授权仍在内存，不进 MySQL（ISSUE-035 / T19）。
- O-2：智能匹配与规则 2 端到端不在本卡关闭。
- O-3：REV-M0-T26 为规格复签，本卡为运行时重签。

## 状态

BE-M0-T18、ISSUE-033、REV-M0-T35 均保持 **in-review**，**不标 done / closed**。
