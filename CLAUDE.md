# Meilisearch4TelegramSearchCKJ

> 基于 Telethon + MeiliSearch 的 Telegram CJK（中文/日文/韩文）消息搜索系统。包含 Bot、REST API、WebUI。

文档同步时间: 2026-02-28

---

## 1. 项目现状

- 当前版本: `0.2.0`
- 主运行链路: `ServiceContainer + ConfigStore + ConfigPolicyService + SearchService + RuntimeControlService + ObservabilityService`
- 前端状态: `webui-example/` 可用于日常管理，遗留项见 `webui-example/webui_gap_analysis.md`
- 统一运行入口: `python -m tg_search`

---

## 2. 核心能力

- Telegram 历史消息下载与实时监听
- MeiliSearch 全文检索（CJK 友好）
- Telegram Bot 搜索/分页/运行控制
- FastAPI REST API + WebSocket 进度推送
- WebUI 管理（登录、搜索、会话同步、存储、Dashboard、AI 配置）
- 白/黑名单动态策略持久化（`system_config.policy`）

---

## 3. 真实架构（代码对齐）

### 3.1 分层

- `src/tg_search/config/`
  - `settings.py`: 静态环境变量配置
  - `config_store.py`: 运行时配置持久化（MeiliSearch `system_config`）
- `src/tg_search/core/`
  - `telegram.py`: Telegram 用户客户端（下载 + 监听）
  - `bot.py`: Telegram Bot 命令入口
  - `meilisearch.py`: MeiliSearch SDK 封装
- `src/tg_search/services/`
  - `container.py`: 统一装配 ServiceContainer
  - `config_policy_service.py`: 白/黑名单策略服务
  - `search_service.py`: Bot/API 统一搜索语义
  - `runtime_control_service.py`: 任务启停状态机
  - `observability_service.py`: 状态/存储/进度快照
  - `download_scheduler.py`: dialog 级顺序下载调度
- `src/tg_search/api/`
  - `app.py`: FastAPI 构建 + lifecycle + access log middleware
  - `routes/`: 业务路由

### 3.2 关键约束

- 运行时策略真源是 `ConfigStore.policy`，不是 `.env` 的 `WHITE_LIST/BLACK_LIST`
- Bot/API 的搜索语义统一走 `SearchService`
- Bot/API 的启停控制统一走 `RuntimeControlService`
- `/status`、`/search/stats`、`/storage/stats` 与 Bot `/ping` 统一走 `ObservabilityService`

---

## 4. 运行方式

```bash
# 安装依赖
uv sync

# 全模式（API + Bot）
python -m tg_search --mode all

# 仅 API
python -m tg_search --mode api-only

# 仅 Bot
python -m tg_search --mode bot-only
```

Docker:

```bash
docker-compose up -d
```

---

## 5. API 端点（代码真实）

### 5.1 认证

- `POST /api/v1/auth/send-code`
- `POST /api/v1/auth/signin`
- `POST /api/v1/auth/token-login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

### 5.2 搜索

- `GET /api/v1/search`
- `GET /api/v1/search/stats`

### 5.3 状态

- `GET /api/v1/status`
- `GET /api/v1/status/dialogs`
- `GET /api/v1/status/progress`

### 5.4 配置与控制

- `GET /api/v1/config`
- `POST /api/v1/config/whitelist`
- `DELETE /api/v1/config/whitelist`
- `POST /api/v1/config/blacklist`
- `DELETE /api/v1/config/blacklist`
- `GET /api/v1/client/status`
- `POST /api/v1/client/start`
- `POST /api/v1/client/stop`

### 5.5 存储 / AI / Dashboard / Dialog Sync

- Storage:
  - `GET /api/v1/storage/stats`
  - `PATCH /api/v1/storage/auto-clean`
  - `POST /api/v1/storage/cleanup/cache`
  - `POST /api/v1/storage/cleanup/media`
- AI Config:
  - `GET /api/v1/ai/config`
  - `PUT /api/v1/ai/config`
  - `POST /api/v1/ai/config/test`
  - `GET /api/v1/ai/models`
- Dashboard:
  - `GET /api/v1/dashboard/activity`
  - `GET /api/v1/dashboard/brief`
- Dialog Sync:
  - `GET /api/v1/dialogs/available`
  - `GET /api/v1/dialogs/synced`
  - `POST /api/v1/dialogs/sync`
  - `PATCH /api/v1/dialogs/{id}/sync-state`
  - `DELETE /api/v1/dialogs/{id}/sync`

### 5.6 WebSocket

- `GET /api/v1/ws/status`（WebSocket）

---

## 6. 鉴权矩阵

- `search/status/config/client/storage`: `API Key` 或 `Bearer`（`verify_api_key_or_bearer_token`）
- `ai/*`, `dashboard/*`, `dialogs/*`: `Bearer-only`
- `auth/*`: 登录链路不要求 Bearer
- `ws/status`:
  - 若未配置 `API_KEY`，允许匿名连接
  - 若配置了 `API_KEY`，需 `?token=<bearer_token>`

---

## 7. 环境变量（按代码分组）

### 7.1 必填

- `APP_ID`
- `APP_HASH`
- `BOT_TOKEN`
- `MEILI_HOST`
- `MEILI_MASTER_KEY`

### 7.2 运行控制 / 可观测性

- `API_ONLY`
- `DISABLE_BOT_AUTOSTART`
- `DISABLE_AUTH_CLEANUP_TASK`
- `OBS_SNAPSHOT_TIMEOUT_SEC`
- `OBS_SNAPSHOT_WARN_MS`
- `API_ACCESS_LOG_ENABLED`
- `API_ACCESS_LOG_SLOW_MS`
- `API_ACCESS_LOG_SKIP_PATHS`
- `API_REQUEST_ID_HEADER`
- `ENABLE_TRACEMALLOC`
- `DEBUG`

### 7.3 配置与性能

- `WHITE_LIST`, `BLACK_LIST`, `POLICY_REFRESH_TTL_SEC`
- `SEARCH_CACHE`, `CACHE_EXPIRE_SECONDS`
- `MAX_PAGE`, `RESULTS_PER_PAGE`
- `SEARCH_PRESENTATION_MAX_HITS`, `SEARCH_CALLBACK_TOKEN_TTL_SEC`
- `BATCH_MSG_UNM`, `NOT_RECORD_MSG`
- `CONFIG_STORE_WAIT_TASK_TIMEOUT_MS`

### 7.4 鉴权与联调

- `API_KEY`, `API_KEY_HEADER`
- `AUTH_TOKEN_STORE_FILE`
- `API_AUTH_SESSION_FILE`
- `ALLOW_TEST_TOKEN_ISSUE`
- `DISABLE_THREAD_OFFLOAD`
- `CORS_ORIGINS`

---

## 8. 可观测性（当前实现）

### 8.1 统一访问日志

- 事件前缀: `[api.access]`
- 核心字段: `request_id method path status duration_ms client ua`
- 响应头回传: `X-Request-ID`（可配置）

### 8.2 业务日志

- `SearchService`: 搜索耗时/缓存命中/分页 callback 编解码
- `RuntimeControlService`: 启停动作与状态
- `ObservabilityService`: snapshot 耗时 + errors/notes
- `dialogs` 路由: `available/synced/sync/patch/delete` 的结构化动作日志
- `ai_config` 路由: `get/put/test/models` 的结果日志（不输出 api_key）
- `ws` 路由: `connection_id` 维度的连接/认证/收发异常日志

---

## 9. 测试策略

- 单元测试: `tests/unit/`（无外部依赖）
- 集成测试: `tests/integration/`（真实 MeiliSearch）

常用命令:

```bash
pytest tests/unit -v
RUN_INTEGRATION_TESTS=true pytest tests/integration -v
pytest -m unit -v
```

---

## 10. 文档索引

- 根 README: `README.md`
- API 模块文档: `src/tg_search/api/CLAUDE.md`
- Config 模块文档: `src/tg_search/config/CLAUDE.md`
- Core 模块文档: `src/tg_search/core/CLAUDE.md`
- Utils 模块文档: `src/tg_search/utils/CLAUDE.md`
- 测试文档: `tests/CLAUDE.md`, `tests/TESTING_GUIDELINES.md`
- 可观测性 Runbook: `docs/operations/observability.md`
- 非最佳实现缺口台账: `docs/operations/non_best_gap.md`
- WebUI 文档: `webui-example/README.md`, `webui-example/CLAUDE.md`

---

## 11. 历史兼容与遗留说明

- `src/tg_search/app.py` 是 Flask 遗留健康检查入口，不属于当前推荐主链路。
- 当前推荐统一入口: `python -m tg_search`（由 `__main__.py` 驱动）。

---

## 12. 本次更新（2026-02-28）

- 全面清理过期目录/端点/测试路径描述，确保与代码一致。
- 补充真实鉴权矩阵、环境变量分组、可观测性日志点。
- 补充遗留入口说明，降低新成员误判风险。
