import threading
import time
import requests
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

from ringbuffer import AudioRingBuffer


class ProducerState(Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class DownloadProgress:
    downloaded_bytes: int
    total_bytes: int
    speed: float
    state: ProducerState
    error_message: Optional[str] = None


class AudioProducer:
    def __init__(
        self,
        ring_buffer: AudioRingBuffer,
        chunk_size: int = 64 * 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.ring_buffer = ring_buffer
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._thread: Optional[threading.Thread] = None
        self._state = ProducerState.IDLE
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._downloaded_bytes = 0
        self._total_bytes = 0
        self._download_speed = 0.0
        self._last_bytes = 0
        self._last_time = 0.0
        self._error_message: Optional[str] = None

        self._on_progress: Optional[Callable[[DownloadProgress], None]] = None
        self._on_state_change: Optional[Callable[[ProducerState], None]] = None

        self._audio_url: Optional[str] = None
        self._bvid: Optional[str] = None
        self._session: Optional[requests.Session] = None

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
        on_state_change: Optional[Callable[[ProducerState], None]] = None,
    ):
        self._on_progress = on_progress
        self._on_state_change = on_state_change

    def _set_state(self, state: ProducerState):
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.bilibili.com/video/{self._bvid}" if self._bvid else "https://www.bilibili.com",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }

    def start(self, audio_url: str, bvid: str = "") -> bool:
        if self._state == ProducerState.DOWNLOADING:
            return False

        self._audio_url = audio_url
        self._bvid = bvid
        self._stop_event.clear()
        self._pause_event.clear()
        self._downloaded_bytes = 0
        self._total_bytes = 0
        self._download_speed = 0.0
        self._error_message = None

        self._session = requests.Session()

        self._thread = threading.Thread(target=self._download_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self._set_state(ProducerState.STOPPED)

        if self._session:
            self._session.close()
            self._session = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def pause(self):
        self._pause_event.set()
        self._set_state(ProducerState.PAUSED)

    def resume(self):
        self._pause_event.clear()
        if self._state == ProducerState.PAUSED:
            self._set_state(ProducerState.DOWNLOADING)

    def _wait_for_buffer_space(self) -> bool:
        while self.ring_buffer.should_pause_download():
            if self._stop_event.is_set():
                return False
            self._set_state(ProducerState.PAUSED)
            time.sleep(0.1)

        if self._state == ProducerState.PAUSED:
            self._set_state(ProducerState.DOWNLOADING)

        return True

    def _download_loop(self):
        retry_count = 0

        while retry_count < self.max_retries and not self._stop_event.is_set():
            try:
                self._set_state(ProducerState.DOWNLOADING)
                self._last_time = time.time()
                self._last_bytes = 0

                response = self._session.get(
                    self._audio_url,
                    headers=self._get_headers(),
                    stream=True,
                    timeout=30,
                )

                if response.status_code != 200:
                    raise requests.RequestException(f"HTTP {response.status_code}")

                self._total_bytes = int(response.headers.get("Content-Length", 0))

                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if self._stop_event.is_set():
                        return

                    while self._pause_event.is_set():
                        if self._stop_event.is_set():
                            return
                        time.sleep(0.1)

                    if not self._wait_for_buffer_space():
                        return

                    if chunk:
                        success = self.ring_buffer.write_non_blocking(chunk)
                        if success:
                            self._downloaded_bytes += len(chunk)
                            self._update_speed()
                            self._notify_progress()
                        else:
                            time.sleep(0.01)

                self._set_state(ProducerState.STOPPED)
                return

            except requests.Timeout:
                retry_count += 1
                self._error_message = f"下载超时，正在重试 ({retry_count}/{self.max_retries})"
                self._notify_progress()
                time.sleep(self.retry_delay)

            except requests.RequestException as e:
                retry_count += 1
                self._error_message = f"网络错误: {str(e)}，正在重试 ({retry_count}/{self.max_retries})"
                self._notify_progress()
                time.sleep(self.retry_delay)

            except Exception as e:
                self._error_message = f"未知错误: {str(e)}"
                self._set_state(ProducerState.ERROR)
                self._notify_progress()
                return

        self._error_message = f"重试次数已达上限 ({self.max_retries})"
        self._set_state(ProducerState.ERROR)
        self._notify_progress()

    def _update_speed(self):
        current_time = time.time()
        elapsed = current_time - self._last_time

        if elapsed >= 0.5:
            bytes_diff = self._downloaded_bytes - self._last_bytes
            self._download_speed = bytes_diff / elapsed
            self._last_time = current_time
            self._last_bytes = self._downloaded_bytes

    def _notify_progress(self):
        if self._on_progress:
            progress = DownloadProgress(
                downloaded_bytes=self._downloaded_bytes,
                total_bytes=self._total_bytes,
                speed=self._download_speed,
                state=self._state,
                error_message=self._error_message,
            )
            self._on_progress(progress)

    def get_progress(self) -> DownloadProgress:
        return DownloadProgress(
            downloaded_bytes=self._downloaded_bytes,
            total_bytes=self._total_bytes,
            speed=self._download_speed,
            state=self._state,
            error_message=self._error_message,
        )

    @property
    def state(self) -> ProducerState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == ProducerState.DOWNLOADING or self._state == ProducerState.PAUSED
