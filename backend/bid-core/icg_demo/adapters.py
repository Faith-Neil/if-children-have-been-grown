# 为什么有这个文件：提供内存存储、模拟建议和真实 Word 文件的演示实现。
# 它解决什么问题：不接数据库或外部模型，也能验证事务、替换接口和下载结果。

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from threading import RLock
from typing import Callable, TypeVar
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from .domain import Account, Chapter, DemoState, Export, Project

T = TypeVar("T")


def seed_state() -> DemoState:
    state = DemoState()
    for user in (
        Account("alpha-editor", "甲公司编写人（合成）", "alpha", "editor"),
        Account("alpha-manager", "甲公司项目经理（合成）", "alpha", "manager"),
        Account("alpha-viewer", "甲公司查看人（合成）", "alpha", "viewer"),
        Account("beta-editor", "乙公司编写人（合成）", "beta", "editor"),
    ):
        state.accounts[user.id] = user
    for company in ("alpha", "beta"):
        project = Project(f"{company}-project", f"{'甲' if company == 'alpha' else '乙'}公司合成投标项目", company)
        state.projects[project.id] = project
        for suffix, volume, title in (("tech", "technical", "技术方案"),
                                      ("business", "business", "商务响应")):
            content = (f"{'甲' if company == 'alpha' else '乙'}公司合成项目的{title}。\n"
                       "本内容仅用于本地演示，不可作为真实承诺或正式递交文件。")
            chapter = Chapter(f"{company}-{suffix}", project.id, title, volume, content)
            chapter.versions.append({"revision": 1, "content": content,
                                     "actor_id": "demo-seed", "created_at": "2026-10-10T00:00:00+00:00"})
            state.chapters[chapter.id] = chapter
    return state


class MemoryRepository:
    mode = "memory"

    def __init__(self, initial_state: DemoState | None = None):
        self._lock = RLock()
        self._state = deepcopy(initial_state if initial_state is not None else seed_state())

    def read(self) -> DemoState:
        with self._lock:
            return deepcopy(self._state)

    def transaction(self, operation: Callable[[DemoState], T]) -> T:
        with self._lock:
            working = deepcopy(self._state)
            result = operation(working)
            # 连返回值拷贝或提交快照拷贝失败，也不能把部分修改写入当前状态。
            safe_result = deepcopy(result)
            committed = deepcopy(working)
            self._state = committed
            return safe_result


class DemoModelProvider:
    name = "demo"
    is_real_model = False
    is_local = True

    def suggest(self, instruction: str, content: str) -> str:
        return (f"{content}\n\n[模拟建议，未调用真实模型]\n"
                f"修改要求：{instruction}\n请由编写人核对内容；确认提交前不会写入正式正文。")


def build_docx(record: Export) -> bytes:
    # 每行写成独立段落，XML 转义保证 &、< 等文字不会变成文件结构。
    def paragraph(text: str, *, title: bool = False) -> str:
        style = '<w:pPr><w:pStyle w:val="Title"/></w:pPr>' if title else ""
        return (f'<w:p>{style}<w:r><w:t xml:space="preserve">'
                f'{escape(text)}</w:t></w:r></w:p>')

    document_body = paragraph("本地演示内部稿，不可正式递交")
    document_body += paragraph(record.title, title=True)
    document_body += "".join(paragraph(line) for line in record.content.splitlines())
    document_body += ("<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
                      "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr>")
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:body>{document_body}</w:body></w:document>')
    contents = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    root_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    document_relationships = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Microsoft YaHei"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
</w:styles>'''
    target = BytesIO()
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", contents)
        archive.writestr("_rels/.rels", root_relationships)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", document_relationships)
        archive.writestr("word/styles.xml", styles)
    return target.getvalue()
