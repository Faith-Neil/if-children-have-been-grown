为什么有这个文件：记录 TV-M0-T05 实际改了什么。

它解决什么问题：避免把单章目录写成矩阵响应和正文已经按教程生成。

# TV-M0-T05 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T05](../tasks/TV-M0.md#tv-m0-t05) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-03 |
| 状态 | in-review。不标 done |
| 代码解释 | [TV-M0-T05](../code/TV-M0-T05.md) |

## 实际变更

- 抽出技术条款后，技术分册只保留一章。标题用招标文件里单独成行的「服务方案」「技术服务方案」或「技术方案」。没有这行时用「服务方案」。
- 二级、三级写在这一章正文里。评分要点和规格书条款各有一个三级标题。没有对应条款的块不补。
- 创建项目时的空章仍叫「技术方案」。一条都没抽到时它保持原样，不算目录。
- 有条款还没有三级标题时，不能确认目录。删掉标题后再确认会被拒绝，目录确认同时取消。

## 验证

- `tests/backend/test_technical_sources.py`：6 项通过。在关掉数据库连接后的内存仓储里跑。
- `export_openapi.py --check` 通过。
- 没有在浏览器里点确认目录。

## 剩余

标题还不能在页面上改名、调顺序或增删。编号固定为 1.1、1.1.1。矩阵响应和正文生成都还没做。上面这句是本卡完成时的边界。矩阵在 T06，正文和偏离表在 T07，都在同一分支，本卡仍是 in-review。

## 集成

集成分支 `feat/iss-047-technical-volume-mvp` 从决定记录 `0b9d1d5` 拉出，父提交是 `origin/main` 的 `36b7e41`。选择新分支而不是改名 `docs/issue-047-technical-volume-baseline`，这样产品提交不会推到 PR #7 的远程分支。不合并进 main。PR #7 只有决定记录，本轮关闭。2026-11-03 在关掉数据库连接的内存仓储里，`python -m pytest tests/backend/test_technical_sources.py` 为 12 项通过，其中包含本卡的目录确认；`python backend/bid-core/export_openapi.py --check` 通过。没有在浏览器里点确认目录。
