# 为什么有这个文件：大文件以二进制请求体直接上传（Content-Type: application/octet-stream），文件名放在查询参数。
# 它解决什么问题：100MB 原件走 JSON + base64 要多出三分之一体积，浏览器还要先拼出上百 MB 的字符串；
# 不引入 multipart 依赖（内网离线部署），边读边计数，超过上限立即 413，不把超大请求读进内存。

from __future__ import annotations

from fastapi import Request

from icg.domain.domain import DomainError
from icg.domain.upload_limits import max_upload_bytes, too_large_message

RAW_BODY_DOC = {
    "requestBody": {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}},
}


async def read_limited_body(request: Request) -> bytes:
    limit = max_upload_bytes()
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise DomainError(413, "FILE_SIZE_LIMIT", too_large_message())
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise DomainError(413, "FILE_SIZE_LIMIT", too_large_message())
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise DomainError(422, "VALIDATION_ERROR", "文件为空。")
    return data
