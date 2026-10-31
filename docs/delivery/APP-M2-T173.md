为什么有这个文件：记录 APP-M2-T173 EditLockBadge、心跳、超时提示、接管（含原 T170 只读态） 的实际交付和测试证据。

它解决什么问题：2026-10-30 看板整治核对后，本卡功能已在代码中实现，但没有交付文档；本文件补齐证据，状态改为 in-review。

# APP-M2-T173：EditLockBadge、心跳、超时提示、接管（含原 T170 只读态）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T173 |
| 代码解释 | [APP-M2-T173](../code/APP-M2-T173.md) |
| 验收 | 2026-10-30：徽标显示本人锁定 / 某某编辑中（只读，锁至几点）/ 未取得编辑权；有操作才发心跳，间隔取公司设置；释放前 5 分钟提示；项目负责人与本分册负责人接管须写理由，旧租约随即失效 |
| 项目进度 | 看板与任务卡同步为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T173](../tasks/APP-M2.md#app-m2-t173)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)

## 实际文件
- `frontend/web/src/editor/EditorPage.tsx`
- `frontend/web/src/editor/useEditorLock.ts`
- `frontend/web/src/editor/autosave-core.ts`
- `backend/bid-core/icg/domain/domain.py`
- `backend/bid-core/icg/domain/workflow_orchestrator.py`

## 测试证据
- `tests/backend/test_demo.py::test_other_members_see_lock_holder_name`
- `tests/backend/test_demo.py::test_takeover_invalidates_old_lease_without_partial_write`
- `tests/backend/test_demo.py::test_manager_takeover_requires_reason_and_failure_preserves_editor_lease`
- `tests/backend/test_demo.py::test_old_heartbeat_and_release_cannot_destroy_manager_takeover`
- `frontend/web/tests/unit/autosave-core.test.mjs`

验证命令：后端全量 `pytest tests/backend`（分两批）、前端 `pnpm lint && pnpm test`、E2E `run-e2e.sh`，均在提交前执行并通过。

## 未实现项与限制
锁超时范围按平台上限 6～60 分钟执行（PRD §6.9 的 10～120 为示例值，硬约束“大于 5 分钟”已满足）。
