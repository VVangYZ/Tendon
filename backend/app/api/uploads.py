"""上传文件的统一大小限制。"""

from fastapi import HTTPException, UploadFile


# 公测环境不接收超过 5 MiB 的单个文件，避免异常上传占用服务资源。
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_READ_CHUNK_BYTES = 1024 * 1024


async def read_limited_upload(file: UploadFile) -> bytes:
    """分块读取上传内容，超过上限立即拒绝。"""
    chunks: list[bytes] = []
    total = 0

    while chunk := await file.read(_READ_CHUNK_BYTES):
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="上传文件不能超过 5 MB")
        chunks.append(chunk)

    return b"".join(chunks)
