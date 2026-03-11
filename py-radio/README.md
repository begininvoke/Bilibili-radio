# B站音频播放器

基于PySide6的B站实时音频流播放器，支持从B站API获取音频流并实时播放。

## 功能特性

- ✅ 支持B站视频URL或BV号输入
- ✅ 自动获取视频信息和音频流地址
- ✅ 实时音频流播放
- ✅ 播放控制（播放/暂停/停止）
- ✅ 音量调节
- ✅ 缓冲区监控
- ✅ 下载和播放速度实时显示

## 系统架构

```
B站API → [Producer下载流] → [RingBuffer] → [Player播放] → 音频输出
```

### 核心组件

1. **RingBuffer (ringbuffer.py)** - 环形缓冲区
   - 线程安全的数据缓冲
   - 自动流量控制
   - 高/低水位管理

2. **Producer (worker.py)** - 音频流生产者
   - 使用FFmpeg解码音频流
   - 自动错误重连
   - 流量自适应控制

3. **Player (player.py)** - 音频播放器
   - PySide6 GUI界面
   - PyAudio音频输出
   - 实时状态监控

## 安装依赖

### 系统要求

- Python 3.7+
- FFmpeg（用于音频解码）
- PortAudio（用于音频播放）

### Windows安装

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 安装FFmpeg：
   - 下载FFmpeg: https://ffmpeg.org/download.html
   - 添加到系统PATH环境变量

3. 安装PortAudio：
   - 通常pyaudio会自动安装PortAudio
   - 如果失败，可以尝试：`pip install pipwin && pipwin install pyaudio`

### Linux安装

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg portaudio19-dev
pip install -r requirements.txt

# CentOS/RHEL
sudo yum install ffmpeg portaudio-devel
pip install -r requirements.txt
```

## 使用方法

### 1. 启动Flask API服务器

```bash
python worker.py
```

服务器将在 `http://localhost:5000` 启动。

### 2. 启动播放器GUI

```bash
python player.py
```

### 3. 使用播放器

1. 在输入框中输入B站视频URL或BV号
   - 例如：`https://www.bilibili.com/video/BV1xx411c7mD`
   - 或直接输入：`BV1xx411c7mD`

2. 点击"获取信息"按钮
3. 查看视频信息（标题、时长、UP主等）
4. 点击"播放"按钮开始播放
5. 使用控制按钮进行播放控制
6. 使用音量滑块调节音量

## API接口

### 获取视频信息
```
GET /get_video_info/<bvid>
```

### 获取播放地址
```
GET /get_play_url/<bvid>/<cid>
```

### 开始播放
```
POST /start_play
Body: {
    "audio_url": "音频流URL",
    "bvid": "BV号"
}
```

### 停止播放
```
POST /stop_play
```

### 暂停播放
```
POST /pause_play
```

### 恢复播放
```
POST /resume_play
```

### 获取状态
```
GET /status
```

## 配置说明

编辑 `config.py` 可以调整以下参数：

- `BUFFER_MAX_SIZE`: 缓冲区大小（默认10MB）
- `BUFFER_HIGH_WATERMARK`: 高水位（默认0.8）
- `BUFFER_LOW_WATERMARK`: 低水位（默认0.3）
- `PRODUCER_CHUNK_SIZE`: 生产者块大小（默认4KB）
- `PLAYER_SAMPLE_RATE`: 播放采样率（默认44100Hz）
- `MONITOR_INTERVAL`: 监控刷新间隔（默认3秒）

## 故障排除

### 1. 无法播放音频

**检查FFmpeg是否安装：**
```bash
ffmpeg -version
```

**检查PortAudio是否安装：**
```bash
python -c "import pyaudio; p = pyaudio.PyAudio(); print('OK')"
```

### 2. 网络错误

- 检查网络连接
- 确认B站视频是否可访问
- 检查API服务器是否正常运行

### 3. 缓冲区问题

- 调整 `BUFFER_MAX_SIZE` 增加缓冲区大小
- 检查网络带宽是否足够
- 查看控制台输出的监控信息

## 性能优化建议

1. **网络优化**
   - 使用稳定的网络连接
   - 考虑使用代理或CDN

2. **缓冲区优化**
   - 根据网络状况调整缓冲区大小
   - 调整高/低水位阈值

3. **播放优化**
   - 调整chunk大小以平衡延迟和稳定性
   - 根据CPU性能调整采样率

## 开发说明

### 项目结构
```
py-radio/
├── ringbuffer.py      # 环形缓冲区
├── worker.py          # Flask API + Producer
├── player.py          # PySide6 GUI播放器
├── config.py          # 配置文件
├── constant.py        # 常量定义
├── ErrorConstant.py   # 错误定义
├── Result.py          # 结果封装
├── requirements.txt   # 依赖列表
└── README.md          # 说明文档
```

### 扩展开发

1. **添加新的音频源**
   - 在 `worker.py` 中添加新的API接口
   - 实现相应的Producer逻辑

2. **自定义GUI**
   - 修改 `player.py` 中的UI布局
   - 添加新的控制功能

3. **性能监控**
   - 扩展监控指标
   - 添加日志记录

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
