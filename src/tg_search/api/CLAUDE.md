[根目录](../../../CLAUDE.md) > [src/tg_search](../../) > **api**

# API 模块

> FastAPI REST API 与 WebSocket 模块，提供 Web 管理界面后端

---

## 模块职责

提供完整的 REST API 和 WebSocket 接口，支持 WebUI 管理界面：

### 核心功能
- **Telegram 认证**: 手机号 + 验证码登录流程
- **消息搜索**: RESTful 搜索接口（带高亮）
- **系统状态**: 运行状态、内存、索引统计
- **配置管理**: 白名单/黑名单动态配置
- **客户端控制**: 启动/停止下载任务
- **实时推送**: WebSocket 下载进度推送

---

## 入口与启动

### 主要文件

| 文件 | 职责 | 行数 |
|------|------|------|
| `app.py` | FastAPI 应用构建与生命周期 | 201 行 |
| `models.py` | Pydantic 请求/响应模型 | 271 行 |
| `deps.py` | 依赖注入函数 | ~80 行 |
| `state.py` | 应用状态管理 | ~100 行 |
| `auth_store.py` | 认证会话与 Token 存储 | ~150 行 |
| `routes/__init__.py` | 路由注册 | 58 行 |
| `routes/auth.py` | 认证端点 | 294 行 |
| `routes/search.py` | 搜索端点 | 226 行 |
| `routes/status.py` | 状态端点 | 117 行 |
| `routes/config.py` | 配置端点 | ~80 行 |
| `routes/control.py` | 控制端点 | ~60 行 |
| `routes/ws.py` | WebSocket 端点 | ~80 行 |

### 启动方式

```bash
# 默认模式（API + Bot）
python -m tg_search

# 仅 API 模式
python -m tg_search --mode api-only

# 自定义端口
python -m tg_search --host 0.0.0.0 --port 8080

# 开发模式（热重载）
python -m tg_search --reload
```

### 生命周期管理

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：
    # 1. 初始化 AppState
    # 2. 初始化 AuthStore
    # 3. 初始化 MeiliSearchClient
    # 4. 初始化 ConfigStore + ConfigPolicyService
    # 5. 如果非 API-only 模式，启动 Bot 后台任务

    yield

    # 关闭时：
    # 1. 停止 AuthStore 清理任务
    # 2. 取消 Bot 任务
```

---

## 对外接口

### 认证端点 (`/api/v1/auth`)

#### POST `/send-code` - 发送验证码

```python
# 请求
{
    "phone_number": "+8613800138000",  # 国际格式
    "force_sms": false                  # 是否强制短信
}

# 响应
{
    "success": true,
    "data": {
        "auth_session_id": "uuid-string",
        "expires_in": 600,
        "phone_number_masked": "+86***8000"
    }
}
```

#### POST `/signin` - 验证码登录

```python
# 请求
{
    "auth_session_id": "uuid-string",
    "phone_number": "+8613800138000",
    "code": "12345",
    "password": "可选的2FA密码"
}

# 响应
{
    "success": true,
    "data": {
        "token": "Bearer token",
        "token_type": "Bearer",
        "expires_in": 86400,
        "user": {
            "id": 123456789,
            "username": "user",
            "first_name": "First",
            "last_name": "Last"
        }
    }
}
```

#### GET `/me` - 获取当前用户

```python
# Headers: Authorization: Bearer <token>

# 响应
{
    "success": true,
    "data": {
        "user": { ... },
        "token_expires_at": "2026-02-07T13:48:06Z"
    }
}
```

#### POST `/logout` - 登出

```python
# Headers: Authorization: Bearer <token>

# 响应
{
    "success": true,
    "data": { "revoked": true }
}
```

### 搜索端点 (`/api/v1/search`)

#### GET `/` - 搜索消息

```python
# 查询参数
q: str                    # 搜索关键词（必填）
chat_id: int | None       # 限定聊天 ID
chat_type: str | None     # 聊天类型：private/group/channel
date_from: datetime | None # 开始日期
date_to: datetime | None   # 结束日期
limit: int = 20           # 返回数量 (1-100)
offset: int = 0           # 偏移量

# 响应
{
    "success": true,
    "data": {
        "hits": [
            {
                "id": "123-456",
                "chat": { "id": 123, "type": "group", "title": "..." },
                "date": "2026-01-01T00:00:00+08:00",
                "text": "原始文本",
                "formatted_text": "<mark>高亮</mark>文本",
                ...
            }
        ],
        "query": "搜索词",
        "processing_time_ms": 10,
        "total_hits": 100,
        "limit": 20,
        "offset": 0
    }
}
```

#### GET `/stats` - 搜索统计

```python
# 响应
{
    "success": true,
    "data": {
        "total_documents": 10000,
        "index_size_bytes": 1024000,
        "is_indexing": false
    }
}
```

### 状态端点 (`/api/v1/status`)

#### GET `/` - 系统状态

```python
# 响应
{
    "success": true,
    "data": {
        "uptime_seconds": 3600.5,
        "meili_connected": true,
        "bot_connected": true,
        "telegram_connected": true,
        "indexed_messages": 10000,
        "memory_usage_mb": 256.5,
        "version": "0.2.0"
    }
}
```

#### GET `/dialogs` - 对话列表

```python
# 响应
{
    "success": true,
    "data": {
        "dialogs": [
            {
                "id": 123,
                "title": "群组名称",
                "type": "group",
                "message_count": 1000,
                "last_synced": "2026-02-06T12:00:00Z",
                "is_syncing": false
            }
        ],
        "total": 10
    }
}
```

#### GET `/progress` - 下载进度

```python
# 响应
{
    "success": true,
    "data": {
        "progress": {
            "123": {
                "dialog_id": 123,
                "dialog_title": "群组名称",
                "current": 500,
                "total": 1000,
                "percentage": 50.0,
                "status": "downloading"
            }
        },
        "count": 1
    }
}
```

### 配置端点 (`/api/v1/config`)

> 说明：白名单/黑名单运行时真源为 `ConfigStore.policy`，由 `ConfigPolicyService` 统一读写。

#### GET `/` - 获取配置

```python
# 响应
{
    "success": true,
    "data": {
        "white_list": [123, 456],
        "black_list": [],
        "owner_ids": [789],
        "batch_msg_num": 200,
        "results_per_page": 5,
        "max_page": 10,
        "search_cache": true,
        "cache_expire_seconds": 7200
    }
}
```

#### POST `/whitelist` - 更新白名单

```python
# 请求
{ "ids": [123, 456, 789] }

# 响应
{
    "success": true,
    "data": {
        "updated_list": [123, 456, 789],
        "added": [789],
        "removed": []
    }
}
```

### 控制端点 (`/api/v1/client`)

#### GET `/status` - 客户端状态

```python
# 响应
{
    "success": true,
    "data": { "is_running": true }
}
```

#### POST `/start` - 启动下载

```python
# 响应
{
    "success": true,
    "data": {
        "status": "started",
        "message": "下载任务已启动"
    }
}
```

#### POST `/stop` - 停止下载

```python
# 响应
{
    "success": true,
    "data": {
        "status": "stopped",
        "message": "下载任务已停止"
    }
}
```

### WebSocket (`/api/v1/ws`)

#### `/progress` - 实时进度推送

```python
# 连接: ws://localhost:8000/api/v1/ws/progress?token=<bearer_token>

# 接收消息格式
{
    "type": "progress",
    "data": {
        "dialog_id": 123,
        "dialog_title": "群组名称",
        "current": 500,
        "total": 1000,
        "percentage": 50.0,
        "status": "downloading"
    },
    "timestamp": "2026-02-06T13:48:06Z"
}
```

---

## 关键依赖与配置

### 外部依赖

| 包 | 用途 |
|-----|------|
| `fastapi` | Web 框架 |
| `uvicorn` | ASGI 服务器 |
| `pydantic` | 数据验证 |
| `websockets` | WebSocket 支持 |
| `anyio` | 异步工具 |

### 内部依赖

```python
# app.py 依赖
from tg_search.api.routes import api_router
from tg_search.api.state import AppState
from tg_search.api.auth_store import AuthStore
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.core.bot import BotHandler
from tg_search.main import run

# routes/auth.py 依赖
from tg_search.api.deps import get_auth_store, verify_bearer_token
from tg_search.api.models import SendCodeRequest, SignInRequest, ...
from tg_search.config.settings import APP_ID, APP_HASH
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | `None` | API 密钥（未设置则无需认证） |
| `API_KEY_HEADER` | `X-API-Key` | API 密钥请求头名称 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | 允许的 CORS 源 |
| `API_ONLY` | `false` | 是否为 API-only 模式 |
| `DEBUG` | `false` | 是否启用调试模式 |

---

## 数据模型

### 通用响应模型

```python
class ApiResponse(BaseModel, Generic[T]):
    """通用 API 响应"""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
```

### 消息模型

```python
class MessageModel(BaseModel):
    """消息模型"""
    id: str
    chat: ChatInfo
    date: datetime
    text: str
    from_user: Optional[UserInfo] = None
    reactions: Dict[str, int] = {}
    reactions_scores: float = 0.0
    text_len: int = 0
    formatted: Optional[Dict[str, Any]] = None  # MeiliSearch _formatted
    formatted_text: Optional[str] = None        # 高亮后的文本
```

### 认证模型

```python
class AuthSession:
    """认证会话（内存存储）"""
    auth_session_id: str
    phone_number: str
    phone_code_hash: str
    created_at: datetime
    attempts: int

class AuthToken:
    """认证 Token（内存存储）"""
    token: str
    user_id: int
    phone_number: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: datetime
    expires_at: datetime
```

---

## 测试与质量

### 测试文件
- `tests/test_api.py`: API 端点测试（20+ 测试用例）
- `tests/test_api_integration.py`: API 集成测试

### 测试覆盖
- [x] 健康检查端点
- [x] 搜索端点（带过滤条件）
- [x] 配置端点（白名单/黑名单）
- [x] 状态端点
- [x] 控制端点
- [x] Pydantic 模型验证
- [x] 进度注册表订阅/发布

### 运行测试
```bash
# 运行 API 测试
pytest tests/test_api.py -v

# 运行所有测试
pytest tests/
```

---

## 常见问题 (FAQ)

### Q1: 如何添加新的 API 端点？

**A:**
1. 在 `routes/` 目录下创建新文件或修改现有文件
2. 定义路由和处理函数
3. 在 `routes/__init__.py` 中注册路由
4. 在 `models.py` 中添加请求/响应模型

```python
# routes/my_route.py
from fastapi import APIRouter, Depends
from tg_search.api.models import ApiResponse
from tg_search.api.deps import verify_api_key_or_bearer_token

router = APIRouter()

@router.get("/my-endpoint", response_model=ApiResponse[dict])
async def my_endpoint():
    return ApiResponse(data={"message": "Hello"})

# routes/__init__.py
from tg_search.api.routes import my_route

api_router.include_router(
    my_route.router,
    prefix="/my",
    tags=["My"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)
```

### Q2: 认证机制如何工作？

**A:** 支持两种认证方式：

1. **API Key 认证**（适合服务端调用）
   ```
   Header: X-API-Key: your_api_key
   ```

2. **Bearer Token 认证**（适合 WebUI）
   ```
   Header: Authorization: Bearer <token>
   ```

认证流程：
1. 用户调用 `/auth/send-code` 发送验证码
2. 用户调用 `/auth/signin` 提交验证码，获取 Token
3. 后续请求携带 `Authorization: Bearer <token>` 头

### Q3: 如何防止搜索过滤器注入？

**A:** 使用 `MeiliFilterBuilder` 安全构建器：

```python
class MeiliFilterBuilder:
    """MeiliSearch 过滤器安全构建器"""
    ALLOWED_FIELDS = {"chat.id", "chat.type", "date", "from_user.id"}
    ALLOWED_CHAT_TYPES = {"private", "group", "channel"}

    def add_chat_id(self, chat_id: int):
        # 整数类型已通过 Pydantic 验证
        self._conditions.append(f"chat.id = {chat_id}")

    def add_chat_type(self, chat_type: ChatType):
        # 使用枚举保证值安全
        self._conditions.append(f'chat.type = "{chat_type.value}"')
```

### Q4: WebSocket 如何处理断线重连？

**A:** 客户端应实现重连逻辑：

```javascript
let ws;
let reconnectInterval = 1000;

function connect() {
    ws = new WebSocket(`ws://localhost:8000/api/v1/ws/progress?token=${token}`);

    ws.onopen = () => {
        reconnectInterval = 1000; // 重置重连间隔
    };

    ws.onclose = () => {
        setTimeout(connect, reconnectInterval);
        reconnectInterval = Math.min(reconnectInterval * 2, 30000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // 处理进度更新
    };
}
```

### Q5: 如何获取共享资源（MeiliSearch 客户端）？

**A:** 使用依赖注入：

```python
from tg_search.api.deps import get_meili_async, MeiliSearchAsync

@router.get("/my-endpoint")
async def my_endpoint(
    meili: MeiliSearchAsync = Depends(get_meili_async),
):
    result = await meili.search("query")
    return ApiResponse(data=result)
```

---

## 相关文件清单

```
src/tg_search/api/
├── __init__.py          # 模块初始化
├── app.py               # FastAPI 应用构建 (201 行)
├── models.py            # Pydantic 模型 (271 行)
├── deps.py              # 依赖注入函数
├── state.py             # 应用状态管理
├── auth_store.py        # 认证会话与 Token 存储
├── routes/
│   ├── __init__.py      # 路由注册 (58 行)
│   ├── auth.py          # 认证端点 (294 行)
│   ├── search.py        # 搜索端点 (226 行)
│   ├── status.py        # 状态端点 (117 行)
│   ├── config.py        # 配置端点
│   ├── control.py       # 控制端点
│   └── ws.py            # WebSocket 端点
└── CLAUDE.md            # 本文档
```

---

## 变更记录 (Changelog)

### 2026-02-06
- 创建模块文档
- 记录所有 API 端点接口
- 添加认证机制说明
- 补充 WebSocket 使用方法
