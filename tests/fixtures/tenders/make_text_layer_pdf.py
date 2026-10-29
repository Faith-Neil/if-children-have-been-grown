# 为什么有这个文件：生成浏览器用例用的“电子版”招标 PDF（有中文文字层，APP-M2-T103 原件定位）。
# 它解决什么问题：用 Adobe 预定义 CMap（UniGB-UCS2-H，未嵌入字体）写中文，正好验证前端随包发布的 PDF.js CMap 能取出文字层并高亮。
# 用法：python tests/fixtures/tenders/make_text_layer_pdf.py frontend/web/e2e/fixtures/tender-text-layer.pdf

import sys
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, TextStringObject

PAGES = [
    ["招标文件：原件定位验收", "招标编号：E2E-PDF-001", "第一章 招标公告"],
    ["第二章 技术要求", "1. 投标人须提供7x24小时驻场运维服务。", "2. 投标文件未按要求盖章的，视为无效投标。"],
]


def _name(value: str) -> NameObject:
    return NameObject(value)


def cjk_pdf(pages: list[list[str]]) -> bytes:
    writer = PdfWriter()
    descriptor = writer._add_object(DictionaryObject({
        _name("/Type"): _name("/FontDescriptor"), _name("/FontName"): _name("/STSong-Light"),
        _name("/Flags"): NumberObject(6), _name("/FontBBox"): ArrayObject([NumberObject(v) for v in (-25, -254, 1000, 880)]),
        _name("/ItalicAngle"): NumberObject(0), _name("/Ascent"): NumberObject(880), _name("/Descent"): NumberObject(-120),
        _name("/CapHeight"): NumberObject(880), _name("/StemV"): NumberObject(93)}))
    descendant = writer._add_object(DictionaryObject({
        _name("/Type"): _name("/Font"), _name("/Subtype"): _name("/CIDFontType0"), _name("/BaseFont"): _name("/STSong-Light"),
        _name("/CIDSystemInfo"): DictionaryObject({_name("/Registry"): TextStringObject("Adobe"),
                                                   _name("/Ordering"): TextStringObject("GB1"), _name("/Supplement"): NumberObject(4)}),
        _name("/FontDescriptor"): descriptor, _name("/DW"): NumberObject(1000)}))
    font = writer._add_object(DictionaryObject({
        _name("/Type"): _name("/Font"), _name("/Subtype"): _name("/Type0"), _name("/BaseFont"): _name("/STSong-Light"),
        _name("/Encoding"): _name("/UniGB-UCS2-H"), _name("/DescendantFonts"): ArrayObject([descendant])}))
    for lines in pages:
        page = writer.add_blank_page(width=595, height=842)
        page[_name("/Resources")] = DictionaryObject({_name("/Font"): DictionaryObject({_name("/F1"): font})})
        ops = ["BT /F1 12 Tf 16 TL 60 780 Td"] + [f"<{line.encode('utf-16-be').hex()}> Tj T*" for line in lines] + ["ET"]
        stream = DecodedStreamObject()
        stream.set_data("\n".join(ops).encode("ascii"))
        page[_name("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


if __name__ == "__main__":
    with open(sys.argv[1], "wb") as handle:
        handle.write(cjk_pdf(PAGES))
