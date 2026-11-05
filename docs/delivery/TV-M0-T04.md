为什么有这个文件：记录 TV-M0-T04 实际改了什么。

它解决什么问题：避免把条款抽取写成目录和正文已经按教程生成。

# TV-M0-T04 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T04](../tasks/TV-M0.md#tv-m0-t04) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-03 |
| 状态 | in-review。不标 done |
| 代码解释 | [TV-M0-T04](../code/TV-M0-T04.md) |

## 实际变更

- 技术分册点「抽取技术条款」后，主观分里用顿号、逗号、分号分开的要点各成一条。
- 规格书按编号逐条抽取。定义、封面、目录、客观分、资质和报价不抽。
- 评分要点和规格书说的是同一件事时，只留一行，两处来源都记在这行上。
- 一条都没抽到时，页面说明这批文件里没有技术响应内容，不进入目录和矩阵。
- 两册旧项目仍用原来的解析。

## 验证

- `tests/backend/test_technical_sources.py`：5 项通过。在关掉数据库连接后的内存仓储里跑。
- `export_openapi.py --check` 通过。
- 没有在浏览器里点抽取。

## 剩余

单章目录、矩阵响应和正文生成都还没做。抽出的条款还不会自动排成服务方案目录。上面两句是本卡完成时的边界。后续卡在同一分支继续，本卡仍是 in-review。

## 集成

集成分支 `feat/iss-047-technical-volume-mvp` 从决定记录 `0b9d1d5` 拉出，父提交是 `origin/main` 的 `36b7e41`。产品提交只在这条分支，不合并进 main。PR #7 只有决定记录，不接收本卡代码，本轮关闭。2026-11-03 在关掉数据库连接的内存仓储里，`python -m pytest tests/backend/test_technical_sources.py` 为 12 项通过，`python backend/bid-core/export_openapi.py --check` 通过。
