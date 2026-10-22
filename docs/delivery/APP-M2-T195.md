# APP-M2-T195：合规检查红线门禁与整本递交版导出交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T195 |
| 代码解释 | [docs/code/APP-M2-T195.md](../code/APP-M2-T195.md) |
| 验收 | 10 项专属自动化单测全绿；344 项前端全量单测全绿；生产构建 858ms 顺利通过；工程治理检查通过 |
| 项目进度 | 前端 M2 推进，APP-M2-T195 提交 in-review，关联 ISSUE-007、ISSUE-005 保持开启，绝不私自标 done |
<!-- task-delivery:end -->

## 1. 任务背景与交付目标

依据 PRD v1.8 §5.11、§5.9、R41 与原交接文档规范：
- **目标**：实现合规检查中心阻断性缺陷（Blocker）醒目展示，并将 Blocker 清零作为整本递交版导出的硬性门禁。
- **核心要求**：
  1. **检查中心红线横幅（APP-M2-T195）**：存在 `blocker`（或 `fatal`/`critical`/`error`）缺陷时，展示红色高亮告警横幅（`data-testid="blocker-alert-banner"`）并列出受阻章节及位置（`data-testid="blocker-chapters-list"`）；
  2. **导出中心红线硬门禁（APP-M2-T195）**：在导出前提中增加“合规红线门禁：无阻断性缺陷（Blocker 清零）”状态项；存在 blocker 时展示阻断警示（`data-testid="export-blocker-warning"`），并将“生成正式递交版”按钮（`data-testid="export-generate-btn"`）强置灰禁用，Tooltip 明确提示拦截原因；
  3. **整本递交版与内部稿导出（APP-M2-T196）**：提供分册范围选择（`data-testid="export-volume-radio"`，技术分册、商务分册、两册合订）、导出类型选择（`data-testid="export-kind-radio"`，内部评审稿与正式递交版双轨制）；
  4. **导出历史与版式指纹（APP-M2-T196）**：导出历史表格（`data-testid="export-history-table"`）展示快照编号（`data-testid="export-history-id"`）、生成时间、操作人、分册范围、类型 Tag、文件大小、SHA256 版式指纹（`data-testid="export-fingerprint"`）及分册下载按钮（`data-testid="export-download-btn"`）。

---

## 2. 变更文件与实现清单

1. **`frontend/web/src/types.ts`（修改）**：
   - 扩充 `Export` 类型定义，包含 `volume`（分册范围）、`created_by` / `operator_name`（操作人）、`size_bytes` / `file_size`（文件大小）、`sha256` / `fingerprint`（版式指纹）。
2. **`frontend/web/src/export-checks-core.ts`（新增）**：
   - 实现了 `isBlocker`：精准识别并归一化红线阻断级别；
   - 实现了 `deriveBlockerSummary`：从检查结果中提取所有 blocker 缺陷并按章节分组聚合；
   - 实现了 `canExportSubmission`：综合校验角色权限、正文完整度、有效检查与 blocker 红线，产出放行裁决；
   - 实现了 `formatFileSize`：人性化文件大小展示与伪随机模拟；
   - 实现了 `formatSha256Fingerprint`：支持 short 与 full 版式指纹规范展示；
   - 实现了 `getExportKindMeta` 与 `getExportVolumeLabel`：标准 ICG 标签映射。
3. **`frontend/web/src/ProjectPages.tsx`（修改）**：
   - ChecksPage：挂载 `blockerSummary.hasBlockers` 警示横幅与章节列表；
   - ExportPage：集成红线门禁前提项、分册范围单选、导出类型单选、阻断告警、强拦截生成按钮与完整导出历史表格。
4. **`tests/frontend/checks-export.test.mjs`（新增）**：
   - 编写 10 项纯逻辑单元测试，覆盖红线识别、空数据处理、章节聚合、递交版门禁判断、文件大小与 SHA256 格式化。
5. **`frontend/web/tests/checks-export.test.mjs`（新增）**：
   - 编写 AST 契约测试，断言 `export-checks-core.ts` 导出符号以及 `ProjectPages.tsx` 中各测试属性节点。

---

## 3. 验收证据与测试输出

### 3.1 专属自动化单测（纯逻辑 + 契约 AST）
```
node --test tests/frontend/checks-export.test.mjs frontend/web/tests/checks-export.test.mjs
✔ export-checks-core.ts exports all required blocker and export helpers (17.8738ms)
✔ ProjectPages.tsx ChecksPage integrates blocker alert banner and chapters list (27.7747ms)
✔ ProjectPages.tsx ExportPage integrates blocker redline gate, options, and history table (17.4329ms)
✔ isBlocker accurately identifies blocker severity levels (0.6886ms)
✔ deriveBlockerSummary handles empty or clean checks with 0 blockers (0.2398ms)
✔ deriveBlockerSummary groups blocker issues by chapter and resolves chapter titles (0.7621ms)
✔ canExportSubmission strictly enforces redline blocker gate (0.1686ms)
✔ formatFileSize formats byte sizes with readable units and deterministic fallback (0.1836ms)
✔ formatSha256Fingerprint formats clean sha256 with full & short display (0.1865ms)
✔ getExportKindMeta and getExportVolumeLabel return standard ICG labels (0.1331ms)
ℹ tests 10
ℹ suites 0
ℹ pass 10
ℹ fail 0
```

### 3.2 全局前端单测全量回归
```
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
ℹ tests 344
ℹ suites 0
ℹ pass 344
ℹ fail 0
ℹ duration_ms 3346.8845
```

### 3.3 生产构建验证与分包体积
```
pnpm --dir frontend/web build
$ tsc -b && vite build
dist/assets/ProjectPages-D0-v2_AN.js  123.05 kB │ gzip: 37.59 kB
dist/assets/StopOutlined-ClC3A2Ig.js    0.65 kB │ gzip:  0.44 kB
✓ built in 858ms
```
无 TypeScript 报错，无体积预警，按需分包正常。

---

## 4. 边界与红线遵从说明

- **红线硬门禁**：正式递交版严格受控，任何阻断缺陷存在时杜绝放行；
- **状态治理**：绝不私自把任务看板标为 `done`，更新为 `in-review`，关联 Issue 保持开启，等待 QA 验收签署。
