为什么有这个文件：留下打开合成 docx 的核对方法和当次结果。

它解决什么问题：避免只说版式已改，却没有可重复的测试计数和缺陷对照。

# 2026-10-12 Word 默认版式核对

关联 [ISSUE-027](../../issues/ISSUE-027.md)、[BE-M0-T15](../delivery/BE-M0-T15.md)。状态 in-review。只用合成数据，没有客户原文。

## 对照

| 缺陷 | 改前 | 本次写法 |
|---|---|---|
| W1 | 无标题级别、目录、页码、页眉页脚 | Heading 1～3、多级编号、TOC 域、`w:updateFields w:val="true"`、正文页码从 1 起、页眉和页脚 |
| W2 | 章节名是普通段落 | 分册用 `# 章节名`，导出为 Heading 1 |
| W3 | 表头行不加粗 | 表头单元格 `w:b`，数据行不加粗 |
| W4 | 默认字体缺 hAnsi | 每处 `w:rFonts` 写 ascii、hAnsi、eastAsia |
| V1 | 封面和正文挤在同一页，封面出现页码 1 | 封面节 `<w:type w:val="nextPage"/>`，封面无页码，正文从 1 起 |
| V2 | 无标题正文又把文档标题写成 Heading 1 | 没有标题标记时不再插入封面标题 |
| V3 | 目录域没有可见占位 | 宋体非标题“目录”，占位文字“右键更新域以生成目录” |
| M1 | 封面标题的 ascii、hAnsi 写成黑体 | 三种字体属性都是方正小标宋。黑体只在未安装时替换，不是拉丁回退 |
| M2 | 承诺函封面没有项目名称 | 下载路由传入 `project_name`，CoverProject 为黑体 16 磅、居中 |
| Q1 | 首行缩进只写了 `firstLineChars` | 正文 `w:ind` 同时写 `w:firstLineChars="200"` 和 `w:firstLine="560"` |
| Q2 | 没有标题时仍写出“目录”和 TOC 域 | 正文没有 `# `、`## `、`### ` 时不写目录标题，也不写 TOC 域 |
| Q3 | 规格文件用英文说明黑体替代 | 改为中文：docx 不能指定缺失字体的替换字体，由 Word 或 WPS 决定；要保证效果，请在本机安装方正小标宋。黑体仍是用户批准的替代字体，不是拉丁回退 |

## 命令

工作目录为仓库根。未设置数据库环境变量。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：335 passed，2 skipped。用例在 `tests/backend/test_docx_default_style.py` 和 `tests/backend/test_sla.py`，打开生成的 docx，检查标题级别、三种字体属性、字号间距、首行缩进 `firstLineChars="200"` 与 `firstLine="560"`、加粗表头、有标题时的 TOC 域和占位文字、无标题时不写“目录”和 TOC 域、封面下一页分节、无标题正文不重复封面标题、一级标题可改左对齐、承诺函封面项目名称、`word/settings.xml` 的 `w:updateFields w:val="true"`、页码与分节、页边距，以及一份左边距改为 3.0 cm 的覆盖版式。

改生成代码之前，这些用例对旧导出失败：没有 Heading1，默认字体没有 hAnsi，表头没有加粗，没有 TOC，只有一节，四边仍是 1440 缇。

治理检查在同一工作区执行 `node scripts/check-project-governance.cjs`。输出：

```text
治理检查通过：227 份 Markdown、366 项任务、28 项 Issue。
```

## 局限

这是 XML 结构核对，不是 Word 或 WPS 的视觉签收。机器上没有方正小标宋时，由本机替换为用户批准的黑体，文件里仍写方正小标宋，不是拉丁回退。目录域的结果要等文字处理软件更新域之后才展开。
