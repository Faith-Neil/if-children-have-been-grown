# 为什么有这个文件：全应用统一的上传大小上限（用户 2026-10-29 决定：招标文件与知识库原件单个最大 100MB）。
# 它解决什么问题：原先招标文件 5MB、知识库 50MB、前端各写一份，真实扫描件（几十 MB）传不上去；
# 现在只在这里定一个数，部署方可用 ICG_MAX_UPLOAD_MB 调整。

from __future__ import annotations

import os

DEFAULT_MAX_UPLOAD_MB = 100


def max_upload_mb() -> int:
    try:
        value = int(os.environ.get("ICG_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
    except ValueError:
        value = DEFAULT_MAX_UPLOAD_MB
    return max(1, min(value, 1024))


def max_upload_bytes() -> int:
    return max_upload_mb() * 1024 * 1024


def max_base64_chars() -> int:
    """JSON + base64 上传通道的长度上限（原文件上限的 4/3，留出余量）。"""
    return max_upload_bytes() * 4 // 3 + 16


def too_large_message() -> str:
    return f"文件须有内容且不超过 {max_upload_mb()}MB。"
