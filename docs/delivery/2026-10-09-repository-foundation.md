# 首轮项目接管与目录基础整理

日期：2026-10-09（UTC+8）。开发类型：仓库内部目录维护，以及 [ISSUE-002](../../issues/ISSUE-002.md) 原型编辑锁修复。起点：`main` / `ce064f6`。

## 完成内容

- 读取 `main`、`xqr`、原型和本地产品材料；登记合作 PR #1 的整合风险。
- UX 文档从 `ui/ux.md` 原文迁至 `docs/design/ux.md`。
- 静态原型整体迁至 `prototypes/bidding-ux/`，更新说明与启动路径。
- 添加 [目录方案](../architecture/repository-layout.md)、[基线差异](../decisions/baseline-gaps.md)、[文档索引](../DOCUMENT_INDEX.md)、[项目状态](../PROJECT_STATUS.md) 与 [PR #1 评审](../reviews/pr-1-integration.md)。
- 将已脱敏 PRD v1.8、字典 v1.9 原文作为供评审参考输入单独保存；保留现有前端三件套及其路径。
- 在编辑锁期间禁用相关修改操作，并在 Diff 确认和编辑命令处理器再次校验只读状态。
- 添加合作维护约定、忽略规则、问题记录和无依赖编辑锁回归测试。

## 修改文件

| 类别 | 路径 |
|---|---|
| 修改 | README.md；prototypes/bidding-ux/README.md、app.js、styles.css |
| 移动 | ui/ux.md → docs/design/ux.md；bidding-ux-prototype/ → prototypes/bidding-ux/ |
| 新增维护入口 | AGENTS.md、.gitignore、docs/DOCUMENT_INDEX.md、docs/PROJECT_STATUS.md |
| 新增方案与参考 | docs/architecture/、docs/decisions/、docs/reviews/、docs/reference/product/ |
| 新增验证与记录 | tests/prototype/editor-lock.test.cjs、issues/、docs/testing/、本交付文档 |

## 验证

6 项实际脚本事件回归通过，JavaScript 语法检查通过。结构与链接校验结果、执行方式和验证边界见 [测试记录](../testing/2026-10-09-repository-foundation.md)。

## 已知问题与下一阶段

正式服务与应用仍未建立；原型保存和版本仍是模拟。建议、Diff 与真实选区上下文及版本显示差异后续单独处理。合作分支的系统方案与当前前端方案有层级和范围差异，尚未整合；技术方案和完整设计包仍缺失。

下一阶段先保全系统/前端两套方案并核对基线，再收敛前端实施视图和 API 契约。当前交付不代表批准数据库/模型选型或完成全系统研发。

## 索引状态

上述新增文档、原型、问题与验证记录已登记到 `docs/DOCUMENT_INDEX.md`。本轮准备独立草稿 PR 供审阅，合作 PR #1 保持待整合状态。
