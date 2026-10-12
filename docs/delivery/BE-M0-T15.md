为什么有这个文件：记录 Word 默认版式这张卡实际改了什么、测了什么。

它解决什么问题：把 W1～W4 和已批准的版式对应到可核对的结果，而不是只留在对话里。

# BE-M0-T15：Word 导出默认版式交付

<!-- task-delivery:start -->
| 项目 | 记录 |
|---|---|
| 任务ID | BE-M0-T15 |
| 代码解释 | [BE-M0-T15](../code/BE-M0-T15.md) |
| 验收 | 2026-10-12，`env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q`：335 passed，2 skipped。`node scripts/check-project-governance.cjs`：治理检查通过：227 份 Markdown、366 项任务、28 项 Issue。合成 docx 断言 firstLineChars=200 与 firstLine=560、无标题时不写目录、有标题时写目录占位、封面下一页分节、方正小标宋三种属性、承诺函项目名称、标题、表头、页码和页边距。规格用中文说明缺失字体由 Word 或 WPS 决定，要保证效果需安装方正小标宋 |
| 项目进度 | as of commit e6215d4, task board is source of truth。该提交时看板为 366 项：32 done、7 in-review、7 in-progress、267 planned、49 blocked、4 ready。本提交把 BE-M0-T11 改为 in-review 后，看板为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。BE-M0 为 15 项，6 项 done。本卡 in-review，不标 done |
<!-- task-delivery:end -->

## 关联与状态

- 2026-10-12，BE-M0，[ISSUE-027](../../issues/ISSUE-027.md)，[任务卡](../tasks/BE-M0.md#be-m0-t15)。
- 分支 `codex/repository-foundation`。未新开 PR。
- 本地验收已跑后台测试和治理检查。等待项目经理 QA 签收。
- 未合入，未发布。

## 完成内容与变更文件

已确认规格见 [Word 默认版式](../standards/word-default-style.md)。`build_docx` 在 `backend/bid-core/icg_demo/docx_style.py`。

封面节写 `<w:type w:val="nextPage"/>`，封面单独成页且没有页码，正文页码从 1 开始。封面标题三种字体属性都是方正小标宋。规格用中文写明：docx 不能指定缺失字体的替换字体，由 Word 或 WPS 决定；要保证效果，请在本机安装方正小标宋。黑体仍是用户批准的替代字体，不是拉丁回退。承诺函下载把项目名称传给 `build_docx`，封面项目名称是黑体 16 磅、居中。正文样式首行缩进同时写 `w:firstLineChars="200"` 和 `w:firstLine="560"`。正文没有标题标记时，不再把文档标题再写成 Heading 1，也不写“目录”和 TOC 域。有标题时，目录前有宋体、非标题的“目录”，TOC 域的占位文字是“右键更新域以生成目录”。一级标题默认居中，`h1_align="left"` 可以改成左对齐。

分册导出用 `chapter_export_block` 把章节名写成一级标题。调用方可以传入 `style` 覆盖默认值。未新增依赖。

## 代码解释

见 [代码解释](../code/BE-M0-T15.md)。

## 验收结果

先写打开 docx 的测试，确认旧导出缺少标题样式、hAnsi、加粗表头、TOC、第二节和批准边距，再改生成代码。通过后再跑全部后台测试。证据见 [验证记录](../testing/2026-10-12-be-m0-t15-word-style.md)。

未用 Word 或 WPS 做视觉签收。内部稿标记仍在页眉，文件仍不可当作正式递交件。

## 项目进度

as of commit e6215d4, task board is source of truth。该提交看板为 366 项：32 done、7 in-review、7 in-progress、267 planned、49 blocked、4 ready。BE-M0-T11 进入 in-review 后，看板为 366 项：32 done、8 in-review、7 in-progress、266 planned、49 blocked、4 ready。BE-M0 共 15 项，完成 6 项。T14 已依据 QA 签署标为 done。本卡 in-review，不标 done。QA 复验 Q1～Q3 的提交是 159b96c。

## 文档与 Issue 同步

| 对象 | 更新或无影响的理由 |
|---|---|
| PRD | 只改任务计数。产品规则未改 |
| ROADMAP | 只改任务计数。阶段和门禁未改 |
| ARCHITECTURE | 未改。演示导出版式不改变架构基线 |
| Issue 看板/详情 | ISSUE-027 为 in-review。ISSUE-023 在同一提交中按 QA 签署 16cf971 和项目经理确认改为 closed |
| TASK_BOARD / PROJECT_STATUS | as of commit e6215d4, task board is source of truth。本卡仍 in-review。T14 已依据 QA 签署标为 done |
| DOCUMENT_INDEX | 已登记本交付、代码说明、验证、同步表和 [默认版式规格](../standards/word-default-style.md) |

## 风险与后续

客户机器上没有方正小标宋、楷体_GB2312 或仿宋_GB2312 时，docx 不能指定由哪一种字体替换，由 Word 或 WPS 决定。要保证效果，请在本机安装这些字体。目录域的结果要等 Word 更新域之后才展开；`w:updateFields` 只是打开时的提示，不是已经算好的目录。视觉签收和客户模板不在本卡。
