# Phase 3: API 层实施计划

> 生成时间: 2026-02-05
> 架构方案: 方案A - 单进程单事件循环
> 约束: `uvicorn --workers 1`

---

## 一、目录结构

```
src/tg_search/api/
├── __init__.py
├── app.py          # build_app() + lifespan 管理
├── deps.py         # 依赖注入辅助函数
├── models.py       # Pydantic 请求/响应模型
├── state.py        # ProgressRegistry 进度追踪
└── routes/
    ├── __init__.py
    ├── search.py   # /api/v1/search, /api/v1/search/stats
    ├── status.py   # /api/v1/status, /api/v1/status/dialogs
    ├── config.py   # /api/v1/config, blacklist/whitelist CRUD
    ├── control.py  # /api/v1/client/start|stop
    └── ws.py       # /api/v1/ws/status (WebSocket)
```

---

## 二、核心设计

### 2.1 Lifespan 管理 (app.py)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    app.state.start_time = time.time()
    app.state.meili_client = MeiliSearchClient(...)
    app.state.progress_registry = ProgressRegistry()

    # 可选：启动 Bot 后台任务
    if not app.state.api_only:
        bot_task = asyncio.create_task(run_bot())
        app.state.bot_task = bot_task

    yield

    # 关闭时
    if hasattr(app.state, 'bot_task'):
        app.state.bot_task.cancel()
    await app.state.meili_client.close()
```

### 2.2 MeiliSearch 线程隔离 (deps.py)

```python
import anyio
from functools import partial

async def run_sync_in_thread(func, *args, **kwargs):
    """将同步 MeiliSearch 调用放入线程池执行"""
    return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))

# 使用示例
async def search_messages(query: str, limit: int):
    return await run_sync_in_thread(
        meili_client.index("messages").search,
        query,
        {"limit": limit}
    )
```

### 2.3 进度追踪 (state.py)

```python
from dataclasses import dataclass, field
from typing import Dict, Set
import asyncio

@dataclass
class ProgressRegistry:
    """下载进度追踪，支持 WebSocket 推送"""
    _subscribers: Set[asyncio.Queue] = field(default_factory=set)
    _progress: Dict[str, dict] = field(default_factory=dict)

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    async def publish(self, event: dict):
        for q in self._subscribers:
            await q.put(event)

    def update_progress(self, dialog_id: int, current: int, total: int):
        self._progress[dialog_id] = {"current": current, "total": total}
        asyncio.create_task(self.publish({
            "type": "progress",
            "dialog_id": dialog_id,
            "current": current,
            "total": total
        }))
```

---

## 三、Pydantic 模型 (models.py)

```python
from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

# 通用响应
class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None

# 分页响应
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int

# 消息相关
class UserInfo(BaseModel):
    id: int
    username: Optional[str] = None

class ChatInfo(BaseModel):
    id: int
    type: str  # 'private' | 'group' | 'channel'
    title: Optional[str] = None
    username: Optional[str] = None

class MessageModel(BaseModel):
    id: str
    chat: ChatInfo
    date: datetime
    text: str
    from_user: UserInfo
    reactions: Dict[str, int] = {}
    reactions_scores: float = 0.0
    text_len: int

# 搜索相关
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    chat_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class SearchResult(BaseModel):
    hits: List[MessageModel]
    query: str
    processing_time_ms: int
    total_hits: int

# 状态相关
class SystemStatus(BaseModel):
    uptime_seconds: float
    meili_connected: bool
    bot_connected: bool
    indexed_messages: int
    memory_usage_mb: float

class DialogInfo(BaseModel):
    id: int
    title: str
    type: str
    message_count: int
    last_synced: Optional[datetime] = None

# 配置相关
class ConfigModel(BaseModel):
    white_list: List[int]
    black_list: List[int]
    owner_ids: List[int]
    batch_msg_num: int
    results_per_page: int
    max_page: int
```

---

## 四、API 路由实现顺序

### 4.1 Search API (routes/search.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/search` | POST | 搜索消息 |
| `/api/v1/search/stats` | GET | 搜索统计 |

### 4.2 Status API (routes/status.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/status` | GET | 系统状态 |
| `/api/v1/status/dialogs` | GET | 对话列表 |

### 4.3 Config API (routes/config.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/config` | GET | 获取配置 |
| `/api/v1/config/whitelist` | POST/DELETE | 白名单 CRUD |
| `/api/v1/config/blacklist` | POST/DELETE | 黑名单 CRUD |

### 4.4 Control API (routes/control.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/client/start` | POST | 启动客户端 |
| `/api/v1/client/stop` | POST | 停止客户端 |

### 4.5 WebSocket (routes/ws.py)

| 端点 | 功能 |
|------|------|
| `/api/v1/ws/status` | 实时状态推送 |

---

## 五、__main__.py 修改

```python
# 新增命令行参数
parser.add_argument('--mode', choices=['all', 'api-only', 'bot-only'], default='all')
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=8000)

# 根据模式启动
if args.mode == 'api-only':
    uvicorn.run("tg_search.api.app:app", host=args.host, port=args.port, workers=1)
elif args.mode == 'bot-only':
    asyncio.run(run_bot_only())
else:  # all
    # FastAPI lifespan 中启动 bot
    uvicorn.run("tg_search.api.app:app", host=args.host, port=args.port, workers=1)
```

---

## 六、实施步骤

1. **创建目录结构** - 创建 `src/tg_search/api/` 及子目录
2. **实现 models.py** - Pydantic 模型定义
3. **实现 state.py** - ProgressRegistry
4. **实现 deps.py** - 依赖注入和线程隔离
5. **实现 app.py** - FastAPI 应用和 lifespan
6. **实现 routes/search.py** - 搜索 API
7. **实现 routes/status.py** - 状态 API
8. **实现 routes/config.py** - 配置 API
9. **实现 routes/control.py** - 控制 API
10. **实现 routes/ws.py** - WebSocket
11. **修改 __main__.py** - 集成启动模式
12. **添加测试** - tests/test_api.py
13. **验证运行** - 启动测试

---

## 七、依赖添加

```toml
# pyproject.toml
dependencies = [
    # 现有依赖...
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "anyio>=4.2.0",
]
```

---

## 八、外部模型会话 ID

- **CODEX_SESSION**: 019c2d63-bef1-7eb3-9b6c-26a60a28851c
- **GEMINI_SESSION**: 3f0cab8c-15ee-4f86-ba97-fc08e41e327f
