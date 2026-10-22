为什么有这个文件：记录 APP-M2-T123 大纲排序、章节类型和增值理由的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现分册（技术/商务）章节树层级呈现、5 类章节类型（专项/通用/系统生成/封面目录/不适用）徽标、同级章节上移/下移排序算法、增值理由快捷模板与弹窗编辑、星号条款(★)与废标条款对应章节绝对禁止标记为不适用的合规红线门禁、非主管分册数据权限只读协同、首屏 Bundle 体积控制（<= 295 kB）与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T123：大纲排序、章节类型和增值理由交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T123 |
| 代码解释 | [docs/code/APP-M2-T123.md](../code/APP-M2-T123.md) |
| 验收 | 11 项专属自动化单测通过；全量 274 项前端单测通过；生产构建首屏产物 294.86 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T123 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-22
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T123](../tasks/APP-M2.md#app-m2-t123)
- 依赖任务：[APP-M1-T15](../tasks/APP-M1.md#app-m1-t15)、[APP-M2-T116](../tasks/APP-M2.md#app-m2-t116)
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **大纲树纯逻辑层 (`frontend/web/src/project/outline-tree.ts`)**：
   - 定义 5 类核心章节类型（`specialized` 专项方案、`general` 通用方案、`system_generated` 系统生成、`cover_and_catalog` 封面目录、`not_applicable` 不适用）；
   - 落实**核心门禁红线**：`canMarkNotApplicable` 严格拦截关联星号条款(★)或废标条款的章节，禁止标记为不适用；
   - 实现了同级章节排序算法 `reorderNodes` 与章节多级编号递归归一化 `normalizeChapterNumbers`；
   - 实现了增值理由校验 `validateValueAddedReason` 与常用预置模板 `VALUE_ADDED_PRESETS`。
2. **章节类型徽标组件 (`frontend/web/src/project/ChapterTypeBadge.tsx`)**：
   - 封装 `ChapterTypeBadge`，呈现对应类型 Tag 与图标，系统生成类型专属紫标识。
3. **增值理由编辑弹窗 (`frontend/web/src/project/ValueAddedReasonModal.tsx`)**：
   - 提供 500 字上限输入、字符数即时统计、常用模板快速插入与数据权限只读态拦截。
4. **大纲树协同编辑核心视图 (`frontend/web/src/project/OutlineTreeView.tsx`)**：
   - 支持技术分册/商务分册 Tab 维度过滤；
   - 呈现章节编号、标题、星号条款标(★)、废标条款标及关联条款数；
   - 章节类型下拉在遇到星号/废标条款时置灰禁用“不适用”选项并提示禁止原因；
   - 支持上移/下移排序按钮；
   - 接入 `useDataPermission`，非主管分册处于分册级只读模式，展示只读警告条并禁用全部写操作；
   - 支持编辑增值理由与点击“编辑台”跳转联动。

### 2. 变更文件清单
- `frontend/web/src/project/outline-tree.ts` (新增): 章节类型元信息、星号废标门禁拦截、排序与编号归一化纯逻辑
- `frontend/web/src/project/ChapterTypeBadge.tsx` (新增): 章节类型徽标组件
- `frontend/web/src/project/ValueAddedReasonModal.tsx` (新增): 增值理由编辑弹窗
- `frontend/web/src/project/OutlineTreeView.tsx` (新增): 大纲树协同编辑核心视图组件
- `tests/frontend/outline-tree.test.mjs` (新增): 7 项纯逻辑单测
- `frontend/web/tests/outline-tree.test.mjs` (新增): 4 项 AST 静态契约与门禁断言测试
- `docs/code/APP-M2-T123.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T123.md` (新增): 交付记录文档

---

## 验收证据

### 1. 自动化单测执行记录
```bash
$ node --test tests/frontend/outline-tree.test.mjs frontend/web/tests/outline-tree.test.mjs
✔ 1. outline-tree.ts 导出核心类型、门禁判定与排序算法 (14.4886ms)
✔ 2. ChapterTypeBadge.tsx 导出徽标组件并支持 5 类章节类型 (3.0505ms)
✔ 3. ValueAddedReasonModal.tsx 具备字数限制、预置模板与只读拦截 (3.5589ms)
✔ 4. OutlineTreeView.tsx 落实星号/废标门禁拦截、权限协同与排序跳转 (4.7318ms)
✔ 1. 章节类型元信息与配置定义 (getChapterTypeMeta) (1.1699ms)
✔ 2. 【核心门禁红线】星号条款章节绝对禁止标记为“不适用” (canMarkNotApplicable) (0.2332ms)
✔ 3. 【核心门禁红线】废标条款章节绝对禁止标记为“不适用” (canMarkNotApplicable) (0.0952ms)
✔ 4. 普通章节允许正常标记为“不适用” (0.0825ms)
✔ 5. 章节同级顺序调整算法 (reorderNodes) (1.4382ms)
✔ 6. 多层级编号归一化 (normalizeChapterNumbers) (0.1661ms)
✔ 7. 增值理由校验 (validateValueAddedReason) (0.1361ms)
ℹ tests 11
ℹ pass 11
ℹ fail 0
```

全量前端单测回归：
```bash
$ node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 274
ℹ pass 274
ℹ fail 0
```

### 2. 生产构建与 Bundle 体积门禁
```bash
$ pnpm --dir frontend/web build
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
dist/assets/index-EIM2ccZO.js                294.86 kB │ gzip:  93.91 kB
✓ built in 1.10s
```
- 首屏主包体积：`294.86 kB` <= `295.00 kB` 门禁红线，严格受控。

---

## 声明
本卡所有代码均经过严格自测与门禁检查，状态标至 **in-review**，绝不私自标 done，关联 Issue 保持开启。
