from __future__ import annotations

from typing import Any, Optional

import requests

from constant import BilibiliAPI as APIConst, HttpHeader
from error_code import APIError
from models import AudioStreamInfo, Track, VideoDetail, VideoInfo, normalize_bvid
from track_service import normalize_search_item, normalize_video_detail


QUALITY_ORDER = {
    "auto": [],
    "high": [30280, 30232, 30216],
    "standard": [30232, 30216, 30280],
}


class BiliClient:
    SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HttpHeader.default_headers())

    @staticmethod
    def is_valid_bvid(bvid: str) -> bool:
        return bool(APIConst.BV_PATTERN.match((bvid or "").strip()))

    @staticmethod
    def extract_bvid(url: str) -> Optional[str]:
        match = APIConst.URL_PATTERN.search((url or "").strip())
        return normalize_bvid(match.group(3)) if match else None

    @staticmethod
    def parse_input(input_str: str) -> Optional[str]:
        value = (input_str or "").strip()
        if BiliClient.is_valid_bvid(value):
            return normalize_bvid(value)
        return BiliClient.extract_bvid(value)

    def search(self, keyword: str, page: int = 1, page_size: int = 20) -> list[Track]:
        keyword = (keyword or "").strip()
        if not keyword:
            raise APIError.validation_error("keyword is required")

        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": max(page, 1),
            "page_size": min(max(page_size, 1), 50),
        }
        try:
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                headers=HttpHeader.search_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise APIError.request_timeout(keyword)
        except requests.HTTPError as exc:
            raise self._http_error(exc, "search")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        payload = self._json_payload(response, "search")
        if payload.get("code") != 0:
            raise APIError.api_error(payload.get("message") or "Bilibili search failed")

        result_items = payload.get("data", {}).get("result") or []
        return [normalize_search_item(item) for item in result_items if item.get("bvid")]

    def get_video_detail(self, bvid: str) -> VideoDetail:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        try:
            response = self.session.get(
                APIConst.VIDEO_INFO_URL,
                params={"bvid": normalize_bvid(bvid)},
                headers=HttpHeader.video_headers(normalize_bvid(bvid)),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.HTTPError as exc:
            raise self._http_error(exc, "video detail")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        payload = self._json_payload(response, "video detail")
        if payload.get("code") != 0:
            if payload.get("code") == -400:
                raise APIError.video_not_found(bvid)
            raise APIError.api_error(payload.get("message") or "Bilibili detail failed")

        return normalize_video_detail(payload.get("data") or {})

    def get_video_info(self, bvid: str) -> VideoInfo:
        return self.get_video_detail(bvid).info

    def get_audio_stream(
        self,
        bvid: str,
        cid: int,
        quality: str = "auto",
    ) -> AudioStreamInfo:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)
        if not cid:
            raise APIError.validation_error("cid is required")

        params = {
            "bvid": normalize_bvid(bvid),
            "cid": int(cid),
            "qn": 16,
            "fnval": 16,
            "fnver": 0,
            "fourk": 0,
        }
        try:
            response = self.session.get(
                APIConst.PLAY_URL,
                params=params,
                headers=HttpHeader.video_headers(normalize_bvid(bvid)),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.HTTPError as exc:
            raise self._http_error(exc, "playurl")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        payload = self._json_payload(response, "playurl")
        if payload.get("code") != 0:
            raise APIError.api_error(payload.get("message") or "Bilibili playurl failed")

        play_data = payload.get("data") or {}
        dash_data = play_data.get("dash") or {}
        audio_streams = dash_data.get("audio") or []
        if not dash_data:
            raise APIError.no_dash_stream()
        if not audio_streams:
            raise APIError.no_audio_stream()

        selected = self._select_audio_stream(audio_streams, quality)
        stream_id = selected.get("id")
        bitrate = int(selected.get("bandwidth") or 0)
        actual_quality = self._quality_label(stream_id, bitrate)
        requested_quality = quality if quality in QUALITY_ORDER else "auto"
        codec = self._codec_label(selected.get("codecs"))
        fallback = requested_quality != "auto" and requested_quality != actual_quality

        return AudioStreamInfo(
            url=selected.get("baseUrl") or selected.get("base_url") or "",
            backup_urls=selected.get("backupUrl") or selected.get("backup_url") or [],
            duration=int(play_data.get("timelength") or 0) // 1000,
            bitrate=bitrate,
            sample_rate=int(selected.get("sampleRate") or 44100),
            channels=int(selected.get("channel") or 2),
            init_range=(selected.get("segmentBase") or {}).get("initialization", ""),
            index_range=(selected.get("segmentBase") or {}).get("indexRange", ""),
            quality=requested_quality,
            actual_quality=actual_quality,
            codec=codec,
            fallback=fallback,
            stream_id=int(stream_id) if stream_id is not None else None,
        )

    def get_video_with_audio(self, input_str: str) -> tuple[VideoInfo, AudioStreamInfo]:
        bvid = self.parse_input(input_str)
        if not bvid:
            raise APIError.validation_error("Cannot parse BVID from input")
        video_info = self.get_video_info(bvid)
        return video_info, self.get_audio_stream(bvid, video_info.cid)

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _select_audio_stream(audio_streams: list[dict[str, Any]], quality: str) -> dict[str, Any]:
        normalized = quality if quality in QUALITY_ORDER else "auto"
        if normalized == "auto":
            return max(audio_streams, key=lambda item: int(item.get("bandwidth") or 0))

        by_id = {int(item.get("id") or 0): item for item in audio_streams}
        for stream_id in QUALITY_ORDER[normalized]:
            if stream_id in by_id:
                return by_id[stream_id]
        return max(audio_streams, key=lambda item: int(item.get("bandwidth") or 0))

    @staticmethod
    def _quality_label(stream_id: Any, bitrate: int) -> str:
        try:
            sid = int(stream_id)
        except (TypeError, ValueError):
            sid = 0
        if sid >= 30280 or bitrate >= 160000:
            return "high"
        if sid >= 30232 or bitrate >= 96000:
            return "standard"
        return "low"

    @staticmethod
    def _codec_label(codecs: Any) -> str:
        value = str(codecs or "").lower()
        if "mp4a" in value:
            return "aac"
        if value:
            return value
        return "aac"

    @staticmethod
    def _json_payload(response: requests.Response, context: str) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            content_type = response.headers.get("content-type", "unknown")
            raise APIError.api_error(
                f"Bilibili {context} returned non-JSON response: "
                f"status={response.status_code}, content_type={content_type}"
            )
        if not isinstance(payload, dict):
            raise APIError.api_error(f"Bilibili {context} returned invalid JSON payload")
        return payload

    @staticmethod
    def _http_error(exc: requests.HTTPError, context: str) -> APIError:
        response = exc.response
        if response is None:
            return APIError.api_error(f"Bilibili {context} HTTP error: {exc}")
        return APIError.api_error(
            f"Bilibili {context} HTTP {response.status_code}: {response.reason}"
        )


BilibiliAPI = BiliClient
