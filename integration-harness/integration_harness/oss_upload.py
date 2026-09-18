from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import oss2


@dataclass(frozen=True)
class OssUploadResult:
    key: str
    success: bool
    error: str | None = None


class OssAccountUploader:
    def __init__(
        self,
        *,
        access_key_id: str,
        access_key_secret: str,
        bucket_name: str,
        endpoint: str,
    ) -> None:
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)

    def upload_file(self, file_path: Path, key: str) -> OssUploadResult:
        try:
            self.bucket.put_object_from_file(key, str(file_path))
            return OssUploadResult(key=key, success=True)
        except oss2.exceptions.OssError as exc:
            return OssUploadResult(key=key, success=False, error=str(exc))
        except Exception as exc:
            return OssUploadResult(
                key=key,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def upload_text(self, key: str, content: str = "") -> OssUploadResult:
        try:
            self.bucket.put_object(key, content.encode("utf-8"))
            return OssUploadResult(key=key, success=True)
        except oss2.exceptions.OssError as exc:
            return OssUploadResult(key=key, success=False, error=str(exc))
        except Exception as exc:
            return OssUploadResult(
                key=key,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def upload_bytes(self, key: str, content: bytes) -> OssUploadResult:
        try:
            self.bucket.put_object(key, content)
            return OssUploadResult(key=key, success=True)
        except oss2.exceptions.OssError as exc:
            return OssUploadResult(key=key, success=False, error=str(exc))
        except Exception as exc:
            return OssUploadResult(
                key=key,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
