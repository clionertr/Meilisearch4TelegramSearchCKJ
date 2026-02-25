# 功能名称：P0-统一搜索服务（SearchService）

> **定位说明**：本规格定义统一 Service 层的搜索能力，将现有分散在 `api/routes/search.py`（MeiliFilterBuilder / _parse_message）与 `core/bot.py`（get_search_results / search_results_cache / _build_results_page）中的搜索逻辑收敛为单一 SearchService。这不是对现有搜索路由的替代，而是在其下方引入 Service 层以消除 Bot/API 行为漂移。

## 1. 业务目标（一句话）
将 Bot 与 API 的消息搜索、过滤、命中解析、分页与缓存策略统一到一个 SearchService，保证检索行为一致。

## 2. 验收标准（Given-When-Then 格式）
1. Given API 调用 `/api/v1/search` 与 Bot 调用 `/search 关键词`，When 使用相同检索条件，Then 命中总数与排序语义一致。
2. Given 传入 `chat_id/chat_type/date_from/date_to` 条件，When 执行搜索，Then Bot 与 API 都走同一过滤构建逻辑。
3. Given Meili 返回 `_formatted` 高亮字段，When 输出结果，Then API 返回 `formatted_text`，Bot 复用同一字段进行展示格式化。
4. Given 查询无结果，When 调用 Service，Then API 返回空 `hits`，Bot 返回“无结果”文案且不报错。
5. Given 查询词包含下划线等特殊字符，When Bot 分页回调翻页，Then 分页参数解析正确，不因 `split("_")` 破坏查询词。

## 3. 简单的技术设计 & 非功能需求
### 3.1 当前问题
- Bot 使用 `get_search_results/search_results_cache/_build_results_page`。
- API 使用 `MeiliFilterBuilder + _parse_message`。
- 两侧在过滤、字段映射、高亮处理、分页契约上存在重复与漂移风险。

### 3.2 Service 接口（建议）
```python
class SearchService:
    async def search(self, query: SearchQuery) -> SearchPage: ...
    async def search_for_presentation(self, query: SearchQuery, page: int, page_size: int) -> SearchPage: ...
```

### 3.3 领域模型（建议）
- `SearchQuery`：`q/chat_id/chat_type/date_from/date_to/limit/offset`
- `SearchHit`：统一 `id/chat/date/text/from_user/reactions/.../formatted_text`
- `SearchPage`：`hits/total_hits/processing_time_ms/limit/offset`

### 3.4 Bot/API 适配职责
- API Route：参数校验 + 调用 Service + 转 `ApiResponse`
- Bot Handler：命令解析 + 调用 Service + 仅负责 Telegram 文本和按钮渲染
- Bot 翻页 callback 数据建议改为 `base64(json)`，避免字符串切分脆弱性

### 3.5 非功能需求
- 单次搜索 95 分位响应时间：`<= 1.5s`（含 Meili 调用）
- SearchService 单测覆盖：过滤构建、hit 解析、异常映射、分页边界
- 不改变现有 API schema（向后兼容前端）

## 4. 任务拆分（每个任务 30-60 分钟）
- [x] T-P0-SS-01 定义 `SearchQuery/SearchHit/SearchPage` DTO。
- [x] T-P0-SS-02 抽离 API `MeiliFilterBuilder` 到 SearchService 内部。
- [x] T-P0-SS-03 抽离 API `_parse_message` 到 SearchService 公共解析器。
- [x] T-P0-SS-04 抽离 Bot `get_search_results`，改为调用 SearchService。
- [x] T-P0-SS-05 抽离 Bot 分页数据编码/解码，修复特殊字符查询翻页。
- [x] T-P0-SS-06 整理缓存策略（是否缓存、TTL、缓存键）并下沉到 Service。
- [x] T-P0-SS-07 API Route 改造为“薄路由”并保持 OpenAPI 不变。
- [x] T-P0-SS-08 增加单元测试与集成回归（Bot/API 双入口一致性）。

## 5. E2E 测试用例清单
1. API `/search?q=foo` 与 Bot `/search foo` 返回同一批首屏命中（按 id 比较）。
2. 指定 `chat_id + date_from/date_to` 时，两端命中集合一致。
3. 查询词 `foo_bar` 在 Bot 翻页可正常工作。
4. 无结果查询时，API 返回空数组，Bot 返回友好文案。
5. Meili 故障时，API 返回稳定错误码，Bot 返回稳定错误提示。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-SS-001：过滤构建统一在 SearchService，杜绝多处字符串拼装。
- ADR-SS-002：SearchService 返回领域 DTO，路由再映射到 Pydantic response model。
- ADR-SS-003：Bot 展示保留 Markdown/按钮形态，但数据源必须来自 SearchService。
- ADR-SS-004：若缓存启用，缓存策略归 Service 管理，避免 Bot/API 双缓存不一致。
- ADR-SS-005：Bot 翻页默认使用 `base64(json)` 编码；当 payload 超过 Telegram 64 bytes 限制时，自动回退短 token（Service 内 TTL 缓存映射）保证稳定翻页。

## 7. 实现笔记（2026-02-25）

### 7.1 代码落点
- `src/tg_search/services/search_service.py`：统一过滤构建、命中解析、分页/缓存、callback 编解码。
- `src/tg_search/services/contracts.py`：`SearchQuery/SearchHit/SearchPage` 领域 DTO。
- `src/tg_search/api/routes/search.py`：瘦路由，仅做参数校验 + DTO -> API Model 映射。
- `src/tg_search/core/bot.py`：统一改为调用 `SearchService`，移除重复搜索编排逻辑。

### 7.2 可观测性
- 新增搜索性能日志：`duration_ms`、`meili_processing_ms`。
- 新增缓存命中日志：`presentation_cache_hit/miss/expired`。
- 新增分页协议日志：`encode_callback mode=inline|token_fallback`、`decode_callback mode=inline|token|legacy`。

### 7.3 配置项
- `SEARCH_CACHE`：统一搜索缓存开关。
- `CACHE_EXPIRE_SECONDS`：搜索缓存 TTL。
- `SEARCH_PRESENTATION_MAX_HITS`：展示层分页预取窗口上限。
- `SEARCH_CALLBACK_TOKEN_TTL_SEC`：分页短 token TTL。
