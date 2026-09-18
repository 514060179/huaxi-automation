from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass(frozen=True)
class HlsSegment:
    url: str
    duration: float


def choose_m3u8_url(doc_info: dict, quality: str = "FD") -> str:
    source = doc_info.get("source")
    if isinstance(source, dict):
        for candidate in [quality, "LD", "SD", "HD", "FD"]:
            url = source.get(candidate)
            if isinstance(url, str) and url:
                return url

    body = doc_info.get("body")
    if isinstance(body, list):
        for item in body:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            url = item.get("object")
            if item_type == quality and isinstance(url, str) and url:
                return url
        for fallback_quality in ["LD", "SD", "HD", "FD"]:
            for item in body:
                if isinstance(item, dict) and item.get("type") == fallback_quality:
                    url = item.get("object")
                    if isinstance(url, str) and url:
                        return url

    raise RuntimeError("docInfo 中未找到可用的 m3u8 URL")


def parse_m3u8(content: str, base_url: str) -> list[HlsSegment]:
    segments: list[HlsSegment] = []
    duration: float | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if line.startswith("#EXTINF:"):
                value = line.split(":", 1)[1].split(",", 1)[0]
                try:
                    duration = float(value)
                except ValueError:
                    duration = None
            continue

        segment_url = urljoin(base_url, line)
        segments.append(HlsSegment(url=segment_url, duration=duration or 10.0))
        duration = None

    return segments
