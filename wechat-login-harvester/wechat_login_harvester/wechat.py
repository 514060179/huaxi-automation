from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import httpx


class WeChatNotifier:
    """Send failure messages to a WeCom group-robot webhook."""

    def __init__(
        self,
        webhook_url: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 5,
        outbox_path: Path | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.max_retries = max_retries
        self.outbox_path = outbox_path
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def send_failure(
        self,
        title: str,
        *,
        details: dict[str, str] | None = None,
    ) -> bool:
        lines = [
            f"⚠️ {title}",
            "",
            f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        ]
        for key, value in (details or {}).items():
            lines.append(f"{key}：{value}")
        content = "\n".join(lines)
        if self._post_with_retries(content):
            return True
        self._append_outbox(content)
        return False

    def _post_with_retries(self, content: str) -> bool:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.post(
                    self.webhook_url,
                    json={
                        "msgtype": "text",
                        "text": {"content": content},
                    },
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError:
                if attempt < self.max_retries:
                    time.sleep(min(2.0 * attempt, 10.0))
                    continue
        return False

    def _append_outbox(self, content: str) -> None:
        if self.outbox_path is None:
            return
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        with self.outbox_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps({"content": content}, ensure_ascii=False) + "\n")

