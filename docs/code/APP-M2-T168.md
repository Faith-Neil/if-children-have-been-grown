为什么有这个文件：说明 APP-M2-T168 编辑台与大纲树深度联动、响应式断点折叠与分册只读协同的具体实现、状态流转与组件契约。

它解决什么问题：阐述基于 PRD v1.8 §5.7.8、§5.12 及设计规范 §3.4、§7.3、§9.6 的编辑台架构升级，将大纲树（OutlineTreeView）深度嵌入编辑台左侧面板，支持技术/商务分册自由切换、星号/废标/系统生成徽标直观展示；落实 APP-M2-T160 响应式断点机制，宽屏（>=1680px）完整展开 3~4 栏，中屏（1280px~1440px）支持大纲目录折叠为迷你竖条、右侧助手折叠与独立抽屉，优先保障正文编辑区 >= 700px 彻底消除横向滚动条；无缝协同 useDataPermission，保持分册只读控制、ReadonlyBanner 与编辑锁心跳机制完好无损。

# APP-M2-T168：代码解释

- 对应任务：[APP-M2-T168](../tasks/APP-M2.md#app-m2-t168) · 编辑台章节加载、数据联动与向后兼容（关联 [APP-M2-T160](../tasks/APP-M2.md#app-m2-t160) 响应式断点、[APP-M2-T161](../tasks/APP-M2.md#app-m2-t161) 章节加载联动）
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 交付文档：[APP-M2-T168 交付](../delivery/APP-M2-T168.md)
- 日期：2026-10-22
- 实际改动与测试路径：
  - [EditorPage.tsx](../../frontend/web/src/EditorPage.tsx)
  - [outline-tree.ts](../../frontend/web/src/outline-tree.ts)
  - [styles.css](../../frontend/web/src/styles.css)
  - [editor-deep-linkage.test.mjs](../../tests/frontend/editor-deep-linkage.test.mjs)
  - [editor-deep-linkage.test.mjs](../../frontend/web/tests/editor-deep-linkage.test.mjs)

---

## 1. 核心业务痛点与技术决策

### 1.1 痛点与需求
1. **大纲与编辑台割裂**：原编辑台左侧仅呈现平铺章节列表与简易单选按钮，缺乏大纲树层级结构、章节类型（专项/通用/系统生成等）徽标、星号条款（★）与废标红线标记，用户无法在编辑正文时快速感知当前章节在大纲中的定位与合规约束；
2. **中屏桌面挤压横滚**：在 1280px ~ 1440px 标准显示器上，三栏布局全部展开时导致中间正文编辑区被压缩至 600px 左右，造成排版挤压并出现横向滚动条；
3. **未保存文字防丢失保护**：用户点击大纲树节点或抽屉中的章节切换时，若正文或草稿存在未保存文字（`dirty = true`），必须无缝触发离开拦截确认弹窗，绝不可静默丢失用户的编辑成果；
4. **分册只读与权限协同**：非当前登录人主管的分册或无权编辑章节，编辑台必须保持分册只读状态（展示 `ReadonlyBanner`、只读富文本视图 `data-testid="readonly-editor-view"`），且禁止获取编辑锁租约。

### 1.2 核心技术决策
- **纯函数映射 (`mapChaptersToOutlineNodes`)**：在 `outline-tree.ts` 中封装章节列表与招标文件条款的联合映射函数，智能推导星号条款（`isStarred`）、废标条款（`isBlocker`）、系统生成（`system_generated`）、封面目录（`cover_and_catalog`）与专项方案（`specialized`），为 UI 层提供统一的树节点数据源；
- **状态驱动的双折叠机制**：引入 `directoryCollapsed`（大纲收起）与 `assistantCollapsed`（助手收起）两组局部状态，配合 `useBreakpoint()` 派生的当前断点层级（`wide` / `standard` / `compact` / `sub-compact`），大纲收起时降级为 44px 迷你竖条（`chapter-directory-collapsed-strip`），助手收起时隐藏整个右侧栏，使得正文编辑区可用宽度达 800px ~ 1200px，彻底消除横滚；
- **独立大纲抽屉 (`outlineDrawerOpen`)**：在大纲目录收起或超窄屏时，顶部工具栏与迷你竖条均提供“以抽屉查看大纲树”按钮，点击在左侧滑出 420px 宽度的 `<Drawer>`，点击任意章节节点后平滑切页并自动关闭抽屉；
- **向后兼容性保障**：严格保留 `data-testid="readonly-editor-view"`、`data-testid="readonly-editor-text"`、`data-testid="editor-center-section"` 等单测与自动化测试桩。

---

## 2. 状态流转与调用链

### 2.1 章节切换与未保存防离开调用链
```text
用户点击 OutlineTreeView 节点 / Drawer 节点
               │
               ▼
   canLeaveCurrentChapter() / dirty 状态判定
        ┌──────┴──────┐
        ▼             ▼
   [dirty = false]  [dirty = true]
        │             │
        │             ▼
        │        唤起 Ant Design Modal.confirm
        │        提示“当前章节还有未保存文字”
        │             │
        │        ┌────┴────┐
        │        ▼         ▼
        │     [继续编辑]  [确认离开]
        │        │         │
        │        ▼         ▼
        │      取消操作   触发 action()
        │                  │
        └─────────┬────────┘
                  ▼
          setChapterId(targetId)
          setVolume(targetVolume)
                  │
                  ▼
      触发 useEffect 依赖监听
                  │
                  ▼
      loadChapter(targetId)
      - 清空当前 suggestion 与 diff
      - 重新拉取 Chapter / Draft
      - useDataPermission 重新计算只读态
      - 若有写权限则续租心跳；只读态则销毁心跳
```

### 2.2 响应式折叠状态与正文区宽度预算
```text
视口变化（window resize）
       │
       ▼
useBreakpoint() 监听到视口宽度变化
       │
       ├─ width >= 1680px (wide):
       │    directoryCollapsed = false, assistantCollapsed = false
       │    正文可用宽度 >= 1000px
       │
       ├─ 1280px <= width < 1440px (compact / standard):
       │    允许用户点击折叠大纲 (44px) 或折叠助手 (0px)
       │    正文可用宽度: 1280 - 48 - 44 - 320 - 32 = 836px >= 700px (无横滚！)
       │
       └─ width < 1280px (sub-compact):
            大纲目录自动推荐折叠或以抽屉展示
            正文可用宽度 >= 700px
```

---

## 3. 改动文件明细

### 3.1 `frontend/web/src/outline-tree.ts`
- 新增并导出纯函数 `mapChaptersToOutlineNodes(chapters, requirements)`：
  - 自动归集与当前章节关联的所有条款；
  - 判定 `isStarred`（`starred` 或 `is_starred`）；
  - 判定 `isBlocker`（`blocker`、`is_blocker` 或 `severity === 'blocker'`）；
  - 智能推导 `chapterType`（评分矩阵推导 `system_generated`，封面目录推导 `cover_and_catalog`，星号/废标推导 `specialized`）；
  - 输出字段支持 `clauseCount`、`requirementCount`、`assigneeName`、`assignee_name`、`chapterNumber` 与 `isLeaf: true`。

### 3.2 `frontend/web/src/EditorPage.tsx`
- 引入 `OutlineTreeView`、`ChapterTypeBadge`、`mapChaptersToOutlineNodes`、`useBreakpoint`；
- 声明 `directoryCollapsed`、`assistantCollapsed`、`outlineDrawerOpen` 状态；
- 使用 `useMemo` 派生 `outlineNodes = mapChaptersToOutlineNodes(workspace.chapters, workspace.requirements)`；
- 替换原有简易左侧目录，折叠时渲染 `chapter-directory-collapsed-strip`，展开时渲染 `OutlineTreeView`；
- 工具栏增加大纲抽屉按钮（`data-testid="toolbar-outline-drawer-btn"`）与助手折叠切换按钮（`data-testid="toggle-assistant-btn"`）；
- 页面底部追加 `<Drawer data-testid="editor-outline-drawer">` 挂载 `OutlineTreeView`。

### 3.3 `frontend/web/src/styles.css`
- 增加 `.editor-layout.directory-collapsed` 与 `.editor-layout.assistant-collapsed` 网格布局类；
- 增加 `.chapter-directory-panel` 树滚动样式与 `.chapter-directory-collapsed-strip` 迷你竖条样式；
- 增加 `@media (max-width: 1440px)` 响应式微调，确保正文区消除横向滚动条。

---

## 4. 自动化测试与契约保证

1. **纯逻辑单元测试 (`tests/frontend/editor-deep-linkage.test.mjs`)**：
   - 基础字段与分册映射；
   - 智能推导星号(★)与废标条款章节，并严格校验红线禁止标记为不适用；
   - 智能推导系统生成与封面目录章节类型与色彩；
   - 响应式断点与编辑台列数派生（宽屏 4 栏、标准/紧凑 3 栏）；
   - 中屏 1280px 编辑区最小 700px 预算计算与零横滚保障；
   - 未保存文字防离开拦截状态流逻辑；
2. **组件契约测试 (`frontend/web/tests/editor-deep-linkage.test.mjs`)**：
   - 静态 AST 检查大纲树组件与响应式 Hook 的引入与调用；
   - 折叠状态与派生大纲节点声明断言；
   - `data-testid` 属性契约（`editor-page-layout`、`collapse-outline-btn`、`expand-outline-btn`、`open-outline-drawer-btn`、`toggle-assistant-btn`、`toolbar-outline-drawer-btn`）；
   - 抽屉与只读态向后兼容契约（`editor-outline-drawer`、`readonly-editor-view`、`readonly-editor-text`、`ReadonlyBanner`）。
