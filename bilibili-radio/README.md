# B站后台播放器



一个基于 Vue 3 + Flask 的 B站视频后台播放器，支持音频流实时播放。

> 当前生产部署已经接入 OIDC、按用户隔离的 B 站凭据与曲库、管理员控制台及 Prometheus/Grafana 监控。完整配置和迁移说明见 [`doc/oidc-admin-monitoring-implementation-2026-07-21.md`](doc/oidc-admin-monitoring-implementation-2026-07-21.md)。本地开发仍可使用无感单用户模式，但只监听 `127.0.0.1`。

## 系统架构



```
┌─────────────────────────────────────────────────────────────────┐
│                        整体系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│   Vue 3 前端                                                     │
│   ├── HTMLAudioElement - 原生音频播放                            │
│   └── Socket.io-client - WebSocket 通信                         │
│                              ↑                                   │
│   Python 后端                                                    │
│   ├── B站API模块 - 获取视频信息和音频URL                          │
│   ├── 流式代理 - 代理转发原始音频流                               │
│   └── Flask + SocketIO - HTTP API + 实时通信                    │
│                              ↑                                   │
│   B站服务器 (api.bilibili.com / CDN)                             │
└─────────────────────────────────────────────────────────────────┘
```



## 数据流



```
用户输入BV号
    ↓
前端 WebSocket 发送 play_video 事件
    ↓
后端解析BV号，调用B站API获取视频信息和音频流URL
    ↓
后端返回代理URL给前端
    ↓
前端 <audio> 元素请求代理URL
    ↓
后端流式代理转发B站CDN的音频流
    ↓
浏览器原生解码AAC音频并播放
```



## 项目结构



```
├── py-radio/                      # Python后端
│   ├── app.py                     # Flask主入口 + WebSocket + 流式代理
│   ├── bilibili_api.py            # B站API封装
│   ├── requirements.txt           # Python依赖
│   └── start.bat                  # Windows启动脚本
│
└── bilibili-player/               # Vue 3前端
    ├── src/
    │   ├── main.ts                # 入口文件
    │   ├── App.vue                # 根组件
    │   ├── audio/
    │   │   ├── StreamingAudioPlayer.ts  # 流式音频播放器
    │   │   └── WsClient.ts              # WebSocket客户端
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

### 前端



- Node.js 18+
- npm 或 yarn

## 安装与运行



### 1. 启动后端服务



**方式一：使用启动脚本**

```
双击运行 py-radio/start.bat
```



**方式二：手动启动**

```
cd py-radio
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python app.py
```



后端服务将在 `http://localhost:5000` 启动

### 2. 启动前端服务



**方式一：使用启动脚本**

```
双击运行 bilibili-player/start.bat
```



**方式二：手动启动**

```
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



| 接口                            | 方法 | 描述           |
| ------------------------------- | ---- | -------------- |
| `/api/video/info/<bvid>`        | GET  | 获取视频信息   |
| `/api/video/audio/<bvid>/<cid>` | GET  | 获取音频流地址 |
| `/api/stream/<bvid>`            | GET  | 流式代理音频流 |
| `/api/stream/stats`             | GET  | 获取流量统计   |
| `/api/stream/stats/reset`       | POST | 重置流量统计   |
| `/api/player/status`            | GET  | 获取播放器状态 |
| `/api/player/stop`              | POST | 停止播放       |

### WebSocket 事件



**客户端发送:**

| 事件         | 数据              | 描述           |
| ------------ | ----------------- | -------------- |
| `play_video` | `{input: string}` | 播放视频       |
| `pause`      | -                 | 暂停播放       |
| `resume`     | -                 | 恢复播放       |
| `stop`       | -                 | 停止播放       |
| `seek`       | `{time: number}`  | 跳转到指定时间 |

**服务端推送:**

| 事件           | 数据                | 描述          |
| -------------- | ------------------- | ------------- |
| `video_info`   | VideoInfo           | 视频信息      |
| `audio_stream` | AudioStreamInfo     | 音频流代理URL |
| `status`       | `{message: string}` | 状态消息      |
| `error`        | `{message: string}` | 错误消息      |

## 核心技术



### 后端



- **Flask + Flask-SocketIO**: HTTP API + WebSocket 实时通信
- **流式代理**: 直接转发原始音频流，无需解码

### 前端



- **Vue 3 + Vite**: 现代化前端框架
- **Pinia**: 状态管理
- **HTMLAudioElement**: 原生音频播放
- **Socket.io-client**: WebSocket 客户端

## 流量优化



采用流式代理方案，直接转发B站原始AAC音频流：

| 方案             | 数据格式                     | 流量 (约)   |
| ---------------- | ---------------------------- | ----------- |
| PCM解码方案      | PCM (44.1kHz, 16bit, stereo) | ~172 KB/s   |
| **流式代理方案** | 原始 AAC (m4s)               | ~16-40 KB/s |

**流量减少约 4-10 倍**

## 故障排除



### 1. 无法播放音频



**检查后端服务:**

```
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



```
cd bilibili-player
npm run build
```



## 许可证



MIT License
