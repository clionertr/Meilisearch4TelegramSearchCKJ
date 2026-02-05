# config 模块

> [根目录](../../../CLAUDE.md) > [src](../CLAUDE.md) > config

---

## 模块职责

集中管理所有环境变量和配置项，提供类型安全的配置访问。

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `env.py` | 环境变量读取与默认值定义 |
| `__init__.py` | 模块初始化 |

---

## 接口说明

### env.py 导出的配置项

#### Telegram API
```python
APP_ID: str          # Telegram API ID
APP_HASH: str        # Telegram API Hash
TOKEN: str           # Bot Token
```

#### MeiliSearch
```python
MEILI_HOST: str      # MeiliSearch 服务地址
MEILI_PASS: str      # Master Key
INDEX_CONFIG: dict   # 索引配置 (searchableAttributes, rankingRules 等)
```

#### 访问控制
```python
WHITE_LIST: List[int]  # 白名单 ID 列表
BLACK_LIST: List[int]  # 黑名单 ID 列表
OWNER_IDS: List[int]   # Bot 管理员 ID
```

规则:

1. 黑名单优先级更高：在黑名单内的 ID 永远拒绝
2. 白名单非空时，仅允许白名单内的 ID
3. 白名单为空时，允许所有不在黑名单内的 ID

#### 性能配置
```python
BATCH_MSG_UNM: int           # 批量上传数量 (默认 200)
SEARCH_CACHE: bool           # 启用搜索缓存
CACHE_EXPIRE_SECONDS: int    # 缓存过期时间
MAX_PAGE: int                # 最大分页数
RESULTS_PER_PAGE: int        # 每页结果数
```

#### 其他
```python
SESSION_STRING: Optional[str]  # Telethon 会话字符串
LOGGING_LEVEL: int             # 日志级别
TIME_ZONE: str                 # 时区
TELEGRAM_REACTIONS: dict       # 表情情感分数映射
```

---

## 使用示例

```python
from Meilisearch4TelegramSearchCKJ.src.config.env import (
    MEILI_HOST, MEILI_PASS, WHITE_LIST
)
```

---

## 注意事项

1. 敏感信息通过环境变量注入，不要硬编码
2. 列表类型配置使用 `ast.literal_eval` 解析
3. `INDEX_CONFIG` 定义了 MeiliSearch 索引的完整配置
