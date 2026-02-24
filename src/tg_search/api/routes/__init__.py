"""
API 路由模块

包含所有 API 端点定义
"""

from fastapi import APIRouter, Depends

from tg_search.api.deps import verify_api_key_or_bearer_token, verify_bearer_token
from tg_search.api.routes import ai_config, auth, config, control, dashboard, dialogs, search, status, storage, ws

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

# Storage 端点 - 需要认证 (P1-ST)
api_router.include_router(
    storage.router,
    prefix="/storage",
    tags=["Storage"],
    dependencies=[Depends(verify_api_key_or_bearer_token)],
)

# AI Config 端点 - Bearer-only（与 SPEC-P1-ai-config AC-1 对齐）
api_router.include_router(
    ai_config.router,
    prefix="/ai",
    tags=["AI Config"],
    dependencies=[Depends(verify_bearer_token)],
)

# Dashboard 端点 - Bearer-only（与 SPEC-P2-dashboard AC-1 对齐）
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(verify_bearer_token)],
)

# Dialog Sync 端点 - Bearer-only（ADR-DS-001，不接受 API Key）
# 鉴权在各路由函数内通过 verify_bearer_token dep 单独控制（不在此处添加全局 dep，
# 避免 FastAPI 双重校验），实际通过各端点 _token 参数强制注入
api_router.include_router(
    dialogs.router,
    prefix="/dialogs",
    tags=["Dialogs"],
)

# WebSocket 端点 - 内部处理 Token 鉴权
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

__all__ = ["api_router"]
