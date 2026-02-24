# 功能名称：P0-会话同步管理 API（Dialog Sync）

## 1. 业务目标（一句话）
提供“可选会话列表、已同步会话列表、会话同步状态控制”API，使 `SelectChats` 和 `SyncedChats` 页面脱离静态 mock。

## 2. 验收标准（Given-When-Then 格式）
1. Given 未携带 Bearer Token，When 调用任一 `/api/v1/dialogs/*`，Then 返回 `401`。
2. Given 携带有效 Bearer Token，When `GET /api/v1/dialogs/available`，Then 返回 `200` 且 `data.dialogs` 为数组。
3. Given `available` 缓存有效，When 连续两次调用 `GET /available`，Then 第二次 `meta.cached=true`。
4. Given `refresh=true`，When `GET /available?refresh=true`，Then 强制绕过缓存并刷新。
5. Given 请求体 `{"dialog_ids":[1,2]}`，When `POST /api/v1/dialogs/sync`，Then 返回 `accepted/ignored/not_found` 三个列表。
6. Given dialog 已同步，When `PATCH /api/v1/dialogs/{dialog_id}/sync-state` with `{"sync_state":"paused"}`，Then 返回更新后的状态。
7. Given dialog 已同步，When `DELETE /api/v1/dialogs/{dialog_id}/sync`（默认 `purge_index=true`），Then 返回 `removed=true` 且 `GET /synced` 不再出现该 dialog，并触发该 chat 的索引删除。
8. Given `dialog_ids=[]`，When `POST /sync`，Then 返回 `422`。
9. Given `dialog_ids` 超过上限 200，When `POST /sync`，Then 返回 `422`。

## 3. 简单的技术设计 & 非功能需求
### 3.1 与现有代码差异（消除分歧）
- 现状：`search/status/config/control` 由 `verify_api_key_or_bearer_token` 保护（双通道）。
- 本 spec 决策：`dialogs` 新端点采用 Bearer-only（用户要求）。
- 兼容策略：仅新增 `dialogs` 采用 Bearer-only；不修改旧端点鉴权行为，后续若全局迁移再单开 RFC。

### 3.2 API 设计（明确 schema）
1. `GET /api/v1/dialogs/available?refresh=false&limit=200`
- 响应：
```json
{
  "success": true,
  "data": {
    "dialogs": [
      {
        "id": -100123,
        "title": "Tech Group",
        "type": "group",
        "message_count": null,
        "sync_state": "inactive"
      }
    ],
    "total": 1
  },
  "meta": {"cached": true, "cache_ttl_sec": 120}
}
```
- `message_count` 说明：Telegram 对话列表无低成本总消息数，当前返回 `null`。

2. `GET /api/v1/dialogs/synced`
- 响应字段：`id/title/type/sync_state/last_synced_at/is_syncing/updated_at`。
- `last_synced_at` 来源：`system_config.sync.dialogs[dialog_id].last_synced_at`。

3. `POST /api/v1/dialogs/sync`
- 请求：`{"dialog_ids":[...], "default_sync_state":"active"}`
- 校验：`1 <= len(dialog_ids) <= 200`，元素去重。
- 响应：
```json
{"success":true,"data":{"accepted":[1],"ignored":[2],"not_found":[3]}}
```

4. `PATCH /api/v1/dialogs/{dialog_id}/sync-state`
- 请求：`{"sync_state":"active"|"paused"}`
- 若 dialog 未同步：`404`。

5. `DELETE /api/v1/dialogs/{dialog_id}/sync?purge_index=true`
- 默认：移除同步配置并删除该 chat 的 MeiliSearch 历史索引。
- 若 `purge_index=false`：仅移除同步配置，不删除历史索引。
- 若执行索引删除失败：不回滚配置删除，返回 `purge_error`。

### 3.3 缓存策略
- `available` 列表缓存 TTL `120s`。
- 缓存失效触发：`refresh=true`、`POST/PATCH/DELETE /dialogs/*` 成功后、服务重启。

### 3.4 数据与持久化
- 配置持久化统一走 [SPEC-P0-config-store.md](/home/sinfor/Games/SteamLibrary/CODE/Meilisearch4TelegramSearchCKJ/docs/specs/SPEC-P0-config-store.md)。
- 不再直接依赖 `settings.WHITE_LIST` 作为唯一真源。
- `WHITE_LIST/BLACK_LIST` 在该阶段作为向后兼容，不作为 dialogs 主数据源。

### 3.5 非功能需求
- 缓存命中响应：`<= 300ms`
- 强刷响应目标：`<= 5s`
- 幂等：重复 `POST /sync` 不产生重复记录

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P0-DS-01 定义 Dialog API 的 Pydantic 模型（含 `sync_state`）。
- [ ] T-P0-DS-02 新增 `dialogs` 路由并接入 Bearer-only 依赖。
- [ ] T-P0-DS-03 实现 `GET /available` + 120s 缓存 + `refresh`。
- [ ] T-P0-DS-04 实现 `GET /synced`（拼装 config + progress 状态）。
- [ ] T-P0-DS-05 实现 `POST /sync`（accepted/ignored/not_found）。
- [ ] T-P0-DS-06 实现 `PATCH /sync-state`。
- [ ] T-P0-DS-07 实现 `DELETE /sync` + `purge_index` 可选路径。
- [ ] T-P0-DS-08 单元测试（边界值、鉴权、幂等、状态码）。
- [ ] T-P0-DS-09 使用真实环境，集成测试接入 `uv run tests/integration/run.py`。

## 5. E2E 测试用例清单
1. 登录后获取 `GET /dialogs/available` -> 返回数组。
2. 连续两次调用 `GET /available` -> 第二次 `meta.cached=true`。
3. `POST /sync` 包含有效和无效 id -> `accepted/not_found` 分类正确。
4. `PATCH /sync-state` active->paused->active 成功。
5. `DELETE /sync` 默认删除索引；`purge_index=false` 走“仅删同步配置”分支。
6. 无 Token 调用 -> `401`。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-DS-001：新增 dialogs 端点 Bearer-only；旧端点保持双通道，避免破坏兼容。
- ADR-DS-002：`message_count` 当前返回 `null`，避免高成本实时统计。
- ADR-DS-003：同步状态与时间由统一 Config Store 持久化，ProgressRegistry 仅提供运行态。
- ADR-DS-004：`DELETE /sync` 默认 `purge_index=true`，防止取消同步后旧索引长期滞留。
