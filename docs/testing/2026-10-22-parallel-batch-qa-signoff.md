# 为什么有这个文件：记录QA对四路并行成果（APP-M2-T162、APP-M2-T094/T095、BE-M0-T09/T17、APP-M2-T184）的独立背靠背复测、全量回归与终验签署结论。

# 它解决什么问题：不轻信各端自报结果，严格履行 QA 裁判职责，独立运行前端 300 项全量单测、后端 58 项专属与核心回归测试、Vite 生产构建包体积检查、以及全库工程治理检查；深度审计四大核心安全门禁（OCC 409 乐观锁冲突识别与合并保护、标的金额脱敏掩码与 ≤3 天倒计时标红预警、旧接口统一 143 错误码/幂等重放与 Alembic 0010 历史锁保留、以及招标文件切片禁止插入正文 can_insert=False 强安全门禁）；出具明确的 PASS 终验签署结论，将各关联任务卡稳妥保持在 in-review，严禁私自标 done 或关闭 Issue。

# 四路并行成果独立背靠背复测与 QA 终验签署报告

- 被验任务：
  - [APP-M2-T162](../tasks/APP-M2.md#app-m2-t162) · 编辑台段落保存、实时字数统计与 OCC 409 冲突合并
  - [APP-M2-T094](../tasks/APP-M2.md#app-m2-t094) · ProjectHeader 摘要条与页签（标的金额脱敏、倒计时标红、八角色页签隔离）
  - [APP-M2-T095](../tasks/APP-M2.md#app-m2-t095) · 项目列表与多维复合筛选（状态、涉密、分册多维筛选、元数据抽屉）
  - [BE-M0-T09](../tasks/BE-M0.md#be-m0-t09) · 旧 /api 统一 143 错误体与幂等规范（V1Error、Idempotency-Key 24h 重放、E2E-D5 /API 404）
  - [BE-M0-T17](../tasks/BE-M0.md#be-m0-t17) · chapter_lease 对齐字典 edit_lock（取得/心跳/接管/释放审计列、保留历史锁行、Alembic 0010）
  - [APP-M2-T184](../tasks/APP-M2.md#app-m2-t184) · 本项目招标文件切片轻量索引检索与结构化证据展示（E08 开关、can_insert=False 门禁、区间合并安全高亮、章节 Prompt 上下文一键注入）
- 关联 Issue：
  - [ISSUE-007](../../issues/ISSUE-007.md)、[ISSUE-021](../../issues/ISSUE-021.md)、[ISSUE-032](../../issues/ISSUE-032.md)、[ISSUE-037](../../issues/ISSUE-037.md)
- 关联交付文档：
  - [docs/delivery/APP-M2-T162.md](../delivery/APP-M2-T162.md)
  - [docs/delivery/APP-M2-T094.md](../delivery/APP-M2-T094.md)
  - [docs/delivery/BE-M0-T09.md](../delivery/BE-M0-T09.md)
  - [docs/delivery/BE-M0-T17.md](../delivery/BE-M0-T17.md)
  - [docs/delivery/APP-M2-T184.md](../delivery/APP-M2-T184.md)
- 关联代码解释文档：
  - [docs/code/APP-M2-T162.md](../code/APP-M2-T162.md)
  - [docs/code/APP-M2-T094.md](../code/APP-M2-T094.md)
  - [docs/code/BE-M0-T09.md](../code/BE-M0-T09.md)
  - [docs/code/BE-M0-T17.md](../code/BE-M0-T17.md)
  - [docs/code/APP-M2-T184.md](../code/APP-M2-T184.md)
- 复验环境：
  - OS: Windows (PowerShell)
  - Python: 3.12.9, pytest: 8.4.2
  - Node: 24.9.0, Vite: 8.3.4, TypeScript: 5.8.2
- 签署结论：**【PASS 终验签署通过】**。
- 纪律与规范：**全部被验任务卡保持 in-review，绝不私自标 done；关联 Issue 保持原状态**。

---

## 一、四路并行核心成果审计与门禁验证矩阵

| 序号 | 成果方向 | 核心需求与门禁维度 | 审计与实测结论 | 状态 |
|---|---|---|---|---|
| **AC-01** | **APP-M2-T162** | 实时字数统计与目标符合诊断 | `calculateWordCount` 准确结合 `target_length` 输出字符数、进度比与偏离度诊断（偏少/符合预期/超出上限），`data-testid="editor-word-count"` 渲染正常。 | **PASS** |
| **AC-02** | **APP-M2-T162** | 脏状态检测与未持锁纯文本守卫 | 基线比对准确识别未保存修改并高亮保存按钮；未获编辑锁时不显示丑陋 disabled textarea，渲染优雅纯文本与获锁指引。 | **PASS** |
| **AC-03** | **APP-M2-T162** | OCC 409 乐观锁冲突识别与双栏合并 | 保存遭遇 409 时正确触发冲突弹窗，提供本地与远程双栏正文比对，支持覆盖保存或放弃本地采用最新。 | **PASS** |
| **AC-04** | **APP-M2-T094** | 标的金额 MaskedField 掩码与倒计时标红 | 标的金额默认掩码，项目负责人调阅须填写 ≥5 字理由，只读成员禁用并 Tooltip 提示；倒计时 ≤3 天橙色/红色高亮标红预警，过期展示“已截止”。 | **PASS** |
| **AC-05** | **APP-M2-T094** | 八角色权限感知与涉密横幅 | `viewer`/`auditor`/`readonly` 成员自动移除 settings 页签入口；涉密项目顶部渲染专用保密 Alert 横幅，列表中带有保密 Tag。 | **PASS** |
| **AC-06** | **APP-M2-T095** | 项目列表复合筛选与元数据抽屉 | 支持状态（筹备/编写/审核/完成）、涉密属性、分册状态等多维筛选与统计卡片；元数据 `<Drawer>` 完整回显项目属性与分册概览。 | **PASS** |
| **AC-07** | **BE-M0-T09** | 旧 /api 统一 143 错误体与幂等重放 | 全量路由统一返回 `{code, message, details, traceId}` 与 `X-Request-ID`；旧变动端点挂载 `Idempotency-Key` 支持 24h 重放与冲突校验；SPA 兜底路由大小写不敏感判断彻底修复 E2E-D5。 | **PASS** |
| **AC-08** | **BE-M0-T17** | chapter_lease 字典对齐与历史保留 | 租约实体扩充取得/心跳/接管/释放审计列与租户隔离；Alembic 0010 增量迁移严格采用 `ADD COLUMN`，杜绝历史锁截断删除；保留客户端 token 鉴权防跨 Tab 覆盖。 | **PASS** |
| **AC-09** | **APP-M2-T184** | 招标文件切片索引与 can_insert=False 门禁 | 自动提取页码、条款编号与类型；关键词区间合并安全高亮杜绝 `<mark>` 嵌套与 XSS；证据卡 `can_insert=False` 强阻断正文插入；支持一键注入章节 Prompt 上下文与指纹更新；E08 特性开关可控。 | **PASS** |

---

## 二、独立复测实测数据与执行凭证

### 1. 后端专属与核心回归测试（58 passed, 0 failed）
执行命令：
```bash
pytest tests/backend/test_error_idempotency.py tests/backend/test_operation_ids.py tests/backend/test_tender_document_retrieval.py tests/backend/test_chapter_edit_detail.py tests/backend/test_editor_ai_context.py tests/backend/test_v1_lease.py tests/backend/test_lease_review.py -v
```
实测输出截断：
```text
tests/backend/test_error_idempotency.py (12 passed)
  - 143 冻结错误码无漂移、统一错误体结构与重试标记
  - 大小写不敏感 SPA 兜底路由 /API 返回 JSON 404（E2E-D5 修复）
  - 旧变动端点 Idempotency-Key 24小时重放与冲突保护
  - chapter_lease 租约实体与数据库快照审计列持久化
tests/backend/test_operation_ids.py (5 passed)
  - operationId 驼峰规范、全局唯一性与 spec demo-v1.json 严格对齐
tests/backend/test_tender_document_retrieval.py (9 passed)
  - 条款属性提取、分词与区间合并高亮防嵌套、E08 开关控制
  - 证据卡 can_insert=False 强门禁、章节 Prompt 上下文注入与清除
  - 跨项目租户隔离与只读角色权限门禁
tests/backend/test_chapter_edit_detail.py (8 passed)
  - 章节详情读取、段落与引用匹配、持锁状态感知
tests/backend/test_editor_ai_context.py (12 passed)
  - 划词所在段落精准匹配、polish Diff 润色建议、无锁 copy_only 强守卫
tests/backend/test_v1_lease.py (4 passed)
  - v1 租约端点规范导出与权限隔离
tests/backend/test_lease_review.py (8 passed)
  - 租约过期接管、续期并发一致性与回滚保证

====================== 58 passed, 23 warnings in 14.63s =======================
```

### 2. 前端专属与全量单元测试（300 passed, 0 failed）
执行命令：
```bash
node --test tests/frontend/*.test.mjs frontend/web/tests/*.test.mjs
```
实测输出统计：
```text
✔ calculateWordCount: 未设目标或非法目标字数 (0.8755ms)
✔ calculateWordCount: 字数偏少 (<80% 目标) (0.1744ms)
✔ calculateWordCount: 字数符合预期 (80% ~ 120% 目标) (0.1779ms)
✔ calculateWordCount: 字数超出上限 (>120% 目标) (0.1041ms)
✔ calculateDirtyState: 准确判定编辑草稿脏状态 (0.2504ms)
✔ isRevisionConflict: 多形态 409 OCC 乐观锁冲突识别 (0.2316ms)
✔ resolveConflictChoice: 决策本地覆盖或放弃本地 (0.9643ms)
✔ EditorPage AST: 正文编辑区三态权限守卫（只读态、未持锁态、持锁编辑态） (36.4147ms)
✔ EditorPage AST: 实时字数统计与目标符合诊断指标 (16.0625ms)
✔ EditorPage AST: 脏状态检测与保存草稿按钮高亮 (9.1594ms)
✔ EditorPage AST: OCC 409 版本冲突检测与合并弹窗 (10.3277ms)
✔ ProjectHeader: 倒计时计算与临期、过期判定 (4.4021ms)
✔ ProjectHeader: 标的金额货币格式化与脱敏掩码规则 (18.9525ms)
✔ ProjectHeader: 八角色权限感知与只读成员设置入口拦截 (0.3905ms)
✔ ProjectListPage: 项目状态与分册状态推导 (0.2442ms)
✔ ProjectListPage: 状态、涉密属性、分册状态与关键词多维筛选 (0.8931ms)
...
ℹ tests 300
ℹ suites 0
ℹ pass 300
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 2842.5804
```

### 3. 前端生产构建与分包检查
执行命令：
```bash
pnpm --dir frontend/web build
```
实测输出：
```text
$ tsc -b && vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 3362 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                0.79 kB │ gzip:   0.54 kB
dist/assets/index-CZMgSkPA.css                34.47 kB │ gzip:   7.53 kB
dist/assets/rolldown-runtime-8BhlS34s.js       0.80 kB │ gzip:   0.47 kB
dist/assets/sla-form-a6AqMBie.js               2.78 kB │ gzip:   1.42 kB
dist/assets/MenuUnfoldOutlined-Nb8MiWYk.js     6.69 kB │ gzip:   2.60 kB
dist/assets/collapse-CkeV8bG4.js              10.50 kB │ gzip:   3.83 kB
dist/assets/SupportPages-B0ZvPPJ4.js          11.32 kB │ gzip:   4.53 kB
dist/assets/ProjectSettingsPage-DR52Kjri.js   22.58 kB │ gzip:   8.93 kB
dist/assets/SlaPages-Cin94_Jy.js              26.98 kB │ gzip:   9.31 kB
dist/assets/ProjectPages-qCAZQRIn.js         116.16 kB │ gzip:  34.97 kB
dist/assets/EditorPage-JB2VZLvr.js           147.40 kB │ gzip:  47.27 kB
dist/assets/AppShell-ziX5RWON.js             222.28 kB │ gzip:  73.19 kB
dist/assets/project-team-CRj9tYqM.js         295.98 kB │ gzip:  90.33 kB
dist/assets/index-I35VoW_y.js                407.16 kB │ gzip: 126.58 kB
dist/assets/jsx-runtime-J66WJ9pO.js          438.61 kB │ gzip: 144.68 kB
✓ built in 843ms
```
- TypeScript 类型检查 0 错误；
- 主包 `index-I35VoW_y.js` 从 660 kB 降至 **407.16 kB**（gzip 126.58 kB），彻底消除分包超限告警；
- `EditorPage-JB2VZLvr.js` 仅 **147.40 kB**（gzip 47.27 kB）；
- 构建用时仅 **843ms**。

### 4. 全库工程治理与规范检查
执行命令：
```bash
node scripts/check-project-governance.cjs
node --test tests/governance/*.test.cjs
```
实测输出：
```text
治理检查通过：450 份 Markdown、397 项任务、37 项 Issue。
ℹ tests 12
ℹ suites 0
ℹ pass 12
ℹ fail 0
ℹ duration_ms 396.4223
```

---

## 三、签署结论与工作规范守则

根据质量管理裁判原则：
1. **APP-M2-T162**、**APP-M2-T094**、**APP-M2-T095**、**BE-M0-T09**、**BE-M0-T17**、**APP-M2-T184** 六项任务实测全方位符合业务标准与安全红线，出具 **【PASS 终验签署通过】** 结论。
2. **严守工作流纪律**：QA 绝不私自将任务看板标为 done，绝不私自关闭业务 Issue；上述任务卡保持 **in-review** 状态，由主 Agent / 项目经理进行后续里程碑确认。
