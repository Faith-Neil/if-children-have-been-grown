为什么有这个文件：留下回执和会话入库的三条测试方式，以及 QA 怎样用两个 worker 再做一次重启。

它解决什么问题：避免只说已经入库，却没有未设库、本地 MySQL 和不可达地址各自的结果。

# 2026-10-12 幂等回执与登录会话核对

关联 [ISSUE-018](../../issues/ISSUE-018.md)、[BE-M0-T11](../delivery/BE-M0-T11.md)。状态 in-review。只用合成数据。密码不进仓库，也不写进本文。

## 未设置数据库

工作目录为仓库根。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：349 passed，6 skipped。mysql 标记测试被跳过。内存仓库仍把回执裁到 2048 条；`cap_receipts=False` 的用例保留 2049 条。并入 e6215d4 的片段发布测试后，通过数从 338 增到 349。

## 本地 mysql:8.4

先启动 `mysql:8.4`，字符集 `utf8mb4`，排序 `utf8mb4_0900_ai_ci`，库名 `icg_demo`。`ICG_DATABASE_URL` 只放在环境里。然后：

```text
alembic -c backend/bid-core/alembic.ini upgrade head
ICG_REQUIRE_MYSQL=1 python3 -m pytest tests/backend -m mysql -q
```

结果：6 passed。其中包括两个新进程之间的资料写入与重放、进程退出后的登录令牌、失败不写回执、2049 条回执不被裁剪，以及 `downgrade base` 后再 `upgrade head` 时 `idempotency_receipt` 和 `user_session` 先消失再出现。

DevOps 可以把后两条 alembic 命令加进 `backend-mysql`。该作业现有的 `python -m pytest tests/backend -m mysql` 已经会执行这条测试。本卡不改 `.github` 工作流。

## 要求 MySQL 但地址不可达

```text
ICG_REQUIRE_MYSQL=1 ICG_DATABASE_URL='mysql+pymysql://user:secret@127.0.0.1:1/icg_demo' python3 -m pytest tests/backend/test_mysql_connection.py::test_health_uses_mysql_connection_without_code_change -m mysql -q --tb=line
```

这条由 `tests/backend/test_mysql_gate.py` 在子进程里执行。2026-10-12 测得整段 pytest 约 1.53 秒。最后一行摘要含 `failed`，不含 `error`，输出不含 `secret`。`connect_timeout` 为 3 秒。导入 `create_app()` 时 `_engine` 仍是空的。

## QA：两个 worker，然后重启

1. 启动 MySQL，只在环境里设置 `ICG_DATABASE_URL`。
2. 在仓库根执行 `alembic -c backend/bid-core/alembic.ini upgrade head`。
3. 在 `backend/bid-core` 执行 `python3 -m uvicorn icg_demo.main:app --host 127.0.0.1 --port 8000 --workers 2`。
4. 用合成账号登录。把同一次 `Idempotency-Key` 和相同正文再发一次，响应头 `Idempotent-Replayed` 为 `true`，正文与第一次相同。
5. 停掉进程再启动。原来的 Bearer 令牌仍能通过 `GET /api/v1/session`。未过期回执仍能重放。
6. 去掉 `ICG_DATABASE_URL` 后再启动，仓库回到内存。不要把密码打进日志。

自动化测试用两个先后退出的新解释器覆盖了第 4 步和第 5 步。两个 worker 同时在线的手工检查留给 QA。

## 治理

```text
node scripts/check-project-governance.cjs
```

输出：

```text
治理检查通过：234 份 Markdown、366 项任务、28 项 Issue。
```
