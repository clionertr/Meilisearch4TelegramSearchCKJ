# 功能名称：P1-存储统计与轻量清理 API（Storage）

## 1. 业务目标（一句话）
为 `Storage` 页面提供当前架构可落地的存储统计与轻量清理能力，避免定义超出现实能力的接口。

## 2. 验收标准（Given-When-Then 格式）
1. Given 未携带 Bearer Token，When 调用 `/api/v1/storage/*`，Then 返回 `401`。
2. Given 已登录，When `GET /api/v1/storage/stats`，Then 返回 `200` 且包含 `index_bytes/total_bytes`。
3. Given 当前版本不落地媒体文件，When `GET /storage/stats`，Then `media_bytes=null` 且 `media_supported=false`。
4. Given 已登录，When `PATCH /api/v1/storage/auto-clean` with `{"enabled":true}`，Then 返回 `200` 且配置持久化。
5. Given 已登录，When `POST /api/v1/storage/cleanup/cache`，Then 返回 `200` 且返回 `targets_cleared`。
6. Given 已登录，When `POST /api/v1/storage/cleanup/media`，Then 返回 `200` 且 `not_applicable=true`（当前版本媒体清理未启用）。

## 3. 简单的技术设计 & 非功能需求
### 3.1 与现状对齐
- 当前项目核心是消息索引，不下载媒体文件。
- 因此 `media` 相关指标与清理在 P1 使用 `not_applicable` 显式返回，不做虚假统计。

### 3.2 API 设计（明确返回）
1. `GET /api/v1/storage/stats`
```json
{
  "success": true,
  "data": {
    "total_bytes": 123456,
    "index_bytes": 123456,
    "media_bytes": null,
    "cache_bytes": null,
    "media_supported": false,
    "cache_supported": false,
    "notes": ["media storage is disabled in current architecture"]
  }
}
```
- `index_bytes` 来源：MeiliSearch `/stats` 的 `databaseSize`（若不可得则 `null` 并给 reason）。

2. `PATCH /api/v1/storage/auto-clean`
- 请求：`{"enabled": true, "media_retention_days": 30}`
- 响应：返回持久化后配置。

3. `POST /api/v1/storage/cleanup/cache`
- 清理目标：API 进程内缓存（例如 dialogs available cache、config cache）。
- 响应：`{"targets_cleared":["dialogs_cache","config_cache"],"freed_bytes":null}`

4. `POST /api/v1/storage/cleanup/media`
- 当前固定返回：`{"not_applicable":true,"reason":"MEDIA_STORAGE_DISABLED","freed_bytes":0}`。

### 3.3 持久化
- 走统一 [SPEC-P0-config-store.md](/home/sinfor/Games/SteamLibrary/CODE/Meilisearch4TelegramSearchCKJ/docs/specs/SPEC-P0-config-store.md) 的 `storage` section。

### 3.4 非功能需求
- `GET /stats`：`<= 800ms`
- 清理端点：`<= 10s`
- 前端操作保持简单：单次请求即完成，不引入异步任务编排。

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P1-ST-01 定义 storage 模型（支持 nullable 字段与 `not_applicable`）。
- [ ] T-P1-ST-02 实现 `GET /stats`（Meili stats + 当前架构能力标识）。
- [ ] T-P1-ST-03 实现 `PATCH /auto-clean` 并持久化到 Config Store。
- [ ] T-P1-ST-04 实现 `POST /cleanup/cache`（清理 API 进程缓存）。
- [ ] T-P1-ST-05 实现 `POST /cleanup/media` 的 not-applicable 响应。
- [ ] T-P1-ST-06 单元测试与集成测试接入 `uv run tests/integration/run.py`。

## 5. E2E 测试用例清单
1. `GET /storage/stats` 返回 `media_supported=false`。
2. `PATCH /auto-clean` 后重启服务，配置保持。
3. `POST /cleanup/cache` 返回 `targets_cleared`。
4. `POST /cleanup/media` 返回 `not_applicable=true`。
5. 无 Token 调用全部 `401`。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-ST-001：P1 阶段不虚构媒体存储能力，显式返回 `not_applicable`。
- ADR-ST-002：缓存清理范围限定在 API 进程可控缓存，不跨线程侵入 Bot 内部状态。
- ADR-ST-003：保持前端一键触发，不引入复杂后台任务系统。
