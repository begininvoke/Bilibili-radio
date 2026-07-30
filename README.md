# Bilibili Radio

Bilibili Radio 是一个把 B 站视频当作音乐电台来使用的播放器项目。当前仓库的主要业务代码在 `bilibili-radio/` 目录下，包含 Vue 3 前端、Flask 后端、播放数据服务、字幕/章节/评论信息，以及面向服务器部署的 Docker Compose 配置。

## 主要能力

- B 站扫码登录，复用用户账号获取收藏、历史、播放列表等内容。
- 音频播放、队列、收藏、下载、搜索、播放详情页和迷你播放器。
- 播放详情页支持字幕、简介、章节、评论区和私人评价。
- 私人评价支持星级、情绪标签和可选留言，用于记录个人听歌感受。
- 后端提供播放记录、偏好分析、管理监控和基础身份能力。
- 支持本地开发、Docker Compose 部署，以及临时公网 IP 的 HTTP 部署模式。

## 目录结构

```text
bilibili-radio/
  bilibili-player/      # Vue 3 前端
  py-radio/             # Flask 后端与服务层
  deploy/               # Linux 部署脚本和环境变量示例
  docker-compose*.yml   # 不同部署模式的 Compose 配置
```

仓库根目录仍保留旧的 `bilibili-player/`、`py-radio/` 目录，用于兼容历史结构；当前开发和部署以 `bilibili-radio/` 为准。

## 本地开发

后端：

```powershell
cd bilibili-radio\py-radio
pip install -r requirements.txt
python app.py
```

前端：

```powershell
cd bilibili-radio\bilibili-player
npm install
npm run dev
```

默认前端开发服务会代理到本地后端。首次使用需要通过 B 站扫码完成登录。

## Linux 部署

在服务器上解压部署包后：

```bash
tar -xzf bilibili-radio-deploy.tar.gz
cd bilibili-radio
cp deploy/env.http-ip.example .env
bash deploy/deploy.sh http-ip
```

`http-ip` 是临时公网 IP 模式，会关闭应用内登录鉴权，适合短期验证。生产环境应放在防火墙、VPN、安全组或反向代理之后，并优先使用域名、HTTPS 和正式鉴权配置。

## 常用检查

后端测试：

```powershell
cd bilibili-radio\py-radio
python -m pytest -q
```

前端构建：

```powershell
cd bilibili-radio\bilibili-player
npm run build
```

部署配置检查：

```bash
docker compose -f bilibili-radio/docker-compose.yml -f bilibili-radio/docker-compose.http-ip.yml config
```
