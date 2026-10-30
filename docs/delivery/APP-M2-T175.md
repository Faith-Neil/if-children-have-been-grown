为什么有这个文件：记录 APP-M2-T175 版本对比与回退的实际交付和测试证据。

它解决什么问题：说明逐段对比怎么对上段落、回退在后台重核哪些条件、回退后历史与段落来源怎么保留。

# APP-M2-T175：版本对比与回退

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T175 |
| 代码解释 | [APP-M2-T175](../code/APP-M2-T175.md) |
| 验收 | 2026-10-30：版本历史里任选旧版本与当前正式版本按段落键逐段对比（未改、改动逐字标增删、新增、删除）；“回退到此版本”调用 `POST /api/v1/projects/{id}/chapters/{cid}/rollback` 生成新版本，历史全部保留，修改方式记“版本回退（回到 vN）”并写审计；后台重核编辑锁、本节编辑权、分册定稿、正文版本、来源依据、未提交草稿、系统生成章节与锁定段落；回来的段落沿用目标版本的段落键与来源 |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T175](../tasks/APP-M2.md#app-m2-t175)（已并入原 T132“版本对比（复用 DiffView）”）
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)；看板工作包 WP-1；依赖 [APP-M2-T161](APP-M2-T161.md)、[APP-M2-T163](APP-M2-T163.md)

## 实际文件
- `backend/bid-core/icg/domain/version_rollback.py`（新）、`backend/bid-core/icg/api/chapter_versions.py`（新）
- `backend/bid-core/icg/domain/paragraph_keys.py`（回退块沿用目标版本键与来源）、`domain.py`（版本列表去掉内部字段）、`schemas.py`（版本记录声明写入方式字段）
- 错误码 `ROLLBACK_NOOP`、`DRAFT_PENDING`
- 前端：`frontend/web/src/editor/version-compare.ts`（新）、`EditorDiffDrawer.tsx`（重写）、`EditorPage.tsx`
- `spec/openapi/demo-v1.json`

## 测试证据
- `tests/backend/test_version_rollback.py`：新版本与历史保留、段落键沿用、审计；锁凭据错 423、版本旧 409、目标相同 409、目标不存在 404、只读成员拒绝、有草稿 409、锁定段落 409、系统章节 409
- `frontend/web/tests/unit/version-compare.test.mjs`：逐段对上、逐字差异、删除段落原位、修改方式标签、回退按钮禁用原因
- `frontend/web/e2e/version-rollback.spec.ts`：浏览器里逐段对比摘要与差异标记、确认回退、正文与版本列表读回
- 全量：后端两批、MySQL 套件、前端 lint/test/build、E2E 30 项

## 未实现项与限制
- 对比固定为“所选历史版本 → 当前正式版本”，不支持任意两个历史版本互比；编辑区未提交的修改不参与对比（页面有提示）。
- 改动不到一半的段落算“改动”，改动过半算“删除 + 新增”（与段落键规则一致）。
