# 为什么有这个文件：附件扫描件插入 Word（PRD v1.8 §5.9.1 规则 7、异常“附件图片过大时自动压缩”，R14；APP-M2-T198）。
# 它解决什么问题：
# 1. 证书、授权书、业绩证明等扫描件（PDF 或图片）按附件归属指定的页码范围转成页面图片，只插入这些页；
# 2. 过大的图片按 A4 正文区 200dpi 等比缩小、转 JPEG 压缩，保持字迹可辨认；
# 3. 敏感附件把水印文字（如“仅用于××项目投标”）斜向平铺烧进图片里，Word 和 WPS 都原样显示、无法单独删掉水印；
# 4. 坏文件、页码超出范围、找不到中文字体时抛出带附件名和页码的错误，由导出批次整体记失败。
# PDF 用 pypdfium2 逐页渲染（扫描件和文字版 PDF 都能出图），图片用 Pillow 读取。

from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass
from io import BytesIO
from xml.sax.saxutils import escape

EMU_PER_CM = 360000
RENDER_DPI = 200
MAX_SIDE_PX = 2339           # A4 长边 200dpi
JPEG_QUALITY = 82
_PDFIUM_LOCK = threading.Lock()  # pdfium 不是线程安全的
FONT_CANDIDATES = (
    "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
)


class AttachmentRenderError(ValueError):
    """附件无法插入：消息里带附件名与页码，直接写进导出失败原因。"""


@dataclass(frozen=True)
class PageImage:
    data: bytes
    extension: str  # jpeg / png
    width_px: int
    height_px: int


def sniff(data: bytes) -> str | None:
    """按文件头判断类型，不信任文件名。"""
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    return None


def page_count(data: bytes) -> int:
    kind = sniff(data)
    if kind == "pdf":
        import pypdfium2 as pdfium
        with _PDFIUM_LOCK:
            try:
                document = pdfium.PdfDocument(data)
            except Exception as error:
                raise AttachmentRenderError(f"PDF 无法打开（{type(error).__name__}）") from error
            try:
                return len(document)
            finally:
                document.close()
    if kind in ("png", "jpeg"):
        _open_image(data)
        return 1
    raise AttachmentRenderError("只支持 PDF、PNG、JPG 扫描件")


def _open_image(data: bytes):
    from PIL import Image
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as error:
        raise AttachmentRenderError(f"图片无法读取（{type(error).__name__}）") from error
    return image


def watermark_font_path() -> str | None:
    configured = os.environ.get("ICG_WATERMARK_FONT", "").strip()
    if configured:
        return configured if os.path.isfile(configured) else None
    return next((path for path in FONT_CANDIDATES if os.path.isfile(path)), None)


def _watermark(image, text: str):
    from PIL import Image, ImageDraw, ImageFont
    path = watermark_font_path()
    if path is None:
        raise AttachmentRenderError("找不到可写中文水印的字体，请安装黑体或设置 ICG_WATERMARK_FONT")
    base = image.convert("RGBA")
    size = max(24, int(min(base.size) / 14))
    font = ImageFont.truetype(path, size)
    box = font.getbbox(text)
    tile_w, tile_h = box[2] - box[0] + size * 3, box[3] - box[1] + size * 4
    side = int(math.hypot(*base.size)) + tile_w
    layer = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for row, y in enumerate(range(0, side, tile_h)):
        for x in range(-(row % 2) * tile_w // 2, side, tile_w):
            draw.text((x, y), text, font=font, fill=(200, 30, 30, 70))
    if layer.getbbox() is None:  # 字体里没有这些字形时 Pillow 什么都不画，不能让敏感附件无水印地导出
        raise AttachmentRenderError(f"水印字体 {os.path.basename(path)} 不含水印文字的字形，请改用黑体等中文字体")
    layer = layer.rotate(30, resample=Image.BICUBIC)
    left, top = (side - base.size[0]) // 2, (side - base.size[1]) // 2
    base.alpha_composite(layer.crop((left, top, left + base.size[0], top + base.size[1])))
    return base.convert("RGB")


def _encode(image) -> PageImage:
    from PIL import Image
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    if max(image.size) > MAX_SIDE_PX:
        image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.LANCZOS)
    out = BytesIO()
    image.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return PageImage(out.getvalue(), "jpeg", image.size[0], image.size[1])


def render_pages(data: bytes, first: int, last: int, watermark: str | None, label: str) -> list[PageImage]:
    """把第 first～last 页（从 1 起）转成可插入的页面图片；敏感附件带水印。"""
    kind = sniff(data)
    images = []
    if kind == "pdf":
        import pypdfium2 as pdfium
        with _PDFIUM_LOCK:
            try:
                document = pdfium.PdfDocument(data)
            except Exception as error:
                raise AttachmentRenderError(f"附件“{label}”的 PDF 无法打开") from error
            try:
                total = len(document)
                if first < 1 or last < first or last > total:
                    raise AttachmentRenderError(f"附件“{label}”只有 {total} 页，指定的第 {first}～{last} 页超出范围")
                for number in range(first, last + 1):
                    try:
                        page = document[number - 1]
                        images.append(page.render(scale=RENDER_DPI / 72).to_pil())
                        page.close()
                    except Exception as error:
                        raise AttachmentRenderError(f"附件“{label}”第 {number} 页无法渲染") from error
            finally:
                document.close()
    elif kind in ("png", "jpeg"):
        if (first, last) != (1, 1):
            raise AttachmentRenderError(f"附件“{label}”是单张图片，页码范围只能是第 1 页")
        try:
            images.append(_open_image(data))
        except AttachmentRenderError as error:
            raise AttachmentRenderError(f"附件“{label}”{error}") from error
    else:
        raise AttachmentRenderError(f"附件“{label}”不是 PDF、PNG 或 JPG 文件")
    result = []
    for number, image in zip(range(first, last + 1), images):
        try:
            result.append(_encode(_watermark(image, watermark) if watermark else image))
        except AttachmentRenderError as error:
            raise AttachmentRenderError(f"附件“{label}”第 {number} 页：{error}") from error
    return result


def drawing(rid: str, number: int, image: PageImage, max_width_cm: float, max_height_cm: float) -> str:
    """一张页面图片：居中独占一段，按正文宽度与页高等比缩放。"""
    ratio = min(max_width_cm / (image.width_px / RENDER_DPI * 2.54), max_height_cm / (image.height_px / RENDER_DPI * 2.54), 1.0)
    cx = int(image.width_px / RENDER_DPI * 2.54 * ratio * EMU_PER_CM)
    cy = int(image.height_px / RENDER_DPI * 2.54 * ratio * EMU_PER_CM)
    name = f"attachment-{number}"
    return ('<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{1000 + number}" name="{escape(name)}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{1000 + number}" name="{escape(name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
