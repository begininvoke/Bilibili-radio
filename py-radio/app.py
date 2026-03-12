import time
import requests
import threading
from flask import Flask, request, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from typing import Optional

from bilibili_api import BilibiliAPI, VideoInfo, AudioStreamInfo
from constant import HttpHeader, Server, Stream
from error_code import APIError, ErrorMessage
from result import Result

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bilibili_api = BilibiliAPI()

current_video_info: Optional[VideoInfo] = None
current_audio_info: Optional[AudioStreamInfo] = None

stream_stats = {
    "total_bytes": 0,
    "start_time": None,
    "current_session_bytes": 0,
}
stream_stats_lock = threading.Lock()


@app.route("/api/video/info/<bvid>", methods=["GET"])
def get_video_info(bvid: str):
    try:
        video_info = bilibili_api.get_video_info(bvid)
        return Result.ok({
            "bvid": video_info.bvid,
            "cid": video_info.cid,
            "title": video_info.title,
            "duration": video_info.duration,
            "owner": video_info.owner,
            "cover": video_info.cover,
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/video/audio/<bvid>/<int:cid>", methods=["GET"])
def get_audio_stream(bvid: str, cid: int):
    try:
        audio_info = bilibili_api.get_audio_stream(bvid, cid)
        return Result.ok({
            "url": audio_info.url,
            "duration": audio_info.duration,
            "bitrate": audio_info.bitrate,
            "sample_rate": audio_info.sample_rate,
            "channels": audio_info.channels,
        }).json()
    except APIError as e:
        return Result.bad_request(e.message)
    except Exception as e:
        return Result.server_error(str(e))


@app.route("/api/player/status", methods=["GET"])
def get_player_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
    }

    if current_video_info:
        status["video_info"] = {
            "bvid": current_video_info.bvid,
            "title": current_video_info.title,
            "duration": current_video_info.duration,
        }

    return Result.ok(status).json()


@app.route("/api/player/stop", methods=["POST"])
def stop_player():
    global current_video_info, current_audio_info

    current_video_info = None
    current_audio_info = None

    return Result.ok().json()


@app.route("/api/stream/<bvid>", methods=["GET"])
def stream_audio(bvid: str):
    global current_audio_info, stream_stats

    if not current_audio_info:
        return Result.bad_request(ErrorMessage.NO_AUDIO_LOADED)

    audio_url = current_audio_info.url
    headers = HttpHeader.stream_headers(bvid)

    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        resp = requests.get(
            audio_url,
            headers=headers,
            stream=True,
            timeout=Stream.TIMEOUT,
        )

        def generate():
            for chunk in resp.iter_content(chunk_size=Stream.CHUNK_SIZE):
                if chunk:
                    yield chunk
                    with stream_stats_lock:
                        stream_stats["total_bytes"] += len(chunk)
                        stream_stats["current_session_bytes"] += len(chunk)

        response_headers = {}
        if "Content-Type" in resp.headers:
            response_headers["Content-Type"] = resp.headers["Content-Type"]
        if "Content-Length" in resp.headers:
            response_headers["Content-Length"] = resp.headers["Content-Length"]
        if "Content-Range" in resp.headers:
            response_headers["Content-Range"] = resp.headers["Content-Range"]
        if "Accept-Ranges" in resp.headers:
            response_headers["Accept-Ranges"] = resp.headers["Accept-Ranges"]
        else:
            response_headers["Accept-Ranges"] = HttpHeader.ACCEPT_RANGES

        return Response(
            generate(),
            status=resp.status_code,
            headers=response_headers,
        )

    except Exception as e:
        print(f"[stream_audio] Error: {e}")
        return Result.server_error(str(e))


@app.route("/api/stream/stats", methods=["GET"])
def get_stream_stats():
    global stream_stats
    with stream_stats_lock:
        stats = stream_stats.copy()

    elapsed = 0
    if stats["start_time"]:
        elapsed = time.time() - stats["start_time"]

    speed = 0
    if elapsed > 0:
        speed = stats["current_session_bytes"] / elapsed

    return Result.ok({
        "total_bytes": stats["total_bytes"],
        "session_bytes": stats["current_session_bytes"],
        "elapsed_seconds": elapsed,
        "bytes_per_second": speed,
        "total_mb": round(stats["total_bytes"] / 1024 / 1024, 2),
        "session_mb": round(stats["current_session_bytes"] / 1024 / 1024, 2),
    }).json()


@app.route("/api/stream/stats/reset", methods=["POST"])
def reset_stream_stats():
    global stream_stats
    with stream_stats_lock:
        stream_stats["total_bytes"] = 0
        stream_stats["current_session_bytes"] = 0
        stream_stats["start_time"] = time.time()
    return Result.ok().json()


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit("connected", {"message": "Connected to server"})


@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")


@socketio.on("play_video")
def handle_play_video(data):
    global current_video_info, current_audio_info, stream_stats

    print(f"[play_video] 收到播放请求: {data}")
    input_str = data.get("input", "")
    if not input_str:
        print("[play_video] 错误: 输入为空")
        emit("error", {"message": ErrorMessage.INPUT_EMPTY})
        return

    try:
        bvid = BilibiliAPI.parse_input(input_str)
        print(f"[play_video] 解析BV号: {bvid}")
        if not bvid:
            emit("error", {"message": ErrorMessage.INVALID_INPUT})
            return

        emit("status", {"message": "正在获取视频信息..."})

        current_video_info = bilibili_api.get_video_info(bvid)
        print(f"[play_video] 获取视频信息成功: {current_video_info.title}")
        current_audio_info = bilibili_api.get_audio_stream(bvid, current_video_info.cid)
        print(f"[play_video] 获取音频流成功")

        with stream_stats_lock:
            stream_stats["current_session_bytes"] = 0
            stream_stats["start_time"] = time.time()

        emit(
            "video_info",
            {
                "bvid": current_video_info.bvid,
                "title": current_video_info.title,
                "duration": current_video_info.duration,
                "owner": current_video_info.owner,
                "cover": current_video_info.cover,
            },
        )

        emit("status", {"message": "正在启动播放..."})

        proxy_url = Server.proxy_url(bvid)
        emit(
            "audio_stream",
            {
                "url": proxy_url,
                "duration": current_video_info.duration,
                "bitrate": current_audio_info.bitrate,
                "sample_rate": current_audio_info.sample_rate,
                "channels": current_audio_info.channels,
            },
        )
        print(f"[play_video] 已发送代理URL: {proxy_url}")

    except APIError as e:
        print(f"[play_video] API错误: {e}")
        emit("error", {"message": f"API错误: {e.message}"})
    except Exception as e:
        print(f"[play_video] 异常: {e}")
        import traceback
        traceback.print_exc()
        emit("error", {"message": f"{ErrorMessage.PLAYBACK_FAILED}: {str(e)}"})


@socketio.on("pause")
def handle_pause():
    emit("status", {"message": "已暂停"})


@socketio.on("resume")
def handle_resume():
    emit("status", {"message": "已恢复播放"})


@socketio.on("stop")
def handle_stop():
    global current_video_info, current_audio_info

    current_video_info = None
    current_audio_info = None

    emit("status", {"message": "已停止播放"})


@socketio.on("seek")
def handle_seek(data):
    time_seconds = data.get("time", 0)
    emit("status", {"message": f"已跳转到 {time_seconds:.1f}秒"})


@socketio.on("get_status")
def handle_get_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
    }

    if current_video_info:
        status["video_info"] = {
            "bvid": current_video_info.bvid,
            "title": current_video_info.title,
            "duration": current_video_info.duration,
        }

    emit("player_status", status)


if __name__ == "__main__":
    print("=" * 60)
    print("B站音频播放器后端服务")
    print("=" * 60)
    print(f"启动HTTP服务器: http://localhost:{Server.PORT}")
    print("WebSocket服务已启用")
    print("=" * 60)

    socketio.run(app, host=Server.HOST, port=Server.PORT, debug=Server.DEBUG, allow_unsafe_werkzeug=True)
