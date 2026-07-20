from __future__ import annotations

import threading
import time
from typing import Optional

import requests

from bili_client import BiliClient
from constant import HttpHeader, Stream
from error_code import APIError
from models import AudioStreamInfo, normalize_bvid


class StreamService:
    def __init__(self, bili_client: BiliClient, cache_ttl_seconds: int = 20 * 60):
        self.bili_client = bili_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, AudioStreamInfo]] = {}
        self._aliases: dict[str, str] = {}
        self._lock = threading.Lock()
        self._stats = {
            "total_bytes": 0,
            "start_time": None,
            "current_session_bytes": 0,
        }

    def get_audio_info(
        self,
        bvid: str,
        cid: Optional[int] = None,
        quality: str = "auto",
    ) -> AudioStreamInfo:
        resolved_cid = cid or self.bili_client.get_video_info(bvid).cid
        alias_key = self._alias_key(bvid, resolved_cid, quality)
        cached = self._get_cached(alias_key)
        if cached:
            return cached

        audio_info = self.bili_client.get_audio_stream(bvid, resolved_cid, quality=quality)
        full_key = f"{alias_key}:{audio_info.stream_identity}"
        with self._lock:
            self._cache[full_key] = (time.time(), audio_info)
            self._aliases[alias_key] = full_key
        return audio_info

    def proxy_stream(
        self,
        bvid: str,
        cid: Optional[int] = None,
        quality: str = "auto",
    ):
        from flask import Response, request

        audio_info = self.get_audio_info(bvid, cid, quality)
        headers = HttpHeader.stream_headers(bvid)
        range_header = request.headers.get("Range")
        if range_header:
            headers["Range"] = range_header

        try:
            upstream = requests.get(
                audio_info.url,
                headers=headers,
                stream=True,
                timeout=Stream.TIMEOUT,
            )
        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        def generate():
            for chunk in upstream.iter_content(chunk_size=Stream.CHUNK_SIZE):
                if chunk:
                    yield chunk
                    with self._lock:
                        self._stats["total_bytes"] += len(chunk)
                        self._stats["current_session_bytes"] += len(chunk)

        response_headers = self._proxy_response_headers(upstream)
        return Response(generate(), status=upstream.status_code, headers=response_headers)

    def get_stats(self) -> dict[str, float | int | None]:
        with self._lock:
            stats = self._stats.copy()
        elapsed = time.time() - stats["start_time"] if stats["start_time"] else 0
        speed = stats["current_session_bytes"] / elapsed if elapsed > 0 else 0
        return {
            "total_bytes": stats["total_bytes"],
            "session_bytes": stats["current_session_bytes"],
            "elapsed_seconds": elapsed,
            "bytes_per_second": speed,
            "total_mb": round(stats["total_bytes"] / 1024 / 1024, 2),
            "session_mb": round(stats["current_session_bytes"] / 1024 / 1024, 2),
        }

    def reset_stats(self) -> None:
        with self._lock:
            self._stats["total_bytes"] = 0
            self._stats["current_session_bytes"] = 0
            self._stats["start_time"] = time.time()

    def _get_cached(self, alias_key: str) -> Optional[AudioStreamInfo]:
        with self._lock:
            full_key = self._aliases.get(alias_key)
            if not full_key:
                return None
            created_at, audio_info = self._cache.get(full_key, (0, None))
            if not audio_info:
                return None
            if time.time() - created_at > self.cache_ttl_seconds:
                self._cache.pop(full_key, None)
                self._aliases.pop(alias_key, None)
                return None
            return audio_info

    @staticmethod
    def _alias_key(bvid: str, cid: int, quality: str) -> str:
        return f"{normalize_bvid(bvid)}:{int(cid)}:{quality or 'auto'}"

    @staticmethod
    def _proxy_response_headers(upstream: requests.Response) -> dict[str, str]:
        headers = {}
        for name in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
            if name in upstream.headers:
                headers[name] = upstream.headers[name]
        headers.setdefault("Accept-Ranges", HttpHeader.ACCEPT_RANGES)
        return headers
