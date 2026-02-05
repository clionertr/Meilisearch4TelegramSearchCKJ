"""
API 模块

提供 FastAPI REST API 层，支持：
- 搜索消息
- 系统状态查询
- 配置管理
- 客户端控制
- WebSocket 实时推送
"""

from tg_search.api.app import build_app

__all__ = ["build_app"]
