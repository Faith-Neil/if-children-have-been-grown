为什么有这个文件：登记 Wave 11 主路径补环——人工处理队列、分册交叉复核与定稿门禁、星号/废标兜底扫描。

它解决什么问题：主链路“生成→检查→转人工→分册定稿→全文检查”此前在人工处理和定稿复核处断开，解析确认缺少疑似遗漏闸门。

# ISSUE-040：Wave 11 主路径补环（人工处理队列 / 交叉复核 / 疑似遗漏）

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-040 |
| 类型 | change |
| 优先级 | P0 |
| 状态 | in-review |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [APP-M2-T133](../docs/tasks/APP-M2.md#app-m2-t133)、[APP-M2-T144](../docs/tasks/APP-M2.md#app-m2-t144)、[APP-M2-T111](../docs/tasks/APP-M2.md#app-m2-t111)、[BE-WORKFLOW-STATE-PERSIST](../docs/tasks/BE-M0.md#be-workflow-state-persist)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6)（草稿，目标 feat/opencode-ICG） |
| 本地验收 | 开发自测通过（2026-10-28），待 QA 独立复测与 PD 产品验收 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | [T133](../docs/delivery/APP-M2-T133.md)、[T144](../docs/delivery/APP-M2-T144.md)、[T111](../docs/delivery/APP-M2-T111.md)、[持久化](../docs/delivery/BE-WORKFLOW-STATE-PERSIST.md) |
| 代码 / 流程解释 | [T133](../docs/code/APP-M2-T133.md)、[T144](../docs/code/APP-M2-T144.md)、[T111](../docs/code/APP-M2-T111.md)、[持久化](../docs/code/BE-WORKFLOW-STATE-PERSIST.md) |
| 验证记录 | [Wave 11 验证](../docs/testing/2026-10-28-wave-11-verification.md) |

## 现象与证据

- `frontend/web/src/app/ProjectWorkspaceContent.tsx` 的 `manual` 页签渲染 `PendingPage`，后端没有人工处理队列（PRD §5.7.6～5.7.7）。
- `workflow_orchestrator.UNIMPLEMENTED_RULES` 含“交叉复核和完整分册定稿”；`volume_finalize.py` 不要求交叉复核、不绑定章节快照，解锁不让检查和导出过期；前端没有任何定稿/解锁按钮；已定稿分册后台仍可取得编辑权（只靠页面禁用）。
- 解析结果页“疑似遗漏 · 待实现”为禁用按钮，确认解析不检查兜底扫描（PRD §5.2.4）。
- MySQL 模式下分册定稿状态只在进程内存（`state.workflows` 不落盘）。

## 影响与分流

- 本次处理：上述四项按 PRD 补齐，页面、后台、数据、权限一起交付；新增 9 个冻结错误码；新增 Alembic 0012。
- 不在本次：章节循环进度页与轮次时间线（APP-M2-T130/T131）的独立页面；兜底词表维护页（APP-M2-T148）；引用未解析页签；模型评审 R28 进入循环；工作流其余聚合的 MySQL 持久化（ISSUE-041）。
- 依赖与阻塞解除条件：无。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| APP-M2-T133 | 人工处理队列列表、处理、驳回、重新检查 | `icg/domain/chapter_loop.py`、`icg/domain/human_queue.py`、`icg/api/chapter_loop.py`、`frontend/web/src/project/ManualQueuePage.tsx` | 见交付 | in-review |
| APP-M2-T144 | 交叉复核、定稿快照、待人工清零、解锁失效、后台只读 | `icg/domain/volume_review.py`、`icg/domain/volume_finalize.py`、`frontend/web/src/project/VolumeFinalizePanel.tsx` | 见交付 | in-review |
| APP-M2-T111 | 星号/废标兜底扫描、疑似遗漏逐条新增或排除、确认闸门 | `icg/domain/post_process.py`、`frontend/web/src/project/OmissionsDrawer.tsx` | 见交付 | in-review |
| BE-WORKFLOW-STATE-PERSIST | 上述新聚合与分册定稿状态写入 MySQL | `alembic/versions/0012_workflow_state.py`、`icg/infra/repositories/workflow_state.py` | 见交付 | in-review |

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 有影响 | 实施澄清 A2～A7，见 [PRD 实施澄清](../docs/decisions/2026-10-28-prd-amendments-wave11.md)，在 [PRD](../docs/PRD.md) 正文登记 |
| ROADMAP | 无影响 | 阶段与里程碑不变 |
| ARCHITECTURE | 有影响 | 新模块与数据表写入 [ARCHITECTURE](../docs/ARCHITECTURE.md) |
| TASK_BOARD | 有影响 | 三张 APP-M2 卡改 in-review，新增持久化卡 |
| PROJECT_STATUS | 有影响 | 记录 Wave 11 |
| DOCUMENT_INDEX | 有影响 | 登记全部新文档 |
