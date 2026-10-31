为什么有这个文件：记录 APP-M2-T101 招标文件上传与版本链的前端与测试交付。

它解决什么问题：说明页面实际做到什么、哪些没做，避免把未运行的测试或未连接的服务当作已验收。

# APP-M2-T101：招标文件上传与版本链

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T101 |
| 代码解释 | [APP-M2-T101](../code/APP-M2-T101.md) |
| 验收 | 2026-10-31：上传时选文件类型（招标文件/澄清/补遗/技术规范书/合同条款/附件），文件表增加类型、版本、上传人与时间列，项目负责人可改类型（已解析的文件不能在补遗/澄清与其他类型间切换）、把旧版“设为被替代”（须选同类型、其后上传的新版并写理由）。验证见 [验证记录](../testing/2026-10-31-wp4-parse-postprocess-frontend.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T101](../tasks/APP-M2.md#app-m2-t101)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.1.1～5.1.5、§5.2.1～5.2.4；后端见提交 `229d05f`

## 实际文件
- 接口：`file_role` 随上传传给 `files/raw`；`POST …/files/{id}/role`、`POST …/files/{id}/supersede`；版本号、上传人、替代关系来自后端 `TenderFile` 字段。
- 前端：`frontend/web/src/project/` 下 `TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`（新）、`AddendumDiffDrawer.tsx`（新）、`parse-postprocess-core.ts`（新）；`shared/types.ts`
- 测试：`parse-postprocess-core.test.mjs` 中“文件版本链”“类型切换限制”用例；`tests/backend/test_tender_files.py`（3 项，设类型、替代链、替代后确认忽略旧文件）；e2e 文件表类型/版本/解析服务列

## 说明
版本链的后端规则（同类型、其后上传、旧条目标“所在文件已被替代”、人工改过的回到待确认）见 `tender_files.py`；>200 页分批的页码范围只在后端字段 `batches` 记录，页面未展示。

## 未实现项与限制
- >200 页分批没有在页面展示批次范围；同指纹复用只在解析服务列标“复用”，没有单独的复用详情；没有用真实 RAGFlow 解析验证。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，以上后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。
