# APP-M2-T167 选区悬浮工具条交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T167 · 选区悬浮工具条（Action Bubble） |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 规范出处 | [PRD v1.8 §5.11.2～§5.11.10](../../docs/reference/product/prd-mvp-v1.8.md)、架构决策 ADR-002 |
| 代码说明 | [APP-M2-T167 代码解释](../code/APP-M2-T167.md) |
| 核心业务代码 | `frontend/web/src/editor/SelectionBubble.tsx`、`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/shared/styles.css` |
| 专属测试套件 | `tests/frontend/cite-selection.test.mjs`、`frontend/web/tests/cite-selection.test.mjs` |
| 前端验证结果 | `pnpm --dir frontend/web build` 编译打包 0 错误；前端 318 项单元与契约测试全量通过 |
| 离线纯洁性 | 100% 离线测试，无任何外部网络外呼，符合 ICG 安全隔离红线 |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **选区划词快捷操作气泡（Selection Action Bubble）**：
   - 气泡容器：实现 `SelectionBubble` 组件，声明 `data-testid="selection-action-bubble"`，包含 `@keyframes bubbleFadeIn` 平滑淡入动效；
   - 选区字数指示：提供 `data-testid="bubble-selected-count"`，实时呈现当前选中文本的字数；
   - AI 润色一键直达：提供 `data-testid="bubble-polish-btn"`，点击自动解除右侧 AI 助手折叠（`setAssistantCollapsed(false)`），切换至 assistant 面板并自动填充润色 Prompt（带字数截断与防篡改约束）；
   - 合规问答一键直达：提供 `data-testid="bubble-compliance-btn"`，点击自动载入合规核对 Prompt 并无缝展开 AI 助手；
   - 快捷收起与抗失焦：提供 `data-testid="bubble-clear-btn"` 一键清除选区，并通过 `e.preventDefault()` 杜绝点击气泡按钮导致正文失焦。

2. **双模式选区感知**：
   - 编辑态下通过 `onSelect` 计算光标与选区；
   - 只读态与未持锁态下通过 `onMouseUp` 计算 `window.getSelection()` 选区；
   - 选区取消或为空时自适应隐藏。

---

## 2. 测试验证结果

- 前端 318 项单测全部绿灯；
- 专属 AST 与交互断言测试 `frontend/web/tests/cite-selection.test.mjs` 全部通过；
- 生产打包 `pnpm --dir frontend/web build` 一次性构建成功。
