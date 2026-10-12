为什么有这个文件：留下项目聚合入库的两种测试方式。

它解决什么问题：避免只说项目已经入库，却没有未设库时的跳过结果，也没有跨进程和回滚的库内结果。

# 2026-10-12 项目聚合核对

关联 [ISSUE-018](../../issues/ISSUE-018.md)、[BE-M0-T13](../delivery/BE-M0-T13.md)。状态 in-review。只用合成数据。密码不进仓库，也不写进本文。

## 未设置数据库

工作目录为仓库根。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：351 passed，11 skipped。11 条跳过都带 mysql 标记。其中 8 条是本卡之前的连接、回执、会话和租约测试，3 条是本卡的项目测试。

## 本地 mysql:8.4

容器只监听本机。连接串来自 `ICG_DATABASE_URL`，并设置 `ICG_REQUIRE_MYSQL=1`。密码不写入仓库。

```text
python3 -m pytest tests/backend -m mysql -q
```

结果：11 passed。跨进程读取能看见项目名称、公司、版本 1、敏感标记否和负责人 `alpha-manager`。该项目的章节列表为空。种子项目 `alpha-project` 不在 `demo_project` 里。回调中途失败时没有项目行。把库中的 `revision` 改掉后再保存，返回 409 `REVISION_CONFLICT`，名称不被覆盖。

## 治理

```text
node scripts/check-project-governance.cjs
```

结果：`治理检查通过：273 份 Markdown、375 项任务、31 项 Issue。`
