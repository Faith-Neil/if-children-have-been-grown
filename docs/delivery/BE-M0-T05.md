为什么有这个文件：记录导出快照这张卡实际交了什么。

它解决什么问题：让单章导出说明它绑定的检查、版本和输入摘要，并在来源变化后拒绝把旧文件当成当前结果。

# BE-M0-T05：导出快照语义交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T05 |
| 代码解释 | [BE-M0-T05](../code/BE-M0-T05.md) |
| 验收 | 2026-10-12：导出响应含 check_id、revision、content_hash、input_fingerprint，且没有 stale 字段。资料变化后旧检查不能再导出，旧下载为 409 EXPORT_STALE。未设连接串时后台测试见验证记录 |
| 项目进度 | 任务看板是准绳。本卡从 ready 改为 in-review。看板为 387 项：51 done、13 in-review、7 in-progress、265 planned、48 blocked、3 ready。BE-M0 为 19 项，9 项 done。本卡 in-review。ISSUE-005 为 in-progress，不关闭。T04 仍为 in-review。T06～T07 仍为 ready |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-005](../../issues/ISSUE-005.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。QA REV-M0-T33 tip `90b2334` 已签。等待项目经理标 done。

## 完成内容与变更文件

单章 `POST /api/chapters/{chapter_id}/exports` 仍同步返回文件记录，不改成异步任务。响应增加当时的检查、已提交版本、正文摘要和项目输入摘要。不新增 `stale` 布尔字段，不新增错误码。

正文变化仍是 409 `CHECK_STALE` / `EXPORT_STALE`。同公司资料变化后，旧检查不能再导出，旧文件下载同样是 409 `EXPORT_STALE`。草稿不进入文件，也不改写这份摘要。

项目级两册导出原有的指纹和 `status` 枚举保持不变。没有重跑 `export_openapi.py`。

## 代码解释

见 [代码解释](../code/BE-M0-T05.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t05-export-snapshot.md)。

## 限制与未完成

- 不标 done，不关闭 ISSUE-005。
- 不改 202/SSE 和 operationId。
- 不改 `.github`，不改 `docs/reference/`，不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑计数。
