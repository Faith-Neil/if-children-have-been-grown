为什么有这个文件：说明回执和登录会话从哪一处写入 MySQL，以及导入时为什么不连接。

它解决什么问题：避免连接发生在 pytest 收集阶段，也避免把 2048 条内存上限套到未过期的库内回执上。

# BE-M0-T11：代码解释

- 对应任务：[BE-M0-T11](../tasks/BE-M0.md#be-m0-t11)；Issue：[ISSUE-018](../../issues/ISSUE-018.md)；交付：[BE-M0-T11](../delivery/BE-M0-T11.md)
- 日期：2026-10-12。入口仍是 `repository_from_environment()`，实现在 `icg_demo/database.py`。

## 改了什么以及为什么

`create_app()` 在 `main.py` 导入时就会执行。以前 `MysqlConnectionRepository` 在构造时连接并执行 `SELECT 1`，连接串不可达时，收集测试就会报错。现在构造只保存连接串。`.engine` 第一次被读取时才建引擎，超时仍是 `CONNECT_TIMEOUT_SECONDS = 3`。连不上就丢掉引擎并抛出原来的异常，不把密码写进日志。

迁移 `0002_sessions_receipts` 建立方案里的 `idempotency_receipt` 和 `user_session`。幂等键、指纹和会话令牌使用 `utf8mb4_bin`。连接时把会话时区设为 `+00:00`。过期行在读取前按 `NOW(6)` 删除，不使用事件调度器，也不按 2048 条裁剪。内存仓库的 `cap_receipts` 仍为 True。

## 入口和调用顺序

1. 未设置 `ICG_DATABASE_URL` 时返回 `MemoryRepository`。设置后返回尚未连接的 MySQL 仓库。调用方传入的仓库优先。
2. `read()` 复制内存中的业务状态，再叠上库里的会话和未过期回执。这次读取不把这两份字典写回内存。
3. `transaction()` 在内存事务里先装载这两份数据，并把 `cap_receipts` 设为 False。业务回调仍改内存中的 `DemoState`。
4. 回调成功后，按本次装载的快照做差量：新增的键插入，本次装载过又被删掉的键删除，不删除别的进程新写入、本进程没装载过的行。主键冲突时事务失败，内存也不提交。
5. 数据库提交成功后，清掉工作副本上的会话和回执，再让内存仓库提交业务数据。回调抛错时两边都不提交，因此失败不留回执。

## 数据与状态

回执键是 `scope_id + user_id + idempotency_key`。`expires_at` 是 `created_at` 加 24 小时。登录令牌没有过期时间，对应 `DemoState.sessions`。种子账号在每个进程的内存里都有，所以从 MySQL 装回的令牌在重启后仍能认证。

资料、章节和租约仍只在内存。跨进程重放返回已保存的 JSON，不重新执行业务写入。

## 关键判断与异常

同一幂等键并发插入时，后到的插入因主键失败并回滚。客户端再用同一键请求时会重放。本卡没有把该冲突改写成 409。`downgrade()` 先删 `user_session`，再删 `idempotency_receipt`。没有新依赖。

## 验证与限制

mysql 标记测试覆盖两进程重放、进程退出后的令牌、失败不写回执、2049 条不裁剪，以及 downgrade base 后再 upgrade head。未设置连接串时这些测试跳过。不可达地址在 `ICG_REQUIRE_MYSQL=1` 下于数秒内 failed，而不是收集 error。工作流文件未改。
