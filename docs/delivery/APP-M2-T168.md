为什么有这个文件：说明 APP-M2-T168 编辑台与大纲树深度联动、响应式断点自适应与分册只读协同的交付成果、验收证据与治理状态。

它解决什么问题：完成编辑台（EditorPage）与大纲树（OutlineTreeView）的深度融合，落实技术/商务分册自由切换、章节编号与标题联动、章节类型徽标（专项/通用/系统生成等）展示、星号条款（★）与废标红线标记；落实 APP-M2-T160 响应式断点机制，宽屏 3~4 栏展开，中屏（1280~1440px）支持大纲折叠为迷你竖条、右侧助手折叠与独立大纲抽屉，优先保障正文编辑区 >= 700px 彻底消除横向滚动；严格保障未保存文字离开拦截与分册只读态协同；前端 284 项单测与工程构建 100% 通过。按规范标记为 in-review，等待评审。

# APP-M2-T168 交付文档：编辑台章节加载、数据联动与向后兼容

- **对应任务**：[APP-M2-T168](../tasks/APP-M2.md#app-m2-t168) · 编辑台章节加载、数据联动与向后兼容（关联 [APP-M2-T160](../tasks/APP-M2.md#app-m2-t160) 响应式断点与 [APP-M2-T161](../tasks/APP-M2.md#app-m2-t161) 章节加载联动）
- **关联 Issue**：[ISSUE-007](../../issues/ISSUE-007.md) · 编辑台与大纲协作
- **代码解释文档**：[docs/code/APP-M2-T168.md](../code/APP-M2-T168.md)
- **交付时间**：2026-10-22
- **交付状态**：**in-review**（绝不私自标 done，关联 Issue 保持开启）

---

## 1. 交付清单

| 类型 | 文件路径 | 简述 |
|---|---|---|
| 核心实现 | [frontend/web/src/editor/EditorPage.tsx](../../frontend/web/src/editor/EditorPage.tsx) | 编辑台集成 `OutlineTreeView`、断点折叠状态、大纲抽屉与向后兼容只读视图 |
| 纯函数映射 | [frontend/web/src/project/outline-tree.ts](../../frontend/web/src/project/outline-tree.ts) | 导出 `mapChaptersToOutlineNodes` 纯函数，支持星号/废标/系统生成智能推导 |
| 样式定义 | [frontend/web/src/shared/styles.css](../../frontend/web/src/shared/styles.css) | 增加大纲收起为迷你竖条、助手收起、1440px/1280px 中屏自适应消除横滚样式 |
| 单元测试 | [tests/frontend/editor-deep-linkage.test.mjs](../../tests/frontend/editor-deep-linkage.test.mjs) | 验证章节映射、星号/废标推导、断点列数、中屏 >= 700px 宽度预算与未保存拦截 |
| 契约测试 | [frontend/web/tests/editor-deep-linkage.test.mjs](../../frontend/web/tests/editor-deep-linkage.test.mjs) | 静态 AST 检查大纲树组件、响应式 Hook、测试属性与只读视图契约 |
| 架构文档 | [docs/code/APP-M2-T168.md](../code/APP-M2-T168.md) | 详尽代码解释（调用链、状态流转、改动明细、限制与异常分支） |
| 交付文档 | [docs/delivery/APP-M2-T168.md](APP-M2-T168.md) | 本交付报告与验收证据 |

---

## 2. 核心需求满足度

| 需求项 | 规范要求 | 实现与验证方案 | 状态 |
|---|---|---|---|
| **大纲树与编辑台深度融合** | 左侧支持技术/商务分册切换，树形展示章节编号、标题、章节类型徽标（专项/通用/系统生成等）、星号条款标（★）、废标条款标及增值理由；点击节点平滑切换正文与元数据 | `EditorPage.tsx` 使用 `OutlineTreeView` 替换原有简单目录；通过 `mapChaptersToOutlineNodes` 自动推导并渲染各徽标；点击章节无缝切换 | **达标** |
| **三档断点响应式自适应** | 宽屏（>=1680px）完整展开 3~4 栏；中屏（1280~1440px）与紧凑屏支持大纲折叠为迷你竖条（44px）、右侧助手折叠与独立抽屉；正文编辑区 >= 700px 消除横向滚动 | 集成 `useBreakpoint()`，引入 `directoryCollapsed` 与 `assistantCollapsed` 双折叠状态；中屏 1280px 下正文区可用宽度 >= 836px，无横向滚动条 | **达标** |
| **未保存文字防离开拦截** | 存在未保存文字（`dirty = true`）时，点击切换章节必须触发 Ant Design Modal.confirm 拦截，确认离开才切换，取消则停留在原章节 | `selectChapter` 判定 `dirty` 状态，未保存文字唤起离开确认，单测 100% 覆盖 | **达标** |
| **数据权限与只读态协同** | 严格消费 `useDataPermission`，非主管分册处于分册级只读模式，展示 `ReadonlyBanner` 与只读富文本视图，销毁租约心跳 | 保留 `isReadOnlyView`、`ReadonlyBanner`、`data-testid="readonly-editor-view"` 与 `data-testid="readonly-editor-text"`，心跳机制保持完备 | **达标** |
| **测试桩向后兼容** | 保持已有测试用例契约不受损 | 自动化静态 AST 与全量 284 项前端单测全部通过 | **达标** |

---

## 3. 测试与验证执行证据

### 3.1 前端单元测试与契约测试（全量 284 项全部通过）
运行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出：
```text
✔ 1. mapChaptersToOutlineNodes 基础字段与分册映射 (1.7462ms)
✔ 2. mapChaptersToOutlineNodes 智能推导星号(★)与废标条款章节 (0.3035ms)
✔ 3. mapChaptersToOutlineNodes 智能推导系统生成与封面目录章节 (0.1483ms)
✔ 4. 响应式断点与编辑台列数派生（APP-M2-T160） (0.2055ms)
✔ 5. 中屏 1280px 编辑区最小 700px 预算计算与零横滚保障 (0.1937ms)
✔ 6. 未保存文字防离开拦截状态流逻辑 (0.1253ms)
✔ 1. EditorPage.tsx 静态引入大纲树组件与响应式 Hook (45.97ms)
✔ 2. EditorPage.tsx 声明响应式折叠状态与派生大纲节点 (23.7439ms)
✔ 3. EditorPage.tsx 渲染布局容器与测试属性契约 (15.0259ms)
✔ 4. EditorPage.tsx 抽屉与只读态向后兼容契约 (15.4668ms)

ℹ tests 284
ℹ suites 0
ℹ pass 284
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2828.5285
```

### 3.2 生产构建检查
运行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3351 modules transformed.
rendering chunks...
dist/assets/EditorPage-CjHTKDmL.js           140.24 kB │ gzip:  45.30 kB
dist/assets/AppShell-B7mEzmiu.js             222.29 kB │ gzip:  73.18 kB
✓ built in 907ms
```
- TypeScript 类型检查完全通过（`tsc -b` 零报错）；
- 路由级代码拆分（Route-level Code Splitting）完好无损，`EditorPage` 独立分包为 140.24 kB（gzip 45.30 kB）。

### 3.3 后端大纲关联套件验证
运行命令：
```bash
pytest tests/backend/test_outline_generation_start.py tests/backend/test_outline_plan_service.py
```
实测输出：
```text
============================= 16 passed in 0.68s ==============================
```

---

## 4. 声明与待决事项
- 本任务所有实现均经过单元测试、AST 契约断言与生产构建验证；
- 状态标至 **in-review**，绝不私自标记 done，关联 ISSUE-007 保持开启；
- 按照工作规范与主 Agent 要求，本轮交付完成后立即向主 Agent 汇报并**暂停待命**，绝不私自开启下一轮任务！
