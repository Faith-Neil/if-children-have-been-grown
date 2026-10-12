为什么有这个文件：记录QA对BE-M0-T11（幂等回执与登录会话入库，ISSUE-018）的正式签署。

它解决什么问题：在真实 MySQL 8.4 上证明跨进程重放、重启后会话/回执仍在、downgrade base 再 upgrade head，以及 Q2 快速失败。

# BE-M0-T11 幂等回执与登录会话入库 QA签署（REV-M0-T28）

- 被验提交：`631d4c9`（feat: store idempotency receipts and sessions in MySQL）；复核基线：`9e3fcdd`（含后续聚合/租约表与 ISSUE-028 假端点夹具，不改 T11 行为）。
- 环境：Linux；Python 3.13；venv `/workspace/qa-venv`；MySQL 8.4.6 监听 `127.0.0.1:33061`，库 `icg`、用户 `icg`，密码只经 `/tmp/qa-mysql-pw` 进环境变量，不进仓库与日志。
- 结论：**通过**。**BE-M0-T11 / ISSUE-018 / 本卡均不标 done / closed**，等项目经理设置。REV-M0-T27 留给 Codex PR #4 / ISSUE-034 改号，本签署用 **REV-M0-T28**。

## 验收对照

| 检查 | 结果 | 证据 |
|---|---|---|
| 未设 `ICG_DATABASE_URL` 后台回归 | 通过 | `env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL pytest tests/backend -q` → **355 passed，13 skipped**（mysql 标记跳过） |
| 真实 MySQL：`ICG_REQUIRE_MYSQL=1` `-m mysql` | 通过 | **12 passed**（含 connection / sessions_receipts / leases / projects） |
| QA M1：`test_alembic_downgrade_to_base_then_upgrade_restores_tables` | 通过 | 单测复跑 **1 passed**；降回 base 后无 `idempotency_receipt` / `user_session`（及后续业务表），再 `upgrade head` 六表恢复 |
| Q2：不可达地址快速失败 | 通过 | `ICG_REQUIRE_MYSQL=1 ICG_DATABASE_URL=…@127.0.0.1:1/…` 跑 health 用例：摘要 **failed**（非 error），整段约 **1.06s**（pytest 0.66s）；输出无 `secret`；`create_app()` 后 `_engine` 仍为 `None` 直至访问 `.engine` |
| 跨进程回执重放 + 会话 | 通过 | `test_receipt_and_session_survive_a_new_process`；失败写不存回执；MySQL 保留 2049 条不被 2048 裁剪 |
| 双 worker 在线 + 重启存活 | 通过 | uvicorn `uvicorn --workers 2`：同键同正文第二次 `Idempotent-Replayed: true`；停掉后 `--workers 1` 再起，原 Bearer `GET /api/v1/session` 仍 200（`alpha-editor`），同键仍重放且 item id 不变；日志/探针无密码 |
| 密码遮蔽 | 通过 | `repr(engine.url)` / `str(engine.url)` 为 `mysql+pymysql://icg:***@…`；uvicorn/health/探针日志 0 次命中真实密码 |
| CI（被验提交） | 通过 | [run 38212536927](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38212536927)（head `631d4c9`）五 job 全绿，含 `backend-mysql` |

## 观察项

- O-1（P3）：`/health` 在 `--workers 2` 时仍报 `single_process: true`（与多 worker 事实不符，不挡签署；建议后端另卡澄清）。
- O-2（P3）：`persistent: false` 仍表示业务聚合未全入库，属 ISSUE-018 范围，本卡不关闭 Issue。
- O-3：先前記号 run `38213011076` 对应文档提交 `e3ec97b`，不是 `631d4c9`；本签署以 `38212536927` 为准。

## 状态

BE-M0-T11、ISSUE-018、REV-M0-T28 均保持 **in-review / in-progress**，**不标 done**。未合入，未发布。
