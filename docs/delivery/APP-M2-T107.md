为什么有这个文件：记录 APP-M2-T107 重抽不覆盖与补遗差异的前端与测试交付。

它解决什么问题：说明页面实际做到什么、哪些没做，避免把未运行的测试或未连接的服务当作已验收。

# APP-M2-T107：重抽不覆盖与补遗差异

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T107 |
| 代码解释 | [APP-M2-T107](../code/APP-M2-T107.md) |
| 验收 | 2026-10-31：补遗/澄清文件在文件表出现“补遗差异”入口，抽屉逐条对照：修改了哪条原条款（逐字标删除与新增）、新增了什么、哪些未定位到原条款（提示去冲突页指定原条款）、事实取值的变化、旧版中被标“所在文件已被替代”的条数。验证见 [验证记录](../testing/2026-10-31-wp4-parse-postprocess-frontend.md) |
| 项目进度 | 看板与任务卡改为 in-review，等待 QA 与项目经理复审；不标 done |
<!-- task-delivery:end -->

## 关联
- 任务卡：[APP-M2-T107](../tasks/APP-M2.md#app-m2-t107)
- Issue：[ISSUE-007](../../issues/ISSUE-007.md)
- 依据：PRD v1.8 §5.1.1～5.1.5、§5.2.1～5.2.4；后端见提交 `229d05f`

## 实际文件
- 接口：`GET …/files/{id}/addendum-diff`（`AddendumDiff`）；`AddendumDiffDrawer.tsx` 按 `diff[].op` 着色。
- 前端：`frontend/web/src/project/` 下 `TenderTab.tsx`、`ParseTab.tsx`、`ConflictCards.tsx`、`MergeSuggestionsDrawer.tsx`（新）、`AddendumDiffDrawer.tsx`（新）、`parse-postprocess-core.ts`（新）；`shared/types.ts`
- 测试：“文件版本链”用例中的差异入口判断；`tests/backend/test_tender_files.py::test_addendum_diff_for_non_amending_file_is_not_amending`、`test_parse_decisions.py::test_unlocated_addendum_assign_target_supersedes_original`

## 说明
重抽不覆盖人工修改与锁定、仅受影响条目回待确认由后端 `parse_decisions.py` 承担；页面只展示结果。

## 未实现项与限制
- “三栏与设计稿并排截图”未做；差异视图只在补遗/澄清文件已解析后可用；闸门条件表格驱动用例由既有 T108 覆盖，本卡未新增。
- 本机没有运行 pytest、tsc、pnpm 构建与 Playwright，以上后端与 e2e 用例只在 CI 执行；结果以 CI 为准，不在此处声明通过。
