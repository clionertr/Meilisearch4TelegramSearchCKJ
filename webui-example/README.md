# TeleMemory WebUI

Telegram 消息搜索与运维管理前端，基于 React 19 + TypeScript + Vite 6。

## 功能范围

- Bearer Token 登录（手机号验证码流程 / token 直登）
- 消息搜索（高亮、分页/无限滚动）
- 会话同步管理（available/synced/sync-state）
- 存储统计与缓存清理
- Dashboard 活动聚合
- AI 配置管理
- WebSocket 实时同步进度

## 前置条件

- Node.js 18+
- 已启动后端 API（默认 `http://localhost:8000`）

## 启动方式

```bash
cd webui-example
cp .env.development.example .env.development
npm install
npm run dev
```

默认访问：`http://localhost:3000`

## 环境变量

模板文件：

- `.env.example`：通用模板
- `.env.development.example`：本地开发推荐

变量说明：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_URL` | `/api/v1` | 后端 API 前缀 |
| `VITE_ENABLE_DEBUG_LOGS` | `false` | 前端 telemetry 开关 |
| `VITE_SLOW_API_WARN_MS` | `1200` | 慢请求 warning 阈值（ms） |

### 推荐本地联调配置

`VITE_API_URL=/api/v1` 时，Vite 会通过 `vite.config.ts` 代理转发到 `http://127.0.0.1:8000`。

## 常见使用路径

### 1) 登录

- 打开 `/login`
- 选择 `Phone` 或 `Token` 模式
- 登录成功后自动进入 `/dashboard`

### 2) 搜索

- 进入 `/search`
- 输入关键词（300ms 防抖）
- 点击结果查看高亮文本、发送者与会话信息

### 3) 会话同步

- `/select-chats` 选择会话并提交同步
- `/synced-chats` 查看 active/paused 状态并切换

### 4) 运维

- `/storage` 查看索引体积、清理缓存
- `/settings` 快速进入 AI 配置、已同步会话等管理项

## 监控与日志

WebUI 内置轻量 telemetry（控制台输出）：

- `api.start`：请求发起
- `api.end`：请求完成（含耗时、status、request_id）
- `api.error`：请求失败
- `ws.state`：WebSocket 连接状态变化
- `ws.message`：WebSocket 消息类型

与后端日志串联：

- 前端和后端都会记录 `X-Request-ID`
- 可用 request_id 快速定位同一请求的前后端链路

## 历史遗留问题

当前 WebUI 仍有部分历史遗留项，见：

- [webui_gap_analysis.md](./webui_gap_analysis.md)

该文档已改为“问题台账”模式，分为：

- 已解决（Done）
- 待处理（Backlog）
- 建议优先级（P0/P1/P2）

## 构建

```bash
npm run build
npm run preview
```
