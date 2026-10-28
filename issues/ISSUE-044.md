为什么有这个文件：登记前端 tests/ 根目录下的单元测试从未被执行的问题。

它解决什么问题：`pnpm test` 的 `node --test tests/**/*.test.mjs` 在 sh 下只展开一层子目录，`frontend/web/tests/*.test.mjs` 的 28 个文件从未在本地或 CI 运行，其中 8 项已经失败，覆盖是假的。

# ISSUE-044：前端根目录测试从未执行

| 项目 | 内容 |
|---|---|
| Issue ID | ISSUE-044 |
| 类型 | bug |
| 优先级 | P1 |
| 状态 | triaged |
| 登记日期 | 2026-10-28 |
| 最后更新日期 | 2026-10-28 |
| revision | 1 |
| 关联 Task | [FE-TEST-ORPHANS](../docs/tasks/FE-M0.md#fe-test-orphans)；[任务看板](../docs/TASK_BOARD.md) |
| 关联 PR | 未创建 |
| 本地验收 | 未执行 |
| 合入 | 未合入 |
| 发布 | 未发布 |
| 交付说明 | 待建立 |
| 代码 / 流程解释 | 待建立 |
| 验证记录 | `node --test tests/*.test.mjs`：157 pass、8 fail（2026-10-28） |

## 现象与证据

失败项集中在会话迟到回包、编辑台离开保护、公司集合读取等早期编排测试，多数是页面重构后断言过期，也可能藏有真实回归。

## 实施任务与互链

| Task ID | 输入与目标 | 涉及路径 | 验收 | 当前状态 |
|---|---|---|---|---|
| FE-TEST-ORPHANS | 逐个判定 8 项失败是断言过期还是真实回归，修复后把根目录测试并入 `pnpm test` | `frontend/web/tests/`、`frontend/web/package.json` | 全部前端测试在 CI 执行且通过 | planned |

## 六份基线评估

| 基线 | 评估 | 理由与路径 |
|---|---|---|
| PRD | 无影响 | 测试缺口 |
| ROADMAP | 无影响 | 阶段不变 |
| ARCHITECTURE | 无影响 | 不改结构 |
| TASK_BOARD | 有影响 | 新增 FE-TEST-ORPHANS |
| PROJECT_STATUS | 有影响 | 如实记录测试覆盖缺口 |
| DOCUMENT_INDEX | 有影响 | 登记本 Issue |
