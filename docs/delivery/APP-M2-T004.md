为什么有这个文件：交付前端业务小组件（LevelTag、AiTag、DirectTag、Cite、SourceBar）的封装实现、测试与验证结果。

它解决什么问题：统一正文与业务标签呈现规范，严格锁定 AI 紫专用，落实答案卡直接采用蓝色标签，提供资料引用悬浮卡片与段落来源依据指纹溯源，且所有文本对比度均符合 WCAG AA 4.5:1 标准。

# APP-M2-T004：业务小组件封装交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T004 |
| 代码解释 | [代码解释](../code/APP-M2-T004.md) |
| 验收 | 前端 141 项测试全部通过（新增 14 项专项全部通过）、`pnpm --dir frontend/web build` 成功且产物体积无反弹，WCAG 4.5:1 对比度通过，AI 紫严格隔离通过 |
| 项目进度 | 标至 in-review。关联 ISSUE-007。依赖 BE-M0-T01（已 done）、APP-M2-T003（in-review）。下一业务组件任务：APP-M2-T005 |
<!-- task-delivery:end -->

## 关联与状态

- 日期：2026-10-21
- 里程碑：APP-M2
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联任务卡：[APP-M2-T004](../tasks/APP-M2.md#app-m2-t004)
- 前置依赖：[BE-M0-T01](../tasks/BE-M0.md#be-m0-t01)（done）、[APP-M2-T003](../tasks/APP-M2.md#app-m2-t003)（in-review）
- 分支：`main`
- 本地验收状态：本地自动化测试与生产构建全部通过，已按流程标至 `in-review`，等待主 Agent、QA 与项目经理评审，严禁私自标 `done`
- 合入 / 发布状态：未合入生产分支，未发布

## 完成内容与变更文件

本次任务在 `frontend/web/` 下完成了统一业务小组件的封装，全面覆盖设计规范 §7.1、§9.3、§9.4、§9.5 及任务要求中的五大业务组件：

1. **`frontend/web/src/business-tags.ts`（新增）**：
   - 提取业务组件纯函数逻辑与色彩令牌：`BIZ_COLOR_TOKENS`、`isAiColor`、`assertNotAiColor`；
   - 严格落实 AI 紫色系防混用检测，确保非 AI 标签误用紫色时直接告警阻断；
   - 实现核心解析器：`resolveLevelTag`（条款与规则级别解析）、`resolveAiTag`（AI 生成/修改变体解析）、`resolveDirectTag`（系统直查深蓝解析）、`resolveCite`（引用元信息解析）、`resolveSourceBar`（段落与底部来源条解析）；
   - 实现依据指纹安全截断与格式化：`formatFingerprint`。

2. **`frontend/web/src/BusinessTags.tsx`（新增）**：
   - **`LevelTag`**：条款级别标签，支持实心红底白字阻断（`blocker`、`void`、废标条款、否决项）、浅红底关键要求（`star`、`critical`、星号条款）、浅橙底警告（`warning`、需复核）、青色加分项/评分项（`bonus`、`scoring`）、极客蓝资格要求（`qualification`）与中性灰一般条款（`general`），均具备无障碍 role 与 aria-label；
   - **`AiTag`**：AI 辅助标签，严格使用锁定 AI 紫（`#6E4BD8` / `#5329B3`），覆盖建议（`suggestion`）、生成（`generated`）、整章候选（`candidate`）、模型建议（`model`）、助手建议（`assistant`）与演示建议（`demo`）；
   - **`DirectTag`**：直接响应 / 直接采用标签，使用蓝色浅底（`#EEF3FC` / `#1E4DB7`），与答案卡规范一致，绝不使用 AI 紫；
   - **`Cite`**：引用标注组件，支持资料证据（`[证]`）、方案片段（`[片]`）、招标原文页码（`P.47`）、事实变量高亮（黄底下划线）与无来源灰标签，内置 Popover 悬浮查看资料名称、版本号、有效期、状态、责任人与摘录内容；
   - **`SourceBar`**：来源条组件，支持段落左侧 3px 色条（覆盖证据、片段、原文、模型、助手、人工、系统 7 种锁定来源色）与横向底部来源条，展示资料名、版本号、依据指纹（`fp: 9f8e7d...`）与核对触发动作。

3. **`frontend/web/src/styles.css`（修改）**：
   - 增加 `.icg-level-tag`、`.icg-level-solid`、`.icg-ai-tag`、`.icg-direct-tag`、`.icg-cite`、`.icg-source-bar-paragraph`、`.icg-source-bar-bottom`、`.icg-source-stale` 等类名，保证与 ProLayout 主题混入时对比度符合标准。

4. **`frontend/web/src/EditorPage.tsx`（修改）**：
   - 接入 `AiTag`、`Cite` 与 `SourceBar`，替换原生零散标签，统一候选标签、招标原文引用与正文来源条。

5. **`tests/frontend/business-tags.test.mjs` 与 `frontend/web/tests/business-tags.test.mjs`（新增）**：
   - 新增 14 项完整的前端测试，全面覆盖色彩对比度公式、AI 紫防混用隔离、标签解析逻辑、AST 导出断言与无障碍属性。

## 代码解释

详细调用链、状态机、色彩令牌与无障碍设计决策参见 [APP-M2-T004 代码解释](../code/APP-M2-T004.md)。

## 验收结果

### 1. 自动化测试套件执行
在仓库根目录执行：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
执行结果：
- **总测试数**：141 项（变更前 127 项，新增 14 项专项测试）
- **通过数**：141 项
- **失败数**：0 项
- **耗时**：约 1.4 秒
- 专项测试验证了：
  - WCAG 4.5:1 对比度公式与各颜色令牌验证全部通过；
  - `isAiColor` 与 `assertNotAiColor` 成功拦截非 AI 标签使用紫色；
  - 条款级别多类别解析（阻断、星号、加分、资格、一般）正确无误；
  - AI 标签 6 种变体推导通过；
  - DirectTag 蓝底白边与防混用断言通过；
  - Cite 5 类引用推导及上标/行内变量分流通过；
  - SourceBar 7 种段落来源色与依据指纹格式化通过；
  - AST 语法树断言 5 大组件导出与 `data-testid` 完整声明。

### 2. 构建与体积审计
在仓库根目录执行：
```bash
pnpm --dir frontend/web build
```
执行结果：
- TypeScript 类型检查完全通过（`tsc -b` 无报错）；
- Vite 生产环境打包耗时 0.92 秒；
- 产物体积无反弹：
  - `dist/assets/index-*.js`：289.99 kB（gzip: 92.21 kB，较前序 289.96 kB 保持完全平稳）；
  - `dist/assets/index-*.css`：24.99 kB（gzip: 5.87 kB）；
  - 路由级代码拆分（Route-level Code Splitting）完好，未打破各页面的延迟加载。

## 项目进度

- 本卡状态由 `planned` 标为 `in-review`。
- 绝不私自将任务标为 `done`，等待主 Agent、QA 与项目经理审查。
- 看板现况：APP-M2 中 T001、T002、T008、T078、T114 为 done，T003、T004 为 in-review，T124 为 ready，其余 planned。
- 下一业务组件任务：[APP-M2-T005](../tasks/APP-M2.md#app-m2-t005)（元数据驱动表格：ProTable 封装、列合并、无横滚优先）。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 无变化。标签和来源规范与 §2.3 / 5.12 / 7.2 契合 |
| ROADMAP | 同步记录 APP-M2-T004 提交 in-review |
| ARCHITECTURE | 无变化。小组件库符合前端现有 ProLayout 与业务标签分层规范 |
| Issue 看板/详情 | ISSUE-007 保持 in-progress；记录 APP-M2-T004 完成开发并提交 in-review |
| TASK_BOARD / PROJECT_STATUS | 更新 TASK_BOARD.md 中 APP-M2-T004 状态为 in-review 并链接交付文档 |
| tasks/APP-M2.md | 更新 APP-M2-T004 状态为 in-review 并注明已提交交付与代码解释 |
| DOCUMENT_INDEX.md | 登记 D-459 ~ D-464 记录及日志行 |

## 风险与后续

1. **TipTap 节点深度集成**：段落左侧 3px 色条当前通过包裹层实现，在后续 APP-M2-T162（SourceBar 来源标记）与富文本编辑器集成时，可作为 TipTap 段落属性进行扩展渲染；
2. **后续组件消费**：后续任务（如 APP-M2-T005 ProTable 封装、APP-M2-T006 表单、APP-M2-T025 矩阵）可直接引入 `BusinessTags.tsx` 展示标准化条款级别、来源条与 AI 标识。
