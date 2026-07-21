from __future__ import annotations

from typing import Any, Callable, Optional

import requests

from constant import BilibiliAPI as APIConst, HttpHeader
from error_code import APIError
from models import AudioStreamInfo, FavoriteFolder, Track, VideoDetail, VideoInfo, normalize_bvid
from track_service import (
    cover_info_from_video_data,
    normalize_favorite_folder,
    normalize_favorite_media_item,
    normalize_player_chapters,
    normalize_player_subtitles,
    normalize_reply_comments,
    normalize_search_item,
    normalize_subtitle_lines,
    normalize_user_profile,
    normalize_video_detail,
    normalize_video_intro,
)


QUALITY_ORDER = {
    "auto": [],
    "high": [30280, 30232, 30216],
    "standard": [30232, 30216, 30280],
}


class BiliClient:
    SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
    HOME_URL = "https://www.bilibili.com/"

    def __init__(
        self,
        timeout: int = 10,
        cookie_provider: Optional[Callable[[], Optional[str]]] = None,
    ):
        self.timeout = timeout
        self.cookie_provider = cookie_provider
        self.session = requests.Session()
        self.session.headers.update(HttpHeader.default_headers())
        self._guest_cookie_ready = False

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
        response = self._request_search(params, keyword)
        payload = self._json_payload(response, "search")
        if payload.get("code") == -412:
            self._ensure_guest_cookies(force=True)
            response = self._request_search(params, keyword)
            payload = self._json_payload(response, "search")

        if payload.get("code") != 0:
            raise APIError.api_error(payload.get("message") or "Bilibili search failed")

        result_items = payload.get("data", {}).get("result") or []
        return [normalize_search_item(item) for item in result_items if item.get("bvid")]

    def get_video_detail(self, bvid: str) -> VideoDetail:
        return normalize_video_detail(self._get_video_detail_payload(bvid))

    def get_cover_info(self, bvid: str, cid: Optional[int] = None) -> dict[str, Any]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)
        payload = self._get_video_detail_payload(bvid)
        return cover_info_from_video_data(payload, cid=cid)

    def get_video_intro(self, bvid: str, cid: Optional[int] = None) -> dict[str, Any]:
        payload = self._get_video_detail_payload(bvid)
        return normalize_video_intro(payload, cid=cid)

    def get_track_subtitles(self, bvid: str, cid: Optional[int] = None) -> dict[str, Any]:
        resolved_bvid, resolved_cid = self._resolve_bvid_cid(bvid, cid)
        player_data = self._get_player_info_payload(resolved_bvid, resolved_cid)
        manifest = normalize_player_subtitles(player_data, resolved_bvid, resolved_cid)
        subtitles = manifest.get("subtitles") or []
        if not subtitles:
            return manifest

        selected = subtitles[0]
        subtitle_url = selected.get("url") or ""
        lines: list[dict[str, Any]] = []
        if subtitle_url:
            try:
                response = self.session.get(
                    subtitle_url,
                    headers=self._with_auth_cookie(HttpHeader.video_headers(resolved_bvid)),
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except requests.Timeout:
                raise APIError.request_timeout("subtitle")
            except requests.HTTPError as exc:
                raise self._http_error(exc, "subtitle")
            except requests.RequestException as exc:
                raise APIError.network_error(str(exc))
            lines = normalize_subtitle_lines(self._json_payload(response, "subtitle"))

        return normalize_player_subtitles(
            player_data,
            resolved_bvid,
            resolved_cid,
            lines=lines,
            selected_subtitle_id=selected.get("id"),
        )

    def get_track_chapters(self, bvid: str, cid: Optional[int] = None) -> dict[str, Any]:
        resolved_bvid, resolved_cid = self._resolve_bvid_cid(bvid, cid)
        return normalize_player_chapters(
            self._get_player_info_payload(resolved_bvid, resolved_cid),
            resolved_bvid,
            resolved_cid,
        )

    def get_track_comments(
        self,
        bvid: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        detail = self._get_video_detail_payload(bvid)
        aid = int(detail.get("aid") or 0)
        if aid <= 0:
            raise APIError.video_not_found(bvid)
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 20), 1), 50)
        try:
            response = self.session.get(
                APIConst.REPLY_MAIN_URL,
                params={
                    "type": 1,
                    "oid": aid,
                    "mode": 3,
                    "next": page - 1,
                    "ps": page_size,
                },
                headers=self._with_auth_cookie(HttpHeader.video_headers(normalize_bvid(bvid))),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise APIError.request_timeout("comments")
        except requests.HTTPError as exc:
            raise self._http_error(exc, "comments")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        payload = self._json_payload(response, "comments")
        if payload.get("code") != 0:
            raise APIError.api_error(payload.get("message") or "Bilibili comments failed")
        return normalize_reply_comments(payload, normalize_bvid(bvid), aid, page, page_size)

    def _get_video_detail_payload(self, bvid: str) -> dict[str, Any]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)

        try:
            response = self.session.get(
                APIConst.VIDEO_INFO_URL,
                params={"bvid": normalize_bvid(bvid)},
                headers=self._with_auth_cookie(HttpHeader.video_headers(normalize_bvid(bvid))),
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

        return payload.get("data") or {}

    def _resolve_bvid_cid(self, bvid: str, cid: Optional[int] = None) -> tuple[str, int]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)
        resolved_bvid = normalize_bvid(bvid)
        if cid:
            return resolved_bvid, int(cid)
        detail = self._get_video_detail_payload(resolved_bvid)
        resolved_cid = int(detail.get("cid") or 0)
        if resolved_cid <= 0:
            raise APIError.validation_error("cid is required")
        return resolved_bvid, resolved_cid

    def _get_player_info_payload(self, bvid: str, cid: int) -> dict[str, Any]:
        if not self.is_valid_bvid(bvid):
            raise APIError.invalid_bvid(bvid)
        if not cid:
            raise APIError.validation_error("cid is required")

        try:
            response = self.session.get(
                APIConst.PLAYER_INFO_URL,
                params={"bvid": normalize_bvid(bvid), "cid": int(cid)},
                headers=self._with_auth_cookie(HttpHeader.video_headers(normalize_bvid(bvid))),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise APIError.request_timeout(bvid)
        except requests.HTTPError as exc:
            raise self._http_error(exc, "player info")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

        payload = self._json_payload(response, "player info")
        if payload.get("code") != 0:
            raise APIError.api_error(payload.get("message") or "Bilibili player info failed")
        return payload.get("data") or {}

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
                headers=self._with_auth_cookie(HttpHeader.video_headers(normalize_bvid(bvid))),
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

    def get_authenticated_user(self) -> dict[str, Any]:
        response = self._authenticated_get(APIConst.NAV_URL, "Bilibili nav")
        payload = self._json_payload(response, "Bilibili nav")
        data = payload.get("data") or {}
        if payload.get("code") != 0 or not data.get("isLogin"):
            raise APIError.auth_required(payload.get("message") or "Bilibili login is required")
        return normalize_user_profile(data).to_dict()

    def list_favorite_folders(self, up_mid: Optional[int] = None) -> list[FavoriteFolder]:
        if not up_mid:
            user = self.get_authenticated_user()
            up_mid = int(user["mid"])

        response = self._authenticated_get(
            APIConst.FAVORITE_FOLDERS_URL,
            "favorite folders",
            params={"up_mid": int(up_mid)},
        )
        payload = self._json_payload(response, "favorite folders")
        if payload.get("code") != 0:
            if payload.get("code") == -101:
                raise APIError.auth_required("Bilibili login is required")
            raise APIError.api_error(payload.get("message") or "Bilibili favorite folders failed")

        folders = (payload.get("data") or {}).get("list") or []
        return [normalize_favorite_folder(item) for item in folders if item.get("id")]

    def list_favorite_tracks(
        self,
        media_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        media_id = int(media_id or 0)
        if media_id <= 0:
            raise APIError.validation_error("mediaId is required")
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 20), 1), 20)

        response = self._authenticated_get(
            APIConst.FAVORITE_RESOURCE_URL,
            "favorite resources",
            params={
                "media_id": media_id,
                "pn": page,
                "ps": page_size,
                "order": "mtime",
                "type": 0,
                "tid": 0,
                "platform": "web",
            },
        )
        payload = self._json_payload(response, "favorite resources")
        if payload.get("code") != 0:
            if payload.get("code") == -101:
                raise APIError.auth_required("Bilibili login is required")
            raise APIError.api_error(payload.get("message") or "Bilibili favorite resources failed")

        data = payload.get("data") or {}
        folder = normalize_favorite_folder(data.get("info") or {"id": media_id})
        medias = data.get("medias") or []
        tracks = []
        unavailable = 0
        for item in medias:
            track = normalize_favorite_media_item(item)
            if track:
                tracks.append(track)
            else:
                unavailable += 1

        return {
            "mediaId": media_id,
            "page": page,
            "pageSize": page_size,
            "hasMore": bool(data.get("has_more")),
            "total": folder.media_count,
            "unavailable": unavailable,
            "folder": folder.to_dict(),
            "tracks": [track.to_dict() for track in tracks],
        }

    def list_all_favorite_tracks(
        self,
        media_id: int,
        max_pages: int = 10,
        page_size: int = 20,
    ) -> dict[str, Any]:
        max_pages = min(max(int(max_pages or 1), 1), 50)
        page_size = min(max(int(page_size or 20), 1), 20)
        pages = []
        all_tracks = []
        unavailable = 0
        has_more = False
        folder = None

        for page in range(1, max_pages + 1):
            current = self.list_favorite_tracks(media_id, page=page, page_size=page_size)
            pages.append(page)
            folder = current["folder"]
            all_tracks.extend(Track.from_dict(track) for track in current["tracks"])
            unavailable += int(current.get("unavailable") or 0)
            has_more = bool(current.get("hasMore"))
            if not has_more:
                break

        return {
            "mediaId": int(media_id),
            "pagesFetched": pages,
            "pageSize": page_size,
            "maxPages": max_pages,
            "hasMore": has_more,
            "total": folder.get("mediaCount", 0) if folder else 0,
            "unavailable": unavailable,
            "folder": folder or {"mediaId": int(media_id), "title": ""},
            "tracks": all_tracks,
        }

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

    def _request_search(self, params: dict[str, Any], keyword: str) -> requests.Response:
        self._ensure_guest_cookies()
        try:
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                headers=HttpHeader.search_headers(),
                timeout=self.timeout,
            )
            if response.status_code == 412:
                self._ensure_guest_cookies(force=True)
                response = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    headers=HttpHeader.search_headers(),
                    timeout=self.timeout,
                )
            response.raise_for_status()
            return response
        except requests.Timeout:
            raise APIError.request_timeout(keyword)
        except requests.HTTPError as exc:
            raise self._http_error(exc, "search")
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

    def _authenticated_get(
        self,
        url: str,
        context: str,
        params: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        cookie = self.cookie_provider() if self.cookie_provider else None
        if not cookie:
            raise APIError.auth_required("Bilibili login is required")
        try:
            response = self.session.get(
                url,
                params=params,
                headers=self._with_auth_cookie(HttpHeader.default_headers()),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response
        except requests.Timeout:
            raise APIError.request_timeout(context)
        except requests.HTTPError as exc:
            raise self._http_error(exc, context)
        except requests.RequestException as exc:
            raise APIError.network_error(str(exc))

    def _ensure_guest_cookies(self, force: bool = False) -> None:
        if self._guest_cookie_ready and not force:
            return
        try:
            response = self.session.get(
                self.HOME_URL,
                headers=HttpHeader.default_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._guest_cookie_ready = True
        except requests.Timeout:
            raise APIError.request_timeout("bilibili guest cookie")
        except requests.RequestException as exc:
            raise APIError.network_error(f"Failed to warm Bilibili guest cookies: {exc}")

    def _with_auth_cookie(self, headers: dict[str, str]) -> dict[str, str]:
        cookie = self.cookie_provider() if self.cookie_provider else None
        if not cookie:
            return headers
        return {**headers, "Cookie": cookie}

    @staticmethod
    def _http_error(exc: requests.HTTPError, context: str) -> APIError:
        response = exc.response
        if response is None:
            return APIError.api_error(f"Bilibili {context} HTTP error: {exc}")
        return APIError.api_error(
            f"Bilibili {context} HTTP {response.status_code}: {response.reason}"
        )


BilibiliAPI = BiliClient
