为什么有这个文件：说明项目聚合从哪一处写入 MySQL，以及哪些聚合仍留在内存。

它解决什么问题：避免把两张演示表看成已经实现了字典 v1.9 的投标项目和成员行。

# BE-M0-T13：代码解释

- 对应任务：[BE-M0-T13](../tasks/BE-M0.md#be-m0-t13)；Issue：[ISSUE-018](../../issues/ISSUE-018.md)；交付：[BE-M0-T13](../delivery/BE-M0-T13.md)
- 日期：2026-10-12。入口仍是 `repository_from_environment()`，实现在 `icg_demo/database.py`。

## 改了什么以及为什么

迁移 `0004_demo_project` 建立 `demo_project` 和 `demo_project_team`。敏感列名为 `is_sensitive`，因为 MySQL 把 `sensitive` 当作保留字，也与字典列名一致。分工是 JSON，不是 `bid_project_member` 的多行。

`transaction()` 在装载会话、回执和租约之后，把库里的项目和分工叠到当前内存上。回调仍使用原来的 `create_project`。成功后按装载快照做差量：本次没装载过且有变化的项目插入；装载过且有变化的项目按旧 `revision` 更新。受影响行数不是 1 时抛出 409 `REVISION_CONFLICT`，SQL 事务回滚，内存仓库也不提交。数据库提交成功后，仍清掉工作副本上的会话、回执和租约，但不清项目。未改过的种子项目不插入，所以空表不会抹掉种子。

## 入口和调用顺序

1. 未设置 `ICG_DATABASE_URL` 时返回 `MemoryRepository`。设置后返回尚未连接的 MySQL 仓库。`create_app()` 导入时不连接。
2. `read()` 和 `transaction()` 第一次使用 `.engine` 才连接，超时仍是 3 秒。
3. 另一个进程读到已提交项目的名称、公司、版本、招标编号、截止时间、敏感标记和负责人。
4. 同一项目在写入进程内存里新建的章节不写入这两张表。另一个进程的章节列表为空。种子章节，例如 `alpha-tech`，仍在各自进程的内存里。

## 数据与状态

对照字典 v1.9 的 `bid_project` 和 `bid_project_member`。偏差和理由写在方案第 6 节，需要项目经理批准。未批准前不补状态、主体、成员行和 A 组审计列。

## 关键判断与异常

失败的回调在保存之前抛出时，不插入项目行，内存也不出现该项目。`downgrade()` 先删 `demo_project_team`，再删 `demo_project`。没有新依赖。

## 验证与限制

mysql 标记测试覆盖跨进程可见、章节不入库、失败回滚和旧版本不覆盖。未设置连接串时这些测试跳过。章节、检查与导出、资料与承诺、工作流与任务、审计仍只在内存。
