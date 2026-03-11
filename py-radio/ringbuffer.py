import threading
import collections
import time
from enum import Enum
from typing import Optional, Tuple


class BufferState(Enum):
    EMPTY = "empty"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    FULL = "full"


class AudioRingBuffer:
    def __init__(
        self,
        max_size: int = 1024 * 1024 * 10,
        low_watermark: float = 0.3,
        high_watermark: float = 0.8,
    ):
        self.buffer: collections.deque = collections.deque()
        self.size: int = 0
        self.max_size: int = max_size
        self.low_watermark: float = low_watermark
        self.high_watermark: float = high_watermark

        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)

        self.monitor_thread: bool = False
        self._total_written: int = 0
        self._total_read: int = 0
        self._write_paused: bool = False

    def write(self, chunk: bytes, timeout: float = 5.0) -> bool:
        with self.not_full:
            start_time = time.time()
            while self.size + len(chunk) > self.max_size:
                if time.time() - start_time > timeout:
                    return False
                if not self.not_full.wait(timeout=timeout):
                    return False

            self.buffer.append(chunk)
            self.size += len(chunk)
            self._total_written += len(chunk)
            self.not_empty.notify_all()
            return True

    def write_non_blocking(self, chunk: bytes) -> bool:
        with self.lock:
            if self.size + len(chunk) > self.max_size:
                if self.buffer:
                    removed = self.buffer.popleft()
                    self.size -= len(removed)
                else:
                    return False

            self.buffer.append(chunk)
            self.size += len(chunk)
            self._total_written += len(chunk)
            return True

    def read(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        with self.not_empty:
            if not self.buffer:
                if not self.not_empty.wait(timeout=timeout):
                    return None

            if not self.buffer:
                return None

            result = bytearray()
            remaining = size

            while remaining > 0 and self.buffer:
                chunk = self.buffer[0]

                if len(chunk) <= remaining:
                    result.extend(chunk)
                    remaining -= len(chunk)
                    self.size -= len(chunk)
                    self._total_read += len(chunk)
                    self.buffer.popleft()
                else:
                    result.extend(chunk[:remaining])
                    self.buffer[0] = chunk[remaining:]
                    self.size -= remaining
                    self._total_read += remaining
                    remaining = 0

            self.not_full.notify_all()
            return bytes(result) if result else None

    def read_non_blocking(self, size: int) -> Optional[bytes]:
        with self.lock:
            if not self.buffer:
                return None

            result = bytearray()
            remaining = size

            while remaining > 0 and self.buffer:
                chunk = self.buffer[0]

                if len(chunk) <= remaining:
                    result.extend(chunk)
                    remaining -= len(chunk)
                    self.size -= len(chunk)
                    self._total_read += len(chunk)
                    self.buffer.popleft()
                else:
                    result.extend(chunk[:remaining])
                    self.buffer[0] = chunk[remaining:]
                    self.size -= remaining
                    self._total_read += remaining
                    remaining = 0

            return bytes(result) if result else None

    def get_state(self) -> BufferState:
        with self.lock:
            fill_ratio = self.size / self.max_size

            if fill_ratio == 0:
                return BufferState.EMPTY
            elif fill_ratio < self.low_watermark:
                return BufferState.LOW
            elif fill_ratio > self.high_watermark:
                return BufferState.HIGH
            elif fill_ratio >= 1.0:
                return BufferState.FULL
            else:
                return BufferState.NORMAL

    def get_fill_ratio(self) -> float:
        with self.lock:
            return self.size / self.max_size

    def should_pause_download(self) -> bool:
        return self.get_fill_ratio() > self.high_watermark

    def should_resume_download(self) -> bool:
        return self.get_fill_ratio() < self.low_watermark

    def get_stats(self) -> dict:
        with self.lock:
            return {
                "size": self.size,
                "max_size": self.max_size,
                "fill_ratio": self.size / self.max_size,
                "chunk_count": len(self.buffer),
                "state": self.get_state().value,
                "total_written": self._total_written,
                "total_read": self._total_read,
            }

    def monitor(self) -> Tuple[int, int]:
        stats = self.get_stats()
        print(
            f"Buffer: {stats['fill_ratio']*100:.1f}% "
            f"({stats['size']}/{stats['max_size']} bytes) "
            f"chunks: {stats['chunk_count']} "
            f"state: {stats['state']}"
        )
        return self.size, len(self.buffer)

    def start_monitoring(self, interval: float = 5.0):
        def monitor_loop():
            while self.monitor_thread:
                self.monitor()
                time.sleep(interval)

        self.monitor_thread = True
        threading.Thread(target=monitor_loop, daemon=True).start()

    def clear(self):
        with self.lock:
            self.buffer.clear()
            self.size = 0
            self.not_full.notify_all()

    def stop(self):
        self.monitor_thread = False
        with self.lock:
            self.not_empty.notify_all()
            self.not_full.notify_all()

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.size > 0
