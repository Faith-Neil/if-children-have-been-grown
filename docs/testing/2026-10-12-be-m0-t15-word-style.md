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

## 命令

工作目录为仓库根。未设置数据库环境变量。

```text
env -u ICG_DATABASE_URL -u ICG_REQUIRE_MYSQL python3 -m pytest tests/backend -q
```

结果：330 passed，2 skipped。新增用例在 `tests/backend/test_docx_default_style.py`，打开生成的 docx，检查标题级别、三种字体属性、字号间距与首行缩进、加粗表头、TOC 域、`word/settings.xml` 的 `w:updateFields w:val="true"`、页码与分节、页边距，以及一份左边距改为 3.0 cm 的覆盖版式。

改生成代码之前，这些用例对旧导出失败：没有 Heading1，默认字体没有 hAnsi，表头没有加粗，没有 TOC，只有一节，四边仍是 1440 缇。

治理检查在同一工作区执行 `node scripts/check-project-governance.cjs`。输出：

```text
治理检查通过：219 份 Markdown、363 项任务、28 项 Issue。
```

## 局限

这是 XML 结构核对，不是 Word 或 WPS 的视觉签收。机器上没有方正小标宋时，打开文件会使用系统回退字体。目录域的结果要等文字处理软件更新域之后才展开。
