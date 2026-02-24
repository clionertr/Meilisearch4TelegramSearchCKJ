# 功能名称：P0-统一运行控制服务（RuntimeControlService）

## 1. 业务目标（一句话）
统一 Bot 与 API 对下载/监听任务的启停与状态查询逻辑，确保单实例内运行状态唯一且可观测。

## 2. 验收标准（Given-When-Then 格式）
1. Given 服务未运行下载任务，When API 调用 `POST /api/v1/client/start`，Then 返回 `started` 且任务进入运行态。
2. Given 服务已运行下载任务，When Bot 执行 `/start_client`，Then 返回 `already_running` 语义且不重复创建任务。
3. Given 服务正在运行，When Bot 执行 `/stop_client` 或 API 调用 `/client/stop`，Then 任务被统一停止且状态一致。
4. Given API-only 模式，When 触发启动动作，Then 统一返回不可启动错误（而非某入口可启动、某入口失败）。
5. Given 并发触发 start/stop，When 多请求同时到达，Then 通过锁保证状态机正确，无重复任务与泄漏。

## 3. 简单的技术设计 & 非功能需求
### 3.1 当前问题
- Bot 使用 `BotHandler.download_task` 管理任务。
- API 使用 `AppState.bot_task` 管理任务。
- 两套状态并行存在，容易出现“一个入口显示运行，另一个入口显示未运行”。

### 3.2 Service 接口（建议）
```python
class RuntimeControlService:
    async def start(self, source: str) -> RuntimeActionResult: ...
    async def stop(self, source: str) -> RuntimeActionResult: ...
    async def status(self) -> RuntimeStatus: ...
```

### 3.3 状态机
- `stopped` -> `starting` -> `running` -> `stopping` -> `stopped`
- 统一由 Service 维护 `task`、`last_action_source`、`last_error`
- 使用 `asyncio.Lock` 包裹 start/stop 临界区

### 3.4 注入方式
- API lifespan 创建单例 `RuntimeControlService` 放入 `AppState`
- BotHandler 初始化时注入同一实例，不再自行维护 `download_task`

### 3.5 非功能需求
- `status()` 读取开销 `<= 50ms`
- start/stop 幂等：重复调用不报错，返回明确状态
- 任务取消后资源释放必须可验证（telegram client cleanup 被调用）

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P0-RCS-01 定义 `RuntimeActionResult/RuntimeStatus` DTO。
- [ ] T-P0-RCS-02 新建 RuntimeControlService 并实现统一 start/stop/status。
- [ ] T-P0-RCS-03 将 API `/client/*` 改为调用 RuntimeControlService。
- [ ] T-P0-RCS-04 将 Bot `/start_client` `/stop_client` 改为调用 RuntimeControlService。
- [ ] T-P0-RCS-05 去除 BotHandler 内部独立 `download_task` 状态源。
- [ ] T-P0-RCS-06 加入并发场景测试（start-start、stop-stop、start-stop 竞争）。
- [ ] T-P0-RCS-07 回归测试 API-only 模式与错误映射。

## 5. E2E 测试用例清单
1. API 启动后，Bot 再启动返回 `already_running`。
2. Bot 停止后，API `GET /client/status` 显示 `is_running=false`。
3. 并发 10 次 `start` 最终仅有 1 个任务运行。
4. API-only 模式下 Bot/API 均返回一致错误。
5. 强制取消任务后，后续可再次启动并正常工作。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-RCS-001：运行控制必须是单一真源（Service），不允许入口各自维护 task。
- ADR-RCS-002：幂等返回优先于抛错，便于前端和 Bot UX。
- ADR-RCS-003：source 字段用于审计（`api`/`bot`），便于排查冲突操作。
- ADR-RCS-004：临界区使用 `asyncio.Lock`，单进程场景足够，分布式扩展另开专题。

