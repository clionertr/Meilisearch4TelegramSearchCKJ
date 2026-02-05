[根目录](../../../CLAUDE.md) > [src/tg_search](../../) > **core**

# Core 模块

> 核心业务逻辑模块，包含 Bot 处理器、Telegram 客户端和 MeiliSearch 客户端

---

## 模块职责

实现应用的三大核心组件：
1. **BotHandler**: Telegram Bot 交互处理（搜索界面）
2. **TelegramUserBot**: Telegram 用户客户端（消息下载与监听）
3. **MeiliSearchClient**: MeiliSearch 搜索引擎客户端（索引管理）

### 核心功能
- **消息下载**: 批量下载历史消息并索引到 MeiliSearch
- **实时监听**: 监听新消息和编辑消息事件
- **搜索交互**: 通过 Bot 提供用户友好的搜索界面
- **异常处理**: 细化的异常分类与重试机制
- **内存监控**: 追踪内存使用情况

---

## 入口与启动

### 主要文件

| 文件 | 职责 | 行数 |
|------|------|------|
| `bot.py` | Bot 事件处理器 | 337 行 |
| `telegram.py` | Telegram 用户客户端 | 474 行 |
| `meilisearch.py` | MeiliSearch 客户端 | 313 行 |
| `logger.py` | 日志配置 | 44 行 |

### 启动流程

```python
# main.py 启动流程
async def main():
    # 1. 创建 MeiliSearch 客户端
    meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)

    # 2. 创建 Telegram 用户客户端
    user_bot_client = TelegramUserBot(meili)
    await user_bot_client.start()

    # 3. 下载并监听消息
    await download_and_listen(user_bot_client, meili)

# __main__.py 入口
def main():
    bot_handler = BotHandler(run)
    asyncio.run(bot_handler.run())
```

---

## 对外接口

### BotHandler 类

#### Bot 命令

| 命令 | 说明 | 权限 |
|------|------|------|
| `/start` | 显示帮助信息 | 公开 |
| `/help` | 显示帮助信息 | 公开 |
| `/start_client` | 启动消息监听与下载 | 管理员 |
| `/stop_client` | 停止消息监听与下载 | 管理员 |
| `/search <query>` | 关键词搜索 | 管理员 |
| `/set_white_list2meili <list>` | 设置白名单到 MeiliSearch | 管理员 |
| `/set_black_list2meili <list>` | 设置黑名单到 MeiliSearch | 管理员 |
| `/cc` | 清除搜索缓存 | 管理员 |
| `/ping` | 检查服务状态 | 管理员 |
| `/about` | 项目信息 | 公开 |

#### 核心方法

```python
class BotHandler:
    def __init__(self, main: Callable):
        """初始化 Bot 处理器"""

    async def initialize(self):
        """初始化 Bot 客户端，注册事件处理器"""

    async def run(self):
        """运行 Bot（阻塞）"""

    async def search_handler(self, event, query: str):
        """搜索处理逻辑"""

    async def send_results_page(self, event, hits, page_number, query):
        """发送搜索结果分页"""

    async def callback_query_handler(self, event):
        """处理分页按钮点击"""
```

### TelegramUserBot 类

#### 核心方法

```python
class TelegramUserBot:
    def __init__(self, meili_client: MeiliSearchClient):
        """初始化 Telegram 客户端"""

    async def start(self):
        """启动客户端并注册事件处理器"""

    async def download_history(
        self,
        peer,
        limit: int | None = None,
        batch_size: int = 200,
        offset_id: int = 0,
        latest_msg_config: dict | None = None,
        meili: MeiliSearchClient | None = None,
        dialog_id: int | None = None
    ):
        """下载历史消息"""

    async def cleanup(self):
        """清理资源（断开连接、垃圾回收）"""

    @staticmethod
    def get_memory_usage() -> tuple[int, int]:
        """获取当前和峰值内存使用（bytes）"""
```

#### 消息序列化函数

```python
async def serialize_message(message: Message, not_edited: bool = True) -> dict | None:
    """
    序列化 Telegram 消息为字典

    Args:
        message: Telethon Message 对象
        not_edited: 是否为原始消息（False 时 ID 包含 edit_ts）

    Returns:
        序列化后的消息字典，失败返回 None
    """

async def serialize_chat(chat) -> dict | None:
    """序列化聊天对象"""

async def serialize_sender(sender) -> dict | None:
    """序列化发送者对象"""

async def serialize_reactions(message: Message) -> dict | None:
    """序列化消息反应（表情）"""

async def calculate_reaction_score(reactions: dict | None) -> float | None:
    """计算反应情感分数"""
```

### MeiliSearchClient 类

#### 核心方法

```python
class MeiliSearchClient:
    def __init__(self, host: str, api_key: str, auto_create_index: bool = True):
        """初始化 MeiliSearch 客户端"""

    def create_index(self, index_name: str = "telegram", primary_key: str | None = "id") -> TaskInfo:
        """创建索引（幂等操作）"""

    @retry(...)  # tenacity 重试装饰器
    def add_documents(self, documents: list[dict], index_name: str = "telegram") -> TaskInfo:
        """添加文档（带自动重试）"""

    def search(self, query: str | None, index_name: str = "telegram", **kwargs) -> dict:
        """搜索文档"""

    def delete_documents(self, document_ids: list[str], index_name: str = "telegram") -> TaskInfo:
        """删除文档"""

    def get_index_stats(self, index_name: str) -> IndexStats:
        """获取索引统计信息"""

    def delete_index(self, index_name: str) -> TaskInfo:
        """删除索引"""
```

### Logger 函数

```python
def setup_logger() -> logging.Logger:
    """
    配置并返回全局 logger

    Features:
    - coloredlogs 控制台输出（带颜色）
    - 文件输出到 log_file.log
    - 自定义 NOTICE 级别（25）
    """
```

---

## 关键依赖与配置

### 外部依赖

| 包 | 用途 |
|-----|------|
| `telethon` | Telegram 客户端库 |
| `meilisearch` | MeiliSearch Python SDK |
| `coloredlogs` | 彩色日志输出 |
| `tenacity` | 重试机制 |
| `pytz` | 时区处理 |

### 内部依赖

```python
# bot.py 依赖
from tg_search.config.settings import APP_ID, APP_HASH, TOKEN, ...
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.utils.formatters import sizeof_fmt
from tg_search.utils.message_tracker import read_config_from_meili

# telegram.py 依赖
from tg_search.config.settings import APP_ID, APP_HASH, BATCH_MSG_UNM, ...
from tg_search.core.logger import setup_logger
from tg_search.utils.message_tracker import update_latest_msg_config4_meili
from tg_search.utils.permissions import is_allowed

# meilisearch.py 依赖
from tg_search.config.settings import INDEX_CONFIG
from tg_search.core.logger import setup_logger
```

---

## 数据模型

### 消息序列化格式

```python
{
    'id': 'chat_id-msg_id' | 'chat_id-msg_id-edit_ts',
    'chat': {
        'id': int,
        'type': 'private' | 'group' | 'channel',
        'title': str | None,
        'username': str | None
    },
    'date': 'ISO-8601 timestamp (Asia/Shanghai)',
    'text': str | None,  # 消息内容或 caption
    'from_user': {
        'id': int,
        'username': str | None
    } | None,
    'reactions': {
        'emoji_or_document_id': int  # count
    } | None,
    'reactions_scores': float | None,
    'text_len': int
}
```

### 自定义异常

#### Telegram 异常

```python
class TelegramNetworkError(Exception):
    """Telegram 网络错误（可重试）"""

class TelegramPermissionError(Exception):
    """Telegram 权限错误（不可重试，需跳过）"""

class TelegramRateLimitError(Exception):
    """Telegram 限流错误（需等待后重试）"""
    def __init__(self, message: str, wait_seconds: int = 0):
        self.wait_seconds = wait_seconds
```

#### MeiliSearch 异常

```python
class MeiliSearchConnectionError(Exception):
    """MeiliSearch 连接错误"""

class MeiliSearchTimeoutError(Exception):
    """MeiliSearch 超时错误"""

class MeiliSearchAPIError(Exception):
    """MeiliSearch API 错误"""
    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        self.status_code = status_code
        self.error_code = error_code
```

---

## 测试与质量

### 测试文件
- `tests/test_meilisearch_handler.py`: MeiliSearch 客户端测试
- `tests/test_tg_client.py`: Telegram 客户端测试
- `tests/test_logger.py`: 日志配置测试

### 测试覆盖
- [x] MeiliSearch CRUD 操作
- [x] 异常处理（连接错误、超时、API 错误）
- [x] 重试机制（tenacity）
- [x] Mock Telegram 客户端

### 质量工具
- pytest + pytest-asyncio: 异步测试
- pytest-cov: 覆盖率报告
- ruff: 代码检查
- mypy: 类型检查

---

## 常见问题 (FAQ)

### Q1: Bot 权限检查如何工作？

**A:** 使用 `@set_permission` 装饰器：
```python
@set_permission
async def search_command_handler(self, event):
    # 只有 OWNER_IDS 中的用户可以执行
    ...

# OWNER_IDS 为空时，所有人都可以使用
```

### Q2: 如何处理 Telegram 限流？

**A:** `TelegramUserBot` 会自动处理：
```python
except FloodWaitError as e:
    logger.warning(f"Rate limited, waiting {e.seconds}s")
    await asyncio.sleep(e.seconds)
```

手动调整批量大小：
```bash
export BATCH_MSG_UNM=100  # 减小批量大小
```

### Q3: MeiliSearch 重试机制如何配置？

**A:** 使用 tenacity 装饰器（已内置）：
```python
@retry(
    stop=stop_after_attempt(3),  # 最多重试 3 次
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 指数退避
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),  # 只重试网络/超时错误
    reraise=True
)
def add_documents(self, documents, index_name="telegram"):
    ...
```

### Q4: 如何监控内存使用？

**A:**
```python
# 启用内存跟踪（settings.py 默认已启用）
export ENABLE_TRACEMALLOC=true

# 查看日志中的内存信息
# Current memory usage: 123.4MB
# Peak memory usage: 234.5MB
```

### Q5: 搜索结果缓存如何工作？

**A:**
- 默认开启（`SEARCH_CACHE=True`）
- 缓存 2 小时（`CACHE_EXPIRE_SECONDS=7200`）
- 使用 `/cc` 命令手动清除缓存
- 缓存存储在 `BotHandler.search_results_cache` 字典中

### Q6: 如何添加新的 Bot 命令？

**A:**
```python
# 在 BotHandler.initialize() 中注册事件
self.bot_client.on(events.NewMessage(pattern=r"^/mycommand (.+)"))(self.my_handler)

# 定义处理函数
@set_permission  # 如果需要权限控制
async def my_handler(self, event):
    arg = event.pattern_match.group(1)
    await event.reply(f"Received: {arg}")

# 在 set_commands_list() 中添加命令描述
commands = [
    BotCommand(command="mycommand", description="我的自定义命令"),
    ...
]
```

---

## 相关文件清单

```
src/tg_search/core/
├── __init__.py          # 模块初始化
├── bot.py               # Bot 处理器 (337 行)
├── telegram.py          # Telegram 客户端 (474 行)
├── meilisearch.py       # MeiliSearch 客户端 (313 行)
├── logger.py            # 日志配置 (44 行)
└── CLAUDE.md            # 本文档
```

---

## 变更记录 (Changelog)

### 2026-02-05
- 创建模块文档
- 记录三大核心类的接口与使用方法
- 添加异常处理规范
- 补充常见问题解答
