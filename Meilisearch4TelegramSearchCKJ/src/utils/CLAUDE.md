# utils 模块

> [根目录](../../../CLAUDE.md) > [src](../CLAUDE.md) > utils

---

## 模块职责

通用工具函数集合，包括配置读写、权限检查、格式化等。

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `record_lastest_msg_id.py` | 消息 ID 增量记录 (本地/MeiliSearch) |
| `is_in_white_or_black_list.py` | 黑白名单权限检查 |
| `fmt_size.py` | 文件大小格式化 |
| `get_memory_usage.py` | 内存使用监控 |
| `bridge.py` | (空文件，预留) |

---

## 接口说明

### record_lastest_msg_id.py

**本地配置 (config.ini)**:
```python
def read_config(filename="config.ini") -> ConfigParser
def write_config(config, filename="config.ini")
def get_latest_msg_id(config, chat_id) -> int
def update_latest_msg_config(peer_id, message, config)
```

**MeiliSearch 配置**:
```python
def read_config_from_meili(meili: MeiliSearchClient) -> dict
def write_config2_meili(meili: MeiliSearchClient, config)
def get_latest_msg_id4_meili(config: dict, chat_id: int) -> int
def update_latest_msg_config4_meili(dialog_id, message, config, meili)
```

配置结构:
```python
{
    'id': 0,                    # 主键
    'WHITE_LIST': [...],        # 白名单
    'BLACK_LIST': [...],        # 黑名单
    '{chat_id}': msg_id,        # 各频道最新消息 ID
}
```

---

### is_in_white_or_black_list.py

```python
def is_allowed(chat_id: int, white_list=None, black_list=None) -> bool
```

逻辑:
1. 黑名单优先级更高：在黑名单内的 ID 永远拒绝
2. 白名单非空时，仅允许白名单内的 ID
3. 白名单为空时，允许所有不在黑名单内的 ID

**装饰器版本**:
```python
@check_is_allowed()
async def some_handler(chat_id, ...):
    ...
```

---

### fmt_size.py

```python
def sizeof_fmt(num, suffix="B") -> str
# 示例: sizeof_fmt(1536) => "1.5KiB"
```

---

### get_memory_usage.py

```python
def get_memory_usage() -> Tuple[int, int]
# 返回 (current, peak) 内存使用量 (bytes)
```

---

## 使用示例

```python
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import (
    read_config_from_meili, get_latest_msg_id4_meili
)
from Meilisearch4TelegramSearchCKJ.src.utils.is_in_white_or_black_list import is_allowed

# 检查权限
if is_allowed(chat_id, white_list, black_list):
    # 处理消息
    pass

# 获取增量位置
config = read_config_from_meili(meili)
offset_id = get_latest_msg_id4_meili(config, dialog_id)
```
