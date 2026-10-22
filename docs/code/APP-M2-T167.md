# APP-M2-T167 选区悬浮工具条代码解释

- 任务编号：[APP-M2-T167](../tasks/APP-M2.md#app-m2-t167)（选区悬浮工具条）
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 规范出处：[PRD v1.8 §5.11.2～§5.11.10](../../docs/reference/product/prd-mvp-v1.8.md)、架构决策 ADR-002
- 交付报告：[APP-M2-T167 交付文档](../delivery/APP-M2-T167.md)
- 核心代码路径：
  - `frontend/web/src/SelectionBubble.tsx`
  - `frontend/web/src/EditorPage.tsx`
  - `frontend/web/src/styles.css`
  - `tests/frontend/cite-selection.test.mjs`
  - `frontend/web/tests/cite-selection.test.mjs`

---

## 1. 架构总览与交互流转

在投标文件正文编制与审校场景中，编写人员或审校人员在浏览或编辑正文时，通过鼠标划选关键语句（`selected_text`），系统在选区正上方自适应浮现轻量 Action Bubble（浮动操作气泡）。

气泡支持：
1. **已选字数指示**（`data-testid="bubble-selected-count"`）：精准显示选区字符数；
2. **一键 AI 润色**（`data-testid="bubble-polish-btn"`）：带入右侧 AI 助手并切换至 polish 润色场景；
3. **一键合规问答**（`data-testid="bubble-compliance-btn"`）：带入右侧 AI 助手并切换至 compliance 场景；
4. **一键清除选区**（`data-testid="bubble-clear-btn"`）：取消划词并收起气泡；
5. **抗失焦保护**：点击气泡内部按钮时阻止默认行为（`e.preventDefault()`），防止编辑区或只读区选区意外丢失。

---

## 2. 核心模块与实现细节

### 2.1 选区快捷气泡组件（`SelectionBubble.tsx`）

- **DOM 契约与结构**：
  - 根容器：声明 `data-testid="selection-action-bubble"`、类名 `icg-selection-bubble`；
  - 绝对定位与边界约束：`position: absolute; transform: translate(-50%, -100%);`；
  - 动效：挂载 `@keyframes bubbleFadeIn 0.15s ease-out` 平滑淡入；
  - 字符计数：`ThunderboltOutlined` 标识 + `data-testid="bubble-selected-count"`；
  - 按钮组：
    - 润色按钮：紫色主题 `#722ed1`，`data-testid="bubble-polish-btn"`；
    - 合规按钮：蓝色主题 `#1677ff`，`data-testid="bubble-compliance-btn"`；
    - 关闭按钮：`CloseOutlined`，`data-testid="bubble-clear-btn"`。

### 2.2 编辑台挂接与事件监听（`EditorPage.tsx`）

- **双模式选区监听**：
  - **编辑态**：在 `Input.TextArea` 绑定 `onSelect={handleTextareaSelect}`，根据 `selectionStart` 与 `selectionEnd` 计算选区并映射到文档纸张坐标；
  - **只读态 / 未持锁态**：在 `readonly-editor-text` 与 `unheld-editor-text` 绑定 `onMouseUp={handleContainerMouseUp}`，基于 `window.getSelection().getRangeAt(0).getBoundingClientRect()` 映射浮动坐标；
  - **空选区防御**：当无选中或选区仅为纯空白字符时自动隐藏（`setSelectionBubble(prev => ({ ...prev, visible: false }))`）。
- **AI 助手无缝打通**：
  - 自动解除助手折叠：`setAssistantCollapsed(false)`；
  - 切换 Tab 到 `'assistant'`；
  - 预填模板化 Prompt 并触发轻量反馈 Notice。

---

## 3. 改动文件与测试

- 改动文件：`frontend/web/src/SelectionBubble.tsx`、`frontend/web/src/EditorPage.tsx`、`frontend/web/src/styles.css`；
- 测试套件：`tests/frontend/cite-selection.test.mjs`、`frontend/web/tests/cite-selection.test.mjs`；
- 构建与单测全量通过。
