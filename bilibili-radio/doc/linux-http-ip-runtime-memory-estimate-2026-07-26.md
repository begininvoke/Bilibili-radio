# Linux HTTP/IP 临时部署与内存估算

## HTTP/IP 模式定位

`http-ip` 是临时过渡方案，不是正式生产方案。

它的特点是：

- 使用公网 IP + HTTP。
- 不配置域名、HTTPS、OIDC。
- `AUTH_MODE=disabled`，应用层会把访问者视为本地 owner。

因此它只能用于：

- 服务器安全组只放行自己的公网 IP。
- 或放在 VPN/Tailscale 内部。
- 或短时间自测、验收、排查部署问题。

一旦要公开给其他人访问，应切到 `production` 或后续自研鉴权模式。

## 包大小

当前 `bilibili-radio-deploy.tar.gz` 约 `3.49 MB`。这是源码部署包，不包含：

- `node_modules`
- 前端 `dist`
- SQLite 运行数据
- 日志
- 本机未跟踪目录

服务器第一次部署会在服务器上构建 Docker 镜像，镜像磁盘占用会远大于 tar.gz。

## 运行内存粗估

单机 `http-ip` 模式只启动：

- `backend`：Python + Gunicorn gthread
- `frontend`：Nginx 静态文件 + API 反代

预估常驻内存：

- 前端 Nginx：约 `20-60 MB`
- 后端 Gunicorn 2 workers + 16 threads：约 `220-450 MB`
- Docker/系统额外开销：约 `50-150 MB`

建议服务器内存：

- 最低可跑：`1 GB`
- 更稳：`2 GB`
- 如果同时开 Prometheus/Grafana：建议 `4 GB+`

## 调低内存的参数

小机器可以在 `.env` 里调低：

```dotenv
WEB_CONCURRENCY=1
WEB_THREADS=8
```

这样后端常驻内存通常能降一截，但并发音频代理能力也会下降。

## 精确测量

部署后用：

```bash
docker stats
docker compose ps
docker compose logs -f backend
```

以服务器实测为准。
