为什么有这个文件：说明托管 MySQL 作业怎样启动，以及密码停在哪里。

它解决什么问题：避免以后把固定密码写回工作流，或把这个作业当成业务数据已经入库。

# BE-M0-T14：代码解释

- 对应任务、Issue、交付文档：[BE-M0-T14](../tasks/BE-M0.md#be-m0-t14)、[ISSUE-025](../../issues/ISSUE-025.md)、[交付](../delivery/BE-M0-T14.md)。
- 日期、实际代码路径、提交 / PR：2026-10-12；`.github/workflows/offline-check.yml`；分支 `codex/repository-foundation`。未创建新 PR。

## 改了什么以及为什么

原 `backend` 作业不设置 `ICG_DATABASE_URL`，标记 `mysql` 的测试会跳过。本卡只增加并行作业 `backend-mysql`。服务容器的环境变量在作业开始前就固定，放不进运行时随机密码，所以改为在步骤里 `docker run mysql:8.4`。仓库不保存密码。

## 入口和调用顺序

1. `Generate runtime database password` 用 `openssl rand -hex 24` 生成 48 位十六进制密码，立刻 `::add-mask::`。密码写入 `$RUNNER_TEMP/mysql-secret/`，并把 `ICG_DATABASE_URL`、`ICG_REQUIRE_MYSQL=1`、`ICG_MYSQL_PASSWORD` 写入 `$GITHUB_ENV`。这些值不打印到步骤日志。
2. `Start MySQL 8.4` 用 `MYSQL_ROOT_PASSWORD_FILE` 读取密码文件，不把密码放在 `docker run` 的 `-e` 参数里。服务器参数是 `--character-set-server=utf8mb4` 和 `--collation-server=utf8mb4_unicode_ci`。镜像在初始化时会先起一个临时服务器，Docker 健康状态可能过早变成 healthy。步骤改为等到日志出现 `MySQL init process done` 并且 `mysqladmin ping` 成功，再执行 `CREATE DATABASE IF NOT EXISTS icg_demo`。日志正文不打印到作业输出。
3. 在仓库根执行 `alembic -c backend/bid-core/alembic.ini upgrade head`。
4. `python -m pytest tests/backend -m mysql --junitxml=mysql-junit.xml -q`。
5. 守卫读取 junit。文件不存在、`tests` 为 0、跳过数等于测试数，或存在失败/错误时，步骤退出 1。

连接串形如 `mysql+pymysql://root:<runtime>@127.0.0.1:3306/icg_demo?charset=utf8mb4`。用户名是容器的 root。应用连接仍按 `database.py` 使用 `utf8mb4_0900_ai_ci`，与服务器默认排序规则不是同一项。

## 数据与状态

作业只创建 `icg_demo` 和 Alembic 的 `alembic_version`。业务读写仍委托内存仓库。会话和幂等回执不入库。密码文件留在运行器临时目录，不进入 Git。

## 关键判断与异常

- 不使用 `MYSQL_RANDOM_ROOT_PASSWORD`，因为该模式会把生成的密码打进容器日志。
- 不使用 `services:`，因为那里不能引用本步骤才生成的密码。
- 作业权限只有 `contents: read`。工作流不引用 `secrets`。
- 原 `backend` 作业不设置连接串，标记测试继续跳过。
- 健康检查失败时只打印“MySQL did not become healthy”，不转储容器日志，避免日志里偶然出现口令。

## 验证与限制

核对见 [2026-10-12 MySQL CI](../testing/2026-10-12-backend-mysql-ci.md)。本作业不覆盖两个进程共享回执，也不覆盖公司内网的 MySQL。
