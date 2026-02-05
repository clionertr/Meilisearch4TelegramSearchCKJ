# src 源代码目录

> [根目录](../../CLAUDE.md) > src

---

## 目录结构

```
src/
├── CLAUDE.md           # 本文档
├── main.py             # CLI 入口点
├── app.py              # Flask 健康检查入口
├── __init__.py
├── config/             # 配置管理
│   └── CLAUDE.md
├── models/             # 核心业务逻辑
│   └── CLAUDE.md
├── utils/              # 工具函数
│   └── CLAUDE.md
└── session/            # Telethon 会话文件存放
```

---

## 入口文件

### main.py

主入口，启动 Telegram 用户客户端和 Bot。

```python
# 核心流程
async def main():
    user_bot_client = TelegramUserBot(meili)
    await user_bot_client.start()
    download_task = asyncio.create_task(download_and_listen(user_bot_client))
    await download_task

# 程序入口
if __name__ == "__main__":
    bot_handler = BotHandler(run)
    asyncio.run(bot_handler.run())
```

**启动顺序**:
1. 初始化 MeiliSearchClient
2. 启动 BotHandler
3. BotHandler 自动启动消息下载/监听任务

---

### app.py

Flask 应用，提供健康检查端点，在后台线程运行 Bot。

```python
@app.route('/')
def health_check():
    return {"status": "healthy"}, 200

# 后台任务在独立线程运行异步代码
def start_background_tasks():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(run_async_code)
```

**端口**: 7860 (容器内)

---

## 子模块索引

| 子模块 | 说明 | 文档 |
|--------|------|------|
| config | 环境变量与配置 | [config/CLAUDE.md](./config/CLAUDE.md) |
| models | 核心业务处理器 | [models/CLAUDE.md](./models/CLAUDE.md) |
| utils | 工具函数 | [utils/CLAUDE.md](./utils/CLAUDE.md) |

---

## 运行方式

```bash
# 方式 1: 直接运行 (推荐开发)
cd Meilisearch4TelegramSearchCKJ/src
python main.py

# 方式 2: Flask 模式 (Docker 部署)
python app.py
```
