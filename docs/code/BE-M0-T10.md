为什么有这个文件：说明进程如何只靠环境变量连上 MySQL，以及空迁移做了什么。

它解决什么问题：避免把“已经能连库”理解成回执、会话或业务表已经入库。

# BE-M0-T10：代码解释

- 对应任务：[BE-M0-T10](../tasks/BE-M0.md#be-m0-t10)；Issue：[ISSUE-018](../../issues/ISSUE-018.md)、[ISSUE-023](../../issues/ISSUE-023.md)；交付：[BE-M0-T10](../delivery/BE-M0-T10.md)
- 日期：2026-10-12。入口是 `icg_demo/database.py` 和 `icg_demo/main.py` 的 `create_app`。迁移在 `backend/bid-core/alembic.ini`。

## 改了什么以及为什么

未传入仓库时，`create_app` 调用 `repository_from_environment()`。`ICG_DATABASE_URL` 为空则返回 `MemoryRepository`。有值则创建 SQLAlchemy 引擎，强制 `utf8mb4` / `utf8mb4_0900_ai_ci`，执行 `SELECT 1`，失败则进程起不来。调用方显式传入的仓库优先，现有测试即使本地设了连接串也不会改走 MySQL。

`MysqlConnectionRepository` 只保存已验证的引擎。`read` 和 `transaction` 仍委托内存仓库。因此 `/health` 的 `repository` 是 `mysql`，`persistent` 仍是 `false`。

## 入口和调用顺序

1. `uvicorn icg_demo.main:app` 导入模块时执行 `create_app(use_configured_model=True)`。
2. 未传入 `repository`，于是读取 `ICG_DATABASE_URL`。
3. 有连接串时先连上 MySQL，再装配原来的路由。
4. 迁移不在启动时自动执行。运维另行运行 `alembic -c backend/bid-core/alembic.ini upgrade head`。`env.py` 只读同一环境变量；没有该变量时直接报错。密码不写入 `alembic.ini`。

空修订 `0001_baseline` 的 `upgrade` 和 `downgrade` 都是空操作。Alembic 只建立 `alembic_version`。

## 数据与状态

业务状态、幂等回执、登录会话和编辑租约仍在进程内存。本卡不创建这些表。字符集由驱动连接参数设置，不依赖调用方是否在连接串里写了 `charset`。

## 关键判断与异常

`mysql_gate()` 给测试用。没有连接串且 `ICG_REQUIRE_MYSQL` 不是 `1` 时，动作为 skip。该变量为 `1` 时，缺连接串或连不上都是 fail。连接串已设置但连不上、又未要求 MySQL 时，同样 fail，不跳过。失败原因只包含异常类型，不包含连接串。

标记 `mysql` 的测试在调用阶段执行这个判断，所以 pytest 记为 failed，而不是 setup error 或 skipped。

## 验证与限制

未设置连接串时后台测试 316 通过、2 条 mysql 测试跳过。镜像 `mysql:8.4` 上 2 条 mysql 测试通过，`ICG_REQUIRE_MYSQL=1` 时同样通过。详见交付和验证记录。回执跨进程、重启后仍在，以及租约表，都不在本卡。
