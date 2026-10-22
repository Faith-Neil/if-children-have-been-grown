为什么有这个文件：说明 APP-M2-T123 大纲排序、章节类型和增值理由的具体实现、状态流转、红线门禁拦截与组件设计。

它解决什么问题：阐述基于 PRD v1.8 §5.7.2、§5.7.8 及原交接 §6.5 M4-F01-F1 的大纲与章节树协同编辑架构，实现分册（技术/商务）章节树层级呈现、5 类章节类型（专项/通用/系统生成/封面目录/不适用）徽标、同级章节上移/下移排序算法、增值理由快捷模板与弹窗编辑，严格落实“星号条款(★)与废标条款对应章节绝对禁止标记为不适用”的合规红线门禁，并深度协同 useDataPermission 进行分册只读保护与编辑台联动。

# APP-M2-T123：代码解释

- 对应任务：[APP-M2-T123](../tasks/APP-M2.md#app-m2-t123) · 大纲排序、章节类型和增值理由（分工复用T15）
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T123 交付](../delivery/APP-M2-T123.md)
- 日期：2026-10-22
- 实际代码路径：
  - [outline-tree.ts](../../frontend/web/src/project/outline-tree.ts)
  - [ChapterTypeBadge.tsx](../../frontend/web/src/project/ChapterTypeBadge.tsx)
  - [ValueAddedReasonModal.tsx](../../frontend/web/src/project/ValueAddedReasonModal.tsx)
  - [OutlineTreeView.tsx](../../frontend/web/src/project/OutlineTreeView.tsx)
  - [outline-tree.test.mjs](../../tests/frontend/outline-tree.test.mjs)
  - [outline-tree.test.mjs](../../frontend/web/tests/outline-tree.test.mjs)

---

## 改了什么以及为什么

### 1. 业务痛点与合规红线
根据 PRD v1.8 §5.7.2（大纲规划方案）、§5.7.8（逐节确认与启动生成）及原交接约束：
- **章节类型多元与规范化**：标书章节根据撰写来源与技术深度分为专项方案（`specialized`）、通用方案（`general`）、系统生成（`system_generated`）、封面目录（`cover_and_catalog`）与不适用（`not_applicable`），需要直观徽标以区分 AI 介入程度与模板能力；
- **【核心门禁红线】禁止不适用**：招标文件中标星号（★）或被判定为废标条款的关键需求，对应的章节**绝对禁止标记为“不适用”**，否则将导致直接废标或重大扣分风险；必须在前端下拉选择时强制置灰禁用，并提供明确悬浮解释，提交前置拦截；
- **大纲结构排序调整**：允许项目负责人与分册负责人在方案编制阶段调整同级章节顺序（上移/下移），排序后系统自适应归一化多层级章节编号（如 1, 1.1, 1.2, 2, 2.1 等）；
- **增值理由阐述**：专项重点方案需要向评审专家展示超出招标文件要求的亮点承诺与增值服务，系统提供预置高频模板与最多 500 字的弹窗编辑；
- **多粒度数据权限协同**：消费 `useDataPermission`，非主管分册（分册级只读）以及只读角色不可修改排序、变更类型或保存增值理由，呈现分册只读警告。

---

## 2. 具体实现架构

### 2.1 纯逻辑层 (`frontend/web/src/project/outline-tree.ts`)
脱离 DOM 纯 TypeScript 实现，具备高可测性与高稳定性：
1. **章节模型与 5 类类型定义**：
   - 导出 `ChapterType`：`'specialized' | 'general' | 'system_generated' | 'cover_and_catalog' | 'not_applicable'`；
   - 导出 `CHAPTER_TYPES_CONFIG` 与 `getChapterTypeMeta`：统一各类型的主题色、中文名与详细描述，其中 `system_generated` 绑定专属紫色 `#722ed1`；
2. **红线门禁拦截函数 (`canMarkNotApplicable` / `validateChapterTypeChange`)**：
   - 当节点包含 `isStarred: true` 时，拦截返回 `allowed: false`，提示“该章节对应星号(★)关键条款，合规门禁严格禁止标记为“不适用”！”；
   - 当节点包含 `isBlocker: true` 时，拦截返回 `allowed: false`，提示“该章节对应废标关键条款，合规门禁严格禁止标记为“不适用”！”；
   - 其他普通章节正常放行；
3. **同级节点重排算法 (`reorderNodes`)**：
   - 保证同级首个节点不可上移，末尾节点不可下移；
   - 上移/下移完成元素互换后，自动重置连续递增的 `orderIndex`；
4. **多层级编号递归归一化 (`normalizeChapterNumbers`)**：
   - 递归计算多层级父子章节编号（`1`, `1.1`, `1.2`, `2`, `2.1` 等），确保大纲展示清晰严谨；
5. **增值理由校验 (`validateValueAddedReason`)**：
   - 校验输入长度上限不超过 500 字符。

---

### 2.2 徽标与弹窗组件封装
1. **`ChapterTypeBadge.tsx`**：
   - 展现章节类型的 Tag（专项方案、通用方案、系统生成、封面目录、不适用）；
   - 若为 `system_generated` 挂载 `.is-system-generated` 专属紫样式；
   - 支持悬停 Tooltip 呈现该章节类型的详细定义；
2. **`ValueAddedReasonModal.tsx`**：
   - 提供快捷预置增值模板（性能提升 20%、7x24h 运维保障、双活灾备、免费巡检演练等）一键填入；
   - 具备 500 字字数统计与即时校验；
   - 接收 `readOnly` 属性，只读模式下展示警告横幅并禁用保存按钮。

---

### 2.3 大纲核心视图组件 (`OutlineTreeView.tsx`)
1. **分册维度筛选**：
   - 支持通过顶栏 Radio 分册视图（技术分册 / 商务分册 / 全部分册）按册切换与统计计数；
2. **章节卡片呈现**：
   - 呈现归一化后的章节编号、标题、`ChapterTypeBadge`、星号条款标（★ 红星）、废标条款标及关联条款数；
   - 展开展示已填写的增值理由概要卡片；
3. **门禁下拉拦截**：
   - 在类型下拉菜单（Select）中动态计算 `isNotApplicableDisabled`：若属于星号或废标条款，“不适用”选项置灰禁用，并弹出 Tooltip 解释禁止原因；
4. **数据权限只读协同**：
   - 消费 `useDataPermission({ volume: activeVolume })`；
   - 当处于非主管分册只读模式时，渲染 `data-testid="readonly-notice-banner"` 警告条，上移/下移按钮与类型下拉框全部置灰禁用；
5. **编辑台跳转联动**：
   - 提供“编辑台”按钮，点击触发 `onNavigateToEditor(chapterId)` 跳转至对应章节的编辑页面。

---

## 3. 测试覆盖与门禁验证

### 3.1 单元测试矩阵
- **纯逻辑单测** (`tests/frontend/outline-tree.test.mjs`，7 个测试点)：
  1. 章节类型元信息与配置定义；
  2. 星号条款章节绝对禁止标记为“不适用”门禁验证；
  3. 废标条款章节绝对禁止标记为“不适用”门禁验证；
  4. 普通章节允许正常标记为“不适用”；
  5. 章节同级顺序调整算法边界与互换；
  6. 多层级编号递归归一化；
  7. 增值理由 500 字上限校验。
- **表现层 AST 与静态契约测试** (`frontend/web/tests/outline-tree.test.mjs`，4 个测试点)：
  1. `outline-tree.ts` 导出符号检查；
  2. `ChapterTypeBadge.tsx` 导出与 `data-testid="chapter-type-badge"` 断言；
  3. `ValueAddedReasonModal.tsx` 导出、字符统计与保存回调契约；
  4. `OutlineTreeView.tsx` 星号/废标门禁拦截、权限协同与排序跳转契约。

### 3.2 门禁验证结果
- **前端全量单测**：`node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs`，全绿通过（**274 passed, 0 failed**）；
- **生产构建体积**：`pnpm --dir frontend/web build`，在 1.10s 内构建成功，主包体积保持为 **294.86 kB**（严格 <= 295.00 kB）。
