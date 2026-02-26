# webui-example 模块文档

> TeleMemory WebUI：React + TypeScript + Vite 构建的 Telegram 搜索与管理前端。

**生成时间**: 2026-02-06（最近同步: 2026-02-26）

[返回根目录](../CLAUDE.md)

---

## 模块定位

`webui-example/` 是后端 `src/tg_search/api/` 的前端管理界面，覆盖以下场景：

- 登录认证（手机号验证码 / Token）
- 消息搜索（高亮、分页）
- 会话同步管理（available/synced/sync-state）
- 存储统计和缓存清理
- Dashboard 活动聚合
- AI 配置管理
- WebSocket 实时进度

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 19 |
| 语言 | TypeScript 5.8 |
| 构建 | Vite 6 |
| 路由 | React Router DOM 7 |
| 状态管理 | Zustand 5 |
| 数据请求 | TanStack React Query 5 + Axios |
| 实时通信 | react-use-websocket |
| 动画 | framer-motion |
| 国际化 | i18next + react-i18next |
| 样式 | Tailwind CSS 4 |

---

## 目录结构（精简）

```text
webui-example/
├── README.md
├── CLAUDE.md
├── .env.example
├── .env.development.example
├── vite.config.ts
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── search.ts
│   │   ├── dialogs.ts
│   │   ├── storage.ts
│   │   ├── status.ts
│   │   ├── config.ts
│   │   ├── dashboard.ts
│   │   ├── ai_config.ts
│   │   └── error.ts
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Search.tsx
│   │   ├── Settings.tsx
│   │   ├── Storage.tsx
│   │   ├── SyncedChats.tsx
│   │   ├── SelectChats.tsx
│   │   └── AIConfig.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   ├── useTheme.ts
│   │   ├── useConfirm.ts
│   │   └── queries/
│   ├── store/
│   │   ├── authStore.ts
│   │   └── statusStore.ts
│   ├── components/
│   │   ├── common/
│   │   ├── dashboard/
│   │   ├── layout/
│   │   ├── search/
│   │   └── Toast/
│   ├── i18n/
│   └── utils/
│       ├── telemetry.ts
│       ├── searchHistory.ts
│       ├── telegramLinks.ts
│       ├── formatters.ts
│       └── constants.ts
```

---

## 运行与联调

### 开发启动

```bash
cd webui-example
cp .env.development.example .env.development
npm install
npm run dev
```

默认端口：`3000`

### 构建

```bash
npm run build
npm run preview
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_URL` | `/api/v1` | 后端 API 前缀 |
| `VITE_ENABLE_DEBUG_LOGS` | `false` | 前端 telemetry 开关 |
| `VITE_SLOW_API_WARN_MS` | `1200` | 慢请求告警阈值（毫秒） |

---

## 关键约定

### 鉴权

- API 客户端在 `src/api/client.ts` 自动注入 `Authorization: Bearer <token>`。
- `401` 会触发全局 `auth:expired` 事件并清理登录状态。
- 路由保护统一通过 `ProtectedRoute`。

### WebSocket

- Hook：`src/hooks/useWebSocket.ts`
- 地址：由 `VITE_API_URL` 自动转换为 `ws://` / `wss://`
- 事件：重点消费 `type=progress`

### 搜索

- 统一通过 `src/api/search.ts` + React Query hooks。
- 后端字段契约已对齐 `formatted_text` 等高亮字段。

---

## 监控与日志

前端 telemetry 事件：

- `api.start`
- `api.end`
- `api.error`
- `ws.state`
- `ws.message`

其中 API 事件包含 `request_id`，可和后端 `api.access` 日志直接关联。

---

## 与后端对照

| 前端模块 | 后端路由 |
|----------|----------|
| `api/auth.ts` | `api/routes/auth.py` |
| `api/search.ts` | `api/routes/search.py` |
| `api/status.ts` | `api/routes/status.py` |
| `api/config.ts` | `api/routes/config.py` |
| `api/storage.ts` | `api/routes/storage.py` |
| `api/dashboard.ts` | `api/routes/dashboard.py` |
| `api/dialogs.ts` | `api/routes/dialogs.py` |
| `api/ai_config.ts` | `api/routes/ai_config.py` |
| `hooks/useWebSocket.ts` | `api/routes/ws.py` |

---

## 遗留问题与规划

WebUI 的历史遗留问题统一维护在：

- `webui_gap_analysis.md`

请按 `Done / Backlog (P0/P1/P2)` 方式维护，不再使用纯主观评分文档。
