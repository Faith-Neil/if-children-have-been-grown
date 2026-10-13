为什么有这个文件：记录编辑租约迁到 `/api/v1` 这张卡实际交了什么。

它解决什么问题：让产品入口使用统一错误体取得、续期和释放编辑权，同时旧验证页仍走原来的 `/api`。

# BE-M0-T04：编辑租约迁到 /api/v1 交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T04 |
| 代码解释 | [BE-M0-T04](../code/BE-M0-T04.md) |
| 验收 | 2026-10-12：v1 取得、续期、接管和释放与原规则一致，错误体为 `{code, message, details, traceId}`。旧 `/api` 租约入口仍返回原成功体。未设连接串时后台测试见验证记录。治理检查见验证记录 |
| 项目进度 | 任务看板是准绳。本卡从 ready 改为 in-review。看板为 387 项：51 done、12 in-review、7 in-progress、265 planned、48 blocked、4 ready。BE-M0 为 19 项，9 项 done。本卡 in-review。ISSUE-005 为 in-progress，不关闭。T05～T07 仍为 ready |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-005](../../issues/ISSUE-005.md)。
- 分支 `codex/repository-foundation`。未新开 PR，未合入，未发布。
- 本地验收已做。QA REV-M0-T32 tip `90b2334` 已签。等待项目经理标 done。

## 完成内容与变更文件

`POST /api/v1/chapters/{chapter_id}/lock`、`/lock/renew`、`/lock/release` 调用原来的取得、续期和释放。时长仍是 120 秒。编写人不能接管他人，负责人接管必须填写理由。失败使用 v1 错误体。

旧 `POST /api/chapters/{chapter_id}/lock` 三路由不删。`frontend/web/src/EditorPage.tsx` 和 `/demo` 验证页继续用它们，成功响应仍不是 `traceId`。

OpenAPI 增加这三条路径。没有重跑 `export_openapi.py`，冻结草案和 `deprecated` 标注仍在。不改 202/SSE，不加数据库，不新增错误码。`operationId` 仍是框架原名，留给 BE-M0-T07。

## 代码解释

见 [代码解释](../code/BE-M0-T04.md)。

## 验收结果

证据见 [验证记录](../testing/2026-10-12-be-m0-t04-v1-lease.md)。

## 限制与未完成

- 不标 done，不关闭 ISSUE-005。
- 不改导出快照、202/SSE 和 operationId。
- 不改 `.github`，不改 `docs/reference/`，不改 PRD、ROADMAP、PROJECT_BRIEF 的里程碑计数。
