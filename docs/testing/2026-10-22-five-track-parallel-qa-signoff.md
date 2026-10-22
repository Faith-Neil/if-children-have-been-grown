# 为什么有这个文件：记录QA对五路并行大成果（APP-M2-T165/T167、APP-M2-T046/T047、APP-M2-T157/T026、APP-M2-T185、BE-M0-T19）的独立背靠背复测、全量回归与终验签署结论。

# 它解决什么问题：不轻信各端自报结果，严格履行 QA 裁判职责，独立运行前端 326 项全量单测、后端 59 项专属与核心回归测试、Vite 生产构建各分包体积检查、以及全库工程治理检查；深度审计五路核心安全门禁（.cite 证据胶囊悬浮与选区 Bubble 气泡、资料库引用可用性诊断与附件 SHA256 防篡改校验、审计日志中心存证不可篡改与租户停用二次确认、AI 建议原地回写六重防御门禁、项目表对齐 bid_project 增量加列与历史数据绝对保留）；出具明确的 PASS 终验签署结论，将各关联任务卡稳妥保持在 in-review，严禁私自标 done 或关闭 Issue。

# 五路并行大成果 QA 独立背靠背复测与终验签署报告

- 被验任务：
  - [APP-M2-T165](../tasks/APP-M2.md#app-m2-t165) & [APP-M2-T167](../tasks/APP-M2.md#app-m2-t167) · 正文证据胶囊 `.cite` 悬浮与选区划词 Action Bubble（前端专员1）
  - [APP-M2-T046](../tasks/APP-M2.md#app-m2-t046) & [APP-M2-T047](../tasks/APP-M2.md#app-m2-t047) · 企业资料库通用列表页与详情通用页附件槽位（前端专员2）
  - [APP-M2-T157](../tasks/APP-M2.md#app-m2-t157) & [APP-M2-T026](../tasks/APP-M2.md#app-m2-t026) · A-06 审计日志中心存证只读与 A-01 企业租户管理（前端专员3）
  - [APP-M2-T185](../tasks/APP-M2.md#app-m2-t185) · AI 助手采纳润色建议原地回写正文协议与六重防御门禁（AI 专员）
  - [BE-M0-T19](../tasks/BE-M0.md#be-m0-t19) · 项目表对齐 `bid_project` 数据字典、Alembic 0011 增量加列迁移与字段映射（后端专员）
- 关联 Issue：
  - [ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-018](../../issues/ISSUE-018.md)、[ISSUE-035](../../issues/ISSUE-035.md)、[ISSUE-037](../../issues/ISSUE-037.md)
- 关联交付文档：
  - [docs/delivery/APP-M2-T165.md](../delivery/APP-M2-T165.md)
  - [docs/delivery/APP-M2-T167.md](../delivery/APP-M2-T167.md)
  - [docs/delivery/APP-M2-T046.md](../delivery/APP-M2-T046.md)
  - [docs/delivery/APP-M2-T047.md](../delivery/APP-M2-T047.md)
  - [docs/delivery/APP-M2-T157.md](../delivery/APP-M2-T157.md)
  - [docs/delivery/APP-M2-T026.md](../delivery/APP-M2-T026.md)
  - [docs/delivery/APP-M2-T185.md](../delivery/APP-M2-T185.md)
  - [docs/delivery/BE-M0-T19.md](../delivery/BE-M0-T19.md)
- 关联代码解释文档：
  - [docs/code/APP-M2-T165.md](../code/APP-M2-T165.md)
  - [docs/code/APP-M2-T167.md](../code/APP-M2-T167.md)
  - [docs/code/APP-M2-T046.md](../code/APP-M2-T046.md)
  - [docs/code/APP-M2-T047.md](../code/APP-M2-T047.md)
  - [docs/code/APP-M2-T157.md](../code/APP-M2-T157.md)
  - [docs/code/APP-M2-T026.md](../code/APP-M2-T026.md)
  - [docs/code/APP-M2-T185.md](../code/APP-M2-T185.md)
  - [docs/code/BE-M0-T19.md](../code/BE-M0-T19.md)
- 复验环境：
  - OS: Windows (PowerShell)
  - Python: 3.12.9, pytest: 8.4.2
  - Node: 24.9.0, Vite: 8.3.4, TypeScript: 5.8.2
- 签署结论：**【PASS 终验签署通过】**。
- 纪律与规范：**全部被验任务卡保持 in-review，绝不私自标 done；关联 Issue 保持原状态**。

---

## 一、五路并行核心成果审计与门禁验证矩阵

| 序号 | 成果方向 | 核心需求与门禁维度 | 审计与实测结论 | 状态 |
|---|---|---|---|---|
| **AC-01** | **前端专员1** (T165/T167) | 正文证据胶囊 `.cite` 悬浮卡片展示 | 正则精准匹配 `[证:ID]` 与 `[片:ID]`；`CiteCapsule` 与 `Popover` 悬浮展示证据名称、编号、核验状态、有效期与摘录，点击联动在来源面板中高亮。 | **PASS** |
| **AC-02** | **前端专员1** (T165/T167) | 选区划词 Action Bubble 与右侧助手直达 | 选中文本即刻弹出 `SelectionBubble`，展示实时字数并提供 AI 润色与合规诊断一键直达，点击抗失焦保护并自动透传划选文本至右侧助手。 | **PASS** |
| **AC-03** | **前端专员2** (T046/T047) | 企业资料库通用列表与五大分类导航 | 支持资质、财务、人员、业绩、模板五大类筛选；状态推导（有效/待核验/已过期/已排除）精准；引用可用性深度诊断（缺协议/过期/历史参考拦截）。 | **PASS** |
| **AC-04** | **前端专员2** (T046/T047) | 资料详情通用页与附件槽位 SHA256 校验 | 详情抽屉展示结构化附件槽位，支持 SHA256 防篡改校验、原件安全预览与带安全告知的下载二次确认，个人证件 MaskedField 脱敏完备。 | **PASS** |
| **AC-05** | **前端专员3** (T157/T026) | A-06 审计日志中心存证只读合规保护 | 呈现安全审计时间线，敏感数据调阅理由强制校验 ≥5 字；密钥脱敏指纹展示；前端杜绝删除与篡改接口，确保只读存证可溯。 | **PASS** |
| **AC-06** | **前端专员3** (T157/T026) | A-01 企业租户管理与停用二次确认 | 支持公司租户信息维护、资料库/RAGFlow 配额监管与状态启停；停用操作严格实施输入租户全名匹配的二次确认校验（PRD §5.10.1 约束）。 | **PASS** |
| **AC-07** | **AI 专员** (APP-M2-T185) | AI 建议原地回写正文双重定位算法 | 落地 `POST /api/v1/projects/{project_id}/chapters/{chapter_id}/accept-ai-suggestion`，支持按段落编号（paragraph_id）或原文片段（original_text）双重定位原地替换正文。 | **PASS** |
| **AC-08** | **AI 专员** (APP-M2-T185) | 原地回写六重防御门禁与版本历史归档 | 严格校验排他编辑锁（未获锁 423 LOCK_LOST，他人持锁 423 LOCK_HELD）；防版本冲突（409 REVISION_CONFLICT）；原子递增 revision 并归档版本历史快照；敏感项目本地模型硬隔离（403）。 | **PASS** |
| **AC-09** | **后端专员** (BE-M0-T19) | 项目表对齐 `bid_project` 数据字典字段 | 扩充 tender_type、budget_amount_cents、deadline_at、security_level、industry、is_archived 与 A 组系统审计字段，保留 is_sensitive 别名向后兼容。 | **PASS** |
| **AC-10** | **后端专员** (BE-M0-T19) | Alembic 0011 增量加列迁移与历史保留 | 严格使用 `ALTER TABLE ADD COLUMN` 语法增量加列，绝对保留历史项目数据，提供完备 downgrade 回滚支持；`implemented_contract` 契约校验全绿。 | **PASS** |

---

## 二、独立复测实测数据与执行凭据

### 1. 后端专属与回归测试套件（59 passed, 0 failed）
执行命令：
```bash
pytest tests/backend/test_project_dictionary_alignment.py tests/backend/test_accept_ai_suggestion.py tests/backend/test_tender_document_retrieval.py tests/backend/test_chapter_edit_detail.py tests/backend/test_editor_ai_context.py tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py -v
```
实测输出统计：
```text
tests/backend/test_project_dictionary_alignment.py (5 passed)
  - 领域模型默认值与别名、数据库 18 元组快照与兼容保存
  - Alembic 0011 迁移结构与脚本有效性
  - v1 与旧版接口兼容、跨公司隔离与软删除过滤
tests/backend/test_accept_ai_suggestion.py (8 passed)
  - paragraph_id 精准段落替换与 original_text 纯文本匹配原地替换
  - 无锁/锁过期 423 LOCK_LOST / LOCK_HELD 门禁
  - OCC 409 REVISION_CONFLICT 冲突门禁
  - 敏感项目本地模型 403 强门禁、只读角色 403 拦截、跨租户 404 隔离
tests/backend/test_tender_document_retrieval.py (9 passed)
tests/backend/test_chapter_edit_detail.py (8 passed)
tests/backend/test_editor_ai_context.py (12 passed)
tests/backend/test_error_idempotency.py (12 passed)
tests/backend/test_operation_ids.py (5 passed)

============================= 59 passed in 18.78s =============================
```

### 2. 前端专属与全量单元测试（326 passed, 0 failed）
执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出统计：
```text
✔ cite-capsule.ts exports required parsing and metadata helpers (13.1681ms)
✔ CiteCapsule.tsx exports CiteCapsule and RichParagraphWithCites with contract testids (7.4187ms)
✔ SelectionBubble.tsx exports SelectionBubble with all action buttons and testids (1.9839ms)
✔ EditorPage.tsx mounts SelectionBubble, RichParagraphWithCites and editor-citation-bar (19.0411ms)
✔ APP-M2-T157: 敏感数据调阅理由合规门禁校验 (>= 5 字规则) (1.3221ms)
✔ APP-M2-T157: 操作类型元信息映射与事件分类准确性 (0.4657ms)
✔ APP-M2-T157: 模型密钥脱敏指纹格式化与明文防泄漏断言 (0.212ms)
✔ APP-M2-T157: 只读保护契约断言：严禁前端提供删除与篡改接口 (0.5568ms)
✔ APP-M2-T157: 审计日志多维检索过滤测试 (1.8814ms)
✔ APP-M2-T026: 企业合规参数基线校验与门禁拦截 (0.3762ms)
✔ APP-M2-T026: 权限感知判定：区分集团管理员、公司管理员、平台管理员与只读人员 (0.2443ms)
✔ APP-M2-T026: 停用公司租户二次确认输入校验 (PRD §5.10.1 约束) (0.1097ms)
✔ CITE_REGEX matches [证:ID] and [片:ID] accurately (0.8459ms)
✔ parseCitations splits pure text without markers into single text segment (0.1863ms)
✔ parseCitations handles mixed text and citations with metadata enrichment (0.1937ms)
✔ extractCitationIds extracts unique evidence and snippet IDs preserving order (0.6644ms)
✔ resolveCitationMeta supplies sensible defaults when not found (0.1601ms)
✔ formatCiteLabel formats evidence and snippet tags (0.0916ms)
✔ Selection bubble logic builds truncated polish & compliance prompts (0.1797ms)
✔ LIBRARY_CATEGORIES defines standard categories and supports label lookup (1.2557ms)
✔ deriveEvidenceStatus accurately computes status with expiration checks (1.3964ms)
✔ checkEvidenceUsability diagnoses invalid reasons for project citation (0.4148ms)
✔ filterEvidenceList filters by category, status, and multi-field keywords (0.3946ms)
✔ RBAC controls library management permissions (0.2599ms)
✔ RBAC controls sensitive field reveal whitelist and masking (0.2469ms)
✔ verifyAttachmentSecurity verifies SHA256 integrity and download audit trail (0.4728ms)
...
ℹ tests 326
ℹ suites 0
ℹ pass 326
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2718.1526
```

### 3. 前端生产打包构建与分包体积门禁
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3371 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.01 kB │ gzip:   0.58 kB
dist/assets/index-Dh3tIuXn.css                34.82 kB │ gzip:   7.63 kB
dist/assets/LibraryPages-BWTcMd_E.js          26.91 kB │ gzip:   9.55 kB
dist/assets/CompanyManagePage-Cb4I4sDN.js     27.46 kB │ gzip:  10.48 kB
dist/assets/EditorPage-BoSBsKwe.js           110.07 kB │ gzip:  34.97 kB
dist/assets/ProjectPages-DKlEOTNR.js         115.74 kB │ gzip:  34.82 kB
dist/assets/AuditLogPage-CJVqjPx2.js         131.88 kB │ gzip:  41.76 kB
dist/assets/AppShell-DLCtKpF1.js             215.27 kB │ gzip:  70.35 kB
dist/assets/index-CgRSHI1d.js                414.52 kB │ gzip: 128.49 kB
dist/assets/jsx-runtime-CG2hsDBP.js          428.80 kB │ gzip: 141.56 kB
✓ built in 793ms
```
- TypeScript 类型检查 0 错误；
- 主包 `index-CgRSHI1d.js` 为 **414.52 kB**（gzip 128.49 kB），保持健康体积；
- 独立按需分包体积优秀：`LibraryPages` 仅 26.91 kB、`CompanyManagePage` 仅 27.46 kB、`EditorPage` 优化降至 110.07 kB、`AuditLogPage` 仅 131.88 kB；
- 构建 0 告警，用时仅 **793ms**。

### 4. 全库工程治理与规范检查
执行命令：
```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
实测输出：
```text
治理检查通过：467 份 Markdown、397 项任务、37 项 Issue。
ℹ tests 12
ℹ suites 0
ℹ pass 12
ℹ fail 0
ℹ duration_ms 444.1952
```

---

## 三、签署结论与工作规范守则

根据质量管理裁判原则：
1. **APP-M2-T165**、**APP-M2-T167**、**APP-M2-T046**、**APP-M2-T047**、**APP-M2-T157**、**APP-M2-T026**、**APP-M2-T185**、**BE-M0-T19** 八项任务卡在本次五路并行研发成果中全面达标，出具 **【PASS 终验签署通过】** 结论。
2. **严守工作流纪律**：QA 绝不私自将任务看板标为 done，绝不私自关闭业务 Issue；上述任务卡稳妥保持 **in-review** 状态，由主 Agent / 项目经理进行后续里程碑确认。
