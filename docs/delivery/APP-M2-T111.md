为什么有这个文件：记录 APP-M2-T111 疑似遗漏处理与确认闸门的实际交付。

它解决什么问题：说明解析结果页的“疑似遗漏 · 待实现”已换成真实流程，以及仍未完成的引用未解析与词表维护。

# APP-M2-T111：疑似遗漏（无批量、排除须理由）交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | APP-M2-T111 |
| 代码解释 | [APP-M2-T111 代码说明](../code/APP-M2-T111.md) |
| 验收 | `tests/backend/test_parse_omissions.py` 4 项通过；前端“无批量按钮”与确认闸门接线单测通过；全量回归见 [Wave 11 验证](../testing/2026-10-28-wave-11-verification.md)。QA/PD 未执行 |
| 项目进度 | in-review；“引用未解析”页签与 APP-M2-T148 仍 planned |
<!-- task-delivery:end -->

## 关联与状态

- 日期 2026-10-28；Issue [ISSUE-040](../../issues/ISSUE-040.md)；任务卡 [APP-M2-T111](../tasks/APP-M2.md#app-m2-t111)
- 分支 `feat/wave-11-main-path`，提交 `06f107d`、`2c8d51c`；[PR #6](https://github.com/Faith-Neil/if-children-have-been-grown/pull/6) 草稿
- 未合入、未发布

## 完成内容与变更文件

- `backend/bid-core/icg/domain/post_process.py`（新）：平台初始词表、扫描、覆盖判定、逐条新增/排除、确认闸门。
- `backend/bid-core/icg/domain/tender_orchestrator.py`：解析后扫描；确认解析前检查疑似遗漏。
- `backend/bid-core/icg/api/chapter_loop.py`：`listScanHits`、`addScanHitAsRequirement`、`excludeScanHit`。
- 错误码 `OMISSIONS_PENDING`（409）。
- `frontend/web/src/project/OmissionsDrawer.tsx`（新）、`ParseTab.tsx`：疑似遗漏入口、抽屉与确认按钮闸门；冲突抽屉中的提示改为只说明“引用未解析”未实现。

## 验收结果

| 验收点（PRD §5.2.4 / 任务卡） | 结果 | 证据 |
|---|---|---|
| ④ 带“★”或废标词、未被条目覆盖的原文列为疑似遗漏 | 通过 | `test_uncovered_disqualification_line_is_suspected_and_blocks_confirm`（“不予受理”行）；`test_ignoring_a_star_requirement_reopens_the_hit_and_reparse_keeps_handled`（★ 条目被忽略后重新成为疑似遗漏） |
| ⑤ 无批量按钮；排除不填理由不能保存 | 通过 | 后台无批量接口、空理由 422；前端单测断言抽屉无批量文案 |
| ⑥ 存在未处理疑似遗漏时不能确认解析结果 | 通过 | 409 `OMISSIONS_PENDING`；页面按钮禁用 |
| 只有项目负责人能处理 | 通过 | 编写人 403 |
| 重新解析不覆盖已处理结果 | 通过 | 排除理由在重新解析后保留 |
| 新增为条目不重复建条目、须重新确认 | 通过 | `test_add_as_requirement_upgrades_line_and_needs_reconfirm` |
| 引用最多两层、循环停止、未解析不阻断 | 未实现 | 本卡只交付疑似遗漏部分，见后续 |

## 项目进度

APP-M2-T111 → in-review（疑似遗漏部分）。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 实施澄清 A5、A6，见 [PRD 实施澄清](../decisions/2026-10-28-prd-amendments-wave11.md) |
| ROADMAP | 无影响 |
| ARCHITECTURE | 已登记 |
| Issue 看板/详情 | ISSUE-040 |
| TASK_BOARD / PROJECT_STATUS | 已同步 |
| DOCUMENT_INDEX | 已登记 |

## 风险与后续

- 本地文字解析器把每行都抽成条目，疑似遗漏主要出现在“含废标词但未被判为星号/废标”的行或被忽略的星号条目；接入真实抽取模型后命中会更多。
- 任务卡标题中的“引用未解析页签”未完成，PM 视情况拆卡或待补齐后再验收。
- 词表维护、试扫、发布（APP-M2-T148）未做。
