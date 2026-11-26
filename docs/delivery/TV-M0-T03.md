为什么有这个文件：记录 TV-M0-T03 实际改了什么。

它解决什么问题：避免把文件类型收口写成抽取算法和目录已经按教程完成。

# TV-M0-T03 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T03](../tasks/TV-M0.md#tv-m0-t03) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-03 |
| 状态 | in-review。不标 done |
| 代码解释 | [TV-M0-T03](../code/TV-M0-T03.md) |

## 实际变更

- 技术分册项目的上传只接受招标文件、技术规范书、其他辅助文件，格式为 pdf、doc、docx。
- 没有招标文件时不能抽取。同一批文件抽取成功后不能再抽，增加、替换或删除文件后才能再抽。
- 文件变动后取消目录确认和矩阵确认。已有正文不删，有内容的章节标成需要重新生成。
- 技术分册页面不再提供补遗差异。已有两册项目的上传类型和补遗差异没有改。

## 验证

- `tests/backend/test_technical_sources.py`：3 项通过。在关掉数据库连接后的内存仓储里跑。
- `frontend/web/tests/unit/parse-postprocess-core.test.mjs`：7 项通过。
- 没有在浏览器里上传文件。

## 剩余

按教程抽取条款、单章目录、矩阵、正文和偏离表都还没做。抽取按钮目前仍走原来的解析。上面两句是本卡完成时的边界。后续卡在同一分支继续，本卡仍是 in-review。

## 集成

集成分支 `feat/iss-047-technical-volume-mvp` 从决定记录 `0b9d1d5` 拉出，父提交是 `origin/main` 的 `36b7e41`。产品提交只在这条分支，不合并进 main。PR #7 只有决定记录，不接收本卡代码，本轮关闭。2026-11-03 在关掉数据库连接的内存仓储里，`python -m pytest tests/backend/test_technical_sources.py` 为 12 项通过，`python backend/bid-core/export_openapi.py --check` 通过。
