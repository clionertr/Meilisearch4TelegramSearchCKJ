# Observability Runbook

## 目标

本项目的可观测性分为三层：

1. 后端访问日志（FastAPI `api.access`）
2. 业务服务日志（`SearchService` / `RuntimeControlService` / `ObservabilityService`）
3. 前端 telemetry（浏览器控制台）

通过统一 `request_id`，可以在前后端快速串联同一条请求链路。

---

## 后端访问日志

事件前缀：`[api.access]`

字段：

- `request_id`: 请求唯一标识（默认 header `X-Request-ID`）
- `method`: HTTP 方法
- `path`: 路径
- `status`: 响应状态码
- `duration_ms`: 接口耗时
- `client`: 客户端 IP（支持 `X-Forwarded-For` / `X-Real-IP`）
- `ua`: User-Agent（最长 120 字符）

相关环境变量（根目录 `.env`）：

- `API_ACCESS_LOG_ENABLED=true|false`
- `API_ACCESS_LOG_SLOW_MS=800`
- `API_ACCESS_LOG_SKIP_PATHS=/health,/docs,/redoc,/openapi.json,/docs/oauth2-redirect`
- `API_REQUEST_ID_HEADER=X-Request-ID`

---

## 业务日志建议检索词

- `SearchService`
- `RuntimeControlService`
- `ObservabilityService`
- `control.start`
- `control.stop`
- `control.status`

示例：

```bash
grep -E "api.access|SearchService|RuntimeControlService|ObservabilityService|control\\." log_file.log
```

---

## 前端 telemetry

开关（`webui-example/.env*`）：

- `VITE_ENABLE_DEBUG_LOGS=true|false`
- `VITE_SLOW_API_WARN_MS=1200`

事件：

- `api.start`
- `api.end`
- `api.error`
- `ws.state`
- `ws.message`

`api.end` 与 `api.error` 会输出 `request_id`，可与后端 `api.access` 对齐排障。

---

## 快速排障流程（建议）

1. 先在浏览器控制台拿到失败请求的 `request_id`。
2. 在服务端日志按 `request_id` 检索对应 `api.access`。
3. 再按时间窗口检索 `SearchService` / `RuntimeControlService` 业务日志。
4. 若是状态相关接口，检查 `ObservabilityService` 中 `notes/errors` 是否出现降级信息。
