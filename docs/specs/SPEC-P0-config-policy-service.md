# 功能名称：P0-统一配置策略服务（ConfigPolicyService）

> 状态：Implemented (2026-02-25)  
> 优先级：P0  
> 关联规格：[`SPEC-P0-service-layer-architecture.md`](./SPEC-P0-service-layer-architecture.md)

## 1. 业务目标（一句话）
将白名单/黑名单策略收敛为单一真源并通过统一 Service 对外提供读写，消除 Bot、API、下载链路之间的配置漂移。

## 2. 验收标准（Given-When-Then）
1. Given Bot 执行策略变更命令，When API 调用 `GET /api/v1/config`，Then 返回与 Bot 刚写入一致的 `white_list/black_list`。
2. Given API 调用 `/api/v1/config/{white|black}list` 更新策略，When 下载任务进行过滤判断，Then 使用最新策略且不依赖进程内旧值。
3. Given 服务重启，When 首次读取策略，Then 仍返回重启前最后一次成功写入的数据。
4. Given 重复提交相同 ID，When 调用新增/删除接口，Then 结果幂等，`added/removed` 精确反映本次变化。
5. Given 无效输入（非整数、超范围、空 payload），When Bot/API 调用更新接口，Then 返回统一错误语义（HTTP 422 或 Bot 统一错误文案）。
6. Given 同时触发多个配置更新请求，When 并发写入发生，Then 最终状态可预测（无丢写、无重复、版本递增）。

## 3. 背景与现状审查（As-Is）
### 3.1 当前实现（代码事实）
- API 路由 `src/tg_search/api/routes/config.py` 直接读写 `settings.WHITE_LIST/BLACK_LIST`（进程内可变列表），不持久化。
- Bot 命令 `src/tg_search/core/bot.py` 中 `/set_white_list2meili` 与 `/set_black_list2meili` 直接写 Meili `config` 索引。
- 下载链路 `src/tg_search/main.py` 使用 `read_config_from_meili` 读取 `config` 索引，并回退到 `settings` 默认值。
- `TelegramUserBot` 初始化时读取一次策略并缓存为实例字段，运行中不自动同步 API 的变更。
- `ConfigStore`（`src/tg_search/config/config_store.py`）已存在且可用，但目前仅覆盖 `sync/storage/ai`，未承载 policy。

### 3.2 问题总结
- 双真源：API 与 Bot 写入路径不同，导致行为不一致。
- 不可持久：API 对策略的修改重启后丢失。
- 可观测性差：策略变更没有统一审计语义。
- 测试空缺：缺少“Bot 写 API 读 / API 写下载生效 / 重启保持”的闭环回归。

## 4. 目标范围（Scope）与非目标（Out of Scope）
### 4.1 Scope
- 新增 `ConfigPolicyService`，作为策略唯一入口。
- `white_list/black_list` 迁移到 `ConfigStore` 新 `policy` section（单一真源）。
- API `GET /config` 与 `/config/{white|black}list` 改为调用 Service。
- Bot 白黑名单命令改为调用 Service，不再直写 Meili `config` 索引。
- 下载过滤链路改为从 Service 获取策略。
- 明确静态配置与动态配置分层：静态参数从 `.env`，运行时策略从 MeiliSearch 文档。

### 4.2 Out of Scope
- 不重构搜索逻辑与运行控制逻辑（分别由 SearchService / RuntimeControlService 处理）。
- 不在本阶段修改 WebUI API 契约字段（保持 `ConfigModel` 不变）。
- 不做分布式多实例一致性协议（当前单进程部署前提）。
- 不兼容 legacy `config` 索引，不提供自动迁移。

## 5. 技术设计（To-Be）
### 5.1 领域模型（建议放 `services/contracts.py`）
```python
class PolicyConfig(BaseModel):
    white_list: list[int]
    black_list: list[int]
    version: int
    updated_at: str
    source: Literal["config_store", "bootstrap_defaults"]


class PolicyChangeResult(BaseModel):
    updated_list: list[int]
    added: list[int] = []
    removed: list[int] = []
    version: int
```

### 5.2 Service 接口
```python
class ConfigPolicyService:
    async def get_policy(self, refresh: bool = False) -> PolicyConfig: ...
    async def add_whitelist(self, ids: list[int], source: str) -> PolicyChangeResult: ...
    async def remove_whitelist(self, ids: list[int], source: str) -> PolicyChangeResult: ...
    async def add_blacklist(self, ids: list[int], source: str) -> PolicyChangeResult: ...
    async def remove_blacklist(self, ids: list[int], source: str) -> PolicyChangeResult: ...
```

### 5.3 存储模型（ConfigStore 扩展）
- 在 `GlobalConfig` 增加 `policy` section：
```python
class PolicySection(BaseModel):
    white_list: list[int] = []
    black_list: list[int] = []
```
- `GlobalConfig` 新增字段：`policy: PolicySection = Field(default_factory=PolicySection)`。
- 所有策略写入通过 `ConfigStore.save_config({"policy": ...})` 完成，沿用 version 递增与缓存机制。

### 5.4 配置读取策略（无迁移、极简）
读取顺序：
1. `.env` 静态配置：`MEILI_HOST`、`MEILI_MASTER_KEY`、`APP_ID`、`APP_HASH`、`BOT_TOKEN` 等启动必需项。
2. `ConfigStore.policy` 动态配置：`white_list`、`black_list` 及后续运行时策略。

初始化规则：
- 若 `ConfigStore` 文档不存在，启动时写入默认 policy（空白名单 + 空黑名单或团队约定默认值）。
- 不读取 legacy `config` 索引，不回退到 `settings.WHITE_LIST/BLACK_LIST` 可变列表。
- `settings` 中策略字段仅保留为“启动默认值来源”，不作为运行时真源。

### 5.5 API/Bot/下载链路接入
- API：`src/tg_search/api/routes/config.py` 改为 `Depends(get_config_policy_service)`。
  - `GET /api/v1/config` 维持 `ConfigModel`；其中策略字段来自 Service，其余静态字段继续来自 `.env -> settings`。
  - `POST/DELETE /whitelist|/blacklist` 返回结构保持 `ListUpdateResponse`，向后兼容现有前端。
- Bot：`src/tg_search/core/bot.py` 的两条策略命令调用 Service，保留原命令名（兼容现有用户）。
- 下载链路：
  - `src/tg_search/main.py` 在启动下载前从 Service 获取策略。
  - `src/tg_search/core/telegram.py` 采用“TTL 拉取 + Service 推送快照”双通道更新，保证同进程写后快速可见。

### 5.6 校验与错误语义
- 统一校验器：
  - `ids` 必须为非空 `list[int]`；
  - 元素去重后处理；
  - 超出 int64 或明显非法值返回校验错误。
- API 侧错误映射：
  - Service 统一抛 `DomainError(code, message, detail)`；
  - `policy_invalid_ids` -> `422`
  - `policy_store_unavailable` -> `503`
  - `policy_version_conflict` -> `409`
  - 参数不合法：`422`
  - 配置存储不可用：`503`
  - 并发写冲突（若启用 expected_version）：`409`
- Bot 侧错误文案不暴露内部堆栈，统一为“参数错误/服务暂不可用/写入冲突”。

### 5.7 非功能需求
- 配置更新接口 P95 `<= 400ms`（单实例，本地 Meili）。
- `GET /config` P95 `<= 200ms`（命中 ConfigStore 缓存）。
- 策略读取失败时启动失败（fail-fast），避免静默退回旧路径导致行为漂移。
- 审计日志字段最少包含：`source`（api/bot/bootstrap）、`action`、`before_size`、`after_size`、`version`。

## 6. 任务拆分（每项 30-60 分钟）
- [x] T-P0-CPS-01 在 `services/contracts.py` 定义 `PolicyConfig/PolicyChangeResult`。
- [x] T-P0-CPS-02 扩展 `ConfigStore` 模型，新增 `policy` section 与默认值。
- [x] T-P0-CPS-03 新建 `ConfigPolicyService` 并实现统一读写逻辑（含幂等处理）。
- [x] T-P0-CPS-04 在 API 依赖注入中注册 `ConfigPolicyService`，改造 `routes/config.py`。
- [x] T-P0-CPS-05 改造 Bot 两条策略命令，移除直写 Meili `config` 索引路径。
- [x] T-P0-CPS-06 改造 `download_and_listen` 与 `TelegramUserBot` 的策略读取入口。
- [x] T-P0-CPS-07 补齐单元测试：幂等、去重、校验、版本冲突。
- [ ] T-P0-CPS-08 补齐集成/E2E：Bot 写 API 读、API 写下载生效、重启保持。（已完成 API 写 -> 运行时 `<1s` 可见）
- [x] T-P0-CPS-09 清理 legacy `config` 的**策略字段**读取/写入路径与文档说明（消息 offset 路径保留）。

## 7. 测试计划（对齐 `tests/TESTING_GUIDELINES.md`）
### 7.1 单元测试（`tests/unit/`，marker=`unit`）
1. `ConfigPolicyService` 幂等新增/删除（重复 ID 不重复计数）。
2. 校验失败路径（空列表、类型错误、越界）。
3. 冷启动逻辑：ConfigStore 无文档时自动初始化默认 policy。
4. API `/config` 路由保持响应 schema 不变（`ConfigModel` + `ListUpdateResponse`）。

### 7.2 集成测试（`tests/integration/`，marker=`integration`/`meili`）
1. 首次启动自动初始化 `system_config.policy` 成功。
2. API 写策略后，`download_and_listen` 的过滤决策立即生效。
3. Bot 写策略后，API `GET /config` 读取一致。
4. 服务重启后策略仍存在（持久化验证）。

### 7.3 推荐执行命令
```bash
pytest tests/unit -v -m unit
RUN_INTEGRATION_TESTS=true pytest tests/integration -v -m "integration and meili"
```

## 8. 风险与回滚
- 风险 1：不做迁移会导致历史策略丢失。  
  控制：发布说明中要求手动导入一次策略或接受重置为空。
- 风险 2：API 与 Bot 同时写导致版本竞争。  
  控制：基于 `ConfigStore.version` 做乐观锁重试（或 409 返回）。
- 风险 3：ConfigStore 不可用时系统无法加载动态策略。  
  控制：启动失败并给出明确错误，禁止 silent fallback。
- 回滚策略：回滚到上一版本代码；本版本内不保留 legacy 兼容分支。

## 9. ADR（架构决策记录）
- ADR-CPS-001：策略配置必须单一真源（`ConfigStore.policy`），禁止并行维护多份可写状态。
- ADR-CPS-002：为保持实现精简，取消 legacy 自动迁移，升级时由运维手动处理历史策略。
- ADR-CPS-003：API 与 Bot 共享同一校验与写入逻辑，避免规则分叉。
- ADR-CPS-004：外部契约稳定优先，`/api/v1/config` 响应 schema 保持兼容。

## 10. 实现笔记（2026-02-25）
- 已新增 Service 层实现：`src/tg_search/services/config_policy_service.py`、`src/tg_search/services/contracts.py`。
- 已扩展 `ConfigStore`：`src/tg_search/config/config_store.py` 中新增 `policy` section，支持 `update_section("policy", ...)`。
- API 配置端点已切换为 Service 依赖：`src/tg_search/api/routes/config.py`。
- Bot 策略命令已切换为 Service：`src/tg_search/core/bot.py`。
- 下载/监听链路已读取统一策略源：`src/tg_search/main.py` + `src/tg_search/core/telegram.py`。
- 监控日志点已补充：
  - `ConfigPolicyService.get_policy` 输出读取耗时、白黑名单规模、版本号；
  - 变更审计日志输出 `source/action/target/before_size/after_size/version`；
  - Telegram 侧策略刷新输出 TTL 与列表规模（debug）。
- 单元测试已覆盖：`tests/unit/test_config_policy_service.py`，并更新 `tests/unit/test_api.py` 的策略服务注入夹具。
- 新增 E2E：`tests/integration/test_service_layer_architecture_e2e.py` 覆盖共享容器注入与 API 写策略后运行时 `<1s` 可见。
- 待补：`tests/integration/` 中的 Bot/API/下载一致性端到端回归（T-P0-CPS-08）。
