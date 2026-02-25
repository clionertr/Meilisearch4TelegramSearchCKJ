# 架构审计与无保留批评（按优先级）

> 审计目标：对当前仓库进行“能上线/不能上线”级别的架构批评。  
> 审计范围：已逐项审阅仓库一方代码与文档（`src/`、`tests/`、`webui-example/`、`docs/specs/`、部署文件）。第三方依赖和缓存目录（如 `node_modules/`、`.mypy_cache/`）仅做风险扫描，不做逐行审阅。

---

## 结论（先说重话）

这个项目**功能很多，但系统边界和安全边界没有立住**。  
当前状态更像“可演示原型 + 大量补丁”，不是可持续演进的生产系统。

如果只看上线阻断项（P0），至少有以下 5 个：
1. 凭据管理失控（硬编码密钥 + 明文 token 持久化 + URL token）。
2. 运行时状态模型失效（`AppState` 与真实 Bot/Telegram 客户端脱节）。
3. 下载链路存在数据一致性漏洞（先推进 offset，再异步写入，且写失败被吞）。
4. 鉴权是“配置不当即裸奔”的默认姿势（`API_KEY` 为空时多数接口直接放行）。
5. 核心能力重复实现，配置真源分裂（Bot/API 各自维护逻辑，行为漂移已发生）。

---

## P0（必须立即修，不修别谈上线）

### P0-1 凭据泄露与密钥管理失控

**证据**
- `tests/integration/test_ai_config.py:44`：硬编码了看起来是真实格式的 `nvapi-...` 密钥。
- `src/tg_search/api/auth_store.py:66-77`：Bearer token + 手机号等 PII 明文序列化。
- `src/tg_search/api/auth_store.py:149-151`：明文写入 `session/auth_tokens.json`。
- `src/tg_search/config/settings.py:132`：默认持久化到本地 `session/auth_tokens.json`。
- `src/tg_search/api/routes/ws.py:101-116` + `webui-example/src/hooks/useWebSocket.ts:8`：token 放在 WebSocket URL query 参数。

**为什么是 P0**
- 这不是“代码风格”问题，是**凭据泄露面**问题。  
- URL token 会进入代理日志、浏览器历史、监控链路；明文 token 文件会进入磁盘备份和误共享链路。

**立即动作**
1. 立刻轮换所有测试/生产密钥，删除硬编码 key（包括 git 历史层面）。
2. 停止在 URL 传 token，WebSocket 改为 `Authorization` header 或一次性短期 ticket。
3. token 持久化改为加密存储（至少 envelope encryption），并最小化存储字段（去掉手机号）。
4. 将 `AUTH_TOKEN_STORE_FILE` 默认改为内存或显式禁用，生产必须显式配置安全存储。

---

### P0-2 运行时状态模型是假的，API 状态与真实系统脱节

**证据**
- `src/tg_search/api/state.py:185-187` 定义了 `telegram_client`/`bot_handler`，但全局没有稳定赋值链路。
- `src/tg_search/api/app.py:102-103` 在 `lifespan` 里创建了局部 `bot_handler` 并运行，但没有挂到 `app_state`。
- `src/tg_search/api/routes/control.py:125-130` 和 `src/tg_search/api/routes/status.py:57-59` 依赖 `app_state.telegram_client`/`bot_handler` 判定状态。
- `src/tg_search/api/routes/dialogs.py:126-130` 直接依赖 `app_state.telegram_client` 拉会话，若为空直接返回空列表。

**为什么是 P0**
- 控制面与数据面不一致：接口可能说“没连上”，但后台在跑；也可能反过来。  
- 这会直接导致 WebUI 误判、运维误判、自动化流程误判。

**立即动作**
1. 定义单一 RuntimeService，统一持有 Bot task / Telegram client 引用。
2. `lifespan`、`/client/start`、`/client/stop` 全部走 RuntimeService，不允许路由直接操作 task。
3. `status/control/dialogs` 只读取 RuntimeService 快照，禁止各路由自行拼状态。

---

### P0-3 下载链路有数据丢失风险（先推进增量位点，再写索引）

**证据**
- `src/tg_search/core/telegram.py:402-404`：先 `update_latest_msg_config4_meili(...)`，再 `_process_message_batch(messages)`。
- `src/tg_search/core/telegram.py:446-460`：批量写入失败仅日志，不抛错，调用方感知不到失败。
- 同文件 `417-419` 末尾分支仍可能先更新位点再写。

**为什么是 P0**
- 一旦 Meili 写失败但 offset 已推进，下次增量同步会跳过该段消息，形成**静默数据丢失**。  
- 这是索引系统最致命的一类错误：你以为同步成功，实际丢数据。

**立即动作**
1. 顺序改为“写入成功 -> 提交位点（checkpoint）”。
2. `_process_message_batch` 失败必须抛异常，由上层决定重试/中断。
3. 给 checkpoint 增加幂等和事务语义（至少确保位点不早于已落盘数据）。

---

### P0-4 鉴权策略“配置错误即裸奔”

**证据**
- `src/tg_search/api/deps.py:42-44`：`API_KEY` 未配置直接跳过 API Key 校验。
- `src/tg_search/api/deps.py:261-264`：双通道鉴权在 `API_KEY is None` 时直接 `auth_type="none"` 放行。
- `src/tg_search/api/routes/__init__.py:22-60`：`/search`、`/status`、`/config`、`/client`、`/storage` 都依赖该双通道。
- `src/tg_search/api/routes/ws.py:113-114`：WebSocket 只有在 `API_KEY` 配置时才校验 token。

**为什么是 P0**
- 安全默认值反了：应该是默认拒绝，而不是默认放行。  
- 配置遗漏会导致管理接口暴露，这在真实部署里非常常见。

**立即动作**
1. 改为默认拒绝（必须显式配置 `ALLOW_ANON=false/true`）。
2. 将读写接口分级：最少也要将 `/config`、`/client`、`/storage` 强制鉴权。
3. WebSocket 强制鉴权，不允许“API_KEY 未配就开放”。

---

### P0-5 核心能力重复实现，配置真源分裂（已出现行为漂移）

**证据**
- Bot 搜索：`src/tg_search/core/bot.py:142-170, 281-340`。  
- API 搜索：`src/tg_search/api/routes/search.py:130-204`。  
- 配置更新走内存 settings：`src/tg_search/api/routes/config.py:52-54, 101-103`。  
- 下载链路读 Meili 配置：`src/tg_search/main.py:38-40` + `src/tg_search/utils/message_tracker.py:45-53`。

**为什么是 P0**
- 同一业务规则有多个“真相来源”，最终必然漂移。  
- 你已经在 `docs/specs/SPEC-P0-service-layer-architecture.md` 里承认要收敛 Service Layer，但代码还没完成收敛。

**立即动作**
1. 立刻冻结新增路由逻辑，先做 Service 收敛：`SearchService` / `RuntimeControlService` / `ConfigPolicyService`。
2. 所有路由和 Bot 命令只做输入输出映射，不做业务决策。
3. 配置统一经 `ConfigStore` 读写，禁止直接改 `settings.WHITE_LIST/BLACK_LIST`。

---

## P1（高风险高成本债务，1-2 个迭代内清掉）

### P1-1 并发策略粗暴，极易触发 Telegram 限流/不稳定

**证据**
- `src/tg_search/main.py:43-45, 91-93`：对所有会话直接建 task 后 `gather`，没有并发上限、没有退避队列。

**问题**
- 群组多时会瞬时并发打满，FloodWait 概率飙升；失败恢复也没有集中调度。

**建议**
- 使用有界并发（Semaphore / worker pool），并按 dialog 粒度做重试预算和退避。

---

### P1-2 错误处理策略混乱：有的过度吞错，有的直接暴露内部细节

**证据**
- 吞错：`src/tg_search/api/routes/status.py:37-38`、`src/tg_search/utils/message_tracker.py:51-53, 59-61`（`print` + 吞异常）。
- 内部细节外泄风险：`src/tg_search/api/routes/control.py:64, 113` 直接把 `str(e)` 回给客户端。

**问题**
- 线上调试和用户错误语义都不稳定；安全和可观测性都差。

**建议**
- 统一错误模型：内部日志记录完整堆栈，对外返回稳定错误码。
- 严禁库层 `print`，统一结构化日志。

---

### P1-3 测试体系“数量多但可信度不够”

**证据**
- 大量跳过逻辑：`tests/integration/conftest.py:28-32, 98-107`。  
- 过时辅助函数：`tests/integration/test_dialog_sync.py:210` 调用 `auth_store.create_token(...)`（实现中并无该 API）。  
- 仍保留 legacy：`tests/integration/legacy/api_integration_legacy.py`。

**问题**
- 用例很多，但真实 CI 里可能大量 skip，回归防线并不可靠。  
- 过时代码混入会误导后续维护者。

**建议**
- 区分 smoke/contract/e2e 三层测试，强制最小通过集。  
- 删除或修复过时测试 helper，清退 legacy 文件。

---

### P1-4 前端认证和连接策略存在安全与体验双风险

**证据**
- token 持久化在 localStorage：`webui-example/src/store/authStore.ts:14-31`。  
- 任意 401 全局登出：`webui-example/src/api/client.ts:31-35`。  
- WebSocket URL 带 token：`webui-example/src/hooks/useWebSocket.ts:8`。

**问题**
- XSS 条件下 token 更易被盗。  
- 瞬时 401（例如后端重启中）会把用户强制踢下线，体验抖动明显。

**建议**
- 使用更安全的 token 承载方案（至少短 TTL + refresh + 最小暴露）。  
- 401 处理区分“可重试/需登出”场景。  
- WS 改 header/ticket 鉴权。

---

### P1-5 明显死代码和历史包袱没有清理

**证据**
- `src/tg_search/app.py` 仍是 Flask + 线程跑异步的旧入口，与主 FastAPI 体系并存。  
- `webui-example/src/services/geminiService.ts:36` 用 `process.env.API_KEY`（Vite 环境通常应 `import.meta.env`），且主流程基本未使用。

**问题**
- 新成员会被错误入口误导，维护成本持续上升。  
- 死代码带来错误示例和安全误用（例如错误的环境变量读取方式）。

**建议**
- 明确唯一入口，删除或标记废弃代码。  
- 未接入主流程的服务要么接入，要么删除。

---

## P2（中优先级，影响长期演进效率）

### P2-1 规格与实现仍有结构性偏差

**现象**
- specs 已定义 Service 化方向（P0/P1），但路由中仍有大量业务逻辑和状态拼装。  
- `storage` 路由直接访问 `config_store._cache`（`src/tg_search/api/routes/storage.py:111-113`），破坏封装边界。

**建议**
- 封装显式公共方法（如 `invalidate_cache()`），禁止外部访问私有成员。

---

### P2-2 部署示例有误导性安全配置

**证据**
- `docker-compose-windows.yml:10` 使用硬编码 `MEILI_MASTER_KEY=myMasterKey123`。

**建议**
- 把示例改为 `${MEILI_MASTER_KEY:?required}` 这类强制注入写法，避免“复制即不安全上线”。

---

### P2-3 文档虽然全，但“工程约束”缺少可执行红线

**问题**
- 当前文档描述很多“应该”，但缺少自动化护栏（pre-commit secret scan、CI policy、最小安全基线检查）。

**建议**
- 增加自动化：`gitleaks`/`detect-secrets`、CI 必跑最小安全测试、部署前配置校验。

---

## 建议的整改顺序（务实版本）

1. **安全止血（1-2 天）**  
   密钥轮换、删硬编码、改 WS 鉴权、默认拒绝策略。
2. **运行时状态收敛（2-4 天）**  
   引入 RuntimeService，统一 start/stop/status 与 telegram client 引用。
3. **下载一致性修复（2-3 天）**  
   checkpoint 提交顺序改造、批处理错误上抛、失败重试策略。
4. **业务层收敛（1-2 周）**  
   搜索/配置/状态逻辑从路由与 Bot 迁入 Service 层，消灭重复实现。
5. **测试与工程卫生（并行 1 周）**  
   清理 stale/legacy 测试，建立最小必过集与 secret scan。

---

## 最后一句（直白版）

你现在最大的敌人不是“功能不够多”，而是“系统真相不唯一”。  
只要状态、配置、鉴权还分裂成多套逻辑，这个项目每加一个功能都会放大不确定性。
