# 为什么有这个文件：用独立适配器读取上传文件中的真实文字和原文位置。
# 它解决什么问题：不把模型生成的内容当作招标原文，扫描 PDF 与不确定页码明确提示。

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from .domain import DomainError


@dataclass
class ParsedDocument:
    pages: list[str]
    pagination: str
    warnings: list[str] = field(default_factory=list)
    # 扫描件（RAGFlow DeepDOC）逐页文字区域及其位置框，用于原件 PDF 上高亮；文字层 PDF 由浏览器 PDF.js 自己定位
    regions: list[list[dict]] = field(default_factory=list)


class LocalTextParser:
    name = "local-text"
    MAX_EXPANDED_BYTES = 20 * 1024 * 1024

    def parse(self, filename: str, content: bytes) -> ParsedDocument:
        suffix = PurePosixPath(filename).suffix.lower()
        if suffix in (".txt", ".md"):
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise DomainError(422, "TEXT_ENCODING", "文本请使用 UTF-8 编码后再上传。") from error
            self._validate_text(text)
            return self._nonempty(ParsedDocument(text.split("\f"), "explicit_form_feed",
                                                 ["文本页码按换页符定位；无换页符时所有原文记为第 1 页。"] ))
        if suffix == ".docx":
            return self._docx(content)
        if suffix == ".pdf":
            return self._pdf(content)
        raise DomainError(422, "FILE_TYPE_UNSUPPORTED", "当前真实解析支持 UTF-8 文本、DOCX 和含文字的 PDF。")

    @staticmethod
    def _validate_text(text: str):
        if any(not (ord(c) in (9, 10, 12, 13) or 32 <= ord(c) <= 0xD7FF
                    or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in text):
            raise DomainError(422, "INVALID_TEXT", "文件含有不能写入 Word 的控制字符。")

    @staticmethod
    def _nonempty(result: ParsedDocument) -> ParsedDocument:
        if not any(page.strip() for page in result.pages):
            raise DomainError(422, "NO_TEXT", "文件中没有可解析的文字。")
        return result

    def _docx(self, content: bytes) -> ParsedDocument:
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 300 or sum(item.file_size for item in entries) > self.MAX_EXPANDED_BYTES:
                    raise DomainError(413, "FILE_EXPANSION_LIMIT", "Word 解压后过大，不能在本地演示中解析。")
                if not {"word/document.xml", "[Content_Types].xml", "_rels/.rels"}.issubset(archive.namelist()):
                    raise DomainError(422, "INVALID_DOCX", "文件不是有效的 DOCX 文档。")
                document = archive.read("word/document.xml")
            if b"<!DOCTYPE" in document.upper() or b"<!ENTITY" in document.upper():
                raise DomainError(422, "INVALID_DOCX", "Word 包含不支持的 XML 声明。")
            root = ElementTree.fromstring(document)
        except (BadZipFile, ElementTree.ParseError, KeyError, RuntimeError) as error:
            raise DomainError(422, "INVALID_DOCX", "无法读取 DOCX 文件结构。") from error
        pages = [""]
        for paragraph in root.iter(namespace + "p"):
            for element in paragraph.iter():
                if element.tag == namespace + "t":
                    pages[-1] += element.text or ""
                elif element.tag == namespace + "tab":
                    pages[-1] += "\t"
                elif element.tag == namespace + "br":
                    if element.attrib.get(namespace + "type") == "page":
                        pages.append("")
                    else:
                        pages[-1] += "\n"
            pages[-1] += "\n"
        for page in pages:
            self._validate_text(page)
        return self._nonempty(ParsedDocument(pages, "explicit_docx_breaks_only",
                                             ["DOCX 页码仅按明确分页符定位；未经过 Word 排版，不代表最终印刷页码。"] ))

    def _pdf(self, content: bytes) -> ParsedDocument:
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise DomainError(422, "PDF_ADAPTER_UNAVAILABLE", "PDF 文字读取适配器未安装，请先使用文本或 DOCX。") from error
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise DomainError(422, "PDF_ENCRYPTED", "加密 PDF 请先提供可读取版本。")
            if len(reader.pages) > 500:
                raise DomainError(413, "PDF_PAGE_LIMIT", "PDF 页数超过本地演示的 500 页限制。")
            pages = [page.extract_text() or "" for page in reader.pages]
        except DomainError:
            raise
        except Exception as error:
            raise DomainError(422, "INVALID_PDF", "无法读取 PDF 文件结构。") from error
        if not any(page.strip() for page in pages):
            raise DomainError(422, "OCR_REQUIRED", "此 PDF 没有可提取文字，扫描件需后续接入 OCR；本次未解析成功。")
        for page in pages:
            self._validate_text(page)
        blank = [str(i + 1) for i, page in enumerate(pages) if not page.strip()]
        if blank:
            raise DomainError(422, "OCR_REQUIRED", "PDF 存在无文字页面，不能把部分提取冒充完整解析。", {"pages": blank})
        return self._nonempty(ParsedDocument(pages, "pdf_page_index"))
