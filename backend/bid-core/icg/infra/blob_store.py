# 为什么有这个文件：上传原件（招标文件等）按内容摘要存到磁盘，业务状态里只记摘要。
# 它解决什么问题：原件原先以 bytes 存在项目工作流 JSON 里；100MB 文件 base64 后超过 MySQL 默认
# max_allowed_packet（64MB），每次事务还要深拷贝整份原件。改为内容寻址文件存储：同一文件只存一份，可离线部署。
# 目录由 ICG_BLOB_DIR 指定；未设置时用 backend/bid-core/data/blobs（已加入 .gitignore）。生产部署须指到持久磁盘并纳入备份。

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "blobs"


def blob_dir() -> Path:
    return Path(os.environ.get("ICG_BLOB_DIR") or _DEFAULT)


def _path(digest: str) -> Path:
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid blob digest")
    return blob_dir() / digest[:2] / digest


def put_blob(data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    target = _path(digest)
    if target.exists() and target.stat().st_size == len(data):
        return digest
    target.parent.mkdir(parents=True, exist_ok=True)
    # 先写临时文件再改名，进程中断不会留下半个文件
    fd, temp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return digest


def get_blob(digest: str) -> bytes:
    path = _path(digest)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise IOError("blob content does not match its digest")
    return data


def file_bytes(record: dict) -> bytes:
    """招标文件记录的原件：新记录读文件存储，旧记录（内联 content）照常读取。"""
    if record.get("content") is not None:
        return record["content"]
    return get_blob(record["blob"])
