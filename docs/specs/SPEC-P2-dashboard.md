# 功能名称：P2-仪表板活动与摘要 API（Dashboard）

## 1. 业务目标（一句话）
提供可测量的首页活动聚合与规则摘要接口，支持 `Dashboard` 页面展示真实统计信息。

## 2. 验收标准（Given-When-Then 格式）
1. Given 未携带 Bearer Token，When 调用 `/api/v1/dashboard/*`，Then 返回 `401`。
2. Given 已登录，When `GET /api/v1/dashboard/activity?window_hours=24&limit=20`，Then 返回 `200` 且 `data.items` 字段符合 schema。
3. Given `limit>100`，When 调用 activity，Then 返回 `422`。
4. Given 已登录，When `GET /api/v1/dashboard/brief?window_hours=24`，Then 返回 `200` 且包含 `summary/template_id/reason`。
5. Given 24h 内消息数 `< min_messages`，When 调用 brief，Then 返回 `summary=""` 且 `reason="NO_ENOUGH_DATA"`。

## 3. 简单的技术设计 & 非功能需求
### 3.1 API 设计（明确 schema）
1. `GET /api/v1/dashboard/activity`
- 参数：`window_hours=24`（1-168），`limit=20`（1-100），`offset=0`。
- 响应项：
```json
{
  "chat_id": -100123,
  "chat_title": "Tech Group",
  "chat_type": "group",
  "message_count": 80,
  "latest_message_time": "2026-02-24T11:59:00Z",
  "top_keywords": ["meilisearch","telegram","api"],
  "sample_message": "..."
}
```

2. `GET /api/v1/dashboard/brief`
- 响应：
```json
{
  "summary": "过去24小时共新增 150 条消息，最活跃会话是 Tech Group（80 条）。",
  "template_id": "brief.v1",
  "source_count": 150,
  "reason": null
}
```

### 3.2 聚合实现（对齐 MeiliSearch 能力）
- 不使用 MeiliSearch 聚合查询。
- 策略：先按时间窗口拉取最近 N 条消息（如 500），在 API 层内存分组聚合。
- 若数据超过 N 导致采样：返回 `sampled=true` 与 `sample_size`。

### 3.3 规则摘要模板（明确）
- 模板 `brief.v1`：
`过去{window_hours}小时共新增 {total_messages} 条消息，最活跃会话是 {top_chat_title}（{top_chat_messages} 条）。`

### 3.4 非功能需求
- `GET /activity`：`<= 1500ms`
- `GET /brief`：`<= 2000ms`
- 返回结构必须稳定，便于前端直出。

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P2-DB-01 定义 activity/brief 的 Pydantic 模型。
- [ ] T-P2-DB-02 实现 `GET /activity`（窗口拉取 + 内存分组）。
- [ ] T-P2-DB-03 实现 `GET /brief`（规则模板 v1）。
- [ ] T-P2-DB-04 增加参数校验与 Bearer 鉴权测试。
- [ ] T-P2-DB-05 集成测试接入 `uv run tests/integration/run.py`。

## 5. E2E 测试用例清单
1. `GET /dashboard/activity` 返回 items schema 完整。
2. `limit` 越界返回 `422`。
3. `GET /dashboard/brief` 在有数据时返回 `template_id=brief.v1`。
4. 低数据量时返回 `reason=NO_ENOUGH_DATA`。
5. 无 Token 调用返回 `401`。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-DB-001：不在 Meili 做聚合，改为 API 层采样聚合。
- ADR-DB-002：摘要采用规则模板，确保 deterministic 且可测。
- ADR-DB-003：P2 只读接口，不引入写操作。
