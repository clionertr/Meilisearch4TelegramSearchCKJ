"""
API 路由模块

包含所有 API 端点定义
"""

from fastapi import APIRouter, Depends

from tg_search.api.deps import verify_api_key
from tg_search.api.routes import config, control, search, status, ws

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 注册子路由（需要认证的端点使用 dependencies 参数）
# 搜索端点 - 需要认证
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(verify_api_key)],
)

# 状态端点 - 需要认证
api_router.include_router(
    status.router,
    prefix="/status",
    tags=["Status"],
    dependencies=[Depends(verify_api_key)],
)

# 配置端点 - 需要认证
api_router.include_router(
    config.router,
    prefix="/config",
    tags=["Config"],
    dependencies=[Depends(verify_api_key)],
)

# 控制端点 - 需要认证
api_router.include_router(
    control.router,
    prefix="/client",
    tags=["Control"],
    dependencies=[Depends(verify_api_key)],
)

# WebSocket 端点 - 不需要认证（WebSocket 通常使用其他认证机制）
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

__all__ = ["api_router"]
