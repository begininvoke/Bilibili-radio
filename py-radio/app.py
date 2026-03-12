import json
import time
import base64
import requests
import threading
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from typing import Optional

from ringbuffer import AudioRingBuffer
from bilibili_api import BilibiliAPI, BilibiliAPIError, VideoInfo, AudioStreamInfo
from producer import AudioProducer, ProducerState
from consumer import AudioConsumer, ConsumerState

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bilibili_api = BilibiliAPI()

ring_buffer: Optional[AudioRingBuffer] = None
producer: Optional[AudioProducer] = None
consumer: Optional[AudioConsumer] = None

current_video_info: Optional[VideoInfo] = None
current_audio_info: Optional[AudioStreamInfo] = None

stream_stats = {
    "total_bytes": 0,
    "start_time": None,
    "current_session_bytes": 0,
}
stream_stats_lock = threading.Lock()


def init_player():
    global ring_buffer, producer, consumer

    ring_buffer = AudioRingBuffer(
        max_size=10 * 1024 * 1024,
        low_watermark=0.3,
        high_watermark=0.8,
    )

    producer = AudioProducer(
        ring_buffer=ring_buffer,
        chunk_size=64 * 1024,
        max_retries=3,
    )

    consumer = AudioConsumer(
        ring_buffer=ring_buffer,
        sample_rate=44100,
        channels=2,
        chunk_size=4096,
    )

    producer.set_callbacks(on_progress=on_producer_progress, on_state_change=on_producer_state_change)

    consumer.set_callbacks(
        on_data=on_consumer_data,
        on_progress=on_consumer_progress,
        on_state_change=on_consumer_state_change,
    )


def on_producer_progress(progress):
    socketio.emit(
        "download_progress",
        {
            "downloaded_bytes": progress.downloaded_bytes,
            "total_bytes": progress.total_bytes,
            "speed": progress.speed,
            "state": progress.state.value,
            "error": progress.error_message,
        },
    )


def on_producer_state_change(state: ProducerState):
    socketio.emit("producer_state", {"state": state.value})


def on_consumer_data(data: bytes):
    encoded_data = base64.b64encode(data).decode("utf-8")
    socketio.emit(
        "audio_data",
        {
            "data": encoded_data,
            "sample_rate": consumer.sample_rate,
            "channels": consumer.channels,
        },
    )


def on_consumer_progress(progress):
    socketio.emit(
        "playback_progress",
        {
            "current_time": progress.current_time,
            "duration": progress.duration,
            "buffer_level": progress.buffer_level,
            "state": progress.state.value,
            "error": progress.error_message,
        },
    )


def on_consumer_state_change(state: ConsumerState):
    socketio.emit("consumer_state", {"state": state.value})


@app.route("/api/video/info/<bvid>", methods=["GET"])
def get_video_info(bvid: str):
    try:
        video_info = bilibili_api.get_video_info(bvid)
        return jsonify(
            {
                "success": True,
                "data": {
                    "bvid": video_info.bvid,
                    "cid": video_info.cid,
                    "title": video_info.title,
                    "duration": video_info.duration,
                    "owner": video_info.owner,
                    "cover": video_info.cover,
                },
            }
        )
    except BilibiliAPIError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/video/audio/<bvid>/<int:cid>", methods=["GET"])
def get_audio_stream(bvid: str, cid: int):
    try:
        audio_info = bilibili_api.get_audio_stream(bvid, cid)
        return jsonify(
            {
                "success": True,
                "data": {
                    "url": audio_info.url,
                    "duration": audio_info.duration,
                    "bitrate": audio_info.bitrate,
                    "sample_rate": audio_info.sample_rate,
                    "channels": audio_info.channels,
                },
            }
        )
    except BilibiliAPIError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/player/status", methods=["GET"])
def get_player_status():
    global current_video_info, current_audio_info

    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
        "producer_state": producer.state.value if producer else "idle",
        "consumer_state": consumer.state.value if consumer else "idle",
        "buffer_stats": ring_buffer.get_stats() if ring_buffer else None,
    }

    if current_video_info:
        status["video_info"] = {
            "bvid": current_video_info.bvid,
            "title": current_video_info.title,
            "duration": current_video_info.duration,
        }

    return jsonify({"success": True, "data": status})


@app.route("/api/player/stop", methods=["POST"])
def stop_player():
    global current_video_info, current_audio_info

    if producer:
        producer.stop()
    if consumer:
        consumer.stop()
    if ring_buffer:
        ring_buffer.clear()

    current_video_info = None
    current_audio_info = None

    return jsonify({"success": True})


@app.route("/api/stream/<bvid>", methods=["GET"])
def stream_audio(bvid: str):
    global current_audio_info, stream_stats

    if not current_audio_info:
        return jsonify({"success": False, "error": "No audio loaded"}), 400

    audio_url = current_audio_info.url

    headers = {
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        resp = requests.get(
            audio_url,
            headers=headers,
            stream=True,
            timeout=30,
        )

        def generate():
            total_sent = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
                    total_sent += len(chunk)
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
            response_headers["Accept-Ranges"] = "bytes"

        status_code = resp.status_code

        return Response(
            generate(),
            status=status_code,
            headers=response_headers,
        )

    except Exception as e:
        print(f"[stream_audio] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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
    
    return jsonify({
        "success": True,
        "data": {
            "total_bytes": stats["total_bytes"],
            "session_bytes": stats["current_session_bytes"],
            "elapsed_seconds": elapsed,
            "bytes_per_second": speed,
            "total_mb": round(stats["total_bytes"] / 1024 / 1024, 2),
            "session_mb": round(stats["current_session_bytes"] / 1024 / 1024, 2),
        }
    })


@app.route("/api/stream/stats/reset", methods=["POST"])
def reset_stream_stats():
    global stream_stats
    with stream_stats_lock:
        stream_stats["total_bytes"] = 0
        stream_stats["current_session_bytes"] = 0
        stream_stats["start_time"] = time.time()
    return jsonify({"success": True})


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
        emit("error", {"message": "请输入BV号或视频链接"})
        return

    try:
        bvid = BilibiliAPI.parse_input(input_str)
        print(f"[play_video] 解析BV号: {bvid}")
        if not bvid:
            emit("error", {"message": "无效的BV号或链接格式"})
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

        proxy_url = f"http://localhost:5000/api/stream/{bvid}"
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

    except BilibiliAPIError as e:
        print(f"[play_video] API错误: {e}")
        emit("error", {"message": f"API错误: {str(e)}"})
    except Exception as e:
        print(f"[play_video] 异常: {e}")
        import traceback
        traceback.print_exc()
        emit("error", {"message": f"播放失败: {str(e)}"})


@socketio.on("pause")
def handle_pause():
    if consumer:
        consumer.pause()
        emit("status", {"message": "已暂停"})


@socketio.on("resume")
def handle_resume():
    if consumer:
        consumer.resume()
        emit("status", {"message": "已恢复播放"})


@socketio.on("stop")
def handle_stop():
    global current_video_info, current_audio_info

    if producer:
        producer.stop()
    if consumer:
        consumer.stop()
    if ring_buffer:
        ring_buffer.clear()

    current_video_info = None
    current_audio_info = None

    emit("status", {"message": "已停止播放"})


@socketio.on("seek")
def handle_seek(data):
    time_seconds = data.get("time", 0)
    if consumer:
        consumer.seek(time_seconds)
        emit("status", {"message": f"已跳转到 {time_seconds:.1f}秒"})


@socketio.on("get_status")
def handle_get_status():
    status = {
        "has_video": current_video_info is not None,
        "video_info": None,
        "producer_state": producer.state.value if producer else "idle",
        "consumer_state": consumer.state.value if consumer else "idle",
        "buffer_stats": ring_buffer.get_stats() if ring_buffer else None,
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
    print("正在初始化播放器组件...")

    init_player()

    print("播放器初始化完成")
    print("启动HTTP服务器: http://localhost:5000")
    print("WebSocket服务已启用")
    print("=" * 60)

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
