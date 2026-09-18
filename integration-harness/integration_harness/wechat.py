from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import httpx


class WeChatNotifier:
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

    def send_markdown(self, content: str) -> bool:
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

    def flush_outbox(self) -> int:
        if self.outbox_path is None or not self.outbox_path.exists():
            return 0

        lines = self.outbox_path.read_text(encoding="utf-8").splitlines()
        remaining: list[str] = []
        sent = 0
        for line in lines:
            try:
                payload = json.loads(line)
                content = payload.get("content")
            except json.JSONDecodeError:
                continue
            if not isinstance(content, str):
                continue
            if self._post_with_retries(content):
                sent += 1
            else:
                remaining.append(line)

        if remaining:
            self.outbox_path.write_text(
                "\n".join(remaining) + ("\n" if remaining else ""),
                encoding="utf-8",
            )
        else:
            self.outbox_path.unlink(missing_ok=True)
        return sent

    def send_exception(
        self,
        *,
        app_id: str,
        token_prefix: str,
        device_id: str,
        session_id: str,
        exc: Exception,
        id_card: str = "",
        name: str = "",
    ) -> bool:
        content = "\n".join(
            [
                "⚠️ 华夏会计网集成测试异常",
                "",
                f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"appId：{app_id}",
                f"idCard：{id_card}",
                f"姓名：{name}",
                f"token前缀：{token_prefix}",
                f"deviceId：{device_id}",
                f"会话ID：{session_id}",
                f"异常类型：{type(exc).__name__}",
                f"异常信息：{exc}",
            ]
        )
        return self.send_markdown(content)

    def send_video_download_failed(
        self,
        *,
        app_id: str,
        token_prefix: str,
        device_id: str,
        session_id: str,
        url: str,
        attempts: int,
        exc: Exception,
        id_card: str = "",
        name: str = "",
    ) -> bool:
        content = "\n".join(
            [
                "⚠️ 视频下载失败预警",
                "",
                f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"appId：{app_id}",
                f"idCard：{id_card}",
                f"姓名：{name}",
                f"token前缀：{token_prefix}",
                f"deviceId：{device_id}",
                f"会话ID：{session_id}",
                f"重试次数：{attempts}",
                f"视频地址：{url}",
                f"最后异常：{exc}",
            ]
        )
        return self.send_markdown(content)

    def send_daily_limit(
        self,
        *,
        app_id: str,
        token_prefix: str,
        device_id: str,
        session_id: str,
        message: str,
        id_card: str = "",
        name: str = "",
    ) -> bool:
        content = "\n".join(
            [
                "⏹️ 学习时长已达今日上限",
                "",
                f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"appId：{app_id}",
                f"idCard：{id_card}",
                f"姓名：{name}",
                f"token前缀：{token_prefix}",
                f"deviceId：{device_id}",
                f"会话ID：{session_id}",
                f"接口消息：{message}",
                "",
                "系统已停止继续学习。",
            ]
        )
        return self.send_markdown(content)

    def send_course_completed(
        self,
        *,
        app_id: str,
        token_prefix: str,
        device_id: str,
        session_id: str,
        course_title: str,
        course_id: str,
        id_card: str = "",
        name: str = "",
    ) -> bool:
        content = "\n".join(
            [
                "✅ 课程学习完成",
                "",
                f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"appId：{app_id}",
                f"idCard：{id_card}",
                f"姓名：{name}",
                f"token前缀：{token_prefix}",
                f"deviceId：{device_id}",
                f"会话ID：{session_id}",
                f"课程：{course_title}",
                f"courseId：{course_id}",
            ]
        )
        return self.send_markdown(content)

    def send_time_window_blocked(
        self,
        *,
        app_id: str,
        token_prefix: str,
        device_id: str,
        start_hour: int,
        end_hour: int,
        id_card: str = "",
        name: str = "",
    ) -> bool:
        content = "\n".join(
            [
                "⏰ 当前不在允许运行时间",
                "",
                f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"appId：{app_id}",
                f"idCard：{id_card}",
                f"姓名：{name}",
                f"token前缀：{token_prefix}",
                f"deviceId：{device_id}",
                f"允许运行时间：{start_hour:02d}:00 - {end_hour:02d}:00",
            ]
        )
        return self.send_markdown(content)
