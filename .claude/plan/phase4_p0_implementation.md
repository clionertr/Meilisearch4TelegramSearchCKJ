# Phase 4 P0 实施计划 - 完整版

> 生成时间: 2026-02-06
> 基于 Codex 后端架构 + Gemini 前端架构综合

---

## 一、项目概览

### 1.1 目标
- 实现 WebUI 的 Telegram 登录认证
- Search 页面接入真实 API
- WebSocket 实时状态推送

### 1.2 技术方案
| 组件 | 方案 |
|------|------|
| 后端鉴权 | 双通道（API Key 或 Bearer Token） |
| Token 生成 | `secrets.token_urlsafe(32)` |
| Token 存储 | 内存 (`AuthStore`) |
| WebSocket 鉴权 | query token (`?token=xxx`) |
| 前端状态 | Zustand + localStorage |
| API 层 | TanStack Query |
| 高亮渲染 | DOMPurify (仅允许 mark) |

---

## 二、后端架构设计 (Codex)

### 2.1 新增文件

| 文件 | 职责 |
|------|------|
| `src/tg_search/api/auth_store.py` | 内存存储登录会话和 Bearer Token |
| `src/tg_search/api/routes/auth.py` | Auth API 端点 (send-code, signin, me, logout) |

### 2.2 修改文件

| 文件 | 变更点 |
|------|--------|
| `src/tg_search/api/deps.py` | 新增 `get_auth_store`, `verify_bearer_token`, `verify_api_key_or_bearer` |
| `src/tg_search/api/state.py` | AppState 添加 `auth_store` |
| `src/tg_search/api/app.py` | lifespan 中初始化 `auth_store` |
| `src/tg_search/api/routes/__init__.py` | 注册 `/auth` 路由，更新其他路由使用双通道鉴权 |
| `src/tg_search/api/routes/ws.py` | 添加 query token 验证 |
| `src/tg_search/api/routes/search.py` | 透传 `_formatted` 字段 |
| `src/tg_search/api/models.py` | 新增 Auth 模型，扩展 MessageModel |

### 2.3 Auth API 规格

#### POST `/api/v1/auth/send-code`
- 请求: `{ phone_number: string, force_sms?: boolean }`
- 响应: `{ auth_session_id, expires_in, phone_number_masked }`
- 错误: `INVALID_PHONE`, `FLOOD_WAIT_{seconds}`, `TG_NETWORK_ERROR`

#### POST `/api/v1/auth/signin`
- 请求: `{ auth_session_id, phone_number, code, password? }`
- 响应: `{ token, token_type, expires_in, user }`
- 错误: `SESSION_NOT_FOUND`, `CODE_INVALID`, `CODE_EXPIRED`, `PASSWORD_REQUIRED`, `PASSWORD_INVALID`

#### GET `/api/v1/auth/me`
- 认证: Bearer Token
- 响应: `{ user, token_expires_at }`

#### POST `/api/v1/auth/logout`
- 认证: Bearer Token
- 响应: `{ revoked: true }`

### 2.4 数据结构

```python
@dataclass
class AuthSession:
    auth_session_id: str
    phone_number: str
    phone_code_hash: str
    expires_at: datetime
    created_at: datetime
    attempts: int = 0

@dataclass
class AuthToken:
    token: str
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    phone_number: str
    expires_at: datetime
    created_at: datetime

class AuthStore:
    sessions: dict[str, AuthSession]
    tokens: dict[str, AuthToken]
```

### 2.5 依赖注入函数

```python
def get_auth_store(request: Request) -> AuthStore
async def verify_bearer_token(...) -> AuthToken
async def verify_api_key_or_bearer_token(...) -> AuthContext
```

---

## 三、前端架构设计 (Gemini)

### 3.1 新增文件

| 文件 | 职责 |
|------|------|
| `webui-example/src/hooks/useAuth.ts` | 封装 sendCode, signIn, me, logout 的 Mutations/Query |
| `webui-example/src/hooks/useSearch.ts` | 封装 Search 的 InfiniteQuery |

### 3.2 修改文件

| 文件 | 变更点 |
|------|--------|
| `webui-example/src/api/client.ts` | 优化拦截器，与 Zustand Store 联动 |
| `webui-example/src/store/authStore.ts` | 增加完整类型定义 |
| `webui-example/src/pages/Login.tsx` | 重构使用 useAuth Hooks |
| `webui-example/src/pages/Search.tsx` | 重构使用 useSearch Hook |

### 3.3 API Hook 签名

```typescript
// useAuth.ts
export const useSendCode = () => useMutation({
  mutationFn: (data: { phone_number: string }) => authApi.sendCode(data)
});

export const useSignIn = () => useMutation({
  mutationFn: (data: SignInRequest) => authApi.signIn(data),
  onSuccess: (data) => { setAuth(data.token, data.user) }
});

export const useMe = () => useQuery({
  queryKey: ['me'],
  queryFn: authApi.me,
  retry: false
});

// useSearch.ts
export const useSearchMessages = (query: string) => useInfiniteQuery({
  queryKey: ['search', query],
  queryFn: ({ pageParam }) => searchApi.search({ q: query, offset: pageParam }),
  getNextPageParam: (lastPage) => ...
});
```

### 3.4 Zustand Store 接口

```typescript
interface UserInfo {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
}

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: UserInfo) => void;
  clearAuth: () => void;
}
```

---

## 四、实施步骤

### 阶段 1：后端基础设施 (Day 1)

| # | 任务 | 文件 |
|---|------|------|
| 1.1 | 创建 AuthStore 数据结构 | `api/auth_store.py` |
| 1.2 | 新增 Auth Pydantic 模型 | `api/models.py` |
| 1.3 | AppState 集成 auth_store | `api/state.py` |
| 1.4 | lifespan 初始化 auth_store | `api/app.py` |

### 阶段 2：认证流程 (Day 2)

| # | 任务 | 文件 |
|---|------|------|
| 2.1 | 实现 /auth/send-code | `api/routes/auth.py` |
| 2.2 | 实现 /auth/signin | `api/routes/auth.py` |
| 2.3 | 实现 /auth/me, /auth/logout | `api/routes/auth.py` |
| 2.4 | 新增 Bearer Token 依赖 | `api/deps.py` |
| 2.5 | 更新路由使用双通道鉴权 | `api/routes/__init__.py` |

### 阶段 3：搜索功能 (Day 3)

| # | 任务 | 文件 |
|---|------|------|
| 3.1 | 透传 _formatted 字段 | `api/routes/search.py` |
| 3.2 | 扩展 MessageModel | `api/models.py` |
| 3.3 | 创建 useSearch Hook | `hooks/useSearch.ts` |
| 3.4 | 重构 Search 页面 | `pages/Search.tsx` |

### 阶段 4：前端认证 (Day 4)

| # | 任务 | 文件 |
|---|------|------|
| 4.1 | 完善 authStore 类型 | `store/authStore.ts` |
| 4.2 | 创建 useAuth Hook | `hooks/useAuth.ts` |
| 4.3 | 重构 Login 页面 | `pages/Login.tsx` |
| 4.4 | 优化 axios 拦截器 | `api/client.ts` |

### 阶段 5：WebSocket (Day 5)

| # | 任务 | 文件 |
|---|------|------|
| 5.1 | WS Token 鉴权 | `api/routes/ws.py` |
| 5.2 | 前端 WS 集成 auth token | `hooks/useWebSocket.ts` |

---

## 五、验收标准

- [ ] 用户可通过手机号 + 验证码登录
- [ ] 支持 2FA 密码验证
- [ ] 登录后 Token 持久化，刷新页面不丢失
- [ ] 搜索结果显示高亮关键词
- [ ] 搜索支持无限滚动加载
- [ ] WebSocket 实时推送同步进度
- [ ] 未登录用户自动跳转登录页
- [ ] API Key 和 Bearer Token 双通道鉴权正常工作

---

## 六、风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 内存 token 跨进程无法共享 | 限制 `--workers 1`，后续迁移 Redis |
| WS query token 泄露 | 使用 TLS，限制日志记录 |
| Telethon session 竞争 | 登录使用独立客户端实例 |
| API Key 用户被 401 | 双通道鉴权保持兼容 |
