# 代码说明：APP-M2-T173 EditLockBadge、心跳、超时提示、接管（含原 T170 只读态）

为什么有这个文件：说明 APP-M2-T173 的入口、调用顺序和关键判断。

它解决什么问题：让复审人不读全部代码也能找到本卡行为落在哪里、由哪一层把关。

<!-- code-explanation:start -->
| 项目 | 记录 |
|---|---|
| 关联任务 | APP-M2-T173 |
| 交付文件 | `docs/delivery/APP-M2-T173.md` |
| 影响模块 | `frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/editor/useEditorLock.ts`、`frontend/web/src/editor/autosave-core.ts`、`backend/bid-core/icg/domain/domain.py`、`backend/bid-core/icg/domain/workflow_orchestrator.py` |
<!-- code-explanation:end -->

## 调用顺序与关键判断
章节接口的 `lock` 增加 `owner_name`；`lockHolderLabel` 生成徽标文字；`useEditorLock` 按 `shouldHeartbeat` 只在有操作后续期，`expiryWarning` 在剩余不足 5 分钟时提示；接管弹窗理由为空时不提交。

## 依赖与限制
锁超时范围按平台上限 6～60 分钟执行（PRD §6.9 的 10～120 为示例值，硬约束“大于 5 分钟”已满足）。
