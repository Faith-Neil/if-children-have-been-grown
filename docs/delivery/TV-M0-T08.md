为什么有这个文件：记录工单 1（管道去闸门）实际改了什么与验收证据。

它解决什么问题：避免仍把「抽取确认 / 进矩阵」当成技术分册主路径闸门。

# TV-M0-T08 交付

| 项 | 内容 |
|---|---|
| 任务 | [TV-M0-T08](../tasks/TV-M0.md#tv-m0-t08) |
| Issue | [ISSUE-047](../../issues/ISSUE-047.md) |
| 日期 | 2026-11-05 |
| 状态 | in-review。建议 PM 在 QA/PD 签署后再标 done；本 Agent 不标 done |
| 代码解释 | [TV-M0-T08](../code/TV-M0-T08.md) |

## 实际变更

- 后端：`technical_only` 解析成功且抽到条款后自动 `parse_confirmed=true` 并拟目录；抽出为空保持未确认且无目录；完成文案区分技术管道与两册人工核对。
- 前端：上传成功后按 `shouldAutoStartTechnicalParse` 自动 `parse/jobs`；成功有目录进编辑台；「抽取技术条款」改为次要「重新解析」；Parse 页去掉「进入矩阵」主按钮；概览改为上传→确认目录→导出三步。
- 单测：`test_technical_sources` 相关 3 项 + `parse-postprocess-core` 自动解析规则。

## 验收证据

- `python -m pytest tests/backend/test_technical_sources.py::test_extract_keeps_scoring_points_and_spec_clauses_on_one_row tests/backend/test_technical_sources.py::test_empty_technical_extract_stops tests/backend/test_technical_sources.py::test_same_files_cannot_be_extracted_twice -q` → 3 passed。
- `pnpm --dir frontend/web exec node --test tests/unit/parse-postprocess-core.test.mjs` → 8 passed。
- 未宣称：动态目录唯一确认（工单 2）、矩阵后台化（工单 3）、双库写作、一键全文、编辑台 UI、写作助手均未在本卡完成。

## 项目进度

工单 1 实现已到 in-review。下一张：工单 2 动态目录唯一确认。分支仍不合 main。

## 基线同步

| 基线 | impact | 同步 |
|---|---|---|
| PRD | 有影响（最短路径指针） | 仍以决定为准；两册正文不改 |
| ROADMAP | 有影响 | 工单 1 完成实现、待签 |
| ARCHITECTURE | 无影响 | 管道语义未改 API 面，仅确认时机 |
| TASK_BOARD / PROJECT_STATUS / DOCUMENT_INDEX / Issue | 有影响 | 本轮已更新 |
| 参考原文 | 无影响 | 不改 |
