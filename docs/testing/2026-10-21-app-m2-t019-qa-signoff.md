为什么有这个文件：记录QA对APP-M2-T019（JobProgress：步骤、子进度、AI 紫进度条）的独立复验与签署结论。

它解决什么问题：不轻信前端自报结果，亲手执行长任务进度与色彩隔离专属单测套件、前端全量单测套件、生产构建打包与包体积门禁审计（<= 295 kB），针对性核查 PRD v1.8 §5.12.4、§5.7.6 与设计规范 9.10 所规定的长任务 5 类核心状态机（pending/running/completed/failed/cancelled）、总进度条与子步骤明细 Timeline/List 展开展示、AI 专属紫色进度条（#722ed1）与非 AI 业务蓝色进度条（#1e4db7）的严格色彩隔离红线、失败容错与 traceId 复制交互，以及全链路零 storage/URL 残留硬断言。

# APP-M2-T019 JobProgress：步骤、子进度、AI 紫进度条独立复测与 QA 签署

- 被验任务：[APP-M2-T019](../tasks/APP-M2.md#app-m2-t019) · JobProgress：步骤、子进度、AI 紫进度条
- 关联审查任务：REV-M0-T62
- 关联 Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 关联交付：[APP-M2-T019 交付](../delivery/APP-M2-T019.md)、[代码解释](../code/APP-M2-T019.md)
- 依赖任务：[APP-M2-T014](../tasks/APP-M2.md#app-m2-t014)
- 被验核心文件：
  - `frontend/web/src/status/job-progress.ts`
  - `frontend/web/src/status/JobProgress.tsx`
  - `frontend/web/src/shared/styles.css`
  - `tests/frontend/job-progress.test.mjs`
  - `frontend/web/tests/job-progress.test.mjs`
- 复验环境：Windows, Node v24.18.0, pnpm v11.20.0
- 结论：**通过 (PASS)**。**APP-M2-T019 保持 in-review，严禁标 done；关联 ISSUE-007 保持原状态**。

## 验收对照

| 检查项 | 结果 | 证据与详细说明 |
|---|---|---|
| AC-01 长任务核心状态机与元信息推导 | 通过 | `job-progress.ts` 严格规范 5 类任务状态（`pending`、`running`、`completed`、`failed`、`cancelled`）；`resolveJobStatusMeta` 派生出规范的状态徽标、中文状态标签与色彩，当任务已完成时强制将百分比进度置为 100% |
| AC-02 AI 紫色与业务蓝色进度条色彩严格隔离 | 通过 | `isAiJob` 准确识别 `generate_chapter`、`evidence_retrieval` 等 13 类内置 AI 任务与前缀扩展；`resolveProgressStrokeColor` 实施色彩红线隔离：AI 任务运行态严格采用专属紫色（`#722ed1`），非 AI 业务任务严格采用系统业务蓝（`#1e4db7`），非 AI 业务严禁呈现紫色 |
| AC-03 多子步骤明细列表与加权进度派生 | 通过 | `deriveJobProgress` 支持显式进度与子步骤加权平均双模式推导；`JobProgress.tsx` 支持以折叠面板展开子步骤明细列表，清晰呈现各子步骤图标、名称、耗时与执行进度 |
| AC-04 耗时友好格式化与时间展示 | 通过 | `formatDuration` 支持毫秒精确转换秒（`X.Xs`）与分秒（`Xm Ys`），满足长耗时等待的用户心理预期 |
| AC-05 失败容错、重试与 Trace ID 交互契约 | 通过 | 任务失败（`status="failed"`）时，组件自动展示醒目的错误容器（`data-testid="job-error-section"`），完整呈现 `errorCode`、`errorMessage` 与 `errorSummary`，提供 `data-testid="job-copy-trace-id"` 一键复制 Trace ID 并调用 `copyText`，支持从失败步骤重试与取消 |
| AC-06 零 storage 与零 URL 残留硬安全断言 | 通过 | 进度计算与组件渲染全链路严禁向 `localStorage`、`sessionStorage` 写入任务敏感明文，URL 中不附加任务敏感详情，杜绝安全旁路泄密 |
| AC-07 生产构建打包与包体积门禁（<= 295 kB） | 通过 | `pnpm --dir frontend/web build` 顺利通过（`tsc -b && vite build` 耗时 737ms，0 错误 0 告警）；首屏主包 `index-EIM2ccZO.js` 体积为 **294.86 kB**（Gzip 后 **93.91 kB**），零包体积膨胀，完全满足 **<= 295 kB** 预算红线 |

## 独立复测试验数据

| 套件 | 执行命令 | 实测结果 | 耗时 |
|---|---|---|---|
| 长任务进度专属单测套件 | `node --test tests/frontend/job-progress.test.mjs frontend/web/tests/job-progress.test.mjs` | **10 passed, 0 failed** (纯逻辑 6 项 + AST/契约测试 4 项) | 0.32s |
| 前端全量单测套件 | `node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs` | **263 passed, 0 failed** (包含 10 项新增专属单测，100% 通过) | 2.08s |
| 前端生产环境构建 | `pnpm --dir frontend/web build` | **构建成功** (`tsc -b && vite build` 耗时 737ms) | 0.74s |
| 首屏主包体积审计 | 检查 `frontend/web/dist/assets/index-*.js` | `index-EIM2ccZO.js` **294.86 kB**（gzip: 93.91 kB），**完全达标 <= 295 kB 门禁** | — |
| 项目工程治理一致性核查 | `node scripts/check-project-governance.cjs` | **0 errors** (治理检查通过) | 0.85s |

## 观察项与边界提示

1. **AI 专属色彩红线隔离的品牌统一性**：通过将 `#722ed1`（紫色）限定于 AI 智能生成与检索任务，而非 AI 业务任务（如 Word/PDF 导出、格式校验）统一使用 `#1e4db7`（蓝色），给用户建立了强烈的“AI 正在推理”与“常规业务正在处理”的心智区分，符合专业企业级软件设计规范。
2. **长任务子步骤与 Trace ID 联动**：在大模型调用超时或外部服务熔断时，`JobProgress` 能够定位到具体的失败子步骤并提供一键复制 Trace ID，极大减轻了业务人员与运维/开发团队的排障沟通成本。
3. **零额外依赖与极限包体积控制**：在引入 Timeline、Progress、Tooltip 等复杂长任务可视化功能的情况下，首屏主包依然精准停留在 294.86 kB，未产生任何冗余膨胀。

## 签署状态

APP-M2-T019 保持 **in-review**，**严禁标 done**。
