# APP-M2-T165 / APP-M2-T167 证据节点 `.cite` 悬浮与选区快捷气泡交付报告

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务目标 | APP-M2-T165（证据节点与 `.cite`） / APP-M2-T167（选区悬浮工具条） |
| 关联 Issue | [ISSUE-007](../../issues/ISSUE-007.md) |
| 规范出处 | [PRD v1.8 §5.11.2～§5.11.10](../../docs/reference/product/prd-mvp-v1.8.md)、架构决策 ADR-002 |
| 代码说明 | [APP-M2-T165 代码解释](../code/APP-M2-T165.md) |
| 核心业务代码 | `frontend/web/src/editor/cite-capsule.ts`、`frontend/web/src/editor/CiteCapsule.tsx`、`frontend/web/src/editor/SelectionBubble.tsx`、`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/shared/styles.css` |
| 专属测试套件 | `tests/frontend/cite-selection.test.mjs`（7 项全部通过）、`frontend/web/tests/cite-selection.test.mjs`（4 项全部通过） |
| 前端验证结果 | `pnpm --dir frontend/web build` 编译打包 0 错误；前端 318 项单元与契约测试全量通过 |
| 离线纯洁性 | 100% 离线测试，无任何外部网络外呼，符合 ICG 安全隔离红线 |
| 当前状态 | in-review（待主 Agent / QA 复核，绝不私自标 done，绝不私自关闭 Issue） |
<!-- task-delivery:end -->

---

## 1. 核心交付内容清单

1. **证据节点与 `.cite` 胶囊悬浮（APP-M2-T165）**：
   - 正则分词提取：实现 `CITE_REGEX` 纯逻辑工具函数，精准匹配 `[证:ID]`（资料证据，淡蓝色 `#1677ff`）与 `[片:ID]`（方案切片，紫色 `#722ed1`）；
   - 胶囊卡片与 Popover 悬浮：基于 Ant Design Popover 实现轻量 `.icg-cite` 胶囊徽标，悬浮呈现资料/切片标题、编号、核验状态（“已核验” / “待核对”）、有效期及引用摘录；
   - 交互联动：提供 `data-testid="cite-highlight-btn"` 操作，点击后在右侧来源面板中定位高亮对应条目并发送提示通知；
   - 只读与未持锁纯文本渲染：在 `readonly-editor-text` 与 `unheld-editor-text` 中挂载 `RichParagraphWithCites`，保持语义排版容器与类名，杜绝 DOM 布局闪烁；
   - 编辑态正文引用条：在可编辑正文区下方挂载 `data-testid="editor-citation-bar"`，实时动态呈现正文当前引用的依据胶囊列表。

2. **选区划词快捷操作气泡（APP-M2-T167）**：
   - 浮动工具条组件：实现 `SelectionBubble`，声明 `data-testid="selection-action-bubble"`，包含 `@keyframes bubbleFadeIn` 平滑淡入动效；
   - 选区字数指示：提供 `data-testid="bubble-selected-count"`，实时呈现当前选中文本的字数；
   - AI 润色一键直达：提供 `data-testid="bubble-polish-btn"`，点击自动解除右侧 AI 助手折叠（`setAssistantCollapsed(false)`），切换至 assistant 面板并自动填充润色 Prompt（带字数截断与防篡改约束）；
   - 合规问答一键直达：提供 `data-testid="bubble-compliance-btn"`，点击自动载入合规核对 Prompt 并无缝展开 AI 助手；
   - 快捷收起与抗失焦：提供 `data-testid="bubble-clear-btn"` 一键清除选区，并通过 `e.preventDefault()` 杜绝点击气泡按钮导致正文失焦。

3. **包体积与构建优化**：
   - 遵守 Route-level Code Splitting 规范，`pnpm --dir frontend/web build` 正常完成分包打包（EditorPage 主包 110 kB，Popover 独立 chunk 5.3 kB）；
   - 无任何多余大依赖引入。

---

## 2. 变更文件清单

| 文件路径 | 状态 | 说明 |
|---|---|---|
| `frontend/web/src/editor/cite-capsule.ts` | 新建 | 正则分词、元数据合并与 ID 提取纯逻辑工具 |
| `frontend/web/src/editor/CiteCapsule.tsx` | 新建 | `CiteCapsule` 悬浮卡片与 `RichParagraphWithCites` 富段落组件 |
| `frontend/web/src/editor/SelectionBubble.tsx` | 新建 | `SelectionBubble` 选区悬浮操作条组件 |
| `frontend/web/src/shared/styles.css` | 修改 | 添加气泡浮动、淡入动效与 `.icg-cite` 悬浮色彩样式 |
| `frontend/web/src/editor/EditorPage.tsx` | 修改 | 正文区挂载选区气泡、只读态富段落、编辑态引用条与事件联动 |
| `tests/frontend/cite-selection.test.mjs` | 新建 | 纯逻辑单测：正则分词、ID 提取、提示词格式化 |
| `frontend/web/tests/cite-selection.test.mjs` | 新建 | AST 静态契约单测：组件导出、`data-testid` 与挂载断言 |

---

## 3. 测试验证结果

### 3.1 前端单测全量执行

执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行结果：
```
ℹ tests 318
ℹ suites 0
ℹ pass 318
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3005.8551
```
其中专属测试用例 11 项 100% 通过：
- `CITE_REGEX matches [证:ID] and [片:ID] accurately`
- `parseCitations splits pure text without markers into single text segment`
- `parseCitations handles mixed text and citations with metadata enrichment`
- `extractCitationIds extracts unique evidence and snippet IDs preserving order`
- `resolveCitationMeta supplies sensible defaults when not found`
- `formatCiteLabel formats evidence and snippet tags`
- `Selection bubble logic builds truncated polish & compliance prompts`
- `cite-capsule.ts exports required parsing and metadata helpers`
- `CiteCapsule.tsx exports CiteCapsule and RichParagraphWithCites with contract testids`
- `SelectionBubble.tsx exports SelectionBubble with all action buttons and testids`
- `EditorPage.tsx mounts SelectionBubble, RichParagraphWithCites and editor-citation-bar`

### 3.2 生产打包验证

执行命令：
```bash
pnpm --dir frontend/web build
```
执行结果：
```
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3371 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.01 kB │ gzip:   0.58 kB
dist/assets/index-Dh3tIuXn.css                34.82 kB │ gzip:   7.63 kB
dist/assets/popover-CrIx6EVB.js                5.31 kB │ gzip:   2.19 kB
dist/assets/EditorPage-BRZNweMy.js           110.06 kB │ gzip:  34.97 kB
✓ built in 1.04s
```
TypeScript 类型检查与生产打包一次性成功通过。

---

## 4. 任务状态与治理结论

- 严格遵循团队规范：绝不私自把任务看板标为 `done`，绝不私自关闭 Issue；
- 当前任务状态：`in-review`；
- 现已将成果提交至主 Agent，并同步更新任务看板、任务文档及文档索引。
