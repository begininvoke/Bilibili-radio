# B站实时音频流播放系统规范文档

## 1. 项目概述

### 1.1 目标
构建一个完整的B站实时音频流播放系统，实现从B站API获取音频流、缓冲管理到音频播放的完整流程。

### 1.2 系统架构
```
B站API → [Producer下载流] → [RingBuffer] → [Consumer播放] → 音频输出
```

### 1.3 核心组件
1. **Producer (worker.py)** - 音频流生产者
2. **RingBuffer (ringbuffer.py)** - 环形缓冲区
3. **Consumer (player.py)** - 音频播放消费者

## 2. 组件详细规范

### 2.1 AudioRingBuffer (ringbuffer.py)

#### 当前状态
✅ 已实现条件变量等待机制  
✅ 已实现监控功能  
⚠️ 需要优化性能和添加流量控制  

#### 改进需求
1. **性能优化**
   - 减少内存分配频率
   - 添加缓冲区水位控制
   - 优化读写性能

2. **功能增强**
   - 添加流量控制接口
   - 添加缓冲区状态查询
   - 添加优雅停止机制

3. **线程安全增强**
   - 添加停止信号处理
   - 防止死锁

#### 接口规范
```python
class AudioRingBuffer:
    def __init__(self, max_size=10MB)
    def write(chunk) -> None
    def read(size, timeout) -> bytes
    def get_buffer_level() -> float  # 新增
    def is_writeable() -> bool  # 新增
    def stop() -> None
    def clear() -> None
```

### 2.2 AudioStreamProducer (worker.py)

#### 当前状态
⚠️ Flask API功能完整  
❌ 生产者逻辑不完整  
❌ 缺少错误处理和重连  
❌ RingBuffer实例管理混乱  

#### 改进需求
1. **架构重构**
   - 分离Flask API和Producer逻辑
   - 创建独立的Producer类
   - 实现全局RingBuffer管理

2. **生产者功能**
   - 实现持续流下载
   - 添加错误重连机制
   - 添加流量控制
   - 支持多音频源切换

3. **状态管理**
   - 添加播放状态跟踪
   - 实现优雅启动/停止
   - 添加进度监控

#### 接口规范
```python
class AudioStreamProducer(threading.Thread):
    def __init__(self, ring_buffer, audio_url, headers)
    def run() -> None
    def stop() -> None
    def pause() -> None
    def resume() -> None
    def get_status() -> dict
```

### 2.3 AudioPlayer (player.py)

#### 当前状态
❌ 完全未实现  

#### 实现需求
1. **核心功能**
   - 从RingBuffer读取音频数据
   - 使用音频库播放（pyaudio/simpleaudio）
   - 支持暂停/恢复/停止

2. **音频处理**
   - 支持AAC/MP3解码
   - 处理音频格式转换
   - 控制播放速度和音量

3. **同步机制**
   - 与Producer协调
   - 处理缓冲区欠载
   - 实现平滑播放

#### 接口规范
```python
class AudioPlayer(threading.Thread):
    def __init__(self, ring_buffer)
    def run() -> None
    def play() -> None
    def pause() -> None
    def stop() -> None
    def set_volume(volume: float) -> None
    def get_status() -> dict
```

## 3. 集成规范

### 3.1 数据流管理
```
1. Flask API接收播放请求
2. 创建/获取全局RingBuffer实例
3. 启动Producer下载音频流
4. 启动Player播放音频
5. 监控播放状态
6. 处理停止/切换请求
```

### 3.2 错误处理
- 网络错误：自动重连，最多3次
- 缓冲区溢出：丢弃旧数据
- 缓冲区欠载：暂停播放，等待数据
- 解码错误：跳过错误帧

### 3.3 性能指标
- 缓冲区大小：10MB（可配置）
- 初始缓冲：至少1MB后开始播放
- 低水位：30%开始预警
- 高水位：80%暂停下载

## 4. 文件结构规范

```
py-radio/
├── ringbuffer.py      # 环形缓冲区
├── worker.py          # Flask API + Producer
├── player.py          # 音频播放器
├── constant.py        # 常量配置
├── ErrorConstant.py   # 错误定义
├── Result.py          # 结果封装
└── requirements.txt   # 依赖管理
```

## 5. 技术选型

### 5.1 音频播放库
**推荐：pyaudio**
- 优点：跨平台、低延迟、功能完整
- 缺点：需要PortAudio库

**备选：simpleaudio**
- 优点：纯Python、简单易用
- 缺点：功能较少

### 5.2 音频解码
**推荐：ffmpeg + pydub**
- 支持多种格式
- 成熟稳定

## 6. 测试规范

### 6.1 单元测试
- RingBuffer读写测试
- Producer下载测试
- Player播放测试

### 6.2 集成测试
- 端到端播放流程
- 错误恢复测试
- 性能压力测试

## 7. 部署规范

### 7.1 环境要求
- Python 3.7+
- PortAudio库（pyaudio依赖）
- ffmpeg（音频解码）

### 7.2 配置管理
- 缓冲区大小
- 超时时间
- 重试策略
