为什么有这个文件：记录 Word 默认版式这张卡实际改了什么、测了什么。

它解决什么问题：把 W1～W4 和已批准的版式对应到可核对的结果，而不是只留在对话里。

# BE-M0-T15：Word 导出默认版式交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T15 |
| 代码解释 | [BE-M0-T15](../code/BE-M0-T15.md) |
| 验收 | 2026-10-12，`env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q`：329 passed，2 skipped。`node scripts/check-project-governance.cjs` 见验证记录。合成 docx 断言标题、三种字体属性、字号间距缩进、加粗表头、TOC、页码和页边距 |
| 项目进度 | 363 项：26 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。BE-M0 为 15 项，5 项 done。T14 仍是托管 MySQL 作业。本卡 in-review，不标 done |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-027](../../issues/ISSUE-027.md)，[任务卡](../tasks/BE-M0.md#be-m0-t15)。
- 分支 `codex/repository-foundation`。未新开 PR。
- 本地验收已跑后台测试和治理检查。等待项目经理 QA 签收。
- 未合入，未发布。

## 完成内容与变更文件

`build_docx` 改到 `backend/bid-core/icg_demo/docx_style.py`。默认版式是 A4，上 2.5 cm、下 2.5 cm、左 2.8 cm、右 2.6 cm。封面标题用方正小标宋，ascii 与 hAnsi 回退黑体，22 磅、居中、加粗。项目名称黑体 16 磅、居中。封面节没有页码。

正文里以 `# `、`## `、`### ` 开头的行分别成为 Heading 1、Heading 2、Heading 3，并接多级编号。标题前后各 0.5 行。一级黑体 16 磅居中；二级楷体_GB2312 15 磅左齐加粗；三级仿宋_GB2312 14 磅左齐加粗。正文仿宋_GB2312 14 磅、两端对齐、固定 28 磅行距、段前段后 0、首行缩进 2 字符。表格宋体 10.5 磅，表头行加粗。页眉页脚宋体 10.5 磅居中。目录是按 1～3 级标题生成的 TOC 域，宋体 12 磅。正文节页码从 1 开始，页脚居中。每处 `w:rFonts` 都写 eastAsia、ascii 和 hAnsi。

分册导出用 `chapter_export_block` 把章节名写成一级标题。调用方可以传入 `style` 覆盖默认值，也可以传入 `project_name`。未新增依赖。

## 代码解释

见 [代码解释](../code/BE-M0-T15.md)。

## 验收结果

先写打开 docx 的测试，确认旧导出缺少标题样式、hAnsi、加粗表头、TOC、第二节和批准边距，再改生成代码。通过后再跑全部后台测试。证据见 [验证记录](../testing/2026-10-12-be-m0-t15-word-style.md)。

未用 Word 或 WPS 做视觉签收。内部稿标记仍在页眉，文件仍不可当作正式递交件。

## 项目进度

363 项中 26 done、9 in-review。BE-M0 共 15 项，完成 5 项。T14 是托管 MySQL 作业。下一张未开始的后端卡仍是既有 ready 或 planned 卡。本卡不自动开始它们。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 只改任务计数。产品规则未改 |
| ROADMAP | 只改任务计数。阶段和门禁未改 |
| ARCHITECTURE | 未改。演示导出版式不改变架构基线 |
| Issue 看板/详情 | ISSUE-027 为 in-review。ISSUE-023 在同一提交中按 QA 签署 16cf971 和项目经理确认改为 closed |
| TASK_BOARD / PROJECT_STATUS | 已改为 363 项，本卡 in-review。BE-M0-T14 仍是托管 MySQL 作业 |
| DOCUMENT_INDEX | 已登记本交付、代码说明、验证和同步表 |

## 风险与后续

客户机器上没有方正小标宋、楷体_GB2312 或仿宋_GB2312 时，版式会落到系统回退字体。目录域需要打开 Word 后更新域，文件里已经写入 TOC 指令。视觉签收和客户模板不在本卡。
