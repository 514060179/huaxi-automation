from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

try:
    import oss2
except Exception:  # pragma: no cover - exercised when dependency is missing
    oss2 = None


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OssDeleteResult:
    prefix: str
    deleted_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class OssClient:
    def __init__(
        self,
        *,
        access_key_id: str,
        access_key_secret: str,
        bucket_name: str,
        endpoint: str,
    ) -> None:
        if oss2 is None:
            raise RuntimeError("oss2 is not installed")
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(
            auth,
            endpoint,
            bucket_name,
            proxies={"http": None, "https": None},
        )

    def delete_prefix(self, prefix: str) -> OssDeleteResult:
        if not prefix.endswith("/"):
            prefix += "/"
        deleted = 0
        try:
            result = self.bucket.list_objects(prefix=prefix)
            for obj in result.object_list:
                if obj.key.endswith("/"):
                    continue
                self.bucket.delete_object(obj.key)
                deleted += 1
            return OssDeleteResult(prefix=prefix, deleted_count=deleted)
        except Exception as exc:
            return OssDeleteResult(
                prefix=prefix,
                deleted_count=deleted,
                error=f"{type(exc).__name__}: {exc}",
            )

    def upload_text(self, key: str, content: str) -> None:
        logger.info("OSS 上传开始：%s", key)
        try:
            self.bucket.put_object(key, content.encode("utf-8"))
        except Exception:
            logger.exception("OSS 上传失败：%s", key)
            raise
        logger.info("OSS 上传成功：%s", key)

    def upload_file(self, file_path: Path, key: str) -> None:
        logger.info("OSS 上传文件开始：%s -> %s", file_path, key)
        try:
            self.bucket.put_object_from_file(key, str(file_path))
        except Exception:
            logger.exception("OSS 上传文件失败：%s", key)
            raise
        logger.info("OSS 上传文件成功：%s", key)


def account_oss_prefix(account_dir: str, id_card: str) -> str:
    base = Path(account_dir)
    return str(base / id_card)
