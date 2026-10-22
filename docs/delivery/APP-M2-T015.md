为什么有这个文件：记录 APP-M2-T015 权限指令 `<Can>` 与按钮隐藏的交付状态、实现内容与验收证据。

它解决什么问题：集中呈现八角色细粒度按钮级鉴权、默认零 DOM 痕迹安全控制、构建体积与自动化单测证据，不提前标 done，供任务验收与质量审计。

# APP-M2-T015：权限指令 `<Can>` 与按钮隐藏交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T015 |
| 代码解释 | [docs/code/APP-M2-T015.md](../code/APP-M2-T015.md) |
| 验收 | 15 项专属自动化单测通过；全量 221 项前端单测通过；生产构建首屏产物 294.82 kB <= 295 kB 门禁达标；工程治理通过 |
| 项目进度 | 前端 M2 阶段推进，APP-M2-T015 提交 in-review，关联 ISSUE-007 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T015](../tasks/APP-M2.md#app-m2-t015)
- 依赖任务：[APP-M2-T014](APP-M2-T014.md)、BE-8ROLES-RBAC
- 分支：`feat/opencode-ICG`
- 本地验收状态：**in-review**（严禁私自标 done）
- 合入 / 发布状态：未合入主干，未发布

---

## 完成内容与变更文件

### 1. 核心产出
1. **纯逻辑权限核验模块 (`frontend/web/src/shell/can-directive.ts`)**：
   - 实现了操作与资源规范化解析 `normalizeAction`（支持冒号分隔与对象参数）；
   - 实现了基于 PRD v1.8 §2.3 的八角色权限判定纯函数 `can(perform, on, context)`；
   - 涵盖只读角色全局熔断、项目创建资质、解析与矩阵确认、章节分配编辑、锁接管、递交导出与内部稿导出差异化控制、敏感身份证号查看门禁等。
2. **权限上下文与 Hook (`frontend/web/src/shell/can-context.ts`, `frontend/web/src/shell/useCan.ts`)**：
   - 创建 `CanContext` React 上下文，支持在页面任意层级通过 `<CanProvider>` 注入；
   - 提供 `useCan(perform, on, context)` 与 `useCanMap(rules, context)` 便捷获取权限核验结果对象。
3. **权限指令组件 (`frontend/web/src/shell/Can.tsx`)**：
   - 封装 `<Can>` 声明式指令组件；
   - **默认严格安全模式**：未授权且无 fallback 时直接返回 `null`，DOM 树上零节点输出，杜绝 CSS `display:none` 绕过；
   - **支持降级模式**：提供 `passThrough` 置灰禁用及 `tooltipOnDisabled` 悬浮提示。
4. **App 顶层集成 (`frontend/web/src/app/App.tsx`)**：
   - 挂载 `<CanProvider>` 全局权限上下文；
   - 工作台“新建项目”按钮由 `<Can perform="project:create">` 保护，无资质角色无法在 DOM 中查看到该按钮。
5. **项目分工鉴权修正 (`frontend/web/src/shell/route-guard.ts`)**：
   - 修正了 `checkChapterEditPermission` 中项目负责人判定的成员边界，严格依据 `member.project_role === 'lead'` 判定，杜绝非负责人被误放行。

### 2. 变更文件清单
- `frontend/web/src/shell/can-directive.ts` (新增): 权限核验纯逻辑核心
- `frontend/web/src/shell/can-context.ts` (新增): React 上下文容器
- `frontend/web/src/shell/useCan.ts` (新增): `useCan` 与 `useCanMap` Hook 封装
- `frontend/web/src/shell/Can.tsx` (新增): `<Can>` 指令组件与 `<CanProvider>`
- `frontend/web/src/app/App.tsx` (修改): 挂载 CanProvider 与包裹新建项目按钮
- `frontend/web/src/shell/route-guard.ts` (修改): 精准化项目负责人判定
- `tests/frontend/can-directive.test.mjs` (新增): 10 项细粒度与表格驱动单测
- `frontend/web/tests/can-directive.test.mjs` (新增): 5 项 AST 与零 DOM 残留契约测试
- `docs/code/APP-M2-T015.md` (新增): 代码解释文档
- `docs/delivery/APP-M2-T015.md` (新增): 交付记录文档

---

## 代码解释

详见 [docs/code/APP-M2-T015.md](../code/APP-M2-T015.md)。涵盖原行为与目标行为对比、状态调用链、零 DOM 残留机制、关键判断与边界保护说明。

---

## 验收结果

### 1. 自动化单元测试验证
执行命令：
```bash
node --test tests/frontend/can-directive.test.mjs frontend/web/tests/can-directive.test.mjs
```
实测输出：
- `can-directive.ts exports can, normalizeAction and types`: 通过
- `useCan.ts exports useCan and useCanMap hooks`: 通过
- `Can.tsx exports Can, CanProvider, CanContext and re-exports hooks`: 通过
- `Can.tsx guarantees complete DOM omission on unauthorized by default`: 通过
- `App.tsx integrates CanProvider and protects create project button with Can directive`: 通过
- `normalizeAction handles colon formats, object parameters, and aliases`: 通过
- `table-driven: 8 roles x project:create permission`: 通过
- `table-driven: 8 roles x project:confirm / parse:confirm / matrix:confirm`: 通过
- `table-driven: 8 roles x submission:export (递交版 Word 导出) strictly limited to project_lead`: 通过
- `table-driven: volume:export_internal (内部稿导出) scope`: 通过
- `table-driven: chapter:edit and chapter:submit fine-grained division of labor`: 通过
- `chapter:takeover (接管编辑锁) permissions`: 通过
- `volume:finalize, volume:check, volume:unlock permissions`: 通过
- `id_card:view (查看完整身份证号) strictly limited to company_admin and data_admin`: 通过
- `universal readonly safety gate blocks all write operations`: 通过
**15 passed, 0 failed**。

全量前端自动化单测回归：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出：**221 passed, 0 failed**（耗时约 4.16s）。

### 2. 生产打包体积门禁验证
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
dist/assets/index-C6HeJH1S.js                294.82 kB │ gzip: 93.88 kB
dist/assets/project-team-DJIscAnz.js         294.79 kB │ gzip: 90.01 kB
✓ built in 1.69s
```
**门禁核验结论**：首屏主包 `index-C6HeJH1S.js` 体积为 **294.82 kB**，严格满足 $\le$ 295 kB 门禁预算要求。

---

## 项目进度

- 当前状态：APP-M2-T015 已完成全部开发与自测，状态标记为 `in-review`。
- 当前任务看板统计：397 项任务中，`done 52、in-review 30、in-progress 7、planned 259、blocked 48、ready 1`。
- 绝不私自标 done，等待 QA 独立复测与项目经理确认。

---

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 核对 PRD v1.8 §2.3 权限矩阵一致，无需调整正文 |
| ROADMAP | 本卡为计划内子任务推进，路线图快照保持稳定 |
| ARCHITECTURE | 权限指令组件规范已对齐前端架构，无需调整正文 |
| Issue 看板/详情 | 关联 [ISSUE-007](../../issues/ISSUE-007.md)，保持开启，不关闭 |
| TASK_BOARD | 同步更新 `APP-M2-T015` 行状态为 `in-review`，顶部统计 `in-review: 30`, `planned: 259` |
| DOCUMENT_INDEX | 登记 `code/APP-M2-T015.md` 与 `delivery/APP-M2-T015.md` 并记录更新记录 |

---

## 风险与后续

1. **后续扩展**：后续页面开发（如编辑台工具栏、导出页单选框、项目设置成员表）建议全面接入 `<Can>` 指令组件替代局部 ad-hoc 判断；
2. **后端协同**：前端按钮隐藏与后端 `BE-8ROLES-RBAC` 守卫互相补充，实现纵深防御。
