# OIDC 域名/IP 与 B 站扫码鉴权决策（2026-07-22）

## 决策结论

OIDC 标准本身不要求绑定服务器 IP。当前项目的生产 OIDC 部署只需要一个稳定的 HTTPS 应用入口、在身份提供方登记精确回调 URI，以及让后端能够访问身份提供方的 Discovery/JWKS/Token 端点。

针对当前仓库，建议如下：

- 公网、多用户或需要统一管理播放器与 Grafana：保留现有 OIDC。
- 私有部署、所有用户都必须拥有 B 站账号，且确定接受 B 站扫码接口的稳定性与合规风险：可以改为“B 站扫码证明身份 + 本地不透明 Session Cookie”。
- 不建议 Web 端改为前端持有 JWT access token + refresh token。当前服务端 Session 已经具备哈希存储、过期、空闲超时、吊销、并发会话限制和 `HttpOnly` Cookie，双 Token 会增加刷新轮换、重放检测和前端泄漏面，却不会消除 HTTPS 与稳定入口的需求。

因此，本轮不应直接删除 OIDC 或实施双 Token。若产品边界确认是“仅 B 站用户的私有/垂直应用”，再按本文迁移方案把扫码提升为应用登录入口，并继续复用现有服务端 Session。

## 当前只有服务器、没有域名时的执行决定

生产方向不改鉴权，先准备一个自有域名并把子域名解析到服务器，例如 `radio.example.com`，再使用现有 Caddy 自动启用 HTTPS 和 OIDC。购买及配置域名的成本显著低于重写并长期维护扫码登录、双 Token、刷新轮换、吊销和 Grafana 鉴权。

域名生效前只允许受控测试：通过防火墙仅放行自己的固定 IP，或放在 VPN/Tailscale 内部；可以临时使用 `AUTH_MODE=disabled`，但绝不能在该模式下直接暴露公网，因为它会把所有请求视为 `legacy-owner`。不要把裸公网 IP + HTTP 当作生产过渡方案。

### 域名预算（2026-07-22 查询）

- 普通、未被注册的 `.com` 按每年约 **70-100 元人民币**准备预算即可；阿里云当前公开页面展示的常规定价处于约 85-95 元/年区间，优惠首年价格会变化。
- `.cn` 通常更便宜，阿里云当前页面展示约 38-42 元/年，但本项目没有必要为了每年几十元差价改变后缀选择。
- 不要依据 `.xyz`、`.top` 等“首年 1 元”促销做生产决策，必须先看第二年续费价。
- 一个主域名可以免费创建多个子域名，例如 `radio.example.com`、`id.example.com`，不需要分别购买。

价格会随注册商和活动变化，购买时以结算页的“续费价格”为主要比较项，而不是首年促销价。

### Cloudflare 注册与性能选择

Cloudflare Registrar 适合非中国内地服务器：域名按注册局与 ICANN 成本价注册、续费，无额外加价，并默认自动续费。其限制是域名必须持续使用 Cloudflare 权威 DNS，不能自行切换到其他 DNS 服务商。

“在 Cloudflare 注册域名”本身不会让网站变慢。速度取决于 DNS 记录的代理状态：

- 推荐初始配置：`radio` 的 `A` 记录指向服务器公网 IP，并设置为 **DNS only（灰色云）**。Cloudflare 只回答 DNS，浏览器直接连接服务器，Caddy 负责 HTTPS，不增加 Cloudflare 代理链路。
- 暂不启用 **Proxied（橙色云）**。开启后，HTTP/HTTPS 流量会先经过 Cloudflare 再回源；中国大陆用户使用普通全球网络时可能出现额外跨境延迟和丢包，尤其不适合未经实测就承载本项目的动态音频流。
- Cloudflare 中国网络是单独的 Enterprise 订阅，不属于普通免费域名/DNS套餐。

服务器地域决定注册商：

- 服务器在中国香港、日本、新加坡或其他境外地区：可直接使用 Cloudflare Registrar，并先采用灰色云。
- 服务器在中国内地且需要 ICP 备案：域名注册商必须满足工信部批复要求。为避免备案核验受阻，优先在阿里云或腾讯云注册并完成实名认证；注册后仍可把 DNS 托管到 Cloudflare，但面向中国大陆用户时同样建议先使用灰色云实测。

### 候选域名 `biliplay.xyz` 评估

截至 2026-07-22，本地 DNS 查询无记录，`.xyz` 注册局 RDAP 返回未找到，与注册页面显示可购买的状态一致。`.xyz` 在 HTTPS、OIDC 和 DNS 上没有技术障碍，后缀本身也不会影响访问速度。

但不建议把 `biliplay.xyz` 作为长期公开产品域名：

- `Bili Play` 已存在其他网站和社交账号使用痕迹，名称区分度不足。
- `bili` 容易使用户误以为产品由 Bilibili 官方提供或背书；B 站开放平台开发者协议对未经授权使用其商标、服务标记和域名标识有明确限制。个人内测风险较低，公开商业化前不应依赖这个名字。
- 页面显示的 `¥14.00` 必须在结算页确认币种以及第二年续费价；如果是首年促销，不能据此评估长期成本。

结论：可用于短期个人测试，但正式生产应选择不含 `bili`、可独立注册商标和运营的原创名称。

### 一年试运行方案：`piliplay.xyz` + 阿里云注册 + 吉隆坡服务器

截至 2026-07-22，`piliplay.xyz` 的 DNS 无记录，`.xyz` 注册局 RDAP 返回未找到，公开搜索未发现明显同名产品冲突。该名称比 `biliplay.xyz` 更适合作为一年试运行域名，但正式商业化前仍需单独完成商标检索。

推荐拓扑：

```text
piliplay.xyz（阿里云注册 / 初期使用 AliDNS）
  -> A 记录
  -> 吉隆坡服务器公网 IP
  -> Caddy :80/:443
  -> frontend / backend / grafana
```

落地配置：

- `APP_DOMAIN=piliplay.xyz`
- `APP_EXTERNAL_URL=https://piliplay.xyz`
- `APP_TRUSTED_HOSTS=piliplay.xyz`
- 播放器 OIDC 回调：`https://piliplay.xyz/api/session/callback`
- Grafana OIDC 回调：`https://piliplay.xyz/grafana/login/generic_oauth`
- AliDNS `A @ -> <吉隆坡服务器 IP>`，TTL 初始设为 600 秒；Caddy 负责公开证书。
- 公网只开放 80/443；SSH 仅允许固定 IP 或 VPN；后端、Grafana、Prometheus 不直接暴露。

阿里云这里只承担域名注册和初期权威 DNS，不是应用托管平台，也不会自动提供当前代码需要的 OIDC IdP。仍需使用托管 IdP，或另外部署 `id.piliplay.xyz` 对应的 IdP 服务。以后将 NS 改到 Cloudflare 时，注册商和续费入口仍留在阿里云。

性能判断取决于用户位置：

- 用户主要在马来西亚或东南亚：吉隆坡节点合适。
- 用户主要在中国大陆：主要风险是浏览器到吉隆坡，以及吉隆坡后端访问 B 站 API/CDN 的两段跨境链路；Cloudflare 橙色云无法稳定解决动态、带鉴权的音频回源。上线前必须从目标用户网络实测首页、搜索、首字节和连续播放。

虽然计划只使用一年，仍建议在阿里云开启自动续费，至少在到期前 60 天确定续费或迁移。域名到期会同时破坏 HTTPS、OIDC 回调、Cookie 域和已有书签；若迁移，应先让新旧域名并行至少 30 天，完成 IdP 回调与应用配置切换后再关闭旧域名续费。

### 公网 IP 临时验收模式

域名配置完成前，可以用公网 IP 做短期单人验收，但必须同时满足：

- 云安全组/防火墙的 80 端口只放行维护者自己的固定公网 IP，SSH 也只允许该 IP 或 VPN；5000、3000、9090、9093 等内部端口不开放。
- 使用基础 `docker-compose.yml`，临时设置 `AUTH_MODE=disabled`，通过 `http://<服务器公网IP>` 访问。
- 不把链接发给其他人，不把该模式当公测或生产入口。
- 测试完成后立即切换到域名 + HTTPS + OIDC，再扩大安全组访问范围。

原因是 `AUTH_MODE=disabled` 会让每个请求直接获得 `legacy-owner` 身份，等价于绕过应用登录；一旦 80 端口对全网开放，任何访问者都可能操作管理员数据和已绑定的 B 站账号。公网 IP 上强行启用 OIDC 还需要受信任 HTTPS 证书以及 IdP 接受精确的 IP 回调 URI，作为几天的过渡方案不值得实施。

### 权威 DNS 服务商选择

对 `piliplay.xyz` 一年试运行、吉隆坡单服务器的当前阶段，首选为阿里云默认免费权威 DNS：注册、续费和解析在一个控制台完成，变量最少；DNS 只负责把域名解析成 IP，不承载音频数据，因此不会成为音频速度瓶颈。若以后需要 Cloudflare 的 WAF、代理或更全球化的 Anycast DNS，再迁移 NS，不需要转移域名注册商。

可靠备选：

| 服务 | 当前成本 | 适用场景 | 本项目判断 |
| --- | --- | --- | --- |
| Cloudflare DNS | Free/Pro 权威 DNS 查询免费 | 全球用户、需要代理/WAF | 首选迁移目标 |
| AWS Route 53 | 每托管区 USD 0.50/月，普通查询 USD 0.40/百万次 | 全球生产、希望 DNS 与注册商解耦 | 最佳付费备选 |
| DNSPod | 免费版免费但无 SLA、最低 TTL 600 秒；专业版新购约 99 元、续费约 188 元/年 | 用户主要在中国大陆 | 国内向备选 |
| Alibaba Cloud DNS | 阿里云注册域名默认可使用免费公共权威 DNS；免费版无 SLA | 当前试运行、已有阿里云账号 | 当前首选 |

购买前必须先决定是否需要自由切换 DNS：

- 在 Cloudflare Registrar 直接购买的域名必须持续使用 Cloudflare Nameserver；若要改成 Route 53 或 DNSPod，需要先把域名转出注册商。
- 若希望随时切换权威 DNS，应在支持自定义 Nameserver 的独立注册商购买，再把 NS 指向 Cloudflare、Route 53 或 DNSPod。

当前不实施多权威 DNS。双供应商需要记录同步、DNSSEC multi-signer、故障切换演练和一致性监控，复杂度与一年单机试运行不匹配。

### 在阿里云购买 `piliplay.xyz` 的落地方案

域名注册商与权威 DNS 服务商是两件独立的事情。在阿里云购买域名不会把 DNS 永久锁在阿里云；后续仍可在阿里云域名控制台修改 NS，将解析迁移到 Cloudflare、Route 53 或其他服务商。域名续费始终由阿里云负责，修改 NS 不等于转移注册商。

针对当前“一年试运行 + 吉隆坡单服务器”的阶段，建议采用以下最小生产方案：

1. 在阿里云创建并通过实名认证的域名信息模板，然后购买 `piliplay.xyz` 一年。
2. 核对首年价和续费价；建议开启自动续费，若试运行结束后确定不再使用，再提前 30～60 天关闭，避免域名意外过期。
3. 起步阶段保留阿里云默认提供的免费权威 DNS，不必为了 DNS 本身立即接入 Cloudflare。
4. 创建 `A` 记录：主机记录 `@` 指向吉隆坡服务器公网 IPv4，TTL 可先设为 600 秒；如需 `www`，增加 `CNAME www -> piliplay.xyz`。
5. 服务器只向公网开放 80/443，由 Caddy 或 Nginx 申请证书并反向代理应用；数据库、Redis、Grafana 等内部端口不得直接暴露。
6. 将正式入口固定为 `https://piliplay.xyz`，再把 OIDC 回调地址、Cookie Secure 策略和应用外部地址统一切到该域名。

若以后确实需要 Cloudflare 的代理、WAF 或抗攻击能力，迁移顺序必须是：

1. 先在 Cloudflare 添加站点并复制现有全部 DNS 记录；
2. 确认 Cloudflare 分配的两条 NS；
3. 如阿里云侧已经启用 DNSSEC，先关闭 DNSSEC 并删除 DS 记录；
4. 再到阿里云“域名控制台 → DNS 管理 → DNS 修改”替换 NS；
5. 等待全球生效并验证解析后，再决定是否为 Web 记录开启橙云代理。

不要先改 NS、后补记录，否则传播期间会出现解析中断。对音频流和动态接口，Cloudflare 初次接入仍建议先使用“仅 DNS（灰云）”，确认链路稳定后再逐项开启代理。

### 阿里云免费解析与 Caddy 免费证书

一句话执行结论：购买域名后，在阿里云免费 DNS 中把 `piliplay.xyz` 的 `A` 记录指向服务器公网 IP，并让公网 80/443 到达 Caddy；Caddy 随后自动申请、部署和续期公开可信的 HTTPS 证书，无需另购 SSL 证书。HTTPS 就绪后，OIDC Client 的回调地址仍需单独登记为 `https://piliplay.xyz/api/session/callback`。

阿里云注册的域名会默认分配免费的公网权威 DNS，不需要另购解析套餐即可创建 `A`、`AAAA`、`CNAME` 等基础记录。自 2026-06-24 起，免费版按主域名计算的日解析量限额为 10 万次；超限后可能动态限速，并且免费版没有 SLA。DNS 查询通常会被运营商或客户端缓存，10 万次 DNS 查询不等于 10 万次页面访问，因此当前个人试运行预计足够，但正式大规模生产需要监控解析量并考虑付费 DNS 或迁移服务商。

“Caddy 申请免费证书”是指 Caddy 通过 ACME 协议，自动向 Let's Encrypt 或 ZeroSSL 等公共证书机构申请浏览器信任的 TLS 证书。证书本身免费；Caddy 还会自动保存证书、在到期前续期，并把 HTTP 请求重定向到 HTTPS。证书不是 Caddy 自己伪造或签发的。

自动签发必须同时满足：

1. `piliplay.xyz` 的 `A` 记录已经解析到吉隆坡服务器公网 IPv4；
2. 云安全组和服务器防火墙允许公网访问 TCP 80、TCP 443；
3. 80/443 没有被其他进程占用，并且最终转发到 Caddy；
4. Caddy 配置中出现真实域名，而不是裸公网 IP；
5. Caddy 的 `/data` 持久化且可写，避免容器重建后丢失证书状态。

当前仓库已经满足配置结构要求：`deploy/Caddyfile` 使用 `{$APP_DOMAIN}` 触发自动 HTTPS，`docker-compose.production.yml` 映射了 80/443，并把 `/data`、`/config` 挂载为持久卷。购买和解析域名后只需在生产 `.env` 中设置：

```dotenv
APP_DOMAIN=piliplay.xyz
APP_EXTERNAL_URL=https://piliplay.xyz
ACME_EMAIL=你的有效邮箱
```

然后启动生产 Compose。首次启动时 Caddy 会自动完成域名控制验证和证书签发；无需在阿里云购买 SSL 证书，也无需手工上传 `.crt`/`.key`。裸公网 IP 通常不能按这条流程获得公开受信任证书，域名解析生效前不要反复启动申请，以免触发证书机构的频率限制。

## 当前 OIDC 到底需要配置什么

本项目没有内置 OIDC Provider，`.env.example` 中的 `https://idp.example.com` 只是占位符。一年试运行阶段选用托管 Auth0；具体的 Tenant、管理员 `sub`、播放器 Client、精确回调和生产 `.env` 配置见 [`auth0-oidc-setup-2026-07-22.md`](auth0-oidc-setup-2026-07-22.md)。第一阶段只接播放器 OIDC，Grafana 暂用强密码本地管理员，待角色声明映射完成后再创建第二个 OIDC Client。

生产环境可以只使用一个应用域名，例如 `radio.example.com`。当前仓库需要的配置如下：

| 对象 | 当前项目值 | 需要做什么 |
| --- | --- | --- |
| 应用公开入口 | `https://radio.example.com` | DNS `A/AAAA` 解析到负载均衡器或服务器；开放 80/443 给 Caddy 申请证书和提供 HTTPS |
| 播放器 OIDC 回调 | `https://radio.example.com/api/session/callback` | 在播放器的 OIDC Client 中精确登记 |
| Grafana OIDC 回调 | `https://radio.example.com/grafana/login/generic_oauth` | 在独立的 Grafana OIDC Client 中精确登记；不部署 Grafana 时不需要 |
| OIDC Issuer | 例如 `https://id.example.com` | 浏览器、后端和 Grafana必须可访问；使用托管 IdP 时无需自己提供这个域名或 IP |
| 服务器 IP | 无 OIDC 标准绑定项 | 仅用于 DNS、路由、防火墙或云厂商特有的白名单，不是 OIDC Client 的标准配置 |

补充边界：

- 回调 URI 按完整字符串匹配，协议、主机、端口和路径都必须一致。
- 当前 `docker-compose.production.yml` 与 Caddy 按域名自动签发证书设计；不要把后端 5000 端口直接暴露到公网。
- IdP 若自托管，可以使用另一个子域名，也可以与应用落在同一公网 IP 后由反向代理分流；OIDC 不要求独立 IP。
- 某个具体 IdP 可能额外要求 Allowed Origins、Logout URI 或 IP 白名单，那是供应商策略，不是 OIDC 协议的通用要求。
- 即使移除 OIDC，只要应用通过公网访问，HTTPS、可信 Host、Cookie 安全属性和反向代理仍然必须保留。双 Token 不能替代这些基础设施。

## 仓库当前的真实鉴权结构

项目不是把 OIDC access token 直接交给浏览器长期使用，而是以下两层：

```text
OIDC 登录 -> 验证 (issuer, subject) -> 创建 app_users
          -> 签发随机不透明 Session -> HttpOnly Cookie

应用 Session -> 用户主动进行 B 站扫码
             -> 获取 B 站 Cookie / B 站 refresh_token
             -> 绑定到该 app_user
```

已有能力：

- `py-radio/oidc_auth.py` 在回调完成后只读取身份声明，随后调用 `IdentityService.create_session()`；OIDC Token 不下发给 Vue，也不保存为业务访问令牌。
- `py-radio/identity_service.py` 生成 48 字节级随机不透明 Session，数据库只保存 SHA-256 哈希；支持绝对过期、空闲过期、管理员短会话、服务端吊销和每用户最多 5 个会话。
- Session Cookie 已设置 `Secure`、`HttpOnly`、`SameSite=Lax`，写请求已有 CSRF 校验。
- `py-radio/auth_service.py` 中的 `refresh_token` 是 **B 站凭据**，只能用于 B 站会话，不是本应用的 refresh token，不能直接拿来给 `/api/**` 鉴权。
- `bili_accounts`、歌单、收藏、最近播放、队列和分析数据已经按 `user_id` 隔离。
- Grafana 当前也是一个独立 OIDC Client。若完全移除 IdP，Grafana 需要改为本地管理员登录或另接认证代理；仅替换播放器登录并不能消除 IdP 运维。

这意味着“去 OIDC”真正需要替换的只是身份引导步骤，不需要推翻应用 Session 层。

## 三种方案对比

| 方案 | 主要优点 | 主要问题 | 适用范围 | 结论 |
| --- | --- | --- | --- | --- |
| 保留 OIDC + 当前 Session | 身份标准化；管理员组与 Grafana 可统一；上游 Token 不进浏览器 | 需要一个 IdP Client；自托管 IdP 时多一个服务 | 公网、多用户、生产运维 | 当前首选 |
| B 站扫码 + 当前不透明 Session | 登录交互最短；复用现有 Session、CSRF 和租户隔离 | 应用身份依赖 B 站扫码接口；需重做扫码前匿名挑战和账号迁移 | 私有部署、B 站垂直产品 | 可选替代方案 |
| B 站扫码 + JWT access/refresh 双 Token | 适合原生客户端或第三方 API 调用 | 必须实现刷新轮换、Token family、重放检测、吊销、密钥轮换、aud/iss 校验；Web 音频 Range 请求处理更复杂 | 多种非浏览器客户端 | 当前不采用 |

## 为什么不能直接把现有 B 站扫码当应用登录

当前扫码接口位于应用鉴权之后：

- `/api/auth/qrcode` 和 `/api/auth/qrcode/status` 不是公开端点。
- `auth_qr_sessions` 以已经登录的 `user_id` 为归属键。
- 扫码成功后，凭据写入当前用户的 `bili_accounts`。

如果简单把这两个接口放开，会产生二维码会话串用、`qrcode_key` 抢占、登录 CSRF、账号重复绑定和首个扫码者抢管理员等问题。正确迁移必须引入独立的匿名登录挑战，而不是复用现有已登录扫码记录。

此外，当前代码调用：

- `passport.bilibili.com/x/passport-login/web/qrcode/generate`
- `passport.bilibili.com/x/passport-login/web/qrcode/poll`
- `api.bilibili.com/x/web-interface/nav`

这套链路返回 B 站网页 Cookie 和 B 站 refresh token。仓库没有使用开放平台应用身份与正式授权契约。B 站官方开放平台确实提供“账号授权/账号绑定”能力，但需要开发者身份认证、应用接入和按平台规则获得权限。公网产品不应把当前网页扫码接口视为稳定的身份协议；若 B 站身份是产品根身份，应优先评估官方开放平台授权。

## 若决定迁移，生产实现必须满足的阻断项

### 1. 单独建立扫码登录挑战

建议新增 `login_challenges`，而不是修改已登录用户使用的 `auth_qr_sessions`：

```text
id                   随机 256-bit 标识，数据库只保存哈希
browser_nonce_hash   绑定发起扫码的浏览器
bili_qrcode_key      只在服务端保存，不回传为鉴权凭据
status               waiting | scanned | confirmed | consumed | expired
expires_at           最长沿用 B 站二维码有效期
confirmed_mid        服务端通过 nav 接口验证得到
consumed_at          只能成功消费一次
```

浏览器只持有 `HttpOnly + Secure + SameSite=Lax` 的挑战 Cookie。轮询接口必须同时匹配挑战 Cookie 与挑战记录，并对创建、轮询、失败和 IP 维度限流。

### 2. 用服务端验证的 B 站 UID 建立外部身份

扫码确认后必须使用收到的 B 站 Cookie 调用 nav 接口，确认 `isLogin=true` 并读取 `mid`。不能信任前端提交的 UID、昵称或二维码状态。

不要继续把身份塞进 `app_users.oidc_issuer/oidc_subject`。建议新增通用表：

```text
external_identities
- id
- user_id
- provider            bilibili | oidc
- provider_subject    B 站 mid 或 OIDC sub
- issuer              OIDC 使用；B 站为空
- created_at
- last_login_at
- UNIQUE(provider, issuer, provider_subject)
```

同时给 `bili_accounts.user_mid` 增加唯一约束。当前表没有该约束，同一个 B 站账号理论上可以绑定到多个应用用户；在 B 站成为根身份后这是不可接受的。

### 3. 继续使用服务端 Session，不把 Token 放进 localStorage

扫码确认并原子消费挑战后：

1. 查找或创建对应 `app_user`。
2. 绑定/更新该用户的 `bili_accounts`。
3. 调用现有 `IdentityService.create_session()`。
4. 把不透明 Session 放入 `HttpOnly` Cookie。
5. 立即销毁扫码挑战中的临时敏感数据。

若未来确实需要原生客户端，再单独设计双 Token：access token 5-15 分钟；refresh token 使用高熵不透明随机值、只保存哈希、每次刷新旋转、检测旧 Token 重放并吊销整个 Token family。B 站返回的 refresh token 与本应用 refresh token 必须物理分表、不同命名、不同密钥和不同生命周期。

### 4. 明确注册与管理员策略

- 禁止“第一个扫码用户自动成为管理员”。
- 私有部署使用精确的 `BILI_BOOTSTRAP_ADMIN_MID` 或离线 CLI 认领 `legacy-owner`。
- 公网版本必须明确开放注册、邀请制或 B 站 UID allowlist，默认不应匿名自助成为有效用户。
- 移除 OIDC 组同步后，角色变更只能来自受审计的本地管理员操作。
- 迁移前要把现有 `(oidc_issuer, oidc_subject)` 与已绑定 `bili_accounts.user_mid` 做冲突审计；没有绑定 B 站账号的 OIDC 用户不能被自动迁移。

### 5. 先修复 B 站凭据加密

当前 Linux/Docker 路径使用自制 XOR 流加密 + HMAC，且密钥文件与 SQLite 位于同一个数据卷附近。这不应作为公网生产凭据保险箱。

迁移前必须：

- 改为成熟 AEAD（AES-256-GCM 或 XChaCha20-Poly1305）。
- 主密钥由 Docker Secret/KMS 注入，与数据库和备份分离。
- 密文保存 `key_id`、nonce、算法版本，支持在线密钥轮换。
- 日志、指标、审计和异常中禁止输出 B 站 Cookie、B 站 refresh token、扫码 key 或应用 Session。

### 6. 处理 Grafana

若删除全部 OIDC 基础设施，只能二选一：

- Grafana 保留独立本地管理员登录，限制在 VPN/内网，并关闭公网直接访问；或
- 本项目实现标准 OAuth/OIDC Provider 供 Grafana 使用。

第二项等于重新自建身份提供方，复杂度高于保留现有 IdP，因此不推荐。公网统一登录场景下，Grafana 是保留 OIDC 的决定性理由之一。

## 推荐落地路线

### 路线 A：保持当前生产方向（推荐）

1. 准备一个应用域名并解析到服务器。
2. 在现有或托管 IdP 建两个 Client，分别登记播放器和 Grafana 的精确回调 URI。
3. 保持当前 OIDC -> 本地不透明 Session -> B 站账号连接的分层。
4. 完成一次真实 HTTPS 登录、扫码、音频 Range、CSRF、登出、管理员和 Grafana 回归。

该路线不需要绑定服务器 IP，也不需要让 Vue 管理 OIDC Token。

### 路线 B：确认 B 站是唯一身份后再迁移

按以下顺序实施，不能直接改路由守卫或公开现有扫码接口：

1. 新增匿名登录挑战、限流和一次性消费测试。
2. 新增通用外部身份表及 `bili_mid` 唯一约束。
3. 实现“扫码确认 -> nav 验证 -> 原子绑定用户 -> 签发当前 Session”。
4. 用显式 B 站 UID/CLI 迁移 `legacy-owner` 与管理员身份。
5. 替换凭据加密和 Secret 管理。
6. 决定 Grafana 继续 OIDC，还是仅限内网使用本地管理员。
7. 完成迁移演练与回滚后，最后再删除 OIDC 路由、字段和依赖。

## 验收标准

- 未扫码用户不能访问 API、封面、字幕、音频流或 WebSocket。
- 一个二维码挑战不能被另一个浏览器消费，成功挑战不能二次使用。
- 同一个 B 站 UID 只能对应一个应用用户，冲突时拒绝而不是覆盖数据。
- 禁用用户或退出登录后，所有服务端 Session 立即失效。
- 修改接口具备 CSRF 防护；Cookie 具备 `Secure`、`HttpOnly` 和合适的 `SameSite`。
- B 站扫码接口超时、限流或变更时，不产生半创建用户或脏绑定。
- 管理员身份只能由精确配置或审计过的管理员操作产生。
- 数据库备份泄漏时，攻击者不能仅凭备份解密 B 站凭据。
- Grafana、Prometheus 和后端内部端口不能绕过公开鉴权边界。

## 依据

- 当前配置：`.env.example`、`docker-compose.production.yml`、`deploy/Caddyfile`
- 当前应用身份：`py-radio/oidc_auth.py`、`py-radio/identity_service.py`
- 当前 B 站扫码：`py-radio/auth_service.py`、`py-radio/constant.py`
- 当前租户表：`py-radio/database.py` v4 migration
- [OpenID Connect Core 1.0：redirect_uri 必须精确匹配](https://openid.net/specs/openid-connect-core-1_0-35.html)
- [OAuth 2.0 Security Best Current Practice（RFC 9700）](https://www.rfc-editor.org/rfc/rfc9700.html)
- [阿里云：快速注册新域名与实名认证信息模板](https://help.aliyun.com/zh/dws/getting-started/quickly-register-a-new-domain-name)
- [阿里云：修改域名 DNS 服务器（Nameserver）](https://help.aliyun.com/zh/dws/user-guide/modify-dns-server)
- [阿里云：注册在阿里云的域名默认使用免费公共权威 DNS](https://help.aliyun.com/zh/dns/pubz-modify-dns-server-for-alibaba-cloud-domain-name)
- [阿里云：2026-06-24 起免费权威 DNS 单域名日解析量限额为 10 万次](https://help.aliyun.com/zh/dns/public-network-authority-analyzes-free-version-speed-limit-notice)
- [Caddy：Automatic HTTPS 的签发、续期与端口要求](https://caddyserver.com/docs/automatic-https)
- [哔哩哔哩开放平台：账号授权与应用接入](https://open.bilibili.com/doc)
- [哔哩哔哩开放平台开发者服务协议](https://open.bilibili.com/agreement/developer-service)
