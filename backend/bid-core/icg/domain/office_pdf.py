# 为什么有这个文件：RAGFlow 只对 PDF（和表格）使用 DeepDOC 版面识别，.doc / .docx 只有文字、没有页码位置。
# 它解决什么问题：招标文件经常是老版 Word。先转成 PDF 再上传，DeepDOC 才能按页还原文字和位置。

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

log = logging.getLogger(__name__)

CONVERT_FAILED = "这份 Word 没能转成 PDF，DeepDOC 无法按页识别版面。请安装 LibreOffice 或 Microsoft Word 后重试。"
_OLE = b"\xd0\xcf\x11\xe0"
_ZIP = b"PK\x03\x04"


def office_magic(suffix: str, data: bytes) -> bool:
    """只有真实 Word 二进制或 docx 压缩包才转换。测试里的纯文本假文件保持原样。"""
    if suffix == ".doc":
        return data.startswith(_OLE)
    if suffix == ".docx":
        return data.startswith(_ZIP)
    return False


def prepare_for_deepdoc(filename: str, data: bytes) -> tuple[str, bytes] | str | None:
    """Word 原件转为 PDF。None 表示不是 Word，调用方仍上传原件。字符串是失败说明。"""
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".doc", ".docx"} or not office_magic(suffix, data):
        return None
    pdf = convert_office_to_pdf(data, suffix)
    if not pdf:
        return CONVERT_FAILED
    stem = PurePosixPath(filename).stem or "tender"
    return f"{stem}.pdf", pdf


def convert_office_to_pdf(data: bytes, suffix: str) -> bytes | None:
    with tempfile.TemporaryDirectory(prefix="icg-office-") as folder:
        directory = Path(folder)
        source = directory / f"source{suffix}"
        source.write_bytes(data)
        target = directory / "source.pdf"
        if _libreoffice(source, directory) and target.is_file() and target.stat().st_size > 0:
            return target.read_bytes()
        if sys.platform == "win32" and _word(source, target) and target.is_file() and target.stat().st_size > 0:
            return target.read_bytes()
        return None


def _soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path("/usr/bin/soffice"),
        Path("/usr/lib/libreoffice/program/soffice"),
    )
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def _libreoffice(source: Path, directory: Path) -> bool:
    binary = _soffice()
    if not binary:
        return False
    profile = directory / "lo-profile"
    try:
        result = subprocess.run(
            [binary, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore",
             "--convert-to", "pdf", "--outdir", str(directory), str(source)],
            timeout=180, capture_output=True, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("libreoffice pdf conversion failed: %s", type(exc).__name__)
        return False
    if result.returncode != 0:
        log.warning("libreoffice pdf conversion exited %s", result.returncode)
        return False
    return True


def _word(source: Path, target: Path) -> bool:
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$word = New-Object -ComObject Word.Application; "
        "try { "
        "$word.Visible = $false; $word.DisplayAlerts = 0; "
        "$doc = $word.Documents.Open($env:ICG_OFFICE_SRC, $false, $true); "
        "$doc.ExportAsFixedFormat($env:ICG_OFFICE_PDF, 17); "
        "$doc.Close($false) "
        "} finally { $word.Quit() }"
    )
    env = os.environ.copy()
    env["ICG_OFFICE_SRC"] = str(source)
    env["ICG_OFFICE_PDF"] = str(target)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            timeout=180, capture_output=True, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("word pdf conversion failed: %s", type(exc).__name__)
        return False
    if result.returncode != 0:
        log.warning("word pdf conversion exited %s", result.returncode)
        return False
    return True
