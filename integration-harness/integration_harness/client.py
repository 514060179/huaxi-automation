from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .config import Config


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class VideoDownloadError(ApiError):
    def __init__(
        self,
        message: str,
        *,
        already_notified: bool = False,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            response_text=response_text,
        )
        self.already_notified = already_notified


class HxaccClient:
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 "
        "Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) "
        "NetType/WIFI MiniProgramEnv/Mac MacWechat/WMPF "
        "MacWechat/3.8.7(0x13080712) UnifiedPCMacWechat(0xf2641d22) "
        "XWEB/25511"
    )
    referer = "https://servicewechat.com/wxf54d0921ad811ae5/167/page-frame.html"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_headers = {
            "User-Agent": self.user_agent,
            "Referer": self.referer,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
        }
        self.learn_headers = {
            **self.base_headers,
            "Cookie": f"sid={config.token};deviceId={config.device_id}",
        }
        self.www_headers = {
            **self.base_headers,
            "Authorization": f"Bearer {config.token}",
        }
        self.video_headers = {
            **self.base_headers,
            "Priority": "u=1, i",
        }
        self.client = httpx.Client(timeout=30.0, verify=self.config.ssl_verify)

    def close(self) -> None:
        self.client.close()

    def _raise_for_status(
        self,
        response: httpx.Response,
        *,
        context: str,
    ) -> None:
        if response.status_code >= 400:
            raise ApiError(
                f"{context} failed with HTTP {response.status_code}",
                status_code=response.status_code,
                response_text=response.text[:500],
            )

    def post_learn_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.learn_base_url}{path}"
        response = self.client.post(
            url,
            json=payload,
            headers={
                **self.learn_headers,
                "Content-Type": "application/json",
                "xweb_xhr": "1",
            },
        )
        self._raise_for_status(response, context=f"POST {path}")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(
                f"POST {path} returned non-JSON body",
                status_code=response.status_code,
                response_text=response.text[:500],
            ) from exc

    def post_www_form(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.www_base_url}{path}"
        response = self.client.post(
            url,
            data=payload,
            headers={
                **self.www_headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "xweb_xhr": "1",
            },
        )
        self._raise_for_status(response, context=f"POST {path}")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(
                f"POST {path} returned non-JSON body",
                status_code=response.status_code,
                response_text=response.text[:500],
            ) from exc

    def get_video_bytes(self, url: str, *, retries: int = 5) -> bytes:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = self.client.get(url, headers=self.video_headers)
                self._raise_for_status(response, context="GET video segment")
                return response.content
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(min(1.0 * attempt, 3.0))
                    continue

        raise ApiError(
            f"GET video segment failed after {retries} attempts: {last_error}",
            status_code=getattr(last_error, "status_code", None),
            response_text=str(last_error)[:300],
        )
