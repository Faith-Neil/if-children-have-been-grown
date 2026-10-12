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
| 密码 | `openssl rand -hex 24`，`::add-mask::`，经 `$GITHUB_ENV` 传给后续步骤。仓库和工作流里没有固定密码 |
| 迁移 | 仓库根 `alembic -c backend/bid-core/alembic.ini upgrade head` |
| 测试 | `python -m pytest tests/backend -m mysql --junitxml=mysql-junit.xml -q` |
| 守卫 | junit 缺失、0 条、全部跳过，或有失败/错误时失败 |

当前标记 `mysql` 的测试在 `tests/backend/test_mysql_connection.py`，共 2 条。它们检查空迁移后的 `alembic_version`，以及 `GET /health` 的 `repository` 为 `mysql`。连接排序规则仍是代码里的 `utf8mb4_0900_ai_ci`。

## 执行过的检查

提交前运行 `node scripts/check-project-governance.cjs`，输出为：治理检查通过：206 份 Markdown、362 项任务、25 项 Issue。该检查不启动 MySQL。数字含同分支已并入的 ISSUE-026。

推送后的 `backend-mysql` 作业结果在作业完成后补记。本地这次没有启动 MySQL 容器。

## 未执行

- 没有把密码、连接串或客户正文写入仓库。
- 没有改原 `backend` 作业，它仍不设置 `ICG_DATABASE_URL`。
- 没有做两个进程共享回执或会话的测试。
- 作业通过也不表示已经合入或已经部署到公司内网。
