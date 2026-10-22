为什么有这个文件：记录QA对APP-M2-T016（数据权限的前端表现：只读态切换）的独立复验与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行数据权限专属单测、前端全量单测套件、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 PRD v1.8 §2.3 与 §5.11.9 所要求的“只读成员与集团管理员看到文本而非控件，不是渲染了 input/select 之后再去 disabled，而是在只读模式下直接渲染排版语义纯文本展示”核心安全约束，全面验证多粒度数据权限判定算法（项目级/分册级/章节级）、跨分册负责人分册只读、非指派章节章节级只读、只读提示横幅清晰指引与操作条抑制安全机制。

# APP-M2-T016 数据权限的前端表现：只读态切换独立复测与 QA 签署

- 被验任务：[APP-M2-T016](../tasks/APP-M2.md#app-m2-t016) · 数据权限的前端表现：只读态切换（项目 / 分册 / 章节）
- 关联审查任务：REV-M0-T56
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T016 交付](../delivery/APP-M2-T016.md)、[代码解释](../code/APP-M2-T016.md)
- 被验核心文件：`frontend/web/src/shell/data-permission.ts`、`frontend/web/src/shell/useDataPermission.ts`、`frontend/web/src/shell/ReadOnlyGate.tsx`、`frontend/web/src/editor/EditorPage.tsx`、`frontend/web/src/library/MetadataForm.tsx`、`frontend/web/src/shared/styles.css`、`tests/frontend/data-permission.test.mjs`、`frontend/web/tests/data-permission.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T016 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 排版语义纯文本展示与零控件 DOM 残留硬安全门禁 | 通过 | `ReadOnlyField` 与 `ReadOnlyGate` 严格遵守 PRD v1.8 §5.11.9 验收约束：只读状态下直接渲染排版语义纯文本 `<span>` 或 `<pre>` 节点，**DOM 树上零 `<input>`、`<textarea>` 或 `<select>` 控件节点**；从底层杜绝攻击者使用浏览器 DevTools 将 `disabled` 改为 `false` 篡改数据 |
| AC-02 八类系统角色项目级数据权限判定 | 通过 | `data-permission.ts` 纯函数 `resolveDataPermission` 表格驱动测试核验：`platform_admin`、`group_admin`、`auditor`、`viewer` 严格熔断进入 `scope: 'project', readOnly: true, reasonType: 'role_readonly'` 全项目只读态；`company_admin` 与 `project_lead` 全项目全分册全章节放行编辑 |
| AC-03 项目内团队角色与非成员边界控制 | 通过 | ① 项目内成员设置 `project_role === 'readonly'` 时，进入 `scope: 'project', readOnly: true, reasonType: 'project_readonly'` 并提示“当前项目团队中被分配为只读成员”；② 非团队成员（未在 `team.members` 登记且非公司管理员）进入 `scope: 'project', readOnly: true, reasonType: 'not_member'` 并提示“您不是当前项目团队成员” |
| AC-04 分册负责人跨分册分工与分册级只读态 | 通过 | 针对分册主管实施精准分工隔离：技术分册主管访问技术分册正常放行，但进入商务分册时，严格转入 `scope: 'volume', readOnly: true, reasonType: 'wrong_volume'`，并明确提示“您当前是【技术分册】负责人，在【商务分册】中处于只读浏览状态”；商务主管进入技术分册同理严格只读拦截 |
| AC-05 普通编写人跨章节与未指派章节级只读态 | 通过 | 投标编写人（`bid_writer`）进入已指派章节放行编辑；进入未指派章节（`assignee_id !== userId`）时，严格转入 `scope: 'chapter', readOnly: true, reasonType: 'not_assigned'`，明确提示“本章节【...】未分配给您，当前仅可只读浏览”；无指派章节跨入其他分册自动按分册级只读拦截 |
| AC-06 编辑台正文纯文本与只读横幅落地 | 通过 | `EditorPage.tsx` 动态计算 `isReadOnlyView = !canEdit || dataPermission.readOnly`：只读模式下，正文输入框切换为排版语义纯文本容器（`<div className="chapter-editor-readonly-text" data-testid="readonly-editor-text"><pre>...`），顶部挂载带具体范围与角色原因的 `ReadonlyBanner`；工具栏写操作按钮安全禁用，同时保留“保留当前文字到本地”与版本查阅能力 |
| AC-07 元数据表单只读态纯文本与操作条抑制 | 通过 | `MetadataForm.tsx` 支持 `readOnly` 属性：开启时表单各项通过 `<ReadOnlyField readOnly={true} />` 输出只读排版纯文本，同时底层逻辑自动隐藏吸底提交操作条 `FormActionFooter`，杜绝只读表单触发保存提交 |
| AC-08 生产构建打包与包体积门禁（<= 295 kB） | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 619ms，0 错误 0 告警）；首屏主包 `index-fu3kmuVM.js` 体积为 **294.86 kB**（Gzip 后 **93.90 kB**），完全满足 **<= 295 kB** 预算门禁红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 数据权限专项测试套件 | `node --test tests/frontend/data-permission.test.mjs frontend/web/tests/data-permission.test.mjs` | **12 passed, 0 failed** (表格驱动 6 项 + AST/纯文本契约断言 6 项) | 0.46s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **233 passed, 0 failed** (包含 12 项数据权限专项单测) | 2.64s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 619ms) | 0.62s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-fu3kmuVM.js` **294.86 kB**（gzip: 93.90 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **“只读渲染排版纯文本而非 disabled 控件”的合规与安全价值**：PRD v1.8 §5.11.9 提出的这一约束极为严谨。普通前端置灰方案极易受到前端黑客攻击（通过 DevTools Console 遍历 input 元素并设 `.disabled = false` 即可提交脏数据）。本项目通过在条件分支中彻底把 `<Input.TextArea>` / 表单 `<input>` 替换为 `<span>` / `<pre>`，从 DOM 树结构上彻底消除了被篡改提交的可能性。
2. **三级粒度清晰的只读原因反馈**：在用户浏览无权编辑的内容时，单纯提示“无权限”容易造成疑惑。本模块输出的 `readOnlyReason` 明确指出了当前身份（如“技术分册负责人”）、目标范围（如“商务分册”）以及行动指引，体验平滑清晰。
3. **首屏主包体积再次逼近极限（294.86 kB / 295.00 kB，余量仅 0.14 kB）**：随着业务组件丰富，虽然全部代码均已接入按需懒加载，但首屏 index chunk 体积已处于门禁临界点。后续任务切勿在首屏直接引入未拆分的重量级图标库或图表库，必须保持高警惕性。

## 签署状态

APP-M2-T016 保持 **in-review**，**严禁标 done**。
