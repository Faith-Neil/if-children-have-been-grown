为什么有这个文件：留下连接、空迁移和严格测试开关的实际结果。

它解决什么问题：让运维按同一组命令接入内网 MySQL，并让 QA 核对 uvicorn 是否只靠环境变量启动。

# 2026-10-12 MySQL 连接与空迁移

关联 [ISSUE-023](../../issues/ISSUE-023.md)、[ISSUE-018](../../issues/ISSUE-018.md)、[BE-M0-T10](../delivery/BE-M0-T10.md)。镜像 `mysql:8.4`。密码没有写入仓库。

## 给运维

业务库环境变量是 `ICG_DATABASE_URL`。密码只放在执行机环境里。示例（把 USER 和 PASSWORD 换成内网账号）：

```text
ICG_DATABASE_URL=mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/icg_demo?charset=utf8mb4
```

在仓库根目录执行迁移：

```text
alembic -c backend/bid-core/alembic.ini upgrade head
```

没有 `ICG_DATABASE_URL` 时这条命令失败，并且不会从文件里读取密码。当前修订 `0001_baseline` 不创建业务表，只留下 `alembic_version`。

内网 CI 先起镜像 `mysql:8.4`，再执行迁移，然后：

```text
ICG_REQUIRE_MYSQL=1 python -m pytest tests/backend -m mysql
```

`ICG_REQUIRE_MYSQL=1` 时，标记 `mysql` 的测试在连接串缺失或数据库连不上时失败，不能跳过。未设置该变量且没有连接串时，这些测试跳过。原 `backend` 作业仍不设置该变量。ISSUE-025 的 `backend-mysql` 作业另行设置，并在运行器上启动 `mysql:8.4`。

字符集为 `utf8mb4`，排序规则为 `utf8mb4_0900_ai_ci`。进程不记录连接串。

## 本次执行

- 未设置 `ICG_DATABASE_URL`：`python -m pytest tests/backend -q` 为 316 passed、2 skipped。两条跳过的是 mysql 标记测试。
- 设置连接串且 `ICG_REQUIRE_MYSQL=1`：`python -m pytest tests/backend -m mysql` 为 2 passed、316 deselected。
- 只设置 `ICG_REQUIRE_MYSQL=1`、不设置连接串：同一选择为 2 failed，摘要里没有 skipped。
- `alembic -c backend/bid-core/alembic.ini upgrade head` 成功。库表只有 `alembic_version`。连接字符集为 `utf8mb4` / `utf8mb4_0900_ai_ci`。
- 容器镜像标签为 `mysql:8.4`。

## 给 QA

只设置 `ICG_DATABASE_URL`，在 `backend/bid-core` 上启动 `uvicorn icg_demo.main:app`。进程完成启动。`GET /health` 返回：

```json
{"status":"ok","mode":"local-demo","repository":"mysql","model":"mock","persistent":false,"single_process":true}
```

`repository` 为 `mysql` 表示已经连上。`persistent` 仍为 false，因为回执、会话和业务行还在内存里。uvicorn 日志中没有密码。

未覆盖：两个进程共享回执、重启后会话仍有效、租约表。这些属于后续卡。
