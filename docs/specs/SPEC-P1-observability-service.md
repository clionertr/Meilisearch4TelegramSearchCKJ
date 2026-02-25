# 功能名称：P1-统一可观测性服务（ObservabilityService）

## 1. 业务目标（一句话）
统一 Bot `/ping` 与 API 状态类接口的数据聚合逻辑，形成一致的系统快照输出能力。

## 2. 验收标准（Given-When-Then 格式）
1. Given Meili 正常可用，When 调用 API `/status` 与 Bot `/ping`，Then 核心统计字段来自同一 Service 快照。
2. Given Meili 临时不可用，When 调用状态接口，Then 两端都返回“服务不可用”语义且不抛未处理异常。
3. Given 有下载任务进行中，When 调用 API `/status/progress` 与 WebSocket 推送，Then 活跃任务数与进度字段一致。
4. Given 需要索引统计，When 调用 API `/search/stats` 与 `/storage/stats`，Then 共用同一底层统计采集逻辑。
5. Given 运行内存统计不可获取（平台限制），When 生成系统状态，Then 返回降级值并附带可诊断说明。

## 3. 简单的技术设计 & 非功能需求
### 3.1 当前问题
- Bot `/ping` 手工拼装 Meili 全局统计文本。
- API `/status`、`/search/stats`、`/storage/stats` 分散读取不同统计，存在重复与字段漂移风险。

### 3.2 Service 接口（建议）
```python
class ObservabilityService:
    async def system_snapshot(self) -> SystemSnapshot: ...
    async def index_snapshot(self) -> IndexSnapshot: ...
    async def storage_snapshot(self) -> StorageSnapshot: ...
    async def progress_snapshot(self) -> ProgressSnapshot: ...
```

### 3.3 数据模型建议
- `SystemSnapshot`：uptime、meili_connected、telegram_connected、bot_running、memory_usage_mb
- `IndexSnapshot`：total_documents、is_indexing、database_size、last_update
- `ProgressSnapshot`：all_progress、active_count
- Presentation 再分别映射为 API JSON 或 Bot 文本

### 3.4 异常与降级
- 采集失败不应导致整个接口 500；返回局部降级并记录 `notes/errors`。
- Bot `/ping` 使用统一错误文案模板，避免泄漏底层异常细节给普通用户。

### 3.5 非功能需求
- 快照接口目标：`<= 800ms`
- 统一日志字段：`trace_id/source/snapshot_type/duration_ms`
- 服务应支持无 Telegram 客户端场景（API-only）

## 4. 任务拆分（每个任务 30-60 分钟）
- [x] T-P1-OBS-01 定义 `SystemSnapshot/IndexSnapshot/StorageSnapshot/ProgressSnapshot` DTO。
- [x] T-P1-OBS-02 抽离 API `/status` 逻辑到 ObservabilityService。
- [x] T-P1-OBS-03 抽离 API `/search/stats` 逻辑到 ObservabilityService。
- [x] T-P1-OBS-04 抽离 API `/storage/stats` 逻辑到 ObservabilityService。
- [x] T-P1-OBS-05 改造 Bot `/ping` 调用 ObservabilityService 并只保留文本渲染。
- [x] T-P1-OBS-06 增加异常降级与统一日志。
- [x] T-P1-OBS-07 增加单元与集成回归测试（正常/故障/降级路径）。

## 5. E2E 测试用例清单
1. 正常场景下 Bot `/ping` 与 API `/status` 的文档数一致。
2. 断开 Meili 后 API `/status` 不 500，返回 `meili_connected=false`。
3. 启动下载任务后 API `/status/progress` `active_count` 与 WebSocket 进度一致。
4. API-only 模式下状态接口可用，`telegram_connected=false`。
5. 状态采集超时时返回降级结果并写审计日志。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-OBS-001：状态聚合必须集中在 ObservabilityService，禁止路由与命令各自采集。
- ADR-OBS-002：快照采集采用“部分失败可用”策略，优先保证接口可响应。
- ADR-OBS-003：Bot 文本展示与 API JSON 展示解耦，数据对象共享。
- ADR-OBS-004：WebSocket 仍保留事件推送角色，但数据来源统一到进度快照接口与 registry。

### 2026-02-25 实现落地记录
- 新增 `src/tg_search/services/observability_service.py`，统一提供 `system/index/storage/progress` 四类快照接口。
- `src/tg_search/services/contracts.py` 新增快照 DTO：`SystemSnapshot`、`IndexSnapshot`、`StorageSnapshot`、`ProgressSnapshot`。
- API 路由改造为统一依赖注入：
  - `/api/v1/status` -> `ObservabilityService.system_snapshot`
  - `/api/v1/status/progress` -> `ObservabilityService.progress_snapshot`
  - `/api/v1/search/stats` -> `ObservabilityService.index_snapshot`
  - `/api/v1/storage/stats` -> `ObservabilityService.storage_snapshot`
- Bot `/ping` 改造为仅渲染展示层文本，状态采集统一走 ObservabilityService；Meili 不可用时返回固定文案“服务不可用”。
- 统一日志字段已落地：`trace_id/source/snapshot_type/duration_ms`，并补充慢采集告警阈值（`OBS_SNAPSHOT_WARN_MS`）。
- 新增配置：
  - `OBS_SNAPSHOT_TIMEOUT_SEC`（快照采集超时，默认 `0.8s`）
  - `OBS_SNAPSHOT_WARN_MS`（慢采集告警阈值，默认 `800ms`）
- 测试落地：
  - 单元：`tests/unit/test_observability_service.py`
  - 真实环境 E2E：`tests/integration/test_observability_service_e2e.py`
  - 并回归通过：`tests/integration/test_storage.py`、`tests/integration/test_service_layer_architecture_e2e.py`
