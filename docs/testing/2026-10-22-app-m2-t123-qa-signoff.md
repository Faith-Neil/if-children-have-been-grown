为什么有这个文件：记录QA对APP-M2-T123（大纲排序、章节类型和增值理由）的独立复验与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行大纲树排序算法、章节类型、增值理由专属单测套件、前端全量单测套件、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 PRD v1.8 §5.7.2、§5.7.8 与设计规范 9.10 所规定的 5 类核心章节类型（专项/通用/系统生成/封面目录/不适用）、核心红线门禁（星号条款★与废标条款对应章节绝对禁止标记为“不适用”，前端下拉置灰禁用与 Tooltip 说明）、同级章节上移/下移排序算法与多层级编号自动归一化、增值理由快捷模板与 500 字上限约束、分册协同与数据权限只读态拦截，以及全链路零 storage/URL 残留硬断言。

# APP-M2-T123 大纲排序、章节类型和增值理由独立复测与 QA 签署

- 被验任务：[APP-M2-T123](../tasks/APP-M2.md#app-m2-t123) · 大纲排序、章节类型和增值理由
- 关联审查任务：REV-M0-T63
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T123 交付](../delivery/APP-M2-T123.md)、[代码解释](../code/APP-M2-T123.md)
- 依赖任务：[APP-M1-T15](../tasks/APP-M1.md#app-m1-t15)、[APP-M2-T116](../tasks/APP-M2.md#app-m2-t116)
- 被验核心文件：
  - `frontend/web/src/outline-tree.ts`
  - `frontend/web/src/ChapterTypeBadge.tsx`
  - `frontend/web/src/ValueAddedReasonModal.tsx`
  - `frontend/web/src/OutlineTreeView.tsx`
  - `tests/frontend/outline-tree.test.mjs`
  - `frontend/web/tests/outline-tree.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T123 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 章节类型元信息与 5 类模型规范 | 通过 | `outline-tree.ts` 与 `ChapterTypeBadge.tsx` 严格定义 5 类核心章节类型：`specialized` 专项方案（业务主蓝 #1e4db7）、`general` 通用方案、`system_generated` 系统生成（专属 AI 紫色 #722ed1）、`cover_and_catalog` 封面目录（中性灰）、`not_applicable` 不适用（橙棕色）；各徽标渲染与色彩隔离完全合规 |
| AC-02 【核心门禁红线】星号/废标条款绝对禁止标记不适用 | 通过 | `canMarkNotApplicable` 纯函数严格校验：关联星号条款(★)或废标条款的章节，一律返回 `allowed=false` 并给出精准合规理由；`OutlineTreeView.tsx` 在类型切换下拉选项中将“不适用”直接置灰禁用（`disabled: isNotApplicableDisabled`），悬停展示 Tooltip 明确说明禁止原因，从前端根源杜绝漏标风险 |
| AC-03 同级章节排序算法与多层级编号自动归一化 | 通过 | `reorderNodes` 算法实现同级节点上移与下移互换，并在首尾两端实施防越界边界保护；`normalizeChapterNumbers` 递归遍历树形结构，自动将章节编号归一化为标准的 `1, 1.1, 1.2, 2` 等级规范层级编码 |
| AC-04 增值理由快捷模板与 500 字上限约束 | 通过 | `ValueAddedReasonModal.tsx` 弹窗支持对专项方案等章节补充增值优势说明；内置常用预置模板（`VALUE_ADDED_PRESETS`）支持一键插入；严格限制 500 字输入上限并在超出时拦截提交 |
| AC-05 分册协同与数据权限只读态拦截 | 通过 | `OutlineTreeView.tsx` 深度引入 `useDataPermission({ volume })`：用户切换至非主管分册时，自动进入分册级只读模式，顶层展示带有锁定图标的警示横幅（`data-testid="readonly-notice-banner"`），禁用全部上移、下移排序按钮、类型切换下拉以及增值理由编辑操作 |
| AC-06 全链路零 storage 与零 URL 残留硬断言 | 通过 | 大纲树交互、章节排序与增值理由编辑全链路严禁向 `localStorage`、`sessionStorage` 写入敏感标书内容，URL 中不挂载敏感参数，保障纯净内存操作 |
| AC-07 生产构建打包与包体积门禁（<= 295 kB） | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 785ms，0 错误 0 告警）；首屏主包 `index-EIM2ccZO.js` 体积为 **294.86 kB**（Gzip 后 **93.91 kB**），零包体积膨胀，完全满足 **<= 295 kB** 预算红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 大纲树与章节类型专属单测套件 | `node --test tests/frontend/outline-tree.test.mjs frontend/web/tests/outline-tree.test.mjs` | **11 passed, 0 failed** (纯逻辑 7 项 + AST/契约测试 4 项) | 0.36s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **274 passed, 0 failed** (包含 11 项新增大纲树专属单测，100% 通过) | 2.42s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 785ms) | 0.79s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-EIM2ccZO.js` **294.86 kB**（gzip: 93.91 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **“星号与废标条款禁止不适用”的零死角门禁**：通过在纯逻辑层 `canMarkNotApplicable`、Select 下拉选项（`disabled: true`）以及提交校验 `validateChapterTypeChange` 设立三道关卡，确保任何试图将核心合规条款设为不适用的误操作均被彻底拦截。
2. **分册只读与团队分工的无缝融合**：技术分册负责人切换至商务分册时，大纲树自动自适应切换为只读态并提供明确横幅解释，既满足跨分册全局通览的需求，又坚守了分工负责人的写操作边界。
3. **极限首屏包体积控制**：新增大纲排序、增值理由弹窗与徽标组件后，前端首屏主包体积依然维持在 294.86 kB，完全符合架构 295 kB 门禁要求。

## 签署状态

APP-M2-T123 保持 **in-review**，**严禁标 done**。
