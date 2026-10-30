# 为什么有这个文件：验证导出时正文 Markdown 转 Word 样式（PRD v1.8 §5.9.1 规则 1、6；平台默认模板一至八级标题，§5.6.1；APP-M2-T196）。
# 它解决什么问题：一至八级标题都有样式且只有一至三级进目录；系统生成章节的 Markdown 表格成为真正的 Word 表格；
# 列表、加粗转换且不残留符号；附件按行号插在覆盖该行的块之后。

import re
from io import BytesIO
from zipfile import ZipFile

from icg.domain.domain import Export
from icg.infra.docx_markdown import blocks, runs
from icg.infra.docx_style import DocxMeta, build_docx

CONTENT = "\n".join([
    "# 第一章 总体方案", "## 1.1 服务体系", "### 1.1.1 组织", "#### 1.1.1.1 岗位", "##### 五级标题", "######## 八级标题",
    "本节**重点**说明`巡检`安排。", "- 每月巡检", "2. 提交报告",
    "| 序号 | 招标条款 | 应答 |", "|---|---|---|", "| 1 | ★提供驻场 | **满足** |", "| 2 | 每月巡检 | 满足 |",
    "表后正文。",
])


def _doc(content=CONTENT, inserts=None):
    data = build_docx(Export("e", "", 1, "", "", "f.docx", "t", content), project_name="合成项目",
                      meta=DocxMeta(kind="internal", volume_name="技术分册"), inserts=inserts)
    archive = ZipFile(BytesIO(data))
    return archive.read("word/document.xml").decode(), archive.read("word/styles.xml").decode(), archive.read("word/numbering.xml").decode()


def test_blocks_and_runs():
    kinds = [(b.kind, b.level) for b in blocks(CONTENT)]
    assert kinds[:6] == [("heading", 1), ("heading", 2), ("heading", 3), ("heading", 4), ("heading", 5), ("heading", 8)]
    assert [k for k, _ in kinds[6:]] == ["para", "bullet", "ordered", "table", "para"]
    table = next(b for b in blocks(CONTENT) if b.kind == "table")
    assert table.lines == (9, 12) and table.rows[0] == ["序号", "招标条款", "应答"] and len(table.rows) == 3
    assert runs("本节**重点**说明`巡检`安排。") == [("本节", False), ("重点", True), ("说明巡检安排。", False)]


def test_word_output_has_eight_heading_levels_real_tables_and_no_markdown_left():
    document, styles, numbering = _doc()
    for level in range(1, 9):
        assert f'w:styleId="Heading{level}"' in styles and f'<w:outlineLvl w:val="{level - 1}"/>' in styles
        assert f'<w:lvl w:ilvl="{level - 1}">' in numbering
    assert re.findall(r'<w:pStyle w:val="(Heading\d)"/>', document) == [f"Heading{n}" for n in (1, 2, 3, 4, 5, 8)]
    assert document.count("PAGEREF") == 3  # 目录只列一至三级
    assert document.count("<w:tbl>") == 1 and document.count("<w:tr>") == 3
    texts = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", document))
    assert "|" not in texts and "**" not in texts and "`" not in texts and "---" not in texts
    assert "• 每月巡检" in texts and "2. 提交报告" in texts and "★提供驻场" in texts
    assert 'w:pStyle w:val="ListBullet"' in document and 'w:styleId="ListBullet"' in styles


def test_attachment_inserted_inside_table_lines_goes_after_the_table():
    marker = '<w:p><w:r><w:t>ATTACHMENT</w:t></w:r></w:p>'
    document, _, _ = _doc(inserts={10: marker})
    assert document.index("</w:tbl>") < document.index("ATTACHMENT") < document.index("表后正文")
