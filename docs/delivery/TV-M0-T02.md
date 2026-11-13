为什么有这个文件：记录 TV-M0-T02 实际改了什么。

它解决什么问题：避免把历史标书上传入口写成抽取、目录和正文已经完成。

# TV-M0-T02 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T02](../tasks/TV-M0.md#tv-m0-t02) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-03 |
| 状态 | in-review。不标 done |
| 代码解释 | [TV-M0-T02](../code/TV-M0-T02.md) |

## 实际变更

- 知识库页不再以方案片段为入口。打开知识库就是历史标书。方案片段页面文件还在，侧栏进不去。
- 历史标书只接受 pdf、doc、docx。上传只追加到已有数据集，不会在上传时新建数据集。
- 数据集还没有时，上传按钮不可用，并提示公司管理员先配置。有写入权限的账号可以点「建立历史标书数据集」。
- 项目经理可以上传，不能改知识库连接和设置。公司管理员仍能看到「数据集配置」。

## 验证

- `pnpm --dir frontend/web exec node --test tests/unit/kb-admin-core.test.mjs tests/unit/react-router.test.mjs`：通过。
- `tests/backend/test_kb_admin.py`：12 项通过。这次是在关掉数据库连接后的内存仓储里跑的。
- 没有在浏览器里点上传。端到端用例 `knowledge-flows.spec.ts` 已改断言，本机没有跑。

## 同步

任务卡、看板、ISSUE-047 和文档索引已把 T02 记为 in-review。T03～T07 仍是 planned。

## 剩余

招标文件与辅助文件、抽取、单章目录、矩阵、正文和偏离表都还没做。上面这句是本卡完成时的边界。后续卡在同一分支继续，本卡仍是 in-review。

## 集成

集成分支 `feat/iss-047-technical-volume-mvp` 从决定记录 `0b9d1d5` 拉出，父提交是 `origin/main` 的 `36b7e41`。产品提交只在这条分支，不合并进 main。PR #7 只有决定记录，不接收本卡代码，本轮关闭。2026-11-03 在关掉数据库连接的内存仓储里，`python -m pytest tests/backend/test_technical_sources.py` 为 12 项通过，`python backend/bid-core/export_openapi.py --check` 通过。
