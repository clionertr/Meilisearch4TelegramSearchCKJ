# Meilisearch4TelegramSearchCKJ

<img src="asset/image-20250206132432097.png" alt="展示图" style="zoom:25%;" />

## 介绍

Telegram 由于中文搜索不断词，官方搜索是灾难性的，pyrogram 太久没维护，性能也跟不上。因此开发了这个基于 Telethon 和 Meilisearch 的解决方案，提供高效的中文（CJK）聊天记录搜索功能。

本项目支持模糊搜索、拼写容错、分页显示等功能，让您轻松搜索 Telegram 聊天历史记录。

## 项目架构

<img src="asset/2025-02-05-1646.png" alt="架构概图" style="zoom:25%;" />

项目由三个主要组件组成：

- **TG Client**：从 Telegram 下载和监听消息，将数据存储到 Meilisearch
- **Meilisearch**：存储消息、增量配置、黑白名单等数据
- **Bot**：与用户交互的前端界面，负责处理搜索请求并启动 TG Client

## 主要功能

- 高效的中文（CJK）聊天记录搜索
- 支持白名单/黑名单过滤对话
- 增量下载和实时监听新消息
- 搜索结果分页显示
- 支持通过转发消息添加用户到黑名单或群组到白名单/黑名单
- 支持 `/rs` 命令重启机器人
- 支持 `/dialog` 命令显示所有对话名称和 ID（带分页功能）
- 配置更新后自动重启

## 部署

详细安装说明请参考 [wiki-安装](https://github.com/clionertr/Meilisearch4TelegramSearchCKJ/wiki/%E5%AE%89%E8%A3%85)

### Docker 部署

本项目支持 Docker 部署，可以使用以下命令：

```bash
# 使用 docker-compose
docker-compose up -d

# 或者直接使用 Docker
docker build -t tg_msg_search_from_meili .
docker run -d --name tg_msg_search_from_meili -p 8012:7860 tg_msg_search_from_meili
```

### 配置文件

项目使用 `settings.toml` 进行配置，请参考 `settings.toml.example` 创建自己的配置文件。

## 使用指南

### 基本命令

- `/start` - 启动机器人
- `/help` - 显示帮助信息
- `/about` - 关于本项目
- `/ping` - 检查机器人是否在线
- `/search [关键词]` - 搜索消息
- `/cc` - 清除搜索缓存
- `/rs` - 重启机器人
- `/dialog` - 显示所有对话名称和 ID（带分页功能）

### 管理命令（仅管理员可用）

- `/start_client` - 启动 TG Client
- `/stop_client` - 停止 TG Client

## 致谢

项目从 [GitHub - tgbot-collection/SearchGram](https://github.com/tgbot-collection/SearchGram) 重构而来，感谢原作者的付出。

特别感谢：
- Telethon 的作者和维护者们
- Meilisearch 团队提供的优秀搜索引擎
- Augment, Claude3.5s 和 GeminiExp 在开发过程中提供的帮助

从这个项目中学习到很多，希望大家喜欢这个项目！[:sparkling_heart:](https://linux.do/images/emoji/apple/sparkling_heart.png?v=12)
