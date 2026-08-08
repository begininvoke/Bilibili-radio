# PiliPlay 接入 Auth0 OIDC 操作手册（2026-07-22）

## 最终选择

当前仓库只是 OIDC Client，没有内置 OIDC Provider。`.env.example` 中的 `https://idp.example.com` 是占位符，不是已经存在的服务。

一年试运行阶段选择托管 Auth0 作为 OIDC Provider：它负责用户账号、登录页、密码验证和签发 OIDC 身份；PiliPlay 只接收回调并建立自己的服务端 Session。阿里云负责域名/DNS，Caddy 负责 HTTPS，三者职责互不替代。

```text
阿里云 DNS：piliplay.xyz -> 吉隆坡服务器 IP
Caddy：      piliplay.xyz 的 HTTPS 证书和反向代理
Auth0：      登录页、用户验证、OIDC issuer/client
PiliPlay：   回调后创建本地 HttpOnly Session
```

Auth0 当前免费计划为 0 美元/月、最多 25,000 MAU，足够本项目试运行。若目标用户主要位于中国大陆，上线前必须从实际网络测试 Auth0 登录跳转；它只影响登录过程，不承载后续音频流量。

## 前置条件

在登记生产回调前先完成：

1. `piliplay.xyz` 的 `A` 记录已经指向服务器；
2. TCP 80/443 已对公网开放并到达 Caddy；
3. 访问 `https://piliplay.xyz` 时证书有效；
4. 尚未用任何 OIDC 身份首次登录 PiliPlay，避免把原 `legacy-owner` 数据绑定到错误用户。

## 一、创建 Auth0 Tenant

1. 打开 <https://auth0.com/> 并注册账号。
2. 创建 Tenant，区域选择控制台提供的、离主要用户最近的可用区域。
3. 进入 Auth0 Dashboard，记录 Settings 页面展示的 **Domain**，例如：

   ```text
   dev-abc123.us.auth0.com
   ```

4. 本项目中的 issuer 写成：

   ```text
   https://dev-abc123.us.auth0.com
   ```

不要购买 Auth0 Custom Domain；一年试运行直接使用 Auth0 分配的 Tenant Domain。

## 二、先创建唯一管理员用户

私有试运行不应开放任意注册：

1. Auth0 Dashboard → **Authentication → Database**；
2. 打开项目使用的 Database Connection；
3. 开启 **Disable Sign Ups**；
4. Auth0 Dashboard → **User Management → Users → Create User**；
5. 填写管理员邮箱和强密码，创建用户；
6. 打开该用户详情，复制不可变的 **user_id**，例如：

   ```text
   auth0|0123456789abcdef
   ```

这个 `user_id` 就是 OIDC Token 中的 `sub`，必须在第一次登录前写入 `OIDC_BOOTSTRAP_ADMIN_SUBJECT`。不要用邮箱代替，因为邮箱可以修改。

## 三、创建播放器 OIDC Client 并登记回调

1. Auth0 Dashboard → **Applications → Applications → Create Application**；
2. 名称填写 `PiliPlay Web`；
3. 类型必须选 **Regular Web Applications**，不能选 Single Page Application；Flask 后端会持有 Client Secret 并完成授权码交换；
4. 进入应用的 **Settings**，填写：

   | Auth0 字段 | 精确值 |
   | --- | --- |
   | Allowed Callback URLs | `https://piliplay.xyz/api/session/callback` |
   | Allowed Logout URLs | `https://piliplay.xyz/` |
   | Allowed Web Origins | `https://piliplay.xyz` |

5. 不使用通配符，不添加路径错误的备用回调，也不要在生产配置中保留 localhost；
6. 保存配置；
7. 从同一 Settings 页面复制 **Domain**、**Client ID** 和 **Client Secret**。Client Secret 只能存放在服务器 Secret/`.env` 中，禁止提交 Git、截图公开或发送到聊天记录。

项目真正发起登录时，浏览器先跳到 Auth0；登录成功后 Auth0 只允许跳回已经登记的精确地址。协议、域名、端口、路径或尾部斜杠任一不同都会产生 callback mismatch。

## 四、填写生产 `.env`

生成应用密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

在服务器项目目录的 `.env` 中填写，示例值必须替换：

```dotenv
APP_DOMAIN=piliplay.xyz
ACME_EMAIL=你的有效邮箱

AUTH_MODE=oidc
APP_SECRET_KEY=上面生成的随机值
APP_EXTERNAL_URL=https://piliplay.xyz
APP_TRUSTED_HOSTS=piliplay.xyz

OIDC_ISSUER_URL=https://dev-abc123.us.auth0.com
OIDC_CLIENT_ID=Auth0中的Client-ID
OIDC_CLIENT_SECRET=Auth0中的Client-Secret
OIDC_SCOPES=openid profile email
OIDC_ADMIN_GROUP=
OIDC_BOOTSTRAP_ADMIN_ISSUER=https://dev-abc123.us.auth0.com
OIDC_BOOTSTRAP_ADMIN_SUBJECT=auth0|0123456789abcdef
OIDC_ALLOW_HTTP=false

GRAFANA_OIDC_ENABLED=false
GRAFANA_DISABLE_LOGIN_FORM=false
GRAFANA_ADMIN_USER=local-admin
GRAFANA_ADMIN_PASSWORD=单独生成的高强度密码
```

注意：

- `OIDC_ISSUER_URL` 和 `OIDC_BOOTSTRAP_ADMIN_ISSUER` 必须完全使用同一个 Auth0 Tenant Domain；
- Auth0 初始接入不要使用 `.env.example` 中的 `groups` scope，设置为 `openid profile email`；
- 第一阶段 `OIDC_ADMIN_GROUP` 留空，由精确的 issuer + sub 认领管理员；
- `.env` 不得提交版本库；Linux 服务器应限制为仅部署账号可读。

## 五、启动与首次验收

```powershell
docker compose -f docker-compose.yml `
  -f docker-compose.monitoring.yml `
  -f docker-compose.production.yml up -d --build
```

验收顺序：

1. 打开 `https://piliplay.xyz`；
2. 未登录请求应跳转到 Auth0 Tenant Domain；
3. 使用前面手工创建的管理员账号登录；
4. Auth0 跳回 `https://piliplay.xyz/api/session/callback`；
5. 最终回到 PiliPlay，并确认原 B 站账号和音乐数据仍在；
6. 后端日志不得出现 Client Secret、authorization code、ID Token 或 Session Cookie；
7. 无痕窗口访问受保护 API 应返回未登录，而不是直接获得 `legacy-owner`。

如果出现 `Callback URL mismatch`，只核对 Auth0 的 Allowed Callback URLs 与 `APP_EXTERNAL_URL + /api/session/callback`；不要临时添加通配符解决。

## 六、Grafana 为什么暂时不接同一个 Client

Grafana 是另一个独立依赖方，必须创建第二个 OIDC Client，回调地址为：

```text
https://piliplay.xyz/grafana/login/generic_oauth
```

当前项目的 Grafana 配置还要求从 `groups` 声明映射 `GrafanaAdmin`。Auth0 默认的 `openid profile email` 不会自动提供项目所期待的 `groups`。第一阶段强行开启会因 `GRAFANA_OIDC_ROLE_ATTRIBUTE_STRICT=true` 拒绝登录。

因此先让播放器 OIDC 稳定运行，Grafana 使用强密码本地管理员；随后再单独创建 `PiliPlay Grafana` Auth0 Application，并设计 Auth0 Role/Action 自定义声明及 Grafana JMESPath 映射。不能复用播放器的 Client Secret，也不能为了省事关闭严格角色校验。

## 官方依据

- [Auth0 Application Settings：Allowed Callback URLs 等字段](https://auth0.com/docs/get-started/applications/application-settings)
- [Auth0 创建用户并进入用户详情](https://auth0.com/docs/manage-users/user-accounts/create-users)
- [Auth0 Connection Settings：私有应用应关闭自助注册](https://auth0.com/docs/authenticate/connection-settings-best-practices)
- [Auth0 当前免费计划](https://auth0.com/pricing)
- [Grafana Generic OAuth：完整 callback 与严格角色映射](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/)

