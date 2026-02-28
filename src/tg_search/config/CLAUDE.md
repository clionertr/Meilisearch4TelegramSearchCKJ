[根目录](../../../CLAUDE.md) > [src/tg_search](../../) > **config**

# Config 模块

> 环境变量配置管理与验证模块（静态配置来源）

---

## 模块职责

负责从环境变量加载静态配置项，并提供配置验证功能。确保应用启动前所有必填配置已正确设置。

> 说明：白名单/黑名单在运行时的真源为 `ConfigStore.policy`。`WHITE_LIST`/`BLACK_LIST` 在此模块中仅作为策略服务冷启动默认值。

### 核心功能
- **配置加载**: 从环境变量读取配置
- **类型转换**: 自动将字符串转换为 Python 类型（int、list、dict、bool）
- **配置验证**: 检查必填项是否设置及是否使用示例值
- **默认值管理**: 为可选配置提供合理的默认值

---

## 入口与启动

### 主要文件
- `settings.py`: 配置定义与验证逻辑

### 使用方式
```python
# 导入配置
from tg_search.config.settings import (
    APP_ID,
    APP_HASH,
    TOKEN,
    MEILI_HOST,
    MEILI_PASS,
    WHITE_LIST,
    BLACK_LIST,
    validate_config
)

# 验证配置（可选，main.py 中已自动调用）
validate_config()  # 如果配置无效会抛出 ConfigurationError
```

---

## 对外接口

### 必填配置

| 变量 | 类型 | 说明 |
|------|------|------|
| `APP_ID` | `int` | Telegram API ID |
| `APP_HASH` | `str` | Telegram API Hash |
| `TOKEN` | `str` | Telegram Bot Token |
| `MEILI_HOST` | `str` | MeiliSearch 服务器地址 |
| `MEILI_PASS` | `str` | MeiliSearch 主密钥 |

### 可选配置（Bot 控制）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `WHITE_LIST` | `list[int]` | `[1]` | 策略服务冷启动白名单默认值 |
| `BLACK_LIST` | `list[int]` | `[]` | 策略服务冷启动黑名单默认值 |
| `POLICY_REFRESH_TTL_SEC` | `int` | `10` | Telegram 监听侧策略刷新间隔（秒） |
| `OWNER_IDS` | `list[int]` | `[]` | Bot 管理员 ID |

### 可选配置（登录）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SESSION_STRING` | `str \| None` | `None` | Telethon 会话字符串（为空则使用文件） |

### 可选配置（日志）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `LOGGING_LEVEL` | `int` | `25` | 控制台日志级别（20=INFO, 25=NOTICE, 30=WARNING） |
| `LOGGING2FILE_LEVEL` | `int` | `30` | 文件日志级别 |

### 可选配置（网络）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `IPv6` | `bool` | `False` | 是否使用 IPv6 |
| `PROXY` | `str \| None` | `None` | 代理设置（格式见 Telethon 文档） |

### 可选配置（性能）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `BATCH_MSG_UNM` | `int` | `200` | 批量上传消息数 |
| `NOT_RECORD_MSG` | `bool` | `True` | 是否不记录消息编辑历史 |

### 可选配置（搜索）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `SEARCH_CACHE` | `bool` | `True` | 是否开启搜索缓存 |
| `CACHE_EXPIRE_SECONDS` | `int` | `7200` | 缓存过期时间（秒） |
| `MAX_PAGE` | `int` | `10` | 最大分页数 |
| `RESULTS_PER_PAGE` | `int` | `5` | 每页显示消息数 |

### 可选配置（其他）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `TIME_ZONE` | `str` | `"Asia/Shanghai"` | 时区（用于消息时间显示） |
| `CONFIG_DB_PATH` | `str` | `"session/config_store.sqlite3"` | 运行时配置与会话状态 SQLite 路径 |
| `TELEGRAM_REACTIONS` | `dict[str, float]` | 预定义 | 表情反应情感分数权重 |
| `INDEX_CONFIG` | `dict` | 预定义 | MeiliSearch 索引配置 |

---

## 关键依赖与配置

### 外部依赖
- `ast`: 用于安全解析列表/字典字符串
- `os`: 读取环境变量

### 内部依赖
- 无（作为最底层模块，不依赖其他内部模块）

### 配置验证逻辑

```python
# 示例值列表（用于检测配置错误）
_EXAMPLE_VALUES = {
    "APP_ID": ["23010002", ""],
    "APP_HASH": ["d1f1d1f1d1f1d1f1d1f1d1f1d1f1d1f1", ""],
    "BOT_TOKEN": ["123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", ""],
    "MEILI_HOST": ["https://username-spacename.hf.space", ""],
    "MEILI_MASTER_KEY": ["eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", ""],
}

def validate_config() -> None:
    """验证所有必填配置项"""
    errors = []
    for var_name, example_vals in _EXAMPLE_VALUES.items():
        value = os.getenv(var_name)
        if value is None:
            errors.append(f"  - {var_name}: 未设置")
        elif value in example_vals:
            errors.append(f"  - {var_name}: 使用了示例值")

    if errors:
        raise ConfigurationError(
            "配置验证失败，以下必填项存在问题:\n" + "\n".join(errors)
        )
```

### 跳过验证

```python
# 在测试或特殊场景下跳过验证
os.environ["SKIP_CONFIG_VALIDATION"] = "true"
```

---

## 数据模型

### ConfigurationError 异常

```python
class ConfigurationError(Exception):
    """配置错误异常"""
    pass

# 使用示例
try:
    validate_config()
except ConfigurationError as e:
    logger.error(f"配置错误: {e}")
```

### TELEGRAM_REACTIONS 权重配置

```python
TELEGRAM_REACTIONS = {
    # 正面情感
    "👍": 1.0,   # 基准正面
    "❤️": 1.5,   # 强烈喜爱
    "🔥": 1.4,   # 热门/精彩
    "🎉": 1.3,   # 庆祝
    "🤩": 1.4,   # 非常喜欢
    "👏": 1.2,   # 赞赏

    # 中性/思考
    "🤔": 0.0,   # 思考
    "🤯": 0.0,   # 震惊

    # 负面情感
    "👎": -1.0,  # 基准负面
    "😱": -0.5,  # 惊恐
    "😢": -0.8,  # 悲伤
    "🤬": -1.2,  # 愤怒
    "💩": -1.5,  # 强烈否定
}
```

### INDEX_CONFIG MeiliSearch 索引配置

```python
INDEX_CONFIG = {
    "displayedAttributes": ["*"],
    "searchableAttributes": ["text", "id"],
    "filterableAttributes": ["chat.type", "date", "from_user", "reactions_scores"],
    "sortableAttributes": ["date", "id"],
    "rankingRules": [
        "words",
        "typo",
        "proximity",
        "attribute",
        "sort",
        "exactness",
        "date:desc",
        "reactions_scores:desc",
    ],
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
    },
    "pagination": {"maxTotalHits": 500},
}
```

---

## 测试与质量

### 测试文件
- `tests/test_configparser.py`: 配置解析测试
- `tests/test_utils.py`: 包含 ConfigurationError 测试

### 测试覆盖
- [x] 配置验证功能
- [x] ConfigurationError 异常
- [x] SKIP_CONFIG_VALIDATION 环境变量

### 质量工具
- Ruff: 代码格式化与检查
- mypy: 类型检查

---

## 常见问题 (FAQ)

### Q1: 如何设置环境变量？

**A:** 创建 `.env` 文件（项目根目录）：
```bash
APP_ID=12345678
APP_HASH=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
MEILI_HOST=http://localhost:7700
MEILI_MASTER_KEY=your_master_key_here
```

或直接在 shell 中导出：
```bash
export APP_ID=12345678
export APP_HASH=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### Q2: WHITE_LIST 和 BLACK_LIST 如何使用？

**A:**
- `WHITE_LIST`/`BLACK_LIST` 仅用于**首次启动或空 policy 文档**时的默认值注入
- 注入后运行时配置统一从 `ConfigStore.policy` 读取
- `BLACK_LIST` 优先级高于白名单：即使在白名单中，黑名单 ID 也会被拒绝

示例：
```bash
# 只同步这两个频道
export WHITE_LIST="[-1001234567890, -1009876543210]"

# 排除某些群组
export BLACK_LIST="[-1001111111111]"
```

### Q3: 如何获取 Telegram API ID 和 Hash？

**A:** 访问 https://my.telegram.org/apps 登录后创建应用。

### Q4: 如何调整日志级别？

**A:**
```bash
# 显示所有 INFO 及以上级别日志
export LOGGING_LEVEL=20

# 只显示 WARNING 及以上级别日志
export LOGGING_LEVEL=30

# 自定义级别：NOTICE（介于 INFO 和 WARNING 之间）
export LOGGING_LEVEL=25  # 默认值
```

### Q5: 配置验证失败怎么办？

**A:** 检查错误提示中列出的配置项：
1. 确保所有必填项都已设置
2. 不要使用示例值（文档中的占位符）
3. 检查拼写和格式

跳过验证（仅用于测试）：
```bash
export SKIP_CONFIG_VALIDATION=true
```

---

## 相关文件清单

```
src/tg_search/config/
├── __init__.py          # 模块初始化（空文件）
├── settings.py          # 配置定义（178 行）
└── CLAUDE.md            # 本文档
```

---

## 变更记录 (Changelog)

### 2026-02-28
- ConfigStore 底层从 MeiliSearch 迁移到 SQLite（`CONFIG_DB_PATH`）
- 拆分持久化模型：`system_config`（全局配置） + `dialog_state`（会话状态 + latest_msg_id）
- 新增 legacy 自动迁移：SQLite 空库时自动导入 Meili `system_config` + `sync_offsets`
- 新增粒度化接口：`upsert_dialog_states`、`delete_dialog_state`、`get/set_latest_msg_id`

### 2026-02-05
- 创建模块文档
- 记录所有配置项及其默认值
- 添加配置验证逻辑说明

### 2026-02-24
- 新增 Config Store 模块（P0 功能）：运行时持久化配置基座
- 更新文件清单与使用示例

---

## Config Store（P0 运行时配置）

> 源文件：[config_store.py](file://./config_store.py) | 规格：[SPEC-P0-config-store.md](../../docs/specs/SPEC-P0-config-store.md)

### 概述

`ConfigStore` 将运行时配置持久化到 SQLite（默认 `session/config_store.sqlite3`），
保留 `GlobalConfig` 读取契约，同时将高频会话状态拆分到行级表中，避免整文档覆盖写入。

### 数据模型

```
SQLite Tables
├── system_meta(id=1, version, updated_at)
├── system_config(key, value_json)
│   ├── storage
│   ├── ai
│   ├── policy
│   └── sync_available_cache_ttl_sec
└── dialog_state(dialog_id PK, sync_state, latest_msg_id, date_from, last_synced_at, updated_at)
```

### 使用示例

```python
from tg_search.config.config_store import ConfigStore
from tg_search.core.meilisearch import MeiliSearchClient

# 初始化（会自动创建 SQLite 表；空库时自动尝试从 Meili 迁移旧数据）
meili = MeiliSearchClient(host, master_key, auto_create_index=False)
store = ConfigStore(meili)

# 读取配置（10s 内命中缓存，cache_hit=true 日志可观测）
cfg = store.load_config()
print(cfg.ai.model)           # "gpt-4o-mini"

# 强制刷新（跳过缓存，直接读 SQLite）
cfg = store.load_config(refresh=True)

# 更新单个 section（只改 ai，不影响 sync/storage）
store.update_section("ai", {
    "model": "gpt-4o",
    "api_key": "sk-xxx",
})

# 全量 patch（可跨多个 section）
store.save_config({
    "storage": {"auto_clean_enabled": True, "media_retention_days": 14},
    "ai":      {"model": "gpt-4o"},
})

# 乐观锁写（expected_version 不匹配时抛出 ValueError）
try:
    store.save_config({"storage": {"auto_clean_enabled": True}}, expected_version=3)
except ValueError as e:
    print(f"并发冲突: {e}")

# 粒度化更新会话状态（不覆盖整份 sync.dialogs）
store.upsert_dialog_states(
    {
        -1001234567890: {
            "sync_state": "active",
            "date_from": None,
            "last_synced_at": None,
            "updated_at": "2026-02-28T12:00:00+00:00",
        }
    }
)

# 增量断点写入（高频，不递增 GlobalConfig.version）
store.set_latest_msg_id(-1001234567890, 123456)
```

### 监控日志格式

| 事件 | 级别 | 日志示例 |
|---|---|---|
| 缓存命中 | INFO | `[ConfigStore] load_config: cache_hit=true version=5` |
| 缓存未命中（正常） | INFO | `[ConfigStore] load_config: 12.3ms cache_hit=false version=5` |
| 读取慢（>100ms） | WARNING | `[ConfigStore] load_config slow: 143.2ms (threshold=100ms) cache_hit=false version=5` |
| 写入正常 | INFO | `[ConfigStore] save_config: 8.4ms version=6 changed_sections=['ai']` |
| 慢写告警 | WARNING | `[ConfigStore] save_config slow: 181.0ms (threshold=120ms) version=6 changed_sections=['sync']` |
| 会话粒度更新 | INFO | `[ConfigStore] upsert_dialog_states count=3 version=8 duration_ms=5.7` |
| legacy 迁移 | INFO | `[ConfigStore] migrated legacy config from Meili index=system_config dialogs=12 offsets=10` |

### 测试

```bash
# 单元测试（不依赖 Meili 配置存储）
pytest tests/unit/test_configparser.py tests/unit/test_config_policy_service.py -v

# E2E 集成测试（搜索相关仍需 MeiliSearch）
RUN_INTEGRATION_TESTS=true pytest tests/integration/test_config_store_e2e.py -v -s

# 通过集成运行器执行（覆盖整个 tests/integration/ 目录）
RUN_INTEGRATION_TESTS=true uv run tests/integration/run.py
```

---

## 相关文件清单

```
src/tg_search/config/
├── __init__.py          # 导出 ConfigStore, GlobalConfig 等
├── settings.py          # 环境变量配置（178 行）
├── config_store.py      # P0 运行时持久化配置（~290 行）
└── CLAUDE.md            # 本文档
```

---
