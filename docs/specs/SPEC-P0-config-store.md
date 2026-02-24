# 功能名称：P0-统一配置持久化基座（Config Store）

## 1. 业务目标（一句话）
为 Dialog Sync、Storage、AI Config 提供统一的实例级全局配置读写能力，避免各功能重复实现且重启丢失。

## 2. 验收标准（Given-When-Then 格式）
1. Given 服务首次启动且配置不存在，When 调用配置读取接口，Then 返回内置默认值并自动初始化配置文档。
2. Given 配置已写入，When 重启服务后再次读取，Then 返回重启前最后一次写入值。
3. Given 两个并发写请求，When 同时更新同一配置字段，Then 后写入成功并带 `version` 递增。
4. Given 配置文档结构不合法，When 服务启动读取配置，Then 回退到默认值并记录告警日志。
5. Given 配置缓存未过期，When 连续读取配置，Then 返回缓存值并标记 `cache_hit=true`。

## 3. 简单的技术设计 & 非功能需求
### 3.1 存储方案（明确）
- 使用 MeiliSearch 新增索引：`system_config`。
- 仅存储一个文档：`id = "global"`。
- 文档结构（示例）：
```json
{
  "id": "global",
  "version": 12,
  "updated_at": "2026-02-24T12:00:00Z",
  "sync": {
    "dialogs": {
      "-100123": {
        "sync_state": "active",
        "last_synced_at": "2026-02-24T10:12:00Z",
        "updated_at": "2026-02-24T10:12:00Z"
      }
    },
    "available_cache_ttl_sec": 120
  },
  "storage": {
    "auto_clean_enabled": false,
    "media_retention_days": 30
  },
  "ai": {
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "api_key": "<plain-text-by-requirement>",
    "updated_at": "2026-02-24T09:00:00Z"
  }
}
```

### 3.2 缓存方案
- API 进程内缓存 `system_config`，TTL = `10s`。
- 写入后主动失效缓存。
- 读取支持 `refresh=true` 强制绕过缓存。

### 3.3 读写接口（内部模块，不对外暴露）
- `load_config(refresh: bool = false) -> GlobalConfig`
- `save_config(patch: dict, expected_version: int | None = None) -> GlobalConfig`
- `update_section(section: Literal["sync", "storage", "ai"], patch: dict) -> GlobalConfig`

### 3.4 非功能需求
- 配置读取目标：`<= 100ms`（缓存命中）
- 配置写入目标：`<= 500ms`
- 写操作必须结构化日志（变更字段、旧值摘要、新值摘要、version）

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P0-CS-07 增加集成测试并接入 `uv run tests/integration/run.py`。
- [ ] T-P0-CS-01 定义 `GlobalConfig` Pydantic 模型（含默认值）。
- [ ] T-P0-CS-02 创建 `system_config` 索引初始化逻辑。
- [ ] T-P0-CS-03 实现 `load_config` + 10s 内存缓存。
- [ ] T-P0-CS-04 实现 `save_config` + `version` 递增控制。
- [ ] T-P0-CS-05 实现 section 级更新辅助函数。
- [ ] T-P0-CS-06 增加单元测试（初始化/重启恢复/并发写/坏文档回退）。


## 5. E2E 测试用例清单
1. 首次启动读配置 -> 自动初始化。
2. 写入 AI 配置后重启 -> 配置保持。
3. 两次并发 patch -> version 正确递增。
4. 手动注入坏 schema -> 启动后回退默认。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-CS-001：采用 MeiliSearch 作为配置持久化后端，避免引入额外数据库。
- ADR-CS-002：配置为实例全局唯一（不做用户隔离）。
- ADR-CS-003：按需求不加密 AI key（仅限制接口回显），后续可升级。
- ADR-CS-004：MeiliSearch Python SDK 的 `get_document()` 返回 `Document` 对象而非裸 `dict`，
  需通过 `dict(raw_doc.__dict__)` 转换后才能传给 `GlobalConfig.model_validate()`。
- ADR-CS-005：`version` 递增为进程内"写-前读"乐观锁（非分布式 CAS），
  足以应对单实例顺序写场景；多实例强一致需求需另行引入分布式锁（当前明确超出范围）。
- ADR-CS-006：测试隔离策略——每个测试类使用独立 `system_config_test_<classname>` 索引，
  测试结束后通过 fixture teardown 自动清理，保证测试幂等。
- ADR-CS-007：`tests/test_config_store.py` 依赖真实 MeiliSearch；当与全套测试并跑时，
  `conftest.py` 会覆盖 `MEILI_MASTER_KEY` 为假值，结合 `.env` 显式覆盖机制和
  fixture 内 `pytest.skip()` 门控，无真实凭据时自动跳过，不影响 CI 其他测试。
