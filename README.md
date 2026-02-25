# Meilisearch4TelegramSearchCKJ

> 基于 Telethon + MeiliSearch 的 Telegram 中文/日文/韩文 (CJK) 消息全文搜索解决方案

## 展示

<img src="asset/image-20250206132432097.png" alt="展示图" style="zoom:25%;" />

## 功能特性

- **消息下载**: 从 Telegram 下载历史消息到 MeiliSearch
- **实时监听**: 监听新消息并自动索引
- **Bot 搜索**: 通过 Telegram Bot 提供搜索界面
- **REST API**: FastAPI 提供 RESTful API + WebSocket 实时推送
- **WebUI**: React 管理界面（会话同步、AI 配置、Dashboard 等）
- **黑白名单**: 灵活的频道/群组/用户同步控制
- **统一策略真源**: 白名单/黑名单运行时统一存储于 MeiliSearch `system_config.policy`

## 架构概览

<img src="asset/2025-02-05-1646.png" alt="架构概图" style="zoom:25%;" />

- **TG Client**: 从 Telegram 下载和监听消息到 MeiliSearch
- **MeiliSearch**: 存储消息、增量配置、黑白名单
- **Bot**: 与用户交互，搜索消息、启动 TG Client
- **REST API**: FastAPI 提供管理、搜索、配置等端点
- **WebUI**: React 前端管理界面

## 快速开始

### Docker 部署（推荐）

1. 克隆仓库
```bash
git clone https://github.com/clionertr/Meilisearch4TelegramSearchCKJ.git
cd Meilisearch4TelegramSearchCKJ
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入你的 Telegram API 和 MeiliSearch 配置
```

3. 启动服务
```bash
docker-compose up -d
```

### 本地部署

1. 安装依赖（需要 Python 3.10+，使用 [uv](https://docs.astral.sh/uv/) 包管理器）
```bash
uv sync
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env
```

3. 启动服务
```bash
# 同时运行 API + Bot
python -m tg_search

# 仅运行 API
python -m tg_search --mode api-only

# 仅运行 Bot
python -m tg_search --mode bot-only
```

## 环境变量

### 必填

| 变量 | 说明 |
|------|------|
| `APP_ID` | Telegram API ID ([获取](https://my.telegram.org/apps)) |
| `APP_HASH` | Telegram API Hash |
| `BOT_TOKEN` | Telegram Bot Token ([@BotFather](https://t.me/BotFather)) |
| `MEILI_HOST` | MeiliSearch 地址 |
| `MEILI_MASTER_KEY` | MeiliSearch 主密钥 |

### 常用可选

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WHITE_LIST` | `[1]` | 策略服务冷启动白名单默认值（运行时真源为 ConfigStore） |
| `BLACK_LIST` | `[]` | 策略服务冷启动黑名单默认值（运行时真源为 ConfigStore） |
| `POLICY_REFRESH_TTL_SEC` | `10` | Telegram 监听端策略刷新间隔（秒） |
| `OWNER_IDS` | `[]` | Bot 管理员 ID |
| `API_KEY` | - | REST API 认证密钥 |
| `API_ONLY` | `false` | 是否仅启动 API（开启后运行控制 start 会统一拒绝） |
| `DISABLE_BOT_AUTOSTART` | `false` | 是否禁用 API 启动时自动拉起 Bot |
| `CORS_ORIGINS` | `http://localhost:5173,...` | 允许的 CORS 源 |
| `SESSION_STRING` | - | Telethon 会话字符串（Docker 环境） |

完整配置说明请参考 [`.env.example`](.env.example)。

## 配置策略说明

- **静态启动配置**: 从 `.env` 读取（如 `APP_ID/APP_HASH/BOT_TOKEN/MEILI_*`）。
- **动态运行配置**: 白名单/黑名单统一从 MeiliSearch `system_config` 索引中的 `policy` 字段读取。
- API 与 Bot 对白/黑名单的修改都会持久化到同一文档，重启后不丢失。

## README 使用示例

### 1) 查看当前策略

```bash
curl -s "http://localhost:8000/api/v1/config" \
  -H "X-API-Key: <your_api_key>" | jq
```

### 2) 追加白名单

```bash
curl -s -X POST "http://localhost:8000/api/v1/config/whitelist" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_api_key>" \
  -d '{"ids":[-1001234567890, -1009876543210]}' | jq
```

### 3) 追加黑名单

```bash
curl -s -X POST "http://localhost:8000/api/v1/config/blacklist" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_api_key>" \
  -d '{"ids":[-1002222222222]}' | jq
```

### 4) Bot 直接设置（覆盖模式）

```text
/set_white_list2meili [-1001234567890, -1009876543210]
/set_black_list2meili [-1002222222222]
```

### 5) 启停下载任务 (API)

```bash
curl -s -X POST "http://localhost:8000/api/v1/client/start" \
  -H "X-API-Key: <your_api_key>" | jq
```

```bash
curl -s -X POST "http://localhost:8000/api/v1/client/stop" \
  -H "X-API-Key: <your_api_key>" | jq
```

### 6) 查看运行控制状态（统一状态机）

```bash
curl -s "http://localhost:8000/api/v1/client/status" \
  -H "X-API-Key: <your_api_key>" | jq
```

典型返回字段：
- `is_running`: 当前是否有下载/监听任务运行
- `state`: `stopped|starting|running|stopping`
- `api_only_mode`: 当前是否 API-only
- `last_action_source`: 最近一次动作来源（`api` / `bot` / `bot_auto`）
- `last_error`: 最近一次运行控制错误（无则 `null`）

### 7) Bot 侧启停与 API 语义一致

```text
/start_client
/stop_client
```

说明：当任务已在运行时，Bot 与 API 都返回 `already_running` 语义；当任务未运行时都返回 `already_stopped` 语义。

### 8) 查看下载进度

```bash
curl -s "http://localhost:8000/api/v1/status/progress" \
  -H "X-API-Key: <your_api_key>" | jq
```

## REST API

API 端点一览：

| 模块 | 前缀 | 说明 |
|------|------|------|
| Auth | `/api/v1/auth/` | Telegram 登录认证 |
| Search | `/api/v1/search/` | 消息搜索 |
| Status | `/api/v1/status/` | 系统状态 |
| Config | `/api/v1/config/` | 黑白名单配置 |
| Control | `/api/v1/client/` | 下载控制 |
| Storage | `/api/v1/storage/` | 存储统计与清理 |
| AI Config | `/api/v1/ai/` | AI 配置管理 |
| Dashboard | `/api/v1/dashboard/` | 活动聚合 |
| Dialogs | `/api/v1/dialogs/` | 会话同步管理 |
| WebSocket | `/api/v1/ws/` | 实时进度推送 |

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 开发

```bash
# 安装开发依赖
uv sync --extra dev

# 运行测试
pytest tests/

# 代码格式化与检查
ruff format src/
ruff check src/
```

详细开发文档请参考 [CLAUDE.md](CLAUDE.md)。

## 致谢

本项目从 [SearchGram](https://github.com/tgbot-collection/SearchGram) 重构而来，感谢原作者的付出。

非常感谢 Telethon 的作者和维护者们！

## License

MIT
