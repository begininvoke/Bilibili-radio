import threading
import subprocess
import time
import struct
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

from ringbuffer import AudioRingBuffer


class ConsumerState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PlaybackProgress:
    current_time: float
    duration: float
    buffer_level: float
    state: ConsumerState
    error_message: Optional[str] = None


class AudioConsumer:
    def __init__(
        self,
        ring_buffer: AudioRingBuffer,
        sample_rate: int = 44100,
        channels: int = 2,
        chunk_size: int = 4096,
    ):
        self.ring_buffer = ring_buffer
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self._thread: Optional[threading.Thread] = None
        self._state = ConsumerState.IDLE
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._current_time = 0.0
        self._duration = 0.0
        self._error_message: Optional[str] = None

        self._on_data: Optional[Callable[[bytes], None]] = None
        self._on_progress: Optional[Callable[[PlaybackProgress], None]] = None
        self._on_state_change: Optional[Callable[[ConsumerState], None]] = None

        self._ffmpeg_process: Optional[subprocess.Popen] = None
        self._audio_url: Optional[str] = None
        self._bvid: Optional[str] = None

    def set_callbacks(
        self,
        on_data: Optional[Callable[[bytes], None]] = None,
        on_progress: Optional[Callable[[PlaybackProgress], None]] = None,
        on_state_change: Optional[Callable[[ConsumerState], None]] = None,
    ):
        self._on_data = on_data
        self._on_progress = on_progress
        self._on_state_change = on_state_change

    def _set_state(self, state: ConsumerState):
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _build_ffmpeg_command(self, audio_url: str, bvid: str = "") -> list:
        headers_str = (
            f"Referer: https://www.bilibili.com/video/{bvid}\r\n"
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
        )

        cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-headers", headers_str,
            "-i", audio_url,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-",
        ]

        return cmd

    def start(self, audio_url: str, bvid: str = "", duration: float = 0.0) -> bool:
        if self._state == ConsumerState.PLAYING:
            return False

        self._audio_url = audio_url
        self._bvid = bvid
        self._duration = duration
        self._current_time = 0.0
        self._stop_event.clear()
        self._pause_event.clear()
        self._error_message = None

        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self._set_state(ConsumerState.STOPPED)

        self._cleanup_ffmpeg()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def pause(self):
        self._pause_event.set()
        self._set_state(ConsumerState.PAUSED)

    def resume(self):
        self._pause_event.clear()
        if self._state == ConsumerState.PAUSED:
            self._set_state(ConsumerState.PLAYING)

    def seek(self, time_seconds: float):
        self._current_time = max(0, min(time_seconds, self._duration))

    def _cleanup_ffmpeg(self):
        if self._ffmpeg_process:
            try:
                self._ffmpeg_process.terminate()
                self._ffmpeg_process.wait(timeout=2.0)
            except Exception:
                if self._ffmpeg_process:
                    self._ffmpeg_process.kill()
            finally:
                self._ffmpeg_process = None

    def _playback_loop(self):
        try:
            self._set_state(ConsumerState.PLAYING)

            cmd = self._build_ffmpeg_command(self._audio_url, self._bvid)
            print(f"[Consumer] Starting FFmpeg with command: {' '.join(cmd[:6])}...")
            
            self._ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.chunk_size * 4,
            )
            print(f"[Consumer] FFmpeg process started, PID: {self._ffmpeg_process.pid}")

            bytes_per_second = self.sample_rate * self.channels * 2
            chunk_count = 0
            last_progress_time = time.time()
            last_send_time = time.time()
            chunks_per_second = bytes_per_second / self.chunk_size
            min_interval = 0.8 / chunks_per_second

            while not self._stop_event.is_set():
                while self._pause_event.is_set():
                    if self._stop_event.is_set():
                        return
                    time.sleep(0.05)

                try:
                    elapsed = time.time() - last_send_time
                    if elapsed < min_interval:
                        time.sleep(min_interval - elapsed)

                    chunk = self._ffmpeg_process.stdout.read(self.chunk_size)
                    if not chunk:
                        if self._ffmpeg_process.poll() is not None:
                            print(f"[Consumer] FFmpeg exited with code: {self._ffmpeg_process.poll()}")
                            stderr_output = self._ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                            if stderr_output:
                                print(f"[Consumer] FFmpeg stderr: {stderr_output[:500]}")
                            break
                        continue

                    chunk_count += 1
                    self._current_time += len(chunk) / bytes_per_second
                    last_send_time = time.time()

                    if self._on_data:
                        self._on_data(chunk)

                    if time.time() - last_progress_time >= 0.5:
                        self._notify_progress()
                        last_progress_time = time.time()
                        if chunk_count % 50 == 0:
                            print(f"[Consumer] Sent {chunk_count} chunks, time: {self._current_time:.1f}s")

                except Exception as e:
                    self._error_message = f"读取音频数据失败: {str(e)}"
                    print(f"[Consumer] Error reading audio data: {e}")
                    self._set_state(ConsumerState.ERROR)
                    break

            print(f"[Consumer] Playback loop ended, total chunks: {chunk_count}, time: {self._current_time:.1f}s")
            self._set_state(ConsumerState.STOPPED)

        except FileNotFoundError as e:
            self._error_message = "FFmpeg未安装或不在PATH中"
            print(f"[Consumer] FFmpeg not found: {e}")
            self._set_state(ConsumerState.ERROR)

        except Exception as e:
            self._error_message = f"播放错误: {str(e)}"
            print(f"[Consumer] Playback error: {e}")
            import traceback
            traceback.print_exc()
            self._set_state(ConsumerState.ERROR)

        finally:
            self._cleanup_ffmpeg()
            self._notify_progress()

    def _notify_progress(self):
        if self._on_progress:
            progress = PlaybackProgress(
                current_time=self._current_time,
                duration=self._duration,
                buffer_level=self.ring_buffer.get_fill_ratio(),
                state=self._state,
                error_message=self._error_message,
            )
            self._on_progress(progress)

    def get_progress(self) -> PlaybackProgress:
        return PlaybackProgress(
            current_time=self._current_time,
            duration=self._duration,
            buffer_level=self.ring_buffer.get_fill_ratio(),
            state=self._state,
            error_message=self._error_message,
        )

    @property
    def state(self) -> ConsumerState:
        return self._state

    @property
    def is_playing(self) -> bool:
        return self._state == ConsumerState.PLAYING
