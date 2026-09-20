from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import oss2
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        self.bucket = oss2.Bucket(
            auth,
            endpoint,
            bucket_name,
            proxies={"http": None, "https": None},
        )
        self.bucket.session.session.verify = False

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

    def list_prefixes(self, prefix: str) -> list[str]:
        result = self.bucket.list_objects(prefix=prefix, delimiter="/")
        return [
            item if isinstance(item, str) else item.prefix
            for item in result.prefix_list
        ]

    def object_exists(self, key: str) -> bool:
        return self.bucket.object_exists(key)

    def delete_object(self, key: str) -> OssUploadResult:
        try:
            self.bucket.delete_object(key)
            return OssUploadResult(key=key, success=True)
        except Exception as exc:
            return OssUploadResult(
                key=key,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
