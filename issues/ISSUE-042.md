为什么有这个文件：登记必需的浏览器端到端作业长期失败，以及资料库表单丢失“历史标书（参考）”“方案片段”类别的回归。

它解决什么问题：e2e 是 offline-check 的必需作业，持续红灯会让后续回归无法被发现；历史标书只能参考是 PRD v1.6 起的明确约束。

# ISSUE-042：e2e 证据抽屉用例与资料库表单脱节

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-042 |
| 类型 | bug |
| 优先级 | P1 |
| 状态 | in-progress |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [FE-E2E-LIBRARY-DRIFT](../docs/tasks/FE-M0.md#fe-e2e-library-drift)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | [PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 只修复了第一项 |
| 本地验收 | 部分：`app-shell.spec.ts` 本地与 CI 均通过；`evidence-drawer.spec.ts` 仍失败（[CI 运行 40652286468](https://github.com/Faith-Neil/if-children-have-been-grown/actions/runs/40652286468)：15 passed、1 failed） |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 待建立（FE） |
| 代码 / 流程解释 | 待建立（FE） |
| 验证记录 | [Wave 11 验证](../docs/testing/2026-10-28-wave-11-verification.md) |

## 现象与证据

`feat/opencode-ICG` 自 `e56d225` 起 offline-check 的 e2e 作业每次都失败（含 tip `4985a9d`），两项用例：

1. `app-shell.spec.ts` “core pages render at 1280/1440/1680”：`export@1280 horizontal overflow` 54px。根因是编辑台在 1280～1439px 的三栏最小宽度 260+650+360 超过内容区约 1216px，切到导出页的瞬间测得溢出。**已在 PR #6 修复**（`frontend/web/src/shared/styles.css` 改为 240/520/360）。
2. `evidence-drawer.spec.ts`：用例按旧版资料库操作“补录合成资料”“资料内容”“人工核对状态”“保存资料”，并新增“历史标书（参考）”“方案片段”两类资料；`94be240` 改版后的表单名称已变，且类别选项只剩主体资质、财务审计、人员证书、业绩案例、通用模板，无法再录入历史标书与方案片段。**未修复**。

## 影响与分流

- 影响：必需作业红灯；资料库无法从页面录入历史标书参考与方案片段，PRD v1.8 §5.3.1、§5.5 能力从页面消失（后台仍支持 `history` 类型且禁止挂为证据）。
- 处理：恢复两类资料的录入入口并保持“历史标书只能查看、不能勾选”；按现行页面文案更新用例，不放宽断言。
- 依赖：无。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| FE-E2E-LIBRARY-DRIFT | 恢复资料类别并让证据抽屉用例按现行页面通过 | `frontend/web/src/library/LibraryPages.tsx`、`frontend/web/e2e/evidence-drawer.spec.ts` | offline-check e2e 作业全绿 | planned |

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 无影响 | 需求未变，是实现回归 |
| ROADMAP | 无影响 | 阶段不变 |
| ARCHITECTURE | 无影响 | 无模块边界变化 |
| TASK_BOARD | 有影响 | 新增 FE-E2E-LIBRARY-DRIFT |
| PROJECT_STATUS | 有影响 | 如实记录 CI 红灯来源 |
| DOCUMENT_INDEX | 有影响 | 登记本 Issue |
