from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

import requests
from flask import Flask, Response, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import HTTPException

from analysis_service import AnalysisService
from auth_service import AuthService
from bili_client import BiliClient
from constant import Server
from database import init_db
from error_code import APIError, ErrorCode, ErrorMessage
from library_service import LibraryService
from models import AudioStreamInfo, Track, VideoInfo, make_track_id, normalize_bvid
from playback_service import PlaybackService
from queue_service import PlayerQueueService
from result import Result
from settings_service import SettingsService
from stream_service import StreamService


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

auth_service = AuthService()
bili_client = BiliClient(cookie_provider=auth_service.get_cookie_header)
library_service = LibraryService()
playback_service = PlaybackService()
queue_service = PlayerQueueService()
stream_service = StreamService(bili_client)
settings_service = SettingsService()
analysis_service = AnalysisService()

current_video_info: Optional[VideoInfo] = None
current_audio_info: Optional[AudioStreamInfo] = None


init_db()


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    return Result.fail(error.message, code=error.code.name).json_with_status(error.status_code)


@app.errorhandler(404)
def handle_not_found(_error):
    return Result.fail("Route not found", code=ErrorCode.NOT_FOUND.name).json_with_status(404)


@app.errorhandler(HTTPException)
def handle_http_exception(error: HTTPException):
    status_code = error.code or 500
    code = ErrorCode.NOT_FOUND.name if status_code == 404 else ErrorCode.VALIDATION_ERROR.name
    return Result.fail(str(error.description), code=code).json_with_status(status_code)


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    app.logger.exception("Unhandled server error: %s", error)
    return Result.server_error(str(error), code=ErrorCode.UNKNOWN_ERROR.name)


@app.get("/api/search")
def search_tracks():
    keyword = request.args.get("keyword", "")
    page = _int_arg("page", 1)
    page_size = _int_arg("page_size", _int_arg("pageSize", 20))
    tracks = bili_client.search(keyword, page=page, page_size=page_size)
    return Result.ok(
        {
            "keyword": keyword,
            "page": page,
            "pageSize": page_size,
            "tracks": [track.to_dict() for track in tracks],
        }
    ).json()


@app.get("/api/images/proxy")
def proxy_image():
    image_url = request.args.get("url", "")
    return _proxy_image_url(image_url)


@app.get("/api/tracks/<bvid>")
def get_track_detail(bvid: str):
    detail = bili_client.get_video_detail(bvid)
    for track in detail.pages:
        library_service.upsert_track(track)
    return Result.ok(detail.to_dict()).json()


@app.get("/api/tracks/<bvid>/cover")
def get_track_cover_default(bvid: str):
    cid = request.args.get("cid", type=int)
    return Result.ok(bili_client.get_cover_info(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/<int:cid>/cover")
def get_track_cover_part(bvid: str, cid: int):
    return Result.ok(bili_client.get_cover_info(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/intro")
def get_track_intro_default(bvid: str):
    cid = request.args.get("cid", type=int)
    return Result.ok(bili_client.get_video_intro(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/<int:cid>/intro")
def get_track_intro_part(bvid: str, cid: int):
    return Result.ok(bili_client.get_video_intro(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/subtitles")
def get_track_subtitles_default(bvid: str):
    cid = request.args.get("cid", type=int)
    return Result.ok(bili_client.get_track_subtitles(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/<int:cid>/subtitles")
def get_track_subtitles_part(bvid: str, cid: int):
    return Result.ok(bili_client.get_track_subtitles(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/chapters")
def get_track_chapters_default(bvid: str):
    cid = request.args.get("cid", type=int)
    return Result.ok(bili_client.get_track_chapters(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/<int:cid>/chapters")
def get_track_chapters_part(bvid: str, cid: int):
    return Result.ok(bili_client.get_track_chapters(bvid, cid=cid)).json()


@app.get("/api/tracks/<bvid>/comments")
@app.get("/api/tracks/<bvid>/<int:_cid>/comments")
def get_track_comments(bvid: str, _cid: Optional[int] = None):
    page = _int_arg("page", 1)
    page_size = _int_arg("page_size", _int_arg("pageSize", 20))
    return Result.ok(bili_client.get_track_comments(bvid, page=page, page_size=page_size)).json()


@app.get("/api/tracks/resolve")
def resolve_track_input():
    input_value = request.args.get("input", "")
    bvid = BiliClient.parse_input(input_value)
    if not bvid:
        raise APIError.invalid_input("Cannot parse BVID from input")
    detail = bili_client.get_video_detail(bvid)
    for track in detail.pages:
        library_service.upsert_track(track)
    return Result.ok(detail.to_dict()).json()


@app.get("/api/tracks/<bvid>/stream-info")
def get_track_stream_info_default(bvid: str):
    cid = request.args.get("cid", type=int)
    quality = request.args.get("quality")
    return Result.ok(_stream_info_payload(bvid, cid=cid, quality=quality)).json()


@app.get("/api/tracks/<bvid>/<int:cid>/stream-info")
def get_track_stream_info_part(bvid: str, cid: int):
    quality = request.args.get("quality")
    return Result.ok(_stream_info_payload(bvid, cid=cid, quality=quality)).json()


@app.get("/api/tracks/<bvid>/stream")
def stream_track_default(bvid: str):
    cid = request.args.get("cid", type=int)
    quality = request.args.get("quality") or settings_service.get_audio_quality_preference()
    return stream_service.proxy_stream(bvid, cid=cid, quality=quality)


@app.get("/api/tracks/<bvid>/<int:cid>/stream")
def stream_track_part(bvid: str, cid: int):
    quality = request.args.get("quality") or settings_service.get_audio_quality_preference()
    return stream_service.proxy_stream(bvid, cid=cid, quality=quality)


@app.get("/api/video/info/<bvid>")
def get_video_info(bvid: str):
    detail = bili_client.get_video_detail(bvid)
    track = detail.info.to_track()
    library_service.upsert_track(track)
    return Result.ok(track.to_dict()).json()


@app.get("/api/video/audio/<bvid>/<int:cid>")
def get_audio_stream(bvid: str, cid: int):
    quality = request.args.get("quality")
    return Result.ok(_stream_info_payload(bvid, cid=cid, quality=quality)).json()


@app.get("/api/player/status")
def get_player_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": current_video_info.to_track().to_dict() if current_video_info else None,
    }
    return Result.ok(status).json()


@app.route("/api/player/queue", methods=["GET", "PUT", "DELETE"])
def player_queue():
    if request.method == "GET":
        return Result.ok(queue_service.get_queue()).json()
    if request.method == "DELETE":
        return Result.ok(queue_service.clear_queue()).json()

    payload = _json_body()
    result = queue_service.save_queue(
        _queue_tracks_from_payload(payload),
        current_index=int(payload.get("currentIndex") or payload.get("current_index") or -1),
        play_mode=str(payload.get("playMode") or payload.get("play_mode") or "order"),
    )
    return Result.ok(result).json()


@app.post("/api/player/stop")
def stop_player():
    global current_video_info, current_audio_info
    current_video_info = None
    current_audio_info = None
    return Result.ok().json()


@app.get("/api/stream/<bvid>")
def stream_audio_legacy(bvid: str):
    cid = None
    if current_video_info and current_video_info.bvid == normalize_bvid(bvid):
        cid = current_video_info.cid
    return stream_service.proxy_stream(bvid, cid=cid, quality=request.args.get("quality", "auto"))


@app.get("/api/stream/stats")
def get_stream_stats():
    return Result.ok(stream_service.get_stats()).json()


@app.post("/api/stream/stats/reset")
def reset_stream_stats():
    stream_service.reset_stats()
    return Result.ok().json()


@app.get("/api/library/recent")
def list_recent():
    limit = _int_arg("limit", 100)
    return Result.ok({"tracks": library_service.list_recent(limit=limit)}).json()


@app.delete("/api/library/recent")
def clear_recent():
    return Result.ok(library_service.clear_recent()).json()


@app.post("/api/library/recent")
def add_recent():
    payload = _json_body()
    track = _resolve_track_from_payload(payload)
    result = library_service.add_recent(
        track,
        position_ms=int(payload.get("positionMs") or payload.get("position_ms") or 0),
        listen_ms=int(payload.get("listenMs") or payload.get("listen_ms") or 0),
        completed=bool(payload.get("completed")),
    )
    return Result.ok(result).json()


@app.get("/api/library/likes")
def list_likes():
    return Result.ok({"tracks": library_service.list_likes()}).json()


@app.post("/api/library/likes/<bvid>")
def add_like(bvid: str):
    payload = _json_body()
    payload.setdefault("bvid", bvid)
    track = _resolve_track_from_payload(payload)
    return Result.ok(library_service.add_like(track)).json()


@app.delete("/api/library/likes/<bvid>")
def remove_like(bvid: str):
    cid = request.args.get("cid", type=int)
    removed = library_service.remove_like(bvid, cid=cid)
    return Result.ok({"bvid": normalize_bvid(bvid), "cid": cid, "removed": removed}).json()


@app.route("/api/library/playlists", methods=["GET", "POST"])
def playlists():
    if request.method == "GET":
        return Result.ok({"playlists": library_service.list_playlists()}).json()

    payload = _json_body()
    tracks = _tracks_from_payload(payload)
    playlist = library_service.create_playlist(payload.get("name", ""), tracks=tracks)
    return Result.ok(playlist).json_with_status(201)


@app.route("/api/library/playlists/<playlist_id>", methods=["GET", "PATCH", "DELETE"])
def playlist_detail(playlist_id: str):
    if request.method == "GET":
        return Result.ok(library_service.get_playlist(playlist_id)).json()
    if request.method == "DELETE":
        return Result.ok(library_service.delete_playlist(playlist_id)).json()

    payload = _json_body()
    playlist = library_service.update_playlist(
        playlist_id,
        name=payload.get("name"),
        cover=payload.get("cover"),
    )
    return Result.ok(playlist).json()


@app.post("/api/library/playlists/<playlist_id>/items:preview")
def preview_playlist_items(playlist_id: str):
    payload = _json_body()
    result = library_service.preview_playlist_items(
        playlist_id,
        tracks=_tracks_from_payload(payload),
        track_ids=_track_ids_from_payload(payload),
    )
    return Result.ok(result).json()


@app.post("/api/library/playlists/<playlist_id>/items:batch")
def batch_playlist_items(playlist_id: str):
    payload = _json_body()
    result = library_service.batch_add_playlist_items(
        playlist_id,
        tracks=_tracks_from_payload(payload),
        track_ids=_track_ids_from_payload(payload),
    )
    return Result.ok(result).json()


@app.post("/api/library/playlists/import/favorite")
def import_favorite_to_new_playlist():
    payload = _json_body()
    favorite = _favorite_import_payload(payload)
    tracks = favorite.pop("tracks")
    name = str(payload.get("name") or favorite["folder"].get("title") or "").strip()
    if not name:
        name = f"Bilibili favorite {favorite['mediaId']}"
    playlist = library_service.create_playlist(name)
    result = library_service.batch_add_playlist_items(playlist["id"], tracks=tracks)
    analysis_service.record_event(
        {
            "event": "favorite_imported",
            "payload": {
                "mediaId": favorite["mediaId"],
                "playlistId": playlist["id"],
                "added": result["added"],
                "duplicated": result["duplicated"],
                "unavailable": result["unavailable"],
            },
        }
    )
    return Result.ok(
        {
            "playlist": library_service.get_playlist(playlist["id"]),
            "import": result,
            "favorite": favorite,
        }
    ).json_with_status(201)


@app.post("/api/library/playlists/<playlist_id>/import/favorite")
def import_favorite_to_playlist(playlist_id: str):
    payload = _json_body()
    favorite = _favorite_import_payload(payload)
    tracks = favorite.pop("tracks")
    result = library_service.batch_add_playlist_items(playlist_id, tracks=tracks)
    analysis_service.record_event(
        {
            "event": "favorite_imported",
            "payload": {
                "mediaId": favorite["mediaId"],
                "playlistId": playlist_id,
                "added": result["added"],
                "duplicated": result["duplicated"],
                "unavailable": result["unavailable"],
            },
        }
    )
    return Result.ok({"import": result, "favorite": favorite}).json()


@app.post("/api/playback/events")
def record_playback_event():
    result = playback_service.record_event(_json_body())
    return Result.ok(result).json()


@app.get("/api/playback/recent")
def playback_recent():
    limit = _int_arg("limit", 100)
    return Result.ok({"tracks": playback_service.list_recent(limit=limit)}).json()


@app.get("/api/playback/resume/<path:track_id>")
def playback_resume(track_id: str):
    return Result.ok(playback_service.get_resume(track_id)).json()


@app.get("/api/auth/status")
def auth_status():
    return Result.ok(auth_service.get_status(refresh=_bool_arg("refresh", False))).json()


@app.get("/api/auth/qrcode")
def auth_qrcode():
    return Result.ok(auth_service.create_qrcode()).json()


@app.get("/api/auth/qrcode/status")
def auth_qrcode_status():
    qrcode_key = request.args.get("qrcodeKey") or request.args.get("qrcode_key") or ""
    return Result.ok(auth_service.poll_qrcode(qrcode_key)).json()


@app.get("/api/auth/profile")
def auth_profile():
    return Result.ok(auth_service.get_profile(refresh=_bool_arg("refresh", True))).json()


@app.post("/api/auth/logout")
def auth_logout():
    return Result.ok(auth_service.logout()).json()


@app.get("/api/bili/favorites")
def list_bili_favorites():
    up_mid = request.args.get("up_mid", type=int) or request.args.get("upMid", type=int)
    folders = bili_client.list_favorite_folders(up_mid=up_mid)
    return Result.ok({"folders": [folder.to_dict() for folder in folders]}).json()


@app.get("/api/bili/favorites/<int:media_id>/tracks")
def list_bili_favorite_tracks(media_id: int):
    page = _int_arg("page", 1)
    page_size = _int_arg("page_size", _int_arg("pageSize", 20))
    return Result.ok(bili_client.list_favorite_tracks(media_id, page=page, page_size=page_size)).json()


@app.post("/api/analysis/events")
def record_analysis_event():
    return Result.ok(analysis_service.record_event(_json_body())).json_with_status(202)


@app.get("/api/settings")
def get_settings():
    return Result.ok(settings_service.to_dict()).json()


@app.patch("/api/settings")
def update_settings():
    payload = _json_body()
    if "audioQualityPreference" in payload or "audio_quality_preference" in payload:
        value = payload.get("audioQualityPreference") or payload.get("audio_quality_preference")
        settings_service.set_audio_quality_preference(value)
    return Result.ok(settings_service.to_dict()).json()


@app.get("/api/settings/audio-quality")
def get_audio_quality_preference():
    return Result.ok(settings_service.to_dict()).json()


@app.patch("/api/settings/audio-quality")
def update_audio_quality_preference():
    payload = _json_body()
    value = payload.get("audioQualityPreference") or payload.get("audio_quality_preference")
    return Result.ok(
        {"audioQualityPreference": settings_service.set_audio_quality_preference(value)}
    ).json()


@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "Connected to server"})


@socketio.on("disconnect")
def handle_disconnect():
    app.logger.info("Client disconnected: %s", request.sid)


@socketio.on("play_video")
def handle_play_video(data):
    global current_video_info, current_audio_info

    input_str = (data or {}).get("input", "")
    if not input_str:
        emit("error", {"message": ErrorMessage.INPUT_EMPTY})
        return

    try:
        bvid = BiliClient.parse_input(input_str)
        if not bvid:
            emit("error", {"message": ErrorMessage.INVALID_INPUT})
            return

        emit("status", {"message": "Loading video info..."})
        current_video_info = bili_client.get_video_info(bvid)
        track = current_video_info.to_track()
        library_service.upsert_track(track)

        emit("status", {"message": "Resolving audio stream..."})
        current_audio_info = stream_service.get_audio_info(bvid, current_video_info.cid)
        stream_service.reset_stats()

        emit("video_info", track.to_dict())
        emit(
            "audio_stream",
            {
                "url": Server.proxy_url(bvid),
                "duration": current_video_info.duration,
                "bitrate": current_audio_info.bitrate,
                "sample_rate": current_audio_info.sample_rate,
                "channels": current_audio_info.channels,
                "quality": current_audio_info.quality,
                "actualQuality": current_audio_info.actual_quality,
                "fallback": current_audio_info.fallback,
            },
        )
        emit("status", {"message": "Ready"})

    except APIError as error:
        emit("error", {"message": error.message, "code": error.code.name})
    except Exception as error:
        app.logger.exception("Socket playback failed: %s", error)
        emit("error", {"message": f"{ErrorMessage.PLAYBACK_FAILED}: {error}"})


@socketio.on("pause")
def handle_pause():
    emit("status", {"message": "Paused"})


@socketio.on("resume")
def handle_resume():
    emit("status", {"message": "Resumed"})


@socketio.on("stop")
def handle_stop():
    global current_video_info, current_audio_info
    current_video_info = None
    current_audio_info = None
    emit("status", {"message": "Stopped"})


@socketio.on("seek")
def handle_seek(data):
    time_seconds = (data or {}).get("time", 0)
    emit("status", {"message": f"Seeked to {float(time_seconds):.1f}s"})


@socketio.on("get_status")
def handle_get_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": current_video_info.to_track().to_dict() if current_video_info else None,
    }
    emit("player_status", status)


def _json_body() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _int_arg(name: str, default: int) -> int:
    value = request.args.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _bool_arg(name: str, default: bool) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _favorite_import_payload(payload: dict[str, Any]) -> dict[str, Any]:
    media_id = int(payload.get("mediaId") or payload.get("media_id") or 0)
    if media_id <= 0:
        raise APIError.validation_error("mediaId is required")

    max_pages = min(max(int(payload.get("maxPages") or payload.get("max_pages") or 10), 1), 50)
    page_size = min(max(int(payload.get("pageSize") or payload.get("page_size") or 20), 1), 20)
    favorite = bili_client.list_all_favorite_tracks(
        media_id,
        max_pages=max_pages,
        page_size=page_size,
    )
    tracks = favorite.pop("tracks")
    favorite["tracks"] = tracks
    favorite["fetched"] = len(tracks)
    return favorite


def _resolve_track_from_payload(payload: dict[str, Any]) -> Track:
    candidate = payload.get("track")
    if isinstance(candidate, dict):
        return Track.from_dict(candidate)
    if payload.get("title") and payload.get("bvid"):
        return Track.from_dict(payload)

    bvid = str(payload.get("bvid") or "").strip()
    if not bvid:
        raise APIError.validation_error("track or bvid is required")

    cid = payload.get("cid")
    detail = bili_client.get_video_detail(bvid)
    if cid:
        track_id = make_track_id(bvid, int(cid))
        for track in detail.pages:
            if track.track_id == track_id:
                return track
        raise APIError.not_found(f"Track part not found: {track_id}")
    return detail.info.to_track()


def _tracks_from_payload(payload: dict[str, Any]) -> list[Track]:
    tracks = payload.get("tracks")
    if not isinstance(tracks, list):
        return []

    result = []
    for item in tracks:
        if isinstance(item, dict):
            result.append(Track.from_dict(item))
    return result


def _queue_tracks_from_payload(payload: dict[str, Any]) -> list[Track]:
    queue = payload.get("queue")
    if isinstance(queue, list):
        return [Track.from_dict(item) for item in queue if isinstance(item, dict)]
    return _tracks_from_payload(payload)


def _track_ids_from_payload(payload: dict[str, Any]) -> list[str]:
    track_ids = payload.get("trackIds") or payload.get("track_ids") or []
    if not isinstance(track_ids, list):
        return []
    return [str(track_id) for track_id in track_ids if track_id]


def _stream_info_payload(bvid: str, cid: Optional[int], quality: Optional[str]) -> dict[str, Any]:
    resolved_bvid = normalize_bvid(bvid)
    resolved_cid = cid
    if resolved_cid is None:
        resolved_cid = bili_client.get_video_info(resolved_bvid).cid
    resolved_quality = quality or settings_service.get_audio_quality_preference()
    audio_info = stream_service.get_audio_info(resolved_bvid, cid=resolved_cid, quality=resolved_quality)
    payload = audio_info.to_dict()
    relative_url = f"/api/tracks/{resolved_bvid}/{resolved_cid}/stream?quality={resolved_quality}"
    payload.update(
        {
            "url": _absolute_url(relative_url),
            "relativeUrl": relative_url,
            "bvid": resolved_bvid,
            "cid": resolved_cid,
        }
    )
    return payload


def _absolute_url(path: str) -> str:
    return f"{request.host_url.rstrip('/')}{path}"


def _proxy_image_url(image_url: str):
    parsed = urlparse(image_url or "")
    if parsed.scheme not in {"http", "https"}:
        raise APIError.validation_error("image url must be http or https")
    if not _is_allowed_image_host(parsed.hostname or ""):
        raise APIError.validation_error("image host is not allowed")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    try:
        upstream = requests.get(image_url, headers=headers, stream=True, timeout=15)
        upstream.raise_for_status()
    except requests.Timeout:
        raise APIError.request_timeout("image proxy")
    except requests.RequestException as exc:
        raise APIError.network_error(str(exc))

    def generate():
        for chunk in upstream.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    response_headers = {
        "Content-Type": upstream.headers.get("Content-Type", "image/jpeg"),
        "Cache-Control": "public, max-age=86400",
    }
    if upstream.headers.get("Content-Length"):
        response_headers["Content-Length"] = upstream.headers["Content-Length"]
    return Response(generate(), status=upstream.status_code, headers=response_headers)


def _is_allowed_image_host(hostname: str) -> bool:
    host = hostname.lower()
    return (
        host == "hdslb.com"
        or host.endswith(".hdslb.com")
        or host == "bilibili.com"
        or host.endswith(".bilibili.com")
        or host == "bilivideo.com"
        or host.endswith(".bilivideo.com")
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Bilibili Radio backend")
    print("=" * 60)
    print(f"HTTP server: http://localhost:{Server.PORT}")
    print("Socket.IO enabled")
    print("=" * 60)
    socketio.run(
        app,
        host=Server.HOST,
        port=Server.PORT,
        debug=Server.DEBUG,
        allow_unsafe_werkzeug=True,
    )
