# 功能名称：P0-统一配置策略服务（ConfigPolicyService）

## 1. 业务目标（一句话）
统一白名单/黑名单等策略配置的读写与持久化，解决 Bot 与 API 各写各读导致的行为不一致问题。

## 2. 验收标准（Given-When-Then 格式）
1. Given Bot 执行设置白名单命令，When API 调用 `GET /api/v1/config`，Then 立即可见同一结果。
2. Given API 调用配置更新接口，When Bot 触发下载过滤判断，Then 使用更新后的同一策略数据。
3. Given 服务重启，When 读取配置，Then 白名单/黑名单保持最新持久化值。
4. Given 重复添加相同 ID，When 执行更新，Then 结果幂等且 `added/removed` 统计正确。
5. Given 非法输入（类型错误、超范围等），When 调用配置更新，Then API 与 Bot 都返回统一校验错误语义。

## 3. 简单的技术设计 & 非功能需求
### 3.1 当前问题
- Bot `/set_white_list2meili`、`/set_black_list2meili` 写入 Meili `config` 索引。
- API `/config/*` 修改 `settings.WHITE_LIST/BLACK_LIST`（进程内可变列表）。
- `main.download_and_listen` 读取旧 `config` 索引，导致 API 改动不一定生效或不可持久。

### 3.2 Service 接口（建议）
```python
class ConfigPolicyService:
    async def get_policy(self) -> PolicyConfig: ...
    async def add_whitelist(self, ids: list[int]) -> PolicyChangeResult: ...
    async def remove_whitelist(self, ids: list[int]) -> PolicyChangeResult: ...
    async def add_blacklist(self, ids: list[int]) -> PolicyChangeResult: ...
    async def remove_blacklist(self, ids: list[int]) -> PolicyChangeResult: ...
```

### 3.3 真源与迁移
- 目标真源：`ConfigStore`（建议新增 `policy` section，或明确映射到既有 section）。
- 兼容读取：迁移期支持从旧 `config` 索引读一次并写回新真源。
- 迁移完成后 Bot/API/下载逻辑均只依赖 ConfigPolicyService。

### 3.4 与下载过滤联动
- `download_and_listen` 与 `TelegramUserBot` 的 `is_allowed` 前读取策略，来源统一为 ConfigPolicyService。
- 可选优化：提供短 TTL 缓存，降低频繁读取开销。

### 3.5 非功能需求
- 配置更新接口 95 分位：`<= 400ms`
- 幂等与一致性优先于“立刻强一致分布式同步”（当前单实例）
- 变更必须记录结构化审计日志（操作者、来源、变更前后摘要）

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P0-CPS-01 定义 `PolicyConfig/PolicyChangeResult` DTO。
- [ ] T-P0-CPS-02 实现 ConfigPolicyService 读写接口并接入 ConfigStore。
- [ ] T-P0-CPS-03 为旧 `config` 索引实现一次性迁移读取逻辑。
- [ ] T-P0-CPS-04 改造 API `/config` 路由为 ConfigPolicyService 调用。
- [ ] T-P0-CPS-05 改造 Bot 白黑名单命令为 ConfigPolicyService 调用。
- [ ] T-P0-CPS-06 改造下载过滤链路（`download_and_listen`/`TelegramUserBot`）读取新真源。
- [ ] T-P0-CPS-07 增加配置一致性回归测试（Bot 写 API 读、API 写 Bot 读、重启保持）。

## 5. E2E 测试用例清单
1. Bot 添加白名单后 API 可读到，且下载流程仅处理该列表内会话。
2. API 删除白名单后 Bot 再搜索/控制时使用新策略。
3. 迁移场景：旧 `config` 索引存在数据，新服务首次启动后自动导入并可读。
4. 连续重复提交相同 ID，结果幂等不重复。
5. 重启后配置不丢失，且 Bot/API 读取一致。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-CPS-001：策略配置必须单一真源，禁止并行维护 `settings` 可变列表与旧索引。
- ADR-CPS-002：迁移期支持向后兼容读取，降低升级风险。
- ADR-CPS-003：命令输入（Bot 文本）与 API 输入都走同一校验器，避免双套规则。
- ADR-CPS-004：是否将策略字段并入现有 `GlobalConfig` 由实现阶段决定，但外部调用统一通过 Service。

