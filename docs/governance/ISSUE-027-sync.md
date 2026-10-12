为什么有这个文件：记录 Word 默认版式这张卡动了哪些基线，以及哪些故意不动。

它解决什么问题：避免把演示导出的版式写成产品规则或架构已经改变。

# ISSUE-027 同步

日期 2026-10-12。revision style-1。状态 in-review。

| 对象 | 是否改动 | 理由 |
|---|---|---|
| PRD | 已改计数 | rebase 后活的看板是 363 项：26 done、9 in-review、7 in-progress、268 planned、49 blocked、4 ready。产品规则、页面和范围没有改 |
| ROADMAP | 已改计数 | 同一组 363 项。阶段、门禁和里程碑没有改。ISSUE-026 已把三份基线写成 8 in-review、49 blocked。本卡新增任务后 in-review 为 9 |
| ARCHITECTURE | 未改 | 默认版式只作用在演示 Word 导出。架构基线里的模块、数据流和部署约束没有变化，所以不改 `docs/ARCHITECTURE.md` |
| PROJECT_BRIEF | 已改计数 | 排期行使用同一组 363 项。不改产品判断 |
| TASK_BOARD | 已改 | BE-M0-T14 已是托管 MySQL 作业。本卡为 BE-M0-T15，状态 in-review。BE-M0 为 15 项，5/15 done |
| PROJECT_STATUS | 已改 | 进度改为 363 项，并写明 W1～W4 由 BE-M0-T15 提交复核 |
| DOCUMENT_INDEX | 已改 | 登记本表、Issue、交付、代码说明和验证 |
| docs/reference | 未改 | 本卡不涉及参考资料 |
| docs/standards/word-default-style.md | 已新增 | 用户确认的版式原文。封面标题三种字体属性都是方正小标宋；黑体只在未安装该字体时替换，不是拉丁回退 |

同一提交按项目经理在 QA 签署 16cf971 后的确认，把 ISSUE-023 标为 closed。Issue 状态词表没有 done，完成状态使用 closed。BE-M0-T10 在 ISSUE-023 的任务表和影响表改为 done。

2026-10-12 补 Q1～Q3：正文首行缩进补 `w:firstLine="560"`，没有标题时不写目录。规格中的英文字段改为中文：docx 不能指定缺失字体的替换字体，由 Word 或 WPS 决定；要保证效果，请在本机安装方正小标宋。黑体仍是用户批准的替代字体，不是拉丁回退。本跟进不新增任务，也不改变 BE-M0-T15 的 in-review。PRD、ROADMAP、ARCHITECTURE、PROJECT_BRIEF 的计数句子保持看板上已有的数字，本提交不改这四份。`docs/reference` 未改。卡片仍为 in-review。
