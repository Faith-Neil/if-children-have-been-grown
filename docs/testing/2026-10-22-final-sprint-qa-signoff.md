# 为什么有这个文件：记录QA对四大终局收尾成果（APP-M2-T195/T196、APP-M2-T020、BE-CHECKS-EXPORT-ALIGN、AI-COMPLIANCE-CROSS-CHECK）的独立背靠背复测、全量回归与终验签署结论。

# 它解决什么问题：不轻信各端自报结果，严格履行 QA 裁判职责，独立运行前端 344 项全量单测、后端 43 项专属与核心回归测试、Vite 生产构建包体积与分包检查、以及全库工程治理检查；深度审计核心质量门禁（检查 blocker 阻断严重度判定、正式递交版 400 CHECK_BLOCKER_EXISTS 强拦截门禁、内部评审稿放行与合规标记、Word 默认版式元数据与 64 位 SHA-256 版式指纹注入、SSE 3 阶梯指数退避重连与轮询降级、以及 AI 正文与 RAGFlow 交叉核验及负偏离废标阻断）；出具明确的 PASS 终验签署结论，将各关联任务卡稳妥保持在 in-review，严禁私自标 done 或关闭 Issue。

# 四大终局收尾成果 QA 独立背靠背复测与终验签署报告

- 被验任务：
  - [APP-M2-T195](../tasks/APP-M2.md#app-m2-t195) & [APP-M2-T196](../tasks/APP-M2.md#app-m2-t196) · 合规检查红线门禁、整本递交版/内部稿双模导出与版式指纹（前端专员1）
  - [APP-M2-T020](../tasks/APP-M2.md#app-m2-t020) · JobProgress：SSE 订阅流、断线 3 阶梯重试与轮询回退（前端专员2）
  - `BE-CHECKS-EXPORT-ALIGN` · 检查 blocker 判定、整本导出 400 强拦截、Word 默认版式元数据与 64 位 SHA256 指纹（后端专员）
  - `AI-COMPLIANCE-CROSS-CHECK` · 正文引用与 RAGFlow 片段交叉比对、置信度推导与负偏离废标阻断（AI 专员）
- 关联 Issue：
  - [ISSUE-005](../../issues/ISSUE-005.md)、[ISSUE-006](../../issues/ISSUE-006.md)、[ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-027](../../issues/ISSUE-027.md)、[ISSUE-037](../../issues/ISSUE-037.md)
- 关联交付文档：
  - [docs/delivery/APP-M2-T195.md](../delivery/APP-M2-T195.md)
  - [docs/delivery/APP-M2-T196.md](../delivery/APP-M2-T196.md)
  - [docs/delivery/APP-M2-T020.md](../delivery/APP-M2-T020.md)
  - [docs/delivery/BE-CHECKS-EXPORT-ALIGN.md](../delivery/BE-CHECKS-EXPORT-ALIGN.md)
  - [docs/delivery/AI-COMPLIANCE-CROSS-CHECK.md](../delivery/AI-COMPLIANCE-CROSS-CHECK.md)
- 关联代码解释文档：
  - [docs/code/APP-M2-T195.md](../code/APP-M2-T195.md)
  - [docs/code/APP-M2-T196.md](../code/APP-M2-T196.md)
  - [docs/code/APP-M2-T020.md](../code/APP-M2-T020.md)
  - [docs/code/BE-CHECKS-EXPORT-ALIGN.md](../code/BE-CHECKS-EXPORT-ALIGN.md)
  - [docs/code/AI-COMPLIANCE-CROSS-CHECK.md](../code/AI-COMPLIANCE-CROSS-CHECK.md)
- 复验环境：
  - OS: Windows (PowerShell)
  - Python: 3.12.9, pytest: 8.4.2
  - Node: 24.9.0, Vite: 8.3.4, TypeScript: 5.8.2
- 签署结论：**【PASS 终验签署通过】**。
- 纪律与规范：**全部被验任务卡保持 in-review，绝不私自标 done；关联 Issue 保持原状态**。

---

## 一、四大终局成果审计与核心门禁验证矩阵

| 序号 | 成果方向 | 核心需求与门禁维度 | 审计与实测结论 | 状态 |
|---|---|---|---|---|
| **AC-01** | **前端专员1** (T195/T196) | 合规检查红线门禁与 Blocker 聚合呈现 | `ChecksPage` 挂载 `blocker-alert-banner` 阻断红色告警横幅与 `blocker-chapters-list` 受阻章节列表，精准计算并展示未通过星号与废标项。 | **PASS** |
| **AC-02** | **前端专员1** (T195/T196) | 正式递交版强阻断与内部评审稿导出放行 | `ExportPage` 强校验 Blocker 清零前提项，存在 Blocker 时 `export-generate-btn` 强制置灰禁用并渲染 `export-blocker-warning` 阻断告警；内部稿允许导出并带风险预警。 | **PASS** |
| **AC-03** | **前端专员1** (T195/T196) | 导出历史表格、SHA-256 版式指纹展示 | 导出记录表格呈现导出类型 Tag、快照 ID、文件大小与 64 位 SHA-256 格式化指纹，提供安全下载操作。 | **PASS** |
| **AC-04** | **前端专员2** (APP-M2-T020) | JobProgress SSE 实时事件流订阅 | 封装 `JobStreamSubscriptionManager`，成功建立 `/api/v1/jobs/{id}/events` 连接，实时推流并更新任务进度与步骤状态。 | **PASS** |
| **AC-05** | **前端专员2** (APP-M2-T020) | 断线 3 阶梯指数退避与轮询平滑降级 | 断线时按 1s -> 2s -> 4s 指数退避重试；3 次失败后平滑降级为 2 秒定时轮询，展示黄色警告 Tag；终态自动销毁连接防泄漏。 | **PASS** |
| **AC-06** | **后端专员** (BE-CHECKS-EXPORT-ALIGN) | 废标红线与星号条款 blocker 严重度判定 | 检查逻辑识别废标条款（`disqualification`）与星号条款（`star`），未响应或缺资质证据时赋予最高严重度 `severity="blocker"`。 | **PASS** |
| **AC-07** | **后端专员** (BE-CHECKS-EXPORT-ALIGN) | 整本递交版导出 400 强拦截与 Word 元数据 | `POST /api/v1/projects/{project_id}/exports` 对含 blocker 的递交版抛出 `400 CHECK_BLOCKER_EXISTS`；导出快照注入 64 位 SHA-256 版式指纹与 Word 默认边距/字体元数据。 | **PASS** |
| **AC-08** | **AI 专员** (AI-COMPLIANCE-CROSS-CHECK) | 正文声明与 RAGFlow 交叉核验及负偏离阻断 | 自动提取正文 SLA、资质、人员声明与 `.cite` 引用；对标招标文件强制条款识别负偏离并阻断（`risk="block"`, 置信度 0.0）；计算证据置信度得分（0.0~1.0）。 | **PASS** |

---

## 二、独立复测实测数据与执行凭据

### 1. 后端专属单测与回归测试套件（43 passed, 0 failed）
执行命令：
```bash
pytest tests/backend/test_checks_export_blocker_gate.py tests/backend/test_ai_compliance_cross_check.py tests/backend/test_accept_ai_suggestion.py tests/backend/test_project_dictionary_alignment.py tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py -v
```
实测输出统计：
```text
tests/backend/test_checks_export_blocker_gate.py (4 passed)
  - 废标红线与星号条款赋予 blocker 严重度
  - 正式递交版导出遇 blocker 拦截 400 CHECK_BLOCKER_EXISTS
  - 内部评审稿导出放行并标记 blocker 与合规提醒
  - 导出快照注入 64 位 SHA-256 版式指纹与 Word 默认版式元数据
tests/backend/test_ai_compliance_cross_check.py (9 passed)
  - 正文声明与 .cite 交叉核验高置信度与证据充分通过
  - 一般性描述证据不足置信度降级
  - 负偏离条款强阻断 (risk="block", confidence=0.0)
  - 失效证据与未支持声明拦截
  - 敏感项目本地模型 403 强门禁、多租户权限隔离与 HTTP 端点测试
tests/backend/test_accept_ai_suggestion.py (8 passed)
tests/backend/test_project_dictionary_alignment.py (5 passed)
tests/backend/test_error_idempotency.py (12 passed)
tests/backend/test_operation_ids.py (5 passed)

============================= 43 passed in 13.41s =============================
```

### 2. 前端专属与全量单元测试（344 passed, 0 failed）
执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出统计：
```text
✔ export-checks-core.ts exports all required blocker and export helpers (18.9637ms)
✔ ProjectPages.tsx ChecksPage integrates blocker alert banner and chapters list (33.5169ms)
✔ ProjectPages.tsx ExportPage integrates blocker redline gate, options, and history table (19.9279ms)
✔ isBlocker accurately identifies blocker severity levels (0.7053ms)
✔ deriveBlockerSummary handles empty or clean checks with 0 blockers (0.2946ms)
✔ deriveBlockerSummary groups blocker issues by chapter and resolves chapter titles (0.7919ms)
✔ canExportSubmission strictly enforces redline blocker gate (0.1766ms)
✔ formatFileSize formats byte sizes with readable units and deterministic fallback (0.329ms)
✔ formatSha256Fingerprint formats clean sha256 with full & short display (0.2428ms)
✔ getExportKindMeta and getExportVolumeLabel return standard ICG labels (0.1593ms)
✔ 1. SSE 文本与多行消息解析 (parseSseLine & parseSseMessage) (1.4848ms)
✔ 2. 指数退避延迟算法计算 (calculateBackoffDelay) (0.504ms)
✔ 3. 任务终态判定集合 (isJobTerminalStatus & TERMINAL_JOB_STATUSES) (0.1645ms)
✔ 4. SSE 模拟订阅与正常进度推送更新 (25.8816ms)
✔ 5. 断线 3 次阶梯指数退避重连与重试计数 (108.0578ms)
✔ 6. 超过 3 次重试后平滑回退至定时轮询模式 (60.8071ms)
✔ 7. 任务进入终态 (completed / failed / cancelled) 自动关闭连接与定时器 (15.3861ms)
...
ℹ tests 344
ℹ suites 0
ℹ pass 344
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3435.4808
```

### 3. 前端生产打包构建与包体积门禁
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3372 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.01 kB │ gzip:   0.58 kB
dist/assets/index-Dh3tIuXn.css                34.82 kB │ gzip:   7.63 kB
dist/assets/LibraryPages-Ce05difw.js          26.91 kB │ gzip:   9.55 kB
dist/assets/CompanyManagePage-DYLc1Jrq.js     27.50 kB │ gzip:  10.50 kB
dist/assets/EditorPage-BhceU-HC.js           110.11 kB │ gzip:  35.00 kB
dist/assets/ProjectPages-D0-v2_AN.js         123.05 kB │ gzip:  37.59 kB
dist/assets/AuditLogPage-BdYHxNEu.js         131.88 kB │ gzip:  41.76 kB
dist/assets/AppShell-CPhzksUy.js             215.27 kB │ gzip:  70.35 kB
dist/assets/index-D4TsQQad.js                414.56 kB │ gzip: 128.50 kB
dist/assets/jsx-runtime-CG2hsDBP.js          428.80 kB │ gzip: 141.56 kB
✓ built in 960ms
```
- TypeScript 类型检查 0 错误；
- 主包 `index-D4TsQQad.js` 为 **414.56 kB**（gzip 128.50 kB），远离 500 kB 告警线；
- `ProjectPages-D0-v2_AN.js`（含 ChecksPage 与 ExportPage）仅 **123.05 kB**（gzip 37.59 kB）；
- `EditorPage-BhceU-HC.js` 仅 **110.11 kB**（gzip 35.00 kB）；
- 构建用时仅 **960ms**，全流程 0 告警通过。

### 4. 全库工程治理与规范检查
执行命令：
```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
实测输出：
```text
治理检查通过：478 份 Markdown、399 项任务、37 项 Issue。
ℹ tests 12
ℹ suites 0
ℹ pass 12
ℹ fail 0
ℹ duration_ms 409.5918
```

---

## 三、签署结论与工作规范守则

根据质量管理裁判原则：
1. **APP-M2-T195**、**APP-M2-T196**、**APP-M2-T020**、**BE-CHECKS-EXPORT-ALIGN**、**AI-COMPLIANCE-CROSS-CHECK** 各项终局核心任务在本次独立复测中全方位达标，出具 **【PASS 终验签署通过】** 结论。
2. **严守工作流纪律**：QA 绝不私自将任务看板标为 done，绝不私自关闭业务 Issue；上述任务卡稳妥保持 **in-review** 状态，由主 Agent / 项目经理进行最终全量归档确认。
