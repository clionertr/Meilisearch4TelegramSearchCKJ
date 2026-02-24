# 功能名称：P1-AI 配置与连通性测试 API（AI Config）

## 1. 业务目标（一句话）
提供实例级 AI 配置读写与连通性测试能力，支撑 `AIConfig` 页面真实保存与校验。

## 2. 验收标准（Given-When-Then 格式）
1. Given 未携带 Bearer Token，When 调用 `/api/v1/ai/*`，Then 返回 `401`。
2. Given 已登录，When `GET /api/v1/ai/config`，Then 返回 `200` 且仅返回 `api_key_set` 不回显明文 key。
3. Given 已登录，When `PUT /api/v1/ai/config` 传入合法参数，Then 返回 `200` 且配置可被后续 `GET` 读取。
4. Given 配置不合法（空 model、非法 URL），When `PUT /ai/config`，Then 返回 `422`。
5. Given 已登录，When `POST /api/v1/ai/config/test`，Then 返回 `200` 且包含 `ok/error_code/error_message/latency_ms`。
6. Given provider 不支持模型列表查询，When `GET /api/v1/ai/models`，Then 返回 `200` 且 `data.models=[current_config_model]`。

## 3. 简单的技术设计 & 非功能需求
### 3.1 前置依赖（明确）
- 新增运行时依赖：`httpx>=0.27`（当前只在 dev 依赖中存在）。
- 不新增 OpenAI/Anthropic SDK，统一使用 HTTP 调用（降低耦合）。

### 3.2 API 设计（明确 schema）
1. `GET /api/v1/ai/config`
```json
{
  "success": true,
  "data": {
    "provider": "openai_compatible",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "api_key_set": true,
    "updated_at": "2026-02-24T12:00:00Z"
  }
}
```

2. `PUT /api/v1/ai/config`
- 请求：
```json
{
  "provider": "openai_compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "api_key": "sk-xxx"
}
```
- 约束：`provider` 暂仅支持 `openai_compatible`（P1范围），其余 provider 预留。

3. `POST /api/v1/ai/config/test`
- 行为：调用 `${base_url}/models`（Bearer `api_key`）进行连通性测试。
- 响应：
```json
{"success":true,"data":{"ok":false,"error_code":"AUTH_FAILED","error_message":"401 unauthorized","latency_ms":234}}
```

4. `GET /api/v1/ai/models`
- 优先动态拉取 `${base_url}/models`。
- 拉取失败时回退 `[current_config_model]` 并返回 `fallback=true`。

### 3.3 持久化
- 实例全局唯一配置，存储在 [SPEC-P0-config-store.md](/home/sinfor/Games/SteamLibrary/CODE/Meilisearch4TelegramSearchCKJ/docs/specs/SPEC-P0-config-store.md) 的 `ai` section。
- 按用户要求不加密存储；接口不回显明文 key。

### 3.4 非功能需求
- `GET/PUT /ai/config`：`<= 300ms`
- `POST /test`：超时 `10s`
- 错误分类：`NETWORK_ERROR | AUTH_FAILED | INVALID_MODEL | PROVIDER_ERROR`

## 4. 任务拆分（每个任务 30-60 分钟）
- [ ] T-P1-AI-01 在运行时依赖中加入 `httpx`。
- [ ] T-P1-AI-02 定义 ai 配置与测试响应模型。
- [ ] T-P1-AI-03 实现 `GET/PUT /ai/config`（不回显 api_key）。
- [ ] T-P1-AI-04 实现 `POST /ai/config/test`（调用 `/models`）。
- [ ] T-P1-AI-05 实现 `GET /ai/models`（动态拉取 + fallback）。
- [ ] T-P1-AI-06 单元测试（参数校验、错误分类、鉴权）。
- [ ] T-P1-AI-07 集成测试接入 `uv run tests/integration/run.py`。

## 5. E2E 测试用例清单
1. `GET /ai/config` 不回显 `api_key`。
2. `PUT /ai/config` 后重启服务，配置保留。
3. 错误 key 触发 `POST /test`，返回 `ok=false` + `AUTH_FAILED`。
4. 有效 key 触发 `POST /test`，返回 `ok=true`。
5. `GET /ai/models` 在 provider 不可用时返回 fallback 列表。

## 6. 实现笔记 & 架构决策记录（ADR）
- ADR-AI-001：P1 仅支持 `openai_compatible`，避免跨 provider 协议分歧。
- ADR-AI-002：不新增 SDK，统一 HTTP 适配，便于测试与替换。
- ADR-AI-003：不加密存储遵循当前需求，但接口层默认脱敏。
