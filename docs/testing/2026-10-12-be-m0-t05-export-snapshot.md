为什么有这个文件：留下单章导出快照的核对方式。

它解决什么问题：确认绑定字段存在，并且资料变化后旧文件不再有效。

# 2026-10-12 导出快照核对

## 命令

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q --tb=line
node scripts/check-project-governance.cjs
```

## 行为

`tests/backend/test_export_snapshot.py` 覆盖：

- 导出响应含 `check_id`、`revision`、`content_hash`、`input_fingerprint` 和 `excludes_drafts: true`，没有 `stale`。
- 创建同公司资料后，用旧检查再导出返回 409 `CHECK_STALE`。
- 同一份旧文件下载返回 409 `EXPORT_STALE`。错误体仍是旧 `/api` 的 `error` 加 `request_id`。

## 结果

未设 `ICG_DATABASE_URL` 与 `ICG_REQUIRE_MYSQL` 时，`python3 -m pytest tests/backend -q --tb=line` 为 365 passed、13 skipped。其中一条警告是 StarletteDeprecationWarning，不记失败。`node scripts/check-project-governance.cjs` 通过：314 份 Markdown、387 项任务、35 项 Issue。ISSUE-005 仍为 in-progress。BE-M0-T05 为 in-review。T04 仍为 in-review。T06～T07 仍为 ready。
