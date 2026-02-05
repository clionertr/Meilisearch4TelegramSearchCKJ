[根目录](../../../CLAUDE.md) > [src/tg_search](../../) > **utils**

# Utils 模块

> 通用工具函数模块，提供格式化、权限检查、消息追踪和内存监控

---

## 模块职责

提供跨模块使用的工具函数，避免代码重复。

### 核心功能
- **formatters**: 数据格式化工具（文件大小）
- **permissions**: 权限检查（白名单/黑名单）
- **message_tracker**: 消息追踪与配置管理（MeiliSearch 存储）
- **memory**: 内存使用监控
- **bridge**: 桥接模块（当前为空）

---

## 入口与启动

### 主要文件

| 文件 | 职责 | 行数 | 导出函数 |
|------|------|------|----------|
| `formatters.py` | 格式化工具 | 7 行 | `sizeof_fmt` |
| `permissions.py` | 权限检查 | 45 行 | `is_allowed`, `check_is_allowed` |
| `message_tracker.py` | 消息追踪 | 69 行 | 6 个函数 |
| `memory.py` | 内存监控 | 10 行 | `get_memory_usage` |
| `bridge.py` | 桥接模块 | 1 行 | 无 |

---

## 对外接口

### formatters.py

#### sizeof_fmt 函数

```python
def sizeof_fmt(num: int, suffix: str = "B") -> str:
    """
    将字节数转换为人类可读格式（KiB、MiB、GiB 等）

    Args:
        num: 字节数
        suffix: 后缀（默认为 "B"）

    Returns:
        格式化后的字符串（如 "1.5MiB"）

    Example:
        >>> sizeof_fmt(1024)
        "1.0KiB"
        >>> sizeof_fmt(1536)
        "1.5KiB"
        >>> sizeof_fmt(1024 * 1024)
        "1.0MiB"
    """
```

### permissions.py

#### is_allowed 函数

```python
def is_allowed(
    chat_id: int,
    sync_white_list: Sequence[int] | None = None,
    sync_black_list: Sequence[int] | None = None,
) -> bool:
    """
    检查聊天 ID 是否允许访问

    逻辑：
    1. 黑名单优先：在黑名单中则拒绝
    2. 白名单非空时，仅允许白名单中的 ID
    3. 白名单为空时，允许所有（除黑名单）

    Args:
        chat_id: Telegram 聊天 ID
        sync_white_list: 白名单（None 视为空列表）
        sync_black_list: 黑名单（None 视为空列表）

    Returns:
        True 允许，False 拒绝

    Example:
        >>> is_allowed(123, [123, 456], [])
        True
        >>> is_allowed(789, [123, 456], [])
        False
        >>> is_allowed(123, [123], [123])
        False  # 黑名单优先
    """
```

#### check_is_allowed 装饰器

```python
def check_is_allowed():
    """
    装饰器：检查函数第一个参数（chat_id）是否允许访问

    Note: 已弃用，建议直接使用 is_allowed 函数

    Example:
        @check_is_allowed()
        async def my_handler(chat_id: int):
            ...
    """
```

### message_tracker.py

#### MeiliSearch 配置管理

```python
def read_config_from_meili(meili: MeiliSearchClient) -> dict:
    """
    从 MeiliSearch 读取配置

    Returns:
        配置字典（包含 WHITE_LIST、BLACK_LIST 和各 chat_id 的最新消息 ID）
        如果不存在则返回 {"id": 0}
    """

def write_config2_meili(meili: MeiliSearchClient, config: dict):
    """写入配置到 MeiliSearch"""

def get_latest_msg_id4_meili(config: dict, chat_id: int) -> int:
    """
    获取指定聊天的最新消息 ID

    Args:
        config: 配置字典（从 read_config_from_meili 获取）
        chat_id: 聊天 ID

    Returns:
        最新消息 ID（不存在则返回 0）
    """

def update_latest_msg_config4_meili(
    dialog_id: int,
    message: dict,
    config: dict,
    meili: MeiliSearchClient
):
    """
    更新配置中的最新消息 ID 并写入 MeiliSearch

    Args:
        dialog_id: 对话 ID
        message: 消息字典（需包含 "id" 字段，格式为 "chat_id-msg_id"）
        config: 配置字典
        meili: MeiliSearch 客户端
    """
```

#### ConfigParser 配置管理（已弃用）

```python
def read_config(filename: str = "config.ini") -> ConfigParser:
    """读取 INI 配置文件（已弃用，使用 MeiliSearch 配置）"""

def write_config(config: ConfigParser, filename: str = "config.ini"):
    """写入 INI 配置文件（已弃用）"""

def get_latest_msg_id(config: ConfigParser, chat_id: str | int) -> int:
    """从 INI 获取最新消息 ID（已弃用）"""

def update_latest_msg_config(peer_id: int, message: dict, config: ConfigParser):
    """更新 INI 配置（已弃用）"""
```

### memory.py

#### get_memory_usage 函数

```python
def get_memory_usage(logger: logging.Logger) -> tuple[int, int]:
    """
    获取当前和峰值内存使用情况

    Args:
        logger: 日志记录器（用于输出内存信息）

    Returns:
        (current, peak) 元组，单位为字节

    Note:
        需要启用 tracemalloc（在 telegram.py 中已自动启用）

    Example:
        >>> current, peak = get_memory_usage(logger)
        # 日志输出: Current memory usage: 123.4MB
        # 日志输出: Peak memory usage: 234.5MB
    """
```

---

## 关键依赖与配置

### 外部依赖

| 包 | 用途 | 使用文件 |
|-----|------|----------|
| `tracemalloc` | 内存跟踪 | `memory.py` |
| `configparser` | INI 配置解析 | `message_tracker.py` (已弃用) |
| `logging` | 日志记录 | `permissions.py`, `memory.py` |

### 内部依赖

```python
# message_tracker.py 依赖
from tg_search.core.meilisearch import MeiliSearchClient

# 其他文件无内部依赖
```

---

## 数据模型

### MeiliSearch 配置格式

```python
{
    "id": 0,  # 固定为 0（单例配置）
    "WHITE_LIST": [1234567890, -1001234567890],  # 白名单
    "BLACK_LIST": [],  # 黑名单
    "1234567890": 123,  # chat_id: latest_msg_id
    "-1001234567890": 456,  # 另一个聊天的最新消息 ID
}
```

### 消息 ID 格式

- **普通消息**: `"chat_id-msg_id"`（如 `"123-456"`）
- **编辑消息**: `"chat_id-msg_id-edit_ts"`（如 `"123-456-1640000000"`）

---

## 测试与质量

### 测试文件
- `tests/test_utils.py`: 工具函数测试

### 测试覆盖
- [x] `sizeof_fmt` 各种单位转换
- [x] `is_allowed` 白名单/黑名单逻辑
- [x] 负数 chat_id 支持（群组 ID）
- [x] 空列表和 None 处理

### 质量工具
- pytest: 单元测试
- ruff: 代码检查

---

## 常见问题 (FAQ)

### Q1: sizeof_fmt 支持哪些单位？

**A:** 按 1024 进制：
- B (Bytes)
- KiB (Kibibytes)
- MiB (Mebibytes)
- GiB (Gibibytes)
- TiB (Tebibytes)
- PiB, EiB, ZiB, YiB

### Q2: 白名单和黑名单的优先级？

**A:** 黑名单优先级最高：
```python
# 即使在白名单中，黑名单 ID 也会被拒绝
is_allowed(123, [123, 456], [123])  # False

# 白名单非空时，不在白名单的 ID 被拒绝
is_allowed(789, [123, 456], [])  # False

# 白名单为空时，允许所有（除黑名单）
is_allowed(789, [], [])  # True
```

### Q3: 如何在 MeiliSearch 中存储配置？

**A:**
```python
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.utils.message_tracker import read_config_from_meili, write_config2_meili

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)

# 读取配置
config = read_config_from_meili(meili)

# 修改配置
config["WHITE_LIST"] = [123, 456]
config["BLACK_LIST"] = []

# 写回 MeiliSearch
write_config2_meili(meili, config)
```

### Q4: 为什么有两套配置管理（INI 和 MeiliSearch）？

**A:**
- **INI 配置**（`read_config`、`write_config`）：早期实现，已弃用
- **MeiliSearch 配置**（`read_config_from_meili`、`write_config2_meili`）：当前使用，支持动态更新（通过 Bot 命令）

### Q5: memory.py 中的 get_memory_usage 如何使用？

**A:**
```python
# 在 telegram.py 中已自动启用 tracemalloc
import tracemalloc
tracemalloc.start()

# 调用函数（通常在批量处理后）
from tg_search.utils.memory import get_memory_usage
current, peak = get_memory_usage(logger)

# 或使用 TelegramUserBot 的静态方法
TelegramUserBot.get_memory_usage()
```

---

## 相关文件清单

```
src/tg_search/utils/
├── __init__.py          # 模块初始化
├── formatters.py        # 格式化工具 (7 行)
├── permissions.py       # 权限检查 (45 行)
├── message_tracker.py   # 消息追踪 (69 行)
├── memory.py            # 内存监控 (10 行)
├── bridge.py            # 桥接模块 (1 行，空)
└── CLAUDE.md            # 本文档
```

---

## 变更记录 (Changelog)

### 2026-02-05
- 创建模块文档
- 记录所有工具函数的接口与用法
- 标注已弃用的 INI 配置管理函数
