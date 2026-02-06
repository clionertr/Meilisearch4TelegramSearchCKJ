"""
API 路由模块

包含所有 API 端点定义
"""

from fastapi import APIRouter, Depends

from tg_search.api.deps import verify_api_key_or_bearer_token
from tg_search.api.routes import auth, config, control, search, status, ws

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 认证端点 - 无需认证（用于登录流程）
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

# 搜索端点 - 需要认证（支持 API Key 或 Bearer Token）
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)

# 状态端点 - 需要认证
api_router.include_router(
    status.router,
    prefix="/status",
    tags=["Status"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)

# 配置端点 - 需要认证
api_router.include_router(
    config.router,
    prefix="/config",
    tags=["Config"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)

# 控制端点 - 需要认证
api_router.include_router(
    control.router,
    prefix="/client",
    tags=["Control"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)

# WebSocket 端点 - 内部处理 Token 鉴权
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

__all__ = ["api_router"]
