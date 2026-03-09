import threading
import collections

class AudioRingBuffer:
    def __init__(self, max_size=1024*1024*10):  # 默认10MB
        self.buffer = collections.deque()
        self.size = 0
        self.max_size = max_size
        self.lock = threading.Lock()
        