# Meilisearch4TelegramSearchCKJ

> 基于 Telethon + MeiliSearch 的 Telegram 中文/日文/韩文 (CJK) 消息搜索解决方案

**生成时间**: 2026-02-05

---

## 项目概述

Telegram 官方搜索对中文支持不佳（不分词），本项目通过 MeiliSearch 全文搜索引擎解决此问题。

### 核心功能
- **消息下载**: 从 Telegram 下载历史消息到 MeiliSearch
- **实时监听**: 监听新消息并自动索引
- **Bot 搜索**: 通过 Telegram Bot 提供搜索界面
- **黑白名单**: 支持配置要同步的频道/群组/用户

---

## 架构总览

```mermaid
graph TB
    subgraph Telegram
        TG_API[Telegram API]
        TG_BOT[Telegram Bot]
    end

    subgraph Application
        UC[TelegramUserBot<br/>消息下载/监听]
        BH[BotHandler<br/>搜索交互]
        MH[MeiliSearchClient<br/>索引操作]
    end

    subgraph Storage
        MS[(MeiliSearch<br/>全文搜索引擎)]
    end

    TG_API --> UC
    UC --> MH
    BH --> MH
    MH --> MS
    TG_BOT <--> BH

    User((用户)) --> TG_BOT
```

### 数据流
1. **下载流程**: Telegram API → TelegramUserBot → serialize → MeiliSearchClient → MeiliSearch
2. **监听流程**: Telegram Events → Handler → MeiliSearch
3. **搜索流程**: User → Bot → MeiliSearch → 格式化结果 → User

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Telegram 库 | Telethon 1.38+ |
| 搜索引擎 | MeiliSearch 0.33+ |
| 日志 | coloredlogs |
| 构建工具 | hatchling (PEP 621) |
| 包管理 | uv |
| 容器化 | Docker / Docker Compose |

---

## 目录结构

```
Meilisearch4TelegramSearchCKJ/
├── CLAUDE.md                    # 本文档
├── pyproject.toml               # 项目配置 (PEP 621)
├── Dockerfile                   # Docker 构建文件
├── docker-compose.yml           # Docker Compose 配置
├── src/
│   └── tg_search/               # 主包
│       ├── __init__.py
│       ├── __main__.py          # CLI 入口 (python -m tg_search)
│       ├── main.py              # 主入口
│       ├── app.py               # Flask 健康检查入口
│       ├── config/              # 配置模块
│       │   ├── __init__.py
│       │   └── settings.py      # 环境变量配置
│       ├── core/                # 核心业务逻辑
│       │   ├── __init__.py
│       │   ├── bot.py           # Bot 处理器
│       │   ├── telegram.py      # Telegram 客户端
│       │   ├── meilisearch.py   # MeiliSearch 客户端
│       │   └── logger.py        # 日志配置
│       ├── utils/               # 工具函数
│       │   ├── __init__.py
│       │   ├── formatters.py    # 格式化工具
│       │   ├── permissions.py   # 权限检查
│       │   └── message_tracker.py # 消息追踪
│       └── session/             # Telethon 会话文件
└── tests/                       # 测试文件
    ├── conftest.py
    ├── test_meilisearch_handler.py
    └── test_utils.py
```

---

## 模块索引

| 模块 | 路径 | 职责 |
|------|------|------|
| **config** | `src/tg_search/config/` | 环境变量配置管理 |
| **core** | `src/tg_search/core/` | 核心业务处理器 |
| **utils** | `src/tg_search/utils/` | 通用工具函数 |
| **tests** | `tests/` | 单元测试 |

---

## 快速命令

```bash
# 激活环境变量
cd /home/sinfor/Games/SteamLibrary/CODE/Meilisearch4TelegramSearchCKJ
source .venv/bin/activate

# 安装依赖（使用 uv）
uv sync

# 安装开发依赖
uv sync --extra dev

# 本地运行（方式 1：模块方式）
python -m tg_search

# 本地运行（方式 2：命令行入口）
tg-search

# Docker 运行
docker-compose up -d

# 运行测试
pytest tests/

# 代码检查
ruff check src/
ruff format src/
```

---

## 环境变量

### 必填
| 变量 | 说明 |
|------|------|
| `APP_ID` | Telegram API ID |
| `APP_HASH` | Telegram API Hash |
| `BOT_TOKEN` | Telegram Bot Token |
| `MEILI_HOST` | MeiliSearch 地址 |
| `MEILI_MASTER_KEY` | MeiliSearch 密钥 |

### 可选
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WHITE_LIST` | `[1]` | 白名单 (频道/群组/用户 ID) |
| `BLACK_LIST` | `[]` | 黑名单 |
| `OWNER_IDS` | `[]` | Bot 管理员 ID |
| `SESSION_STRING` | - | Telethon 会话字符串 |
| `LOGGING_LEVEL` | `25` | 控制台日志级别 |
| `BATCH_MSG_UNM` | `200` | 批量上传消息数 |
| `TIME_ZONE` | `Asia/Shanghai` | 时区 |

---

## 开发规范

### 代码风格
- 使用类型注解
- 异步函数使用 `async/await`
- 日志使用 `setup_logger()` 获取 logger
- 使用 ruff 进行代码格式化和检查

### 导入规范
```python
# 正确的导入方式
from tg_search.config.settings import APP_ID, APP_HASH
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.utils.formatters import sizeof_fmt
```

### 消息序列化格式
```python
{
    'id': 'chat_id-msg_id',           # 主键
    'chat': {...},                     # 聊天信息
    'date': 'ISO8601',                 # 时间戳
    'text': '...',                     # 消息内容
    'from_user': {...},                # 发送者
    'reactions': {...},                # 表情反应
    'reactions_scores': float          # 情感分数
}
```

---

## 相关链接

- **GitHub**: https://github.com/clionertr/Meilisearch4TelegramSearchCKJ
- **Wiki**: https://github.com/clionertr/Meilisearch4TelegramSearchCKJ/wiki
- **原项目**: https://github.com/tgbot-collection/SearchGram
