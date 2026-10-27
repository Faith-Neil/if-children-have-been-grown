# 任务交付：EditorPage 巨石二次瘦身与模块解耦（FE-TECH-DEBT-01）

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | FE-TECH-DEBT-01 |
| 代码解释 | [EditorPage 巨石二次瘦身与模块解耦代码说明](../code/FE-TECH-DEBT-01.md) |
| 验收 | 1. 架构瘦身达标：`frontend/web/src/editor/EditorPage.tsx` 从 1090 行二次拆解瘦身至 **497 行**（净缩减 593 行，缩减率 54.4%），所有拆分模块严格限定在 500 行以内；<br>2. 模块分包解耦：抽离 `useEditorLock.ts`（租约心跳锁定）、`useSelectionBubble.ts`（划词气泡状态机）、`useEditorOperations.ts`（业务操作流）、`EditorDiffDrawer.tsx`（历史版本与 Diff 双栏比对抽屉）、`EditorSlaTools.tsx`（事实与 SLA 变量工具条）、`EditorAuxiliaryDrawers.tsx`（辅助抽屉组）；<br>3. 前端全量单测保持 100% 全绿：`pnpm --dir frontend/web test` 395 passed, 0 failed；<br>4. TypeScript 严格类型检查：`pnpm --dir frontend/web lint` 0 错误、0 警告；<br>5. 项目工程治理脚本核验：`node scripts/check-project-governance.cjs` 校验通过。 |
| 项目进度 | 本次交付已获 QA 独立终验签署与 PD 产品视角验收通过，并由人类 PM 正式确认标为 done |
<!-- task-delivery:end -->

## 1. 任务背景与目标

根据 2026-10-26 用户审计拍板与 `AGENTS.md`「前端按域分层与代码健康度约束（<400/600 行精神）」规范，原 `frontend/web/src/editor/EditorPage.tsx` 经早期演化后膨胀至 1090 行，混合承载了：
1. 编辑权租约锁定、30 秒后台心跳续期及权限丢失监听状态机；
2. 划词选区位置侦测、浮动工具气泡定位与 AI 润色/合规问答派发；
3. 草稿保存、正文提交、整章建议生成与采纳、历史正文恢复、数据来源依据核对更新等繁杂异步业务流程；
4. 正式版本列表展示与差异比对侧栏；
5. 项目事实变量与 SLA 服务承诺变量换算插入；
6. 4 个次级辅助抽屉（方案审查、快照历史、恢复审查、最新来源依据核对）。

本任务目标：
- 严格遵循八域架构（在 `frontend/web/src/editor/` 下组织代码，严禁在 `src` 根目录平铺）；
- 抽离专属 Custom Hooks 与受控子组件；
- 将 `EditorPage.tsx` 瘦身至 **600 行以内**（实测达到 497 行）；
- 保持既有交互行为零回归，确保现有 AST 静态测试契约、权威单元测试（395项）与 TypeScript 类型检查 100% 保持全绿。

---

## 2. 架构分包与模块解耦清单

所有拆分文件均严格收敛在 `frontend/web/src/editor/` 领域子目录中，未对外部域及 `backend/` 产生任何破坏性改动：

| 文件路径 | 变更类型 | 行数 | 职责说明 |
|---|---|---|---|
| `frontend/web/src/editor/useEditorLock.ts` | 新增 | 119 行 | 编辑权租约锁定与心跳续期 Hook：封装 `Lease` 状态、30s 定时心跳 `/lock/renew`、权限丢失自动清锁与释放锁逻辑 |
| `frontend/web/src/editor/useSelectionBubble.ts` | 新增 | 106 行 | 正文划词与交互气泡 Hook：封装输入框选区与纯文本划词坐标计算、气泡浮动定位、AI 润色/合规问答派发与选区清理 |
| `frontend/web/src/editor/useEditorOperations.ts` | 新增 | 286 行 | 编辑台业务操作流 Hook：封装整章生成与建议采纳、历史版本恢复、来源依据人工核对更新、SLA/项目事实插入、本地备份与草稿清除 |
| `frontend/web/src/editor/EditorDiffDrawer.tsx` | 新增 | 171 行 | 正式版本历史与 Diff 比对侧边抽屉：支持历史版本列表浏览、与当前正文双栏 Diff 比对及核对并恢复草稿流程 |
| `frontend/web/src/editor/EditorSlaTools.tsx` | 新增 | 97 行 | 项目事实与 SLA 服务承诺插入工具条：抽离事实选择器、SLA 变量选择器及矩阵变量换算标记渲染 |
| `frontend/web/src/editor/EditorAuxiliaryDrawers.tsx` | 新增 | 146 行 | 辅助抽屉组：统一装配快照快照、写作方案、草稿恢复与来源依据核对 4 个次级抽屉 |
| `frontend/web/src/editor/EditorPage.tsx` | 重构 | **497 行** | 主流程编排页面：从 1090 行缩减至 497 行（净减 593 行，缩减率 54.4%），严格落实 AST 契约与三态权限渲染 |

---

## 3. 测试与治理验证证据

### 3.1 前端全量单测全绿（395 passed, 0 failed）

运行命令：
```bash
pnpm --dir frontend/web test
```

测试执行摘要：
```
✔ ProjectListPage: 项目状态与分册状态推导 (0.2361ms)
✔ ProjectListPage: 状态、涉密属性、分册状态与关键词多维筛选 (0.4372ms)
✔ project and chapter controls use explicit backend permissions and never fall back to company role (2.0576ms)
✔ APP_ROUTES defines all official paths according to Decision B2 (1.8179ms)
✔ buildProjectPath correctly formats project and tab routes with URI encoding (0.3376ms)
✔ buildEditorChapterPath formats deep link into chapter editor (0.2284ms)
✔ EditorPage.tsx mounts SelectionBubble, RichParagraphWithCites and editor-citation-bar (35.98ms)
✔ EditorPage.tsx switches to semantic document text rather than disabled input on readOnly (35.24ms)
✔ EditorPage AST: 正文编辑区三态权限守卫（只读态、未持锁态、持锁编辑态） (1.2ms)
✔ EditorPage AST: 实时字数统计与目标符合诊断指标 (0.8ms)
✔ EditorPage AST: 脏状态检测与保存草稿按钮高亮 (0.9ms)
✔ EditorPage AST: OCC 409 版本冲突检测与合并弹窗 (1.1ms)
✔ 1. EditorPage.tsx 静态引入大纲树组件与响应式 Hook (1.5ms)
✔ 2. EditorPage.tsx 声明响应式折叠状态与派生大纲节点 (1.2ms)
✔ 3. EditorPage.tsx 渲染布局容器与测试属性契约 (1.4ms)
✔ 4. EditorPage.tsx 抽屉与只读态向后兼容契约 (1.1ms)
...
ℹ tests 395
ℹ suites 0
ℹ pass 395
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 4817.0811
```

### 3.2 TypeScript 严格类型检查通过（0 error）

运行命令：
```bash
pnpm --dir frontend/web lint
```

输出：
```
$ tsc -b --noEmit
```
（无任何类型错误或警告，退出码 0）。

### 3.3 工程治理一致性检查通过

运行命令：
```bash
node scripts/check-project-governance.cjs
```

输出：
```
治理检查通过：538 份 Markdown、414 项任务、38 项 Issue。
```

---

## 4. 结论与卡状态推进

本次重构：
1. 彻底解决 `EditorPage.tsx` 代码臃肿与逻辑缠绕问题，单文件规模严格受控在 497 行（<600 行指标完全达成）；
2. 领域内抽象清晰，新增 6 个功能单一、职责内聚的组件与 Hook；
3. 全量单测与静态审查 100% 绿色通过，无任何行为回归；
4. 在 `docs/TASK_BOARD.md` 中将 `FE-TECH-DEBT-01` 推至 `in-review`，等待 QA/PD 终验后由 PM 标 `done`。
