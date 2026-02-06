# Phase 4 P0: WebUI 开发实施计划

> 生成时间: 2026-02-06
> 认证方案: Bearer Token (不透明随机字符串)
> SESSION_ID: Codex=019c30ac-d6f3-7f52-832b-0ad183776d9d, Gemini=ff189436-f490-44d6-a6bd-6baf510103ea

---

## 一、任务概览

| 任务 | 后端 | 前端 | 优先级 |
|------|------|------|--------|
| Telegram 登录认证 | Auth API (4个端点) | 多步验证 UI | P0 |
| Search 页面功能化 | 透传 `_formatted` 高亮 | API 接入 + 分页 | P0 |
| WebSocket 状态推送 | Token 鉴权 | Hook 封装 + UI | P0 |

---

## 二、后端实施计划

### 2.1 文件结构规划

**新增文件：**
- `src/tg_search/api/routes/auth.py` - Auth API 端点
- `src/tg_search/api/auth_store.py` - Token/Session 内存存储

**修改文件：**
- `src/tg_search/api/models.py` - 新增 Auth 请求/响应模型
- `src/tg_search/api/deps.py` - 新增 Bearer Token 验证依赖
- `src/tg_search/api/state.py` - AppState 添加 auth_store
- `src/tg_search/api/routes/__init__.py` - 注册 auth 路由
- `src/tg_search/api/routes/ws.py` - 添加 Token 鉴权
- `src/tg_search/api/routes/search.py` - 透传 `_formatted` 字段

### 2.2 Auth API 设计

#### POST `/api/v1/auth/send-code`

**请求：**
```json
{
  "phone_number": "+8613800138000",
  "force_sms": false
}
```

**响应：**
```json
{
  "auth_session_id": "abc123...",
  "expires_in": 300,
  "phone_number_masked": "+86***8000"
}
```

**错误码：**
- `INVALID_PHONE_NUMBER` (400)
- `FLOOD_WAIT` (429) - 包含 wait_seconds
- `SEND_CODE_FAILED` (503)

#### POST `/api/v1/auth/signin`

**请求：**
```json
{
  "auth_session_id": "abc123...",
  "phone_number": "+8613800138000",
  "code": "12345",
  "password": null
}
```

**响应（成功）：**
```json
{
  "token": "tg_xxxxxxxxxxxx",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": 123456789,
    "username": "user",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**错误码：**
- `AUTH_SESSION_NOT_FOUND` (400)
- `CODE_INVALID` (401)
- `CODE_EXPIRED` (401)
- `PASSWORD_REQUIRED` (403) - 需要 2FA
- `PASSWORD_INVALID` (401)

#### GET `/api/v1/auth/me`

**Header:** `Authorization: Bearer <token>`

**响应：**
```json
{
  "user": { "id": 123, "username": "..." },
  "token_expires_at": "2026-02-07T10:00:00Z"
}
```

#### POST `/api/v1/auth/logout`

**Header:** `Authorization: Bearer <token>`

**响应：** `{ "revoked": true }`

### 2.3 Token 存储设计

```python
# auth_store.py
class AuthStore:
    auth_sessions: dict[str, AuthSessionRecord]  # auth_session_id -> record
    tokens: dict[str, TokenRecord]               # token -> record
    lock: asyncio.Lock

@dataclass
class AuthSessionRecord:
    phone_number: str
    phone_code_hash: str
    telethon_client: TelegramClient
    expires_at: datetime

@dataclass
class TokenRecord:
    user_info: dict
    telegram_session: str  # StringSession
    expires_at: datetime
    created_at: datetime
```

**过期策略：**
- auth_session TTL: 5 分钟
- token TTL: 24 小时 (可配置)
- 清理: 惰性删除 + 后台定时任务

### 2.4 WebSocket 鉴权

```python
# ws.py
@router.websocket("/status")
async def websocket_status(websocket: WebSocket):
    # 从 query 获取 token
    token = websocket.query_params.get("token")
    if not token or not auth_store.validate_token(token):
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await manager.connect(websocket)
    # ... 原有逻辑
```

### 2.5 Search 高亮透传

```python
# search.py - 修改 _parse_message
def _parse_message(hit: dict) -> MessageModel:
    # ... 现有逻辑
    return MessageModel(
        # ... 现有字段
        formatted_text=hit.get("_formatted", {}).get("text"),  # 新增
    )
```

---

## 三、前端实施计划

### 3.1 文件结构规划

```
webui-example/
├── src/
│   ├── api/                    # [新增] API 层
│   │   ├── client.ts           # axios 配置
│   │   ├── auth.ts             # 认证接口
│   │   └── search.ts           # 搜索接口
│   ├── store/                  # [新增] Zustand
│   │   ├── authStore.ts        # 认证状态
│   │   └── statusStore.ts      # WS 进度状态
│   ├── hooks/                  # [新增] Hooks
│   │   ├── useWebSocket.ts     # WS 封装
│   │   └── useDebounce.ts      # 搜索防抖
│   ├── components/             # [新增] 组件
│   │   ├── common/
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── Highlight.tsx
│   │   └── search/
│   │       └── SearchResultCard.tsx
│   ├── utils/
│   │   └── sanitize.ts         # DOMPurify
│   └── pages/                  # [修改]
│       ├── Login.tsx           # 多步验证
│       └── Search.tsx          # API 接入
```

### 3.2 组件层次设计

**Login 页面：**
```
LoginContainer
├── StepPhone        # 步骤1: 输入手机号
├── StepCode         # 步骤2: 输入验证码
└── StepPassword     # 步骤3: 2FA 密码 (可选)
```

**Search 页面：**
```
Search
├── SearchHeader     # 搜索框 + 防抖
├── SearchFilters    # 过滤器
└── ResultsList      # 无限滚动
    └── SearchResultCard  # 单条结果
```

### 3.3 状态管理 (Zustand)

```typescript
// store/authStore.ts
interface AuthState {
  token: string | null;
  user: User | null;
  isLoggedIn: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

// store/statusStore.ts
interface StatusState {
  tasks: Record<number, ProgressEvent>;
  overallStatus: 'idle' | 'syncing' | 'error';
  updateTask: (event: ProgressEvent) => void;
}
```

### 3.4 API 层 (TanStack Query)

```typescript
// api/search.ts
export const useSearchMessages = (params: SearchParams) => {
  return useInfiniteQuery({
    queryKey: ['search', params],
    queryFn: ({ pageParam = 0 }) =>
      api.get('/search', { params: { ...params, offset: pageParam } }),
    getNextPageParam: (lastPage) =>
      lastPage.offset + lastPage.limit < lastPage.total_hits
        ? lastPage.offset + lastPage.limit
        : undefined,
  });
};

// api/auth.ts
export const useSendCode = () => useMutation({
  mutationFn: (phone: string) => api.post('/auth/send-code', { phone_number: phone })
});

export const useSignIn = () => useMutation({
  mutationFn: (data: SignInRequest) => api.post('/auth/signin', data)
});
```

### 3.5 依赖安装

```bash
cd webui-example
npm install zustand @tanstack/react-query axios react-use-websocket dompurify
npm install -D @types/dompurify
```

---

## 四、实施步骤 (按优先级)

### 第一阶段：基础设施 (Day 1)

| # | 任务 | 涉及文件 | 负责 |
|---|------|----------|------|
| 1.1 | 创建 auth_store.py | `src/tg_search/api/auth_store.py` | 后端 |
| 1.2 | 添加 Auth Pydantic 模型 | `src/tg_search/api/models.py` | 后端 |
| 1.3 | AppState 集成 auth_store | `src/tg_search/api/state.py` | 后端 |
| 1.4 | 安装前端依赖 | `webui-example/package.json` | 前端 |
| 1.5 | 配置 axios 拦截器 | `webui-example/src/api/client.ts` | 前端 |
| 1.6 | 创建 authStore | `webui-example/src/store/authStore.ts` | 前端 |

### 第二阶段：认证流程 (Day 2)

| # | 任务 | 涉及文件 | 负责 |
|---|------|----------|------|
| 2.1 | 实现 /auth/send-code | `src/tg_search/api/routes/auth.py` | 后端 |
| 2.2 | 实现 /auth/signin | `src/tg_search/api/routes/auth.py` | 后端 |
| 2.3 | 实现 /auth/me, /auth/logout | `src/tg_search/api/routes/auth.py` | 后端 |
| 2.4 | Bearer Token 依赖 | `src/tg_search/api/deps.py` | 后端 |
| 2.5 | 注册 auth 路由 | `src/tg_search/api/routes/__init__.py` | 后端 |
| 2.6 | Login 多步验证 UI | `webui-example/src/pages/Login.tsx` | 前端 |
| 2.7 | ProtectedRoute 组件 | `webui-example/src/components/common/` | 前端 |

### 第三阶段：搜索功能 (Day 3)

| # | 任务 | 涉及文件 | 负责 |
|---|------|----------|------|
| 3.1 | 透传 _formatted 字段 | `src/tg_search/api/routes/search.py` | 后端 |
| 3.2 | 更新 MessageModel | `src/tg_search/api/models.py` | 后端 |
| 3.3 | useSearchMessages Hook | `webui-example/src/api/search.ts` | 前端 |
| 3.4 | Search 页面 API 接入 | `webui-example/src/pages/Search.tsx` | 前端 |
| 3.5 | Highlight 安全渲染组件 | `webui-example/src/components/common/` | 前端 |
| 3.6 | 无限滚动实现 | `webui-example/src/pages/Search.tsx` | 前端 |

### 第四阶段：WebSocket (Day 4)

| # | 任务 | 涉及文件 | 负责 |
|---|------|----------|------|
| 4.1 | WS Token 鉴权 | `src/tg_search/api/routes/ws.py` | 后端 |
| 4.2 | useWebSocket Hook | `webui-example/src/hooks/useWebSocket.ts` | 前端 |
| 4.3 | statusStore | `webui-example/src/store/statusStore.ts` | 前端 |
| 4.4 | Dashboard 进度 UI | `webui-example/src/pages/Dashboard.tsx` | 前端 |

---

## 五、验收标准

- [ ] 用户可通过手机号 + 验证码登录
- [ ] 支持 2FA 密码验证
- [ ] 登录后 Token 持久化，刷新页面不丢失
- [ ] 搜索结果显示高亮关键词
- [ ] 搜索支持无限滚动加载
- [ ] WebSocket 实时推送同步进度
- [ ] 未登录用户自动跳转登录页

---

## 六、注意事项

### 安全
- 永不日志记录 phone_code_hash 和 session string
- 高亮 HTML 必须通过 DOMPurify 处理
- Token 使用 secrets.token_urlsafe(32) 生成

### 性能
- 搜索输入使用 300ms 防抖
- 长列表考虑虚拟滚动

### 运维
- 限流 send-code 接口（60秒/手机号）
- 监控 auth 失败次数和活跃 Token 数
