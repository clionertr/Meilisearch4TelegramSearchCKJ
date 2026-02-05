"""
API 路由模块

包含所有 API 端点定义
"""

from fastapi import APIRouter

from tg_search.api.routes import config, control, search, status, ws

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(status.router, prefix="/status", tags=["Status"])
api_router.include_router(config.router, prefix="/config", tags=["Config"])
api_router.include_router(control.router, prefix="/client", tags=["Control"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

__all__ = ["api_router"]
