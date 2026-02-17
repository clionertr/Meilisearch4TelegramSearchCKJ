# 重构清单 - Meilisearch4TelegramSearchCKJ

> 生成时间: 2026-02-05 (P0 计划更新: 2026-02-06)
> 进度同步: 2026-02-17
> 目标: 修复现有问题 + 添加 API 层 + WebUI + 包结构规范化

---

## 目录

1. [项目概览](#1-项目概览)
2. [问题清单](#2-问题清单)
3. [建议的目标结构](#3-建议的目标结构)
4. [任务表](#4-任务表)
5. [执行状态快照 (2026-02-17)](#5-执行状态快照-2026-02-17)

---

## 1. 项目概览

### 当前功能
- Telegram 消息下载与实时监听
- MeiliSearch 全文搜索 (支持 CJK)
- Telegram Bot 交互搜索
- 黑白名单过滤
- 搜索结果缓存与分页

### 技术栈
| 组件 | 技术 |
|------|------|
| 语言 | Python 3.12 |
| Telegram | Telethon 1.38 |
| 搜索引擎 | MeiliSearch 0.33 |
| 日志 | coloredlogs |
| 容器 | Docker |

### 核心文件速查
| 文件 | 职责 |
|------|------|
| `src/main.py` | CLI 入口，启动下载/监听 |
| `src/app.py` | Flask 健康检查入口 |
| `src/config/env.py` | 环境变量配置 |
| `src/models/telegram_client_handler.py` | Telegram 用户客户端 |
| `src/models/bot_handler.py` | Bot 命令处理 |
| `src/models/meilisearch_handler.py` | MeiliSearch 封装 |
| `src/models/logger.py` | 日志配置 |
| `src/utils/record_lastest_msg_id.py` | 增量记录工具 |
| `src/utils/is_in_white_or_black_list.py` | 权限检查 |

---

## 2. 问题清单

### 2.1 高优先级 - 必须修复

#### P1-01: 异常处理过于宽泛
**问题**: 33 处 `except Exception as e` 吞掉所有异常，难以调试

| 文件 | 行号 | 当前代码 | 建议 |
|------|------|----------|------|
| `src/models/meilisearch_handler.py` | 33-35 | `except Exception as e` | 区分 `ConnectionError`, `TimeoutError` |
| `src/models/meilisearch_handler.py` | 55-57 | `except Exception as e` | 添加重试装饰器 |
| `src/models/meilisearch_handler.py` | 76-80 | 递归重试后仍 raise | 使用 `tenacity` 库 |
| `src/models/telegram_client_handler.py` | 115-117 | `except Exception as e` | 细化 Telethon 异常 |
| `src/models/telegram_client_handler.py` | 166-168 | `except Exception as e` | 同上 |
| `src/models/telegram_client_handler.py` | 266-268 | `except Exception as e` | 保留 `FloodWaitError` 单独处理 ✓ |
| `src/models/bot_handler.py` | 125-127 | `except Exception as e` | 细化搜索异常 |
| `src/utils/record_lastest_msg_id.py` | 44-46 | `except Exception as e` | 细化 MeiliSearch 异常 |

---

#### P1-02: 测试覆盖为零
**问题**: 4 个测试文件都是手动脚本，不是单元测试

| 文件 | 问题 |
|------|------|
| `tests/test_meilisearch.py` | 全部注释掉，只有 print 语句 |
| `tests/test_logger.py` | 仅手动打印日志 |
| `tests/test_tg_client.py` | 需要真实 API 连接 |
| `tests/test_configparser.py` | 无断言 |

**需要添加**:
- [ ] `tests/conftest.py` - pytest fixtures
- [ ] `tests/test_meilisearch_handler.py` - mock MeiliSearch
- [ ] `tests/test_telegram_handler.py` - mock Telethon
- [ ] `tests/test_bot_handler.py` - mock Bot 命令
- [ ] `tests/test_utils.py` - 工具函数测试

---

#### P1-03: 配置安全问题
**问题**: `env.py` 包含示例敏感值

| 文件 | 行号 | 问题 | 建议 |
|------|------|------|------|
| `src/config/env.py` | 6 | `APP_ID = os.getenv("APP_ID", "23010002")` | 必填项不设默认值 |
| `src/config/env.py` | 7 | `APP_HASH` 有示例默认值 | 启动时校验必填项 |
| `src/config/env.py` | 8 | `BOT_TOKEN` 有示例默认值 | 同上 |
| `src/config/env.py` | 11-12 | `MEILI_HOST/PASS` 有默认值 | 同上 |

---

### 2.2 中优先级 - 应该修复

#### P2-01: 类型注解不完整
**问题**: 函数缺少类型注解，IDE 提示差

| 文件 | 行号 | 函数 | 缺失 |
|------|------|------|------|
| `src/models/telegram_client_handler.py` | 39 | `serialize_chat(chat)` | 参数和返回类型 |
| `src/models/telegram_client_handler.py` | 57 | `serialize_sender(sender)` | 同上 |
| `src/models/telegram_client_handler.py` | 98 | `serialize_message(message, not_edited)` | 返回类型 |
| `src/models/bot_handler.py` | 226 | `format_search_result(hit)` | 参数类型 `hit: dict` |
| `src/utils/record_lastest_msg_id.py` | 17 | `update_latest_msg_config` | 所有参数 |

---

#### P2-02: 代码重复
**问题**: 相似逻辑未抽取

| 文件 | 行号 | 重复内容 |
|------|------|----------|
| `src/models/bot_handler.py` | 247-264 | `send_results_page` |
| `src/models/bot_handler.py` | 266-282 | `edit_results_page` (95% 相同) |

**建议**: 提取 `_build_results_page()` 公共方法

---

#### P2-03: 包结构不规范
**问题**: 导入路径冗长

| 当前 | 问题 |
|------|------|
| `from Meilisearch4TelegramSearchCKJ.src.config.env import X` | 5 层嵌套 |
| `Meilisearch4TelegramSearchCKJ/Meilisearch4TelegramSearchCKJ/src/` | 项目名重复 |

**建议**: 采用 `src/` layout，包名改为 `tg_search`

---

#### P2-04: setup.py 不完整
**问题**: 依赖未声明

| 文件 | 行号 | 问题 |
|------|------|------|
| `setup.py` | 7-8 | `install_requires=[]` 为空 |
| - | - | 应迁移到 `pyproject.toml` |

---

### 2.3 低优先级 - 建议修复

#### P3-01: 代码风格问题

| 文件 | 行号 | 问题 |
|------|------|------|
| `src/utils/record_lastest_msg_id.py` | 62 | `except  KeyError` 双空格 |
| `src/utils/record_lastest_msg_id.py` | 文件名 | `lastest` → `latest` 拼写错误 |
| `src/models/bot_handler.py` | 227 | `len(hit['text']) > 360` 魔法数字 |
| `src/models/logger.py` | 9 | `'log_file.log'` 硬编码路径 |

---

#### P3-02: 未完成的 TODO

| 文件 | 行号 | 内容 |
|------|------|------|
| `src/models/bot_handler.py` | 18-20 | `# TODO 1. 加速未缓存时的搜索速度` |
| `src/models/bot_handler.py` | 291 | `# TODO 加速未缓存时的搜索速度` |

---

#### P3-03: 潜在性能问题

| 文件 | 行号 | 问题 | 建议 |
|------|------|------|------|
| `src/models/bot_handler.py` | 117-121 | 搜索后立即请求额外缓存 | 改为懒加载 |
| `src/models/telegram_client_handler.py` | 25 | `tracemalloc.start()` 生产环境开销 | 改为配置控制 |

---

## 3. 建议的目标结构

### 3.1 目录结构

```
meilisearch-tg-search/                  # 项目根目录
├── pyproject.toml                      # [新] 统一配置
├── README.md
├── REFACTOR_CHECKLIST.md               # 本文档
├── CLAUDE.md
├── Dockerfile
├── docker-compose.yml
├── .env.example                        # [新] 环境变量模板
│
├── src/
│   └── tg_search/                      # [重命名] 简短包名
│       ├── __init__.py
│       ├── __main__.py                 # [新] python -m tg_search
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py             # [重命名] env.py
│       │
│       ├── core/                       # [重命名] models → core
│       │   ├── __init__.py
│       │   ├── telegram.py             # telegram_client_handler.py
│       │   ├── meilisearch.py          # meilisearch_handler.py
│       │   ├── bot.py                  # bot_handler.py
│       │   └── logger.py
│       │
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── message_tracker.py      # [重命名] record_lastest_msg_id.py
│       │   ├── permissions.py          # [重命名] is_in_white_or_black_list.py
│       │   └── formatters.py           # fmt_size.py + 其他格式化
│       │
│       └── api/                        # [新增] FastAPI
│           ├── __init__.py
│           ├── main.py                 # FastAPI app
│           ├── deps.py                 # 依赖注入
│           └── routes/
│               ├── search.py
│               ├── config.py
│               └── status.py
│
├── tests/                              # [移动] 测试到根目录
│   ├── conftest.py
│   ├── test_meilisearch.py
│   ├── test_telegram.py
│   ├── test_bot.py
│   └── test_api.py
│
└── frontend/                           # [新增] React WebUI
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── pages/
        │   ├── Search.tsx
        │   ├── Config.tsx
        │   └── Status.tsx
        └── components/
            └── ...
```

### 3.2 pyproject.toml 模板

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "meilisearch-tg-search"
version = "0.2.0"
description = "Telegram CJK message search powered by MeiliSearch"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [{ name = "clionertr" }]

dependencies = [
    "telethon>=1.38.0",
    "meilisearch>=0.33.0",
    "coloredlogs>=15.0",
    "pytz>=2024.1",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "tenacity>=8.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "mypy>=1.8",
    "ruff>=0.2",
    "httpx>=0.26",  # FastAPI 测试
]

[project.scripts]
tg-search = "tg_search.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/tg_search"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 120
select = ["E", "F", "I", "W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_ignores = true
```

### 3.3 API 端点规划

```yaml
# 搜索
GET  /api/v1/search
  params: q, page, limit, chat_type, date_from, date_to
  response: { hits: [...], total: n, page: n }

GET  /api/v1/search/stats
  response: { total_messages: n, total_chats: n, last_update: "..." }

# 配置
GET  /api/v1/config
  response: { whitelist: [...], blacklist: [...], ... }

PUT  /api/v1/config/whitelist
  body: { ids: [123, 456] }

PUT  /api/v1/config/blacklist
  body: { ids: [789] }

# 状态
GET  /api/v1/status
  response: { bot: "running", client: "downloading", progress: 0.75 }

GET  /api/v1/status/dialogs
  response: [{ id: 123, title: "...", synced: 1000, total: 2000 }]

# 控制
POST /api/v1/client/start
POST /api/v1/client/stop

# WebSocket (实时状态)
WS   /api/v1/ws/status
  messages: { type: "progress", data: {...} }
```

---

## 4. 任务表

### Phase 1: 稳定核心 (预计 3-5 天)

> 目标: 不改变功能，修复关键问题

| 序号 | 任务 | 涉及文件 | 验收标准 |
|------|------|----------|----------|
| 1.1 | 添加配置校验 | `src/config/env.py` | 缺少必填项时启动报错 |
| 1.2 | 细化 MeiliSearch 异常 | `src/models/meilisearch_handler.py` | 区分连接/超时/API 错误 |
| 1.3 | 细化 Telegram 异常 | `src/models/telegram_client_handler.py` | 区分网络/权限/限流错误 |
| 1.4 | 添加重试装饰器 | `src/models/meilisearch_handler.py` | 使用 `tenacity` 重试 |
| 1.5 | 添加 pytest 框架 | `tests/conftest.py` | `pytest` 可运行 |
| 1.6 | 添加 MeiliSearch 单元测试 | `tests/test_meilisearch_handler.py` | 覆盖 CRUD 操作 |
| 1.7 | 添加工具函数测试 | `tests/test_utils.py` | 覆盖 `is_allowed`, `sizeof_fmt` |
| 1.8 | 修复代码风格 | 多个文件 | ruff 检查通过 |

**检查点**: `pytest` 通过，现有功能正常

---

### Phase 2: 包结构重构 (预计 2-3 天)

> 目标: 规范化包结构，简化导入

| 序号 | 任务 | 说明 |
|------|------|------|
| 2.1 | 创建 `pyproject.toml` | 替代 `setup.py` + `requirements.txt` |
| 2.2 | 重命名包为 `tg_search` | 移动 `Meilisearch4TelegramSearchCKJ/src/` → `src/tg_search/` |
| 2.3 | 重命名模块文件 | 见 [3.1 目录结构](#31-目录结构) |
| 2.4 | 更新所有导入语句 | 全局替换 |
| 2.5 | 添加 `__main__.py` | 支持 `python -m tg_search` |
| 2.6 | 移动测试到根目录 | `tests/` 放项目根 |
| 2.7 | 更新 Dockerfile | 适配新结构 |
| 2.8 | 更新 CLAUDE.md | 反映新结构 |

**检查点**: `pip install -e .` 成功，`pytest` 通过，Docker 构建成功

---

### Phase 3: 添加 API 层 (预计 3-5 天)

> 目标: FastAPI 后端，为 WebUI 提供接口

| 序号 | 任务 | 涉及文件 |
|------|------|----------|
| 3.1 | 创建 FastAPI 应用骨架 | `src/tg_search/api/main.py` |
| 3.2 | 实现搜索 API | `src/tg_search/api/routes/search.py` |
| 3.3 | 实现配置 API | `src/tg_search/api/routes/config.py` |
| 3.4 | 实现状态 API | `src/tg_search/api/routes/status.py` |
| 3.5 | 添加 WebSocket 状态推送 | `src/tg_search/api/routes/status.py` |
| 3.6 | 添加 API 测试 | `tests/test_api.py` |
| 3.7 | 生成 OpenAPI 文档 | 自动 `/docs` |
| 3.8 | 集成 Bot + API 共存 | 更新 `__main__.py` |

**检查点**: `/docs` 可访问，API 端点可调用，Bot 功能正常

---

### Phase 4: WebUI 开发 (预计 5-7 天)

> 目标: React 管理后台
>
> **当前状态 (2026-02-17)**: P0 核心链路已打通（Auth / Search / WebSocket）
> - 已完成：Auth API、Bearer Token、Search 高亮透传、WebSocket 鉴权、前端登录流与受保护路由
> - 已完成：前端搜索字段契约对齐后端（`total_hits`、`chat`、`from_user`）
> - 已完成：前端 WebSocket 事件契约对齐后端（`type=progress` + `data.dialog_id`）
> - 已完成：Search 页面重复防抖清理（统一 300ms）
> - 待完成：Phase 4 的 P1/P2 管理能力（Storage/AIConfig/活动流等）

#### 4.0 需求评估分析

##### ✅ 当前执行状态（仅保留现状）

| 能力 | 状态 | 说明 |
|------|------|------|
| Telegram 登录认证 | ✅ 已完成 | `/api/v1/auth/send-code`、`/signin`、`/me`、`/logout` 可用 |
| Search 页面功能化 | ✅ 已完成 | 前端已接入 `/api/v1/search`，高亮字段 `formatted_text` 生效 |
| WebSocket 状态推送 | ✅ 已完成 | `/api/v1/ws/status` 已鉴权，前端已按 `progress.data` 消费 |
| 前后端字段契约 | ✅ 已完成 | Search 与 WS 字段结构已统一（2026-02-17） |

##### ⏭️ 下一阶段（P1/P2）

| 优先级 | 任务 | 当前状态 |
|-------|------|----------|
| P1 | Dashboard 真实数据（活动流/对话状态） | 待开发 |
| P1 | SyncedChats 管理能力（白/黑名单联动） | 待开发 |
| P1 | Storage 统计与清理 API + 页面接入 | 待开发 |
| P2 | AI 配置持久化与连接测试 | 待开发 |
| P2 | i18n 国际化 | 待开发 |

---

#### 4.1 当前技术基线（执行中）

- 认证: Bearer Token（不透明随机字符串）
- 后端存储: 内存（`auth_store.py`）
- 前端状态: Zustand + TanStack Query
- WebSocket 鉴权: query token（`?token=xxx`）
- 构建验证: 前端 `npm run build`、后端 `pytest -q`

**检查点**: WebUI 可访问，功能与 Bot 一致，认证流程完整

---

### Phase 5: 完善与优化 (持续)

| 序号 | 任务 | 优先级 |
|------|------|--------|
| 5.1 | 完善类型注解 + mypy | 中 |
| 5.2 | 添加 pre-commit hooks | 中 |
| 5.3 | CI/CD (GitHub Actions) | 中 |
| 5.4 | 搜索高级过滤 (时间/频道) | 低 |
| 5.5 | 国际化 (i18n) | 低 |
| 5.6 | 性能监控面板 | 低 |

---

## 5. 执行状态快照 (2026-02-17)

### 阶段进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1: 稳定核心 | ✅ 已完成 | 已建立测试体系并通过回归验证 |
| Phase 2: 包结构重构 | ✅ 已完成 | `src/tg_search` 与 `pyproject.toml` 已落地 |
| Phase 3: API 层 | ✅ 已完成 | FastAPI 路由、鉴权、测试均可用 |
| Phase 4: WebUI P0 | ✅ 已完成 | 登录、搜索、WebSocket 主链路打通 |
| Phase 4: WebUI P1/P2 | ⏳ 进行中 | Storage、AI、活动流等管理能力待补齐 |

### 验证结果

- 后端测试：`pytest -q` 通过（`59 passed, 1 skipped`）
- 前端构建：`npm run build` 通过（Vite 生产构建成功）

---

## 快速开始 (给新贡献者)

```bash
# 1. 克隆并安装
git clone https://github.com/clionertr/Meilisearch4TelegramSearchCKJ.git
cd Meilisearch4TelegramSearchCKJ
pip install -e ".[dev]"

# 2. 运行测试
pytest

# 3. 本地开发
cp .env.example .env
# 编辑 .env 填入真实配置
python -m tg_search

# 4. Docker 运行
docker-compose up -d
```

---

## 贡献指南

1. Fork 仓库
2. 创建功能分支: `git checkout -b feature/xxx`
3. 提交前运行: `ruff check . && pytest`
4. 提交信息格式: `feat: 添加xxx功能` / `fix: 修复xxx问题`
5. 创建 Pull Request

---

## 相关链接

- **GitHub**: https://github.com/clionertr/Meilisearch4TelegramSearchCKJ
- **原项目**: https://github.com/tgbot-collection/SearchGram
- **MeiliSearch 文档**: https://docs.meilisearch.com
- **Telethon 文档**: https://docs.telethon.dev
