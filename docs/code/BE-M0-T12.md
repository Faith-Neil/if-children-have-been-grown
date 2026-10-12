为什么有这个文件：说明编辑租约从哪一处写入 MySQL，以及为什么没有按字典 v1.9 建全表。

它解决什么问题：避免把 120 秒演示租约写成已经实现了心跳、公司隔离和历史锁。

# BE-M0-T12：代码解释

- 对应任务：[BE-M0-T12](../tasks/BE-M0.md#be-m0-t12)；Issue：[ISSUE-018](../../issues/ISSUE-018.md)；交付：[BE-M0-T12](../delivery/BE-M0-T12.md)
- 日期：2026-10-12。入口仍是 `repository_from_environment()`，实现在 `icg_demo/database.py`。

## 改了什么以及为什么

迁移 `0003_chapter_lease` 建立 `chapter_lease`。主键是 `chapter_id`。`token` 和 `session_token` 使用 `utf8mb4_bin`。没有外键，因为 `chapter` 表还没有。

`transaction()` 在装载会话和回执之后，把库里的租约叠到对应章节的 `lock` 上。回调仍使用原来的 `acquire_lock`、`renew_lock` 和 `release_lock`。成功后按装载快照做差量：新租约插入，到期时间或令牌变化则更新，本次装载过又被清掉的行删除。不删除别的进程新写入、本进程没装载过的行。数据库提交成功后，清掉工作副本上的 `lock`，再让内存仓库提交正文。未设置连接串时这条路径不运行。

## 入口和调用顺序

1. 未设置 `ICG_DATABASE_URL` 时返回 `MemoryRepository`。设置后返回尚未连接的 MySQL 仓库。`create_app()` 导入时不连接。
2. `read()` 和 `transaction()` 第一次使用 `.engine` 才连接，超时仍是 3 秒。
3. 续期只改 `expires_at`。令牌、占用者和会话令牌保持不变。时长仍是 `LEASE_SECONDS = 120`。
4. 另一个会话在租约未过期时仍被拒绝。把 `expires_at` 改到过去之后，新的登录会话可以取得新令牌。

## 数据与状态

对照字典 v1.9 的 `edit_lock`。本表只有当前租约的五个字段。心跳、取得时间、接管原因、释放原因、`company_id` 和 A 组审计列都没有。这些偏差和理由写在方案第 5 节，需要项目经理批准。

## 关键判断与异常

过期行不在读取前按 `NOW(6)` 删除。领域代码自己比较应用时钟，过期的租约仍能被新会话替换。`downgrade()` 删除 `chapter_lease`。没有新依赖。

## 验证与限制

mysql 标记测试覆盖跨进程续期、未过期拒绝和过期接管。未设置连接串时这些测试跳过，其余后台测试仍走内存。正文、草稿和审计仍只在内存。
