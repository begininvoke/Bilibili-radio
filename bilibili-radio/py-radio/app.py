from __future__ import annotations

from typing import Any, Optional

from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import HTTPException

from auth_service import AuthService
from bili_client import BiliClient
from constant import Server
from database import init_db
from error_code import APIError, ErrorCode, ErrorMessage
from library_service import LibraryService
from models import AudioStreamInfo, Track, VideoInfo, make_track_id, normalize_bvid
from playback_service import PlaybackService
from result import Result
from stream_service import StreamService


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bili_client = BiliClient()
library_service = LibraryService()
playback_service = PlaybackService()
stream_service = StreamService(bili_client)
auth_service = AuthService()

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


@app.get("/api/tracks/<bvid>")
def get_track_detail(bvid: str):
    detail = bili_client.get_video_detail(bvid)
    for track in detail.pages:
        library_service.upsert_track(track)
    return Result.ok(detail.to_dict()).json()


@app.get("/api/tracks/<bvid>/stream")
def stream_track_default(bvid: str):
    cid = request.args.get("cid", type=int)
    quality = request.args.get("quality", "auto")
    return stream_service.proxy_stream(bvid, cid=cid, quality=quality)


@app.get("/api/tracks/<bvid>/<int:cid>/stream")
def stream_track_part(bvid: str, cid: int):
    quality = request.args.get("quality", "auto")
    return stream_service.proxy_stream(bvid, cid=cid, quality=quality)


@app.get("/api/video/info/<bvid>")
def get_video_info(bvid: str):
    detail = bili_client.get_video_detail(bvid)
    track = detail.info.to_track()
    library_service.upsert_track(track)
    return Result.ok(track.to_dict()).json()


@app.get("/api/video/audio/<bvid>/<int:cid>")
def get_audio_stream(bvid: str, cid: int):
    quality = request.args.get("quality", "auto")
    audio_info = stream_service.get_audio_info(bvid, cid=cid, quality=quality)
    payload = audio_info.to_dict()
    payload["url"] = f"/api/tracks/{normalize_bvid(bvid)}/{cid}/stream?quality={quality}"
    return Result.ok(payload).json()


@app.get("/api/player/status")
def get_player_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": current_video_info.to_track().to_dict() if current_video_info else None,
    }
    return Result.ok(status).json()


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
    return Result.ok({"qrLoginEnabled": auth_service.qr_login_enabled()}).json()


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


def _track_ids_from_payload(payload: dict[str, Any]) -> list[str]:
    track_ids = payload.get("trackIds") or payload.get("track_ids") or []
    if not isinstance(track_ids, list):
        return []
    return [str(track_id) for track_id in track_ids if track_id]


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
