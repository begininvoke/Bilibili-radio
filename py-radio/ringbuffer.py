import threading
import collections
import time
import subprocess

class AudioRingBuffer:
    def __init__(self, max_size=1024*1024*10):
        self.buffer = collections.deque()
        self.size = 0
        self.max_size = max_size
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)  # 用于通知读取线程有新数据可读（条件变量）
        self.monitor_thread = False
        self.playing = False




    def start_decode(self, url, referer="https://www.bilibili.com") :
        # 启动 FFmpeg 进程，将音频流转码为 PCM 并写入 RingBuffer
        cmd = [
            'ffmpeg',
            '-headers', f'Referer: {referer}',
            '-i', url,                 # 输入：B站音频流 URL
            '-f', 's16le',             # 输出格式：16-bit Little-Endian PCM
            '-acodec', 'pcm_s16le',    # 编解码器
            '-ar', '44100',            # 采样率
            '-ac', '2',                # 声道数
            '-'                        # 输出到 stdout
        ]
        self.ffmpeg_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,    
            stderr=subprocess.PIPE     
        )
        self.playing = True
            
    def _produce_loop(self):
        # 从 FFmpeg stdout 读取 PCM 数据，写入 RingBuffer
        chunk_size = 4096  #4KB
        while self.playing:
            chunk = self.ffmpeg_process.stdout.read(chunk_size)
            if not chunk:
                break  # 解码退出
            self.buffer.write(chunk)
        self.playing = False
        self.ffmpeg_process.stdout.close()


    # 条件变量写法while(条件不符合) wait();
    def write(self, chunk):
        with self.not_empty:
            while self.size + len(chunk) > self.max_size:
                # lru - remove oldest data if needed
                if self.buffer:
                    removed = self.buffer.popleft()
                    self.size -= len(removed)
                else:
                    break
            self.buffer.append(chunk)
            self.size += len(chunk)
            # 通知读取线程有新数据可读
            self.not_empty.notify_all()

    def read(self, size, timeout=None):
        with self.not_empty:
            while not self.buffer:
                if not self.not_empty.wait(timeout=timeout):
                     return None 
            
            result = bytearray()
            remaining = size
            
            while remaining > 0 and self.buffer:
                chunk = self.buffer[0]  # 查看第一个块
                
                if len(chunk) <= remaining:
                    # 整块取走
                    result.extend(chunk)
                    remaining -= len(chunk)
                    self.size -= len(chunk)
                    self.buffer.popleft()
                else:
                    # 只取部分，剩下的留在 deque 头部
                    result.extend(chunk[:remaining])
                    self.buffer[0] = chunk[remaining:]  # 更新头部块
                    self.size -= remaining
                    remaining = 0     
            return bytes(result) if result else None


    def monitor(self):
        progress = (self.size / self.max_size) * 100
        print(f"Buffer Progress: {progress:.2f}% ({self.size}/{self.max_size} bytes)")
        return self.size, len(self.buffer)
    
    def start_monitoring(self, interval=5):
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
    
    def stop(self):
        self.monitor_thread = False