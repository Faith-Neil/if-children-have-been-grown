为什么有这个文件：记录托管 MySQL 作业实际跑了什么，以及密码有没有进仓库。

它解决什么问题：避免用工作流文件存在代替一次真实的 mysql 标记测试。

# BE-M0-T14 托管 MySQL 作业核对

日期 2026-10-12。ISSUE-025 / BE-M0-T14。分支 `codex/repository-foundation`。关联连接实现 `7d97369`。

## 作业约定

| 项 | 实际写法 |
|---|---|
| 运行器 | `ubuntu-24.04` |
| Python | 3.13.5，与既有 backend 作业相同 |
| 权限 | 作业级 `contents: read`。不引用 `secrets` |
| 镜像 | `mysql:8.4`，由步骤内 `docker run` 启动，不用 `services:` |
| 服务器字符集 | `utf8mb4` / `utf8mb4_unicode_ci` |
| 库 | `icg_demo` |
| 连接 | `ICG_DATABASE_URL=mysql+pymysql://root:<runtime>@127.0.0.1:3306/icg_demo?charset=utf8mb4`，另设 `ICG_REQUIRE_MYSQL=1` |
| 密码 | `openssl rand -hex 24`，`::add-mask::`。密码文件只给启动步骤。后续步骤只收到 `ICG_DATABASE_URL`。仓库和工作流里没有固定密码，也不导出 `ICG_MYSQL_PASSWORD` |
| 迁移 | 仓库根 `alembic -c backend/bid-core/alembic.ini upgrade head` |
| 测试 | `python -m pytest tests/backend -m mysql --junitxml=mysql-junit.xml -q` |
| 守卫 | junit 缺失、0 条、任一跳过，或有失败/错误时失败 |

当前标记 `mysql` 的测试在 `tests/backend/test_mysql_connection.py`，共 2 条。它们检查空迁移后的 `alembic_version`，以及 `GET /health` 的 `repository` 为 `mysql`。连接排序规则仍是代码里的 `utf8mb4_0900_ai_ci`。

## 执行过的检查

`b91d331` 提交前的治理检查输出为：治理检查通过：206 份 Markdown、362 项任务、25 项 Issue。该检查不启动 MySQL。数字含当时已并入的 ISSUE-026。

本次补记前再次运行，输出为：治理检查通过：213 份 Markdown、362 项任务、27 项 Issue。多出来的文档和 Issue 来自已并入的 ISSUE-010 决定记录，以及 ISSUE-028、ISSUE-029。任务数仍是 362。该检查不启动 MySQL。

推送 `b91d331` 后的作业：https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/38207508936 。`backend-mysql` 成功。库字符集输出为 `utf8mb4` / `utf8mb4_unicode_ci`。pytest 为 2 passed、320 deselected。junit 为 tests=2、skipped=0、failures=0、errors=0。密码在日志里显示为掩码。本地这次没有启动 MySQL 容器。第一次推送 `763064a` 的启动步骤赶上了镜像的临时初始化服务器，已改为等到 `MySQL init process done` 且 ping 成功。

## 未执行

- 没有把密码、连接串或客户正文写入仓库。
- 没有改原 `backend` 作业，它仍不设置 `ICG_DATABASE_URL`。
- 没有做两个进程共享回执或会话的测试。
- 作业通过也不表示已经合入或已经部署到公司内网。
