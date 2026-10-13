为什么有这个文件：记录QA对BE-M0-T05（导出快照语义）的正式签署。

它解决什么问题：确认导出绑定检查/版本/正文摘要/输入摘要，来源变化后旧导出失效。

# BE-M0-T05 导出快照语义 QA签署（REV-M0-T33）

- 被验 tip：`90b2334`；实现提交含 `d67eeb3`。
- 环境：同 T04；**未设**数据库连接串。
- 结论：**通过**。**BE-M0-T05 / ISSUE-005 / 本卡均不标 done / closed**。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| 绑定字段 | 通过 | `ExportResponse` / `test_export_snapshot.py`：含 `check_id`、`revision`、`content_hash`、`input_fingerprint`、`excludes_drafts: true`；无 `stale` 布尔字段 |
| 来源变化后旧导出失效 | 通过 | 资料变化后旧检查再导出 409 `CHECK_STALE`；旧文件下载 409 `EXPORT_STALE` |
| 专项 + 无库全量 | 通过 | 专项 20 passed；全量 **381 passed，13 skipped** |
| 治理 | 通过 | 同签署提交治理检查 |

## 独立复跑命令

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend/test_export_snapshot.py -q --tb=line
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend -q --tb=line
node scripts/check-project-governance.cjs
```

## 观察项

- O-1：不把导出改成异步；不新增错误码；不关闭 ISSUE-005。

## 状态

BE-M0-T05、ISSUE-005、REV-M0-T33 均保持 **in-review / in-progress**，**不标 done**。
