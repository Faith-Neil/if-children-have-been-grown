为什么有这个文件：说明默认版式从哪一处生成，以及一个投标怎样覆盖它。

它解决什么问题：避免以后改导出时只找到旧的普通段落，不知道标题、目录和页码写在哪。

# BE-M0-T15：代码解释

- 对应任务：[BE-M0-T15](../tasks/BE-M0.md#be-m0-t15)；Issue：[ISSUE-027](../../issues/ISSUE-027.md)；交付：[BE-M0-T15](../delivery/BE-M0-T15.md)
- 日期：2026-10-12。入口仍是 `icg_demo.adapters.build_docx`，实现在 `icg_demo/docx_style.py`。

## 改了什么以及为什么

旧的 `build_docx` 把每一行写成普通段落，标题只用 Title 样式，表头不加粗，默认字体没有 hAnsi，也没有编号、目录、页眉页脚和第二节。QA 的 W1～W4 都出在这里。分册导出还把章节名和正文用换行拼在一起，所以章节名也是普通段落。

现在 `DocxStyle` 保存纸张边距、封面、三级标题、正文、表格、页眉页脚和目录的字体与字号。`DEFAULT_DOCX_STYLE` 是 [已确认规格](../standards/word-default-style.md)。`build_docx(..., style=None, project_name=None)` 在未传入版式时用这份默认值。传入另一份 `DocxStyle` 时，边距和字体按那一份写。封面标题的 eastAsia、ascii 和 hAnsi 都是方正小标宋。黑体只在本机没有方正小标宋时由系统替换，不是拉丁或西文回退。一级标题默认居中；规格允许居中或左对齐，把 `h1_align` 改成 `left` 即可覆盖。其余字体三个属性写同一个字体名。

## 入口和调用顺序

1. 单章下载、分册下载和承诺函下载仍调用 `build_docx`。
2. 分册在 `workflow.export` 里用 `chapter_export_block` 生成 `# 章节名` 加正文，并把项目名称放进下载数据。
3. `build_docx` 先写封面和封面节。封面节写 `<w:type w:val="nextPage"/>`，不写页码，因此封面单独成页。承诺函下载把项目名称传给 `project_name`，封面用 CoverProject：黑体 16 磅、居中。
4. 正文节从页码 1 开始。正文出现 `# `、`## ` 或 `### ` 时，先写宋体、非标题样式的“目录”，再写 TOC 域 `TOC \o "1-3" \h \z \u`，域结果的占位文字是“右键更新域以生成目录”。没有任何标题标记时不写“目录”，也不写 TOC 域，并且不再把文档标题再写成 Heading 1。正文样式的首行缩进同时写 `w:firstLineChars="200"` 和 `w:firstLine="560"`。
5. 表格放在正文节。第一行保留表头重复，并给单元格加粗。
6. 页眉写内部稿标记。正文页脚写 PAGE 域。封面页脚不写 PAGE 域。
7. `word/settings.xml` 写入 `<w:updateFields w:val="true"/>`，让 Word 在打开文件时提示更新 TOC 域。

## 数据与状态

导出不读数据库，也不改内存状态。样式对象是不可变数据。正文里的 `&`、`<`、`>` 仍做 XML 转义。空行仍保留为段落，既有“每一行都出现在文件里”的检查继续成立。

## 关键判断与异常

封面标题使用 CoverTitle，不使用 Heading，因此不会进入目录。“目录”使用 TocTitle，也没有大纲级别。目录只收集 Heading 1～3。页码从正文第一节开始，封面没有页码。没有新增第三方库；打不开的部分仍用标准库 `zipfile` 和 XML。

## 验证与限制

测试直接打开生成的 zip，核对样式、字体三属性、间距、首行缩进的字符数和 560 缇、表头、有标题时的 TOC、目录标题和占位文字、无标题时不写目录、封面的下一页分节、无标题正文不重复封面标题、一级标题可改为左对齐、`word/settings.xml` 里的 `w:updateFields w:val="true"`、页码和边距。承诺函下载另核对封面项目名称。没有在 Word 或 WPS 里做视觉签收。客户模板不是本卡的默认值，需要时传入另一份 `DocxStyle`。
