为什么有这个文件：记录QA对BE-M0-T04（编辑租约迁到 /api/v1）的正式签署。

它解决什么问题：确认 v1 取得/续期/释放与旧规则一致，旧 /api 入口仍在，OpenAPI 含三条路径。

# BE-M0-T04 编辑租约迁到 /api/v1 QA签署（REV-M0-T32）

- 被验 tip：`90b2334`（`codex/repository-foundation`，含 PR #4 merge）；实现提交含 `471675c`。
- 环境：Linux；Python 3.13；venv `/workspace/qa-venv`；**未设** `ICG_DATABASE_URL` / `ICG_REQUIRE_MYSQL`（本卡交付约定）。
- 结论：**通过**。**BE-M0-T04 / ISSUE-005 / 本卡均不标 done / closed**，等项目经理设置。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| v1 取得/续期 120 秒、接管与释放 | 通过 | `tests/backend/test_v1_lease.py`：到期=时钟+120；续期令牌不变；无理由 423 `LOCK_HELD` 且体为 `{code,message,details,traceId}`；缺理由 409 `TAKEOVER_REASON_REQUIRED`；编写人接管 403 `FORBIDDEN`；释放 `{released:true}` |
| 旧 `/api` 锁入口保留 | 通过 | 旧 renew 仍 200，成功体无 `traceId` |
| OpenAPI 三条 v1 路径 | 通过 | 运行中 OpenAPI 与 `spec/openapi/demo-v1.json` 均含 `/api/v1/chapters/{chapter_id}/lock`、`/lock/renew`、`/lock/release` |
| 专项 + 无库全量 | 通过 | 专项（lease/export/evidence/error）**20 passed**；`pytest tests/backend -q` → **381 passed，13 skipped** |
| 治理 | 通过 | 签署前基线：322 Markdown、389 任务、36 Issue；签署提交后加本卡再跑 |

## 独立复跑命令

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend/test_v1_lease.py -q --tb=line
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python -m pytest tests/backend -q --tb=line
# → 381 passed, 13 skipped
node scripts/check-project-governance.cjs
```

## 观察项

- O-1（P3）：设 `ICG_DATABASE_URL` 时部分租约用例会因跨测残留租约失败（隔离问题）；本卡验收按交付约定在无库下签署。
- O-2：不关闭 ISSUE-005；T06/T07 仍 ready。

## 状态

BE-M0-T04、ISSUE-005、REV-M0-T32 均保持 **in-review / in-progress**，**不标 done**。未发布。
