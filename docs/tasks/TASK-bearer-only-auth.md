# TASK: 仅 Bearer 认证改造（前后端）

更新时间：2026-03-04  
状态：`Draft / 待确认后实施`

## 1. 信息来源与范围

本任务文档基于以下文件梳理：

- `CLAUDE.md`（仓库根目录）
- `../CLAUDE.md`（当前工作树上级入口，指向本仓库）
- `src/tg_search/api/*`（后端 API 与鉴权实现）
- `webui-example/src/*`（前端认证与请求链路）
- `README.md`、`webui-example/README.md`
- `tests/unit/*`、`tests/integration/*`（认证相关测试）

## 2. 当前项目总结（简版）

项目是一个 Telegram 消息检索系统，后端为 FastAPI + Telethon + MeiliSearch，前端为 React + TypeScript（`webui-example`）。

主要链路：

1. Bot/Runtime 下载与监听 Telegram 消息；
2. MeiliSearch 存储与全文搜索；
3. FastAPI 提供 REST + WebSocket；
4. WebUI 通过 Bearer Token 访问 API 并展示管理能力（搜索、配置、同步、存储、Dashboard、AI 配置）。

当前版本文档中标记为 `0.2.0`，服务层已收敛到 `ServiceContainer + SearchService + RuntimeControlService + ObservabilityService`。

## 3. 当前认证状态与覆盖率

## 3.1 后端认证机制现状

当前后端同时存在三种鉴权路径：

1. `verify_bearer_token`：严格 Bearer（`Authorization: Bearer <token>`）。
2. `verify_api_key_or_bearer_token`：API Key / Bearer 双通道二选一。
3. WebSocket `/api/v1/ws/status`：使用 query 参数 `?token=<token>`，并且仅在 `API_KEY` 配置时强制校验；未配置 `API_KEY` 时可无 token 接入。

另有一个测试端点：

- `/api/v1/auth/dev/issue-token`：受 `verify_api_key` 保护（且 `ALLOW_TEST_TOKEN_ISSUE=true` 才可用）。

## 3.2 API 端点覆盖率（按路由分组）

统计口径：`src/tg_search/api/routes/*.py` 中声明的 HTTP 端点（共 34 个）+ WebSocket 端点（1 个）。

| 分组 | 端点数 | 当前策略 |
|---|---:|---|
| `/auth` | 6 | 3 个免 header（send-code/signin/token-login）；2 个 Bearer（me/logout）；1 个 API Key（dev/issue-token） |
| `/search` | 2 | API Key 或 Bearer |
| `/status` | 3 | API Key 或 Bearer |
| `/config` | 5 | API Key 或 Bearer |
| `/client` | 3 | API Key 或 Bearer |
| `/storage` | 4 | API Key 或 Bearer |
| `/ai` | 4 | Bearer-only |
| `/dashboard` | 2 | Bearer-only |
| `/dialogs` | 5 | Bearer-only |
| `/ws/status` | 1(ws) | query token（且与 `API_KEY` 开关联动） |

### 覆盖率结论

1. 受保护 HTTP 端点：31/34（其余 3 个是登录换 token 入口）。
2. Bearer 可用于：30/31 个受保护 HTTP 端点（除 `/auth/dev/issue-token` 外）。
3. API Key 可用于：18/31 个受保护 HTTP 端点（17 个双通道 + 1 个 dev 端点）。
4. 安全一致性问题：当 `API_KEY` 未配置时，双通道依赖会直接放行（`auth_type="none"`），导致 `/search` `/status` `/config` `/client` `/storage` 组可“无认证访问”。

## 3.3 前端认证覆盖

前端当前事实上已经以 Bearer 为主：

1. `webui-example/src/api/client.ts` 请求拦截器统一注入 `Authorization: Bearer <token>`；
2. `401` 时统一触发 `auth:expired` 并清理登录态；
3. 登录页支持手机号验证码流程与 token 直登（最终都拿到 Bearer）；
4. WebSocket hook 通过 `?token=${token}` 连接 `/ws/status`。

结论：前端主流程没有 API Key 依赖，改造重点在后端与测试/文档对齐。

## 3.4 测试覆盖现状（认证维度）

现状是 Bearer 与 API Key 混合覆盖：

1. Bearer 重点覆盖：
   - `tests/integration/test_ai_config.py`
   - `tests/integration/test_dashboard_e2e.py`
   - `tests/integration/test_dialog_sync.py`
   - `tests/integration/test_dialog_sync_e2e.py`
2. API Key 重点覆盖：
   - `tests/integration/test_storage.py`
   - `tests/integration/test_service_layer_architecture_e2e.py`
   - `tests/integration/test_search_service_e2e.py`
   - `tests/integration/conftest.py`（全局 client 默认可挂 X-API-Key）
   - `tests/integration/run.py`（自动签发 token 时可带 X-API-Key）
3. 单测层面：`tests/unit/test_auth_store.py` 覆盖 token 存储/撤销/过期；`tests/unit/test_api.py` 主要覆盖 auth 基本流程，但对 API Key/Bearer 决策矩阵覆盖不足。

## 4. 改造目标（确认版）

目标：前后端“业务鉴权”统一为 Bearer-only，取消 API Key 作为 API 调用凭证。

明确目标边界：

1. 所有需要鉴权的业务端点统一 `Authorization: Bearer <token>`。
2. 不再存在 `API_KEY` 放行分支，不再允许 API Key 访问业务端点。
3. WebSocket 继续可用 Bearer token（传输方式待确认：query 参数或其它）。
4. 前端继续复用现有 Bearer 请求拦截器，不引入重复逻辑。
5. 文档与测试全部切换到 Bearer 口径。

## 5. 代码复用策略（本次改造重点）

避免“每个端点各写一套认证逻辑”，统一复用：

1. 抽象统一 token 校验函数（供 HTTP dependency 和 WebSocket 共用）：
   - 输入：`token` 字符串；
   - 输出：`AuthToken | None`；
   - 错误映射统一（`TOKEN_MISSING` / `TOKEN_INVALID`）。
2. 保留并强化 `parse_bearer_token`，避免重复解析 Authorization 头。
3. 路由层统一用同一个依赖（例如 `verify_bearer_token`），删除双通道依赖。
4. 测试层增加共享 helper（签发测试 token、构造 auth headers），减少每个文件重复造轮子。

## 6. 实施任务分解（待你确认后执行）

## Phase 0 - 基线冻结

1. 建立认证矩阵快照（端点 -> 当前策略 -> 目标策略）。
2. 跑一轮现有测试，记录与认证相关失败基线（便于对比）。

## Phase 1 - 后端依赖层改造（核心）

1. 在 `src/tg_search/api/deps.py` 删除 API Key 相关逻辑：
   - `verify_api_key`
   - `verify_api_key_or_bearer_token`
   - `api_key_header`
2. 保留并增强 Bearer 依赖与错误语义，统一返回结构。
3. 若需要保留兼容期变量，明确标注“已废弃，不参与鉴权”。

## Phase 2 - 路由鉴权策略统一

1. `src/tg_search/api/routes/__init__.py`：
   - `/search` `/status` `/config` `/client` `/storage` 从“双通道”切换为 Bearer-only。
2. `dialogs` 保持 Bearer-only（已有实现），去除注释中的历史兼容描述。
3. `/auth/dev/issue-token` 策略调整（见“待确认决策”）。

## Phase 3 - WebSocket 鉴权统一

1. `src/tg_search/api/routes/ws.py` 去除 `API_KEY` 条件开关。
2. 无论环境如何，统一要求 token 并校验有效性。
3. 与 HTTP Bearer 语义对齐：缺失/无效时统一 4401 并记录清晰日志。

## Phase 4 - 前端对齐（最小改动）

1. 保持 `api/client.ts` Bearer 注入逻辑不变（复用现有实现）。
2. 仅对 WebSocket token 传递方式做对齐（若后端参数名调整则同步）。
3. 校验 Login / ProtectedRoute / auth expired 事件链不受回归。

## Phase 5 - 测试迁移与补强

1. 将仍依赖 X-API-Key 的集成测试迁移为 Bearer：
   - `tests/integration/test_storage.py`
   - `tests/integration/conftest.py`
   - `tests/integration/test_service_layer_architecture_e2e.py`
   - `tests/integration/test_search_service_e2e.py`
   - `tests/integration/run.py`（token bootstrap）
2. 为 `deps.py` 增加单测，覆盖：
   - 缺失 Authorization -> 401/TOKEN_MISSING；
   - 非法 token -> 401/TOKEN_INVALID；
   - 合法 token -> 放行。
3. 增加 WebSocket 认证单测/集成测，验证“始终要求 token”。

## Phase 6 - 文档与配置收口

1. 更新 `README.md` 认证说明与 curl 示例（全部改为 Authorization Bearer）。
2. 更新 `src/tg_search/api/CLAUDE.md` 中 API Key 相关章节。
3. 更新 `.env.example` 与配置注释，标明 API Key 已废弃或移除。
4. 更新 `webui-example/README.md` 的 WebSocket 认证说明（如有变化）。

## 7. 待确认决策（请你拍板）

1. `/api/v1/auth/dev/issue-token` 是否保留？
   - 方案 A：保留，仅 `ALLOW_TEST_TOKEN_ISSUE=true` 时开放（不再依赖 API Key）。
   - 方案 B：删除该端点，测试统一走真实登录或直接操作 `AuthStore`。
2. WebSocket Bearer 传递方式是否继续 `query token`？
   - 方案 A：保持 `?token=`（浏览器兼容性最好，改动最小）。
   - 方案 B：改为其它方式（实现更复杂，前端兼容成本更高）。
3. `token-login` 是否保留？
   - 方案 A：保留（便于开发/恢复会话）。
   - 方案 B：删除（更严格，但会影响现有 WebUI 登录分支）。

## 8. 验收标准（完成编码后判定）

1. 业务受保护端点统一 Bearer-only（无 API Key 分支）。
2. `API_KEY` 配置与否不再影响业务接口认证强度。
3. WebUI 全路径（登录、搜索、状态、配置、同步、存储、Dashboard、AI）可正常使用。
4. 认证相关测试全部通过，且新增用例覆盖关键失败路径。
5. 文档示例不再出现 `X-API-Key` 调用业务 API。

