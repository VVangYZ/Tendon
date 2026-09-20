"""上传文件大小限制测试。"""

import asyncio
from io import BytesIO
import unittest

from fastapi import HTTPException, UploadFile

from app.api.uploads import MAX_UPLOAD_BYTES, read_limited_upload


class UploadLimitTest(unittest.TestCase):
    """确保精确上限可用，超出上限会被服务端拒绝。"""

    def test_accepts_file_at_limit(self) -> None:
        file = UploadFile(filename="at-limit.dxf", file=BytesIO(b"x" * MAX_UPLOAD_BYTES))

        content = asyncio.run(read_limited_upload(file))

        self.assertEqual(len(content), MAX_UPLOAD_BYTES)

    def test_rejects_file_larger_than_limit(self) -> None:
        file = UploadFile(filename="too-large.dxf", file=BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)))

        with self.assertRaises(HTTPException) as context:
            asyncio.run(read_limited_upload(file))

        self.assertEqual(context.exception.status_code, 413)
