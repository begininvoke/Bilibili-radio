# B站后台播放器

一个基于 Vue 3 + Flask 的 B站视频后台播放器，支持音频流实时播放。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        整体系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│   Vue 3 前端 (消费者)                                            │
│   ├── Web Audio API (AudioWorklet) - 音频解码与播放              │
│   └── WebSocket Client - 接收音频流                              │
│                              ↑                                   │
│   Python 后端 (生产者)                                           │
│   ├── B站API模块 - 获取视频信息和音频URL                          │
│   ├── FFmpeg - 音频解码 (AAC → PCM)                              │
│   ├── RingBuffer - 线程安全的环形缓冲区                           │
│   └── Flask + WebSocket - HTTP API + 实时通信                    │
│                              ↑                                   │
│   B站服务器 (api.bilibili.com / CDN)                             │
└─────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
e:\plug\
├── py-radio/                      # Python后端
│   ├── app.py                     # Flask主入口 + WebSocket
│   ├── bilibili_api.py            # B站API封装
│   ├── producer.py                # 流式下载生产者
│   ├── consumer.py                # 消费者（解码+推送）
│   ├── ringbuffer.py              # 环形缓冲区
│   ├── config.py                  # 配置文件
│   ├── constant.py                # 常量定义
│   ├── requirements.txt           # Python依赖
│   └── start.bat                  # Windows启动脚本
│
└── bilibili-player/               # Vue 3前端
    ├── src/
    │   ├── main.ts                # 入口文件
    │   ├── App.vue                # 根组件（透明背景）
    │   ├── audio/
    │   │   ├── AudioPlayer.ts     # 音频播放器核心
    │   │   └── WsClient.ts        # WebSocket客户端
    │   ├── stores/
    │   │   └── playerStore.ts     # 播放状态管理
    │   ├── components/
    │   │   ├── PlayerControls.vue # 播放控制组件
    │   │   ├── ProgressBar.vue    # 进度条组件
    │   │   ├── VolumeControl.vue  # 音量控制组件
    │   │   ├── StatusDisplay.vue  # 状态显示组件
    │   │   ├── VideoInfo.vue      # 视频信息组件
    │   │   └── UrlInput.vue       # URL输入组件
    │   └── types/
    │       └── index.ts           # TypeScript类型定义
    ├── package.json
    ├── vite.config.ts
    └── start.bat                  # Windows启动脚本
```

## 环境要求

### 后端
- Python 3.8+
- FFmpeg（用于音频解码）

### 前端
- Node.js 18+
- npm 或 yarn

## 安装与运行

### 1. 安装 FFmpeg

**Windows:**
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到任意目录（如 `C:\ffmpeg`）
3. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量

**验证安装:**
```bash
ffmpeg -version
```

### 2. 启动后端服务

**方式一：使用启动脚本**
```bash
双击运行 py-radio/start.bat
```

**方式二：手动启动**
```bash
cd py-radio
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python app.py
```

后端服务将在 `http://localhost:5000` 启动

### 3. 启动前端服务

**方式一：使用启动脚本**
```bash
双击运行 bilibili-player/start.bat
```

**方式二：手动启动**
```bash
cd bilibili-player
npm install
npm run dev
```

前端服务将在 `http://localhost:3000` 启动

## 使用方法

1. 打开浏览器访问 `http://localhost:3000`
2. 在输入框中输入 B站视频链接或BV号
   - 例如：`https://www.bilibili.com/video/BV1xx411c7mD`
   - 或直接输入：`BV1xx411c7mD`
3. 点击"播放"按钮开始播放
4. 使用控制按钮进行播放控制：
   - ▶/⏸ 播放/暂停
   - ⏹ 停止
   - 🔊 音量调节
   - 进度条拖动跳转

## API 接口

### HTTP API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/video/info/<bvid>` | GET | 获取视频信息 |
| `/api/video/audio/<bvid>/<cid>` | GET | 获取音频流地址 |
| `/api/player/status` | GET | 获取播放器状态 |
| `/api/player/stop` | POST | 停止播放 |

### WebSocket 事件

**客户端发送:**
| 事件 | 数据 | 描述 |
|------|------|------|
| `play_video` | `{input: string}` | 播放视频 |
| `pause` | - | 暂停播放 |
| `resume` | - | 恢复播放 |
| `stop` | - | 停止播放 |
| `seek` | `{time: number}` | 跳转到指定时间 |

**服务端推送:**
| 事件 | 数据 | 描述 |
|------|------|------|
| `video_info` | VideoInfo | 视频信息 |
| `audio_data` | AudioDataPacket | 音频PCM数据 |
| `playback_progress` | PlaybackProgress | 播放进度 |
| `download_progress` | DownloadProgress | 下载进度 |
| `status` | `{message: string}` | 状态消息 |
| `error` | `{message: string}` | 错误消息 |

## 核心技术

### 后端
- **Flask + Flask-SocketIO**: HTTP API + WebSocket 实时通信
- **FFmpeg**: 音频解码 (AAC/M4A → PCM)
- **RingBuffer**: 线程安全的环形缓冲区，支持流量控制
- **多线程**: 生产者-消费者模式

### 前端
- **Vue 3 + Vite**: 现代化前端框架
- **Pinia**: 状态管理
- **Web Audio API**: 音频播放
- **ScriptProcessorNode**: PCM 数据处理
- **Socket.io-client**: WebSocket 客户端

## 配置说明

### 后端配置 (py-radio/config.py)

```python
BUFFER_MAX_SIZE = 10 * 1024 * 1024      # 缓冲区大小 (10MB)
BUFFER_HIGH_WATERMARK = 0.8              # 高水位 (暂停下载)
BUFFER_LOW_WATERMARK = 0.3               # 低水位 (恢复下载)
PRODUCER_CHUNK_SIZE = 64 * 1024          # 下载块大小 (64KB)
PLAYER_SAMPLE_RATE = 44100               # 采样率
PLAYER_CHANNELS = 2                      # 声道数
```

### 前端配置 (bilibili-player/vite.config.ts)

```typescript
server: {
  port: 3000,                           // 前端端口
  proxy: {                              // 代理配置
    '/api': 'http://localhost:5000',
    '/socket.io': 'http://localhost:5000'
  }
}
```

## 故障排除

### 1. 无法播放音频

**检查 FFmpeg:**
```bash
ffmpeg -version
```

**检查后端服务:**
```bash
curl http://localhost:5000/api/player/status
```

### 2. WebSocket 连接失败

- 确认后端服务已启动
- 检查端口 5000 是否被占用
- 检查浏览器控制台错误信息

### 3. 获取视频信息失败

- 确认 BV 号格式正确
- 检查网络连接
- 确认视频是否存在

## 开发说明

### 构建生产版本

```bash
cd bilibili-player
npm run build
```

### 类型检查

```bash
cd bilibili-player
npm run type-check
```

## 许可证

MIT License
