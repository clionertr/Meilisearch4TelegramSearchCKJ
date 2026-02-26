"""
WebSocket 路由

提供实时状态推送
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tg_search.api.state import AppState
from tg_search.config.settings import API_KEY
from tg_search.core.logger import setup_logger

logger = setup_logger()

router = APIRouter()


def get_client_ip(websocket: WebSocket) -> str:
    """
    获取客户端真实 IP 地址

    支持代理服务器场景，按优先级检查：
    1. X-Forwarded-For 头（第一个 IP）
    2. X-Real-IP 头
    3. 直接连接的客户端 IP
    """
    # 检查 X-Forwarded-For（代理转发的真实 IP）
    x_forwarded_for = websocket.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个（真实客户端 IP）
        return x_forwarded_for.split(",")[0].strip()

    # 检查 X-Real-IP（Nginx 等反向代理常用）
    x_real_ip = websocket.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    # 回退到直接连接的客户端 IP
    if websocket.client:
        return websocket.client.host

    return "unknown"


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> str:
        """
        接受 WebSocket 连接

        Returns:
            客户端 IP 地址
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        client_ip = get_client_ip(websocket)
        logger.info(
            f"WebSocket connected from {client_ip}, "
            f"total connections: {len(self.active_connections)}"
        )
        return client_ip

    def disconnect(self, websocket: WebSocket, client_ip: Optional[str] = None):
        """断开 WebSocket 连接"""
        self.active_connections.remove(websocket)
        ip_info = f" from {client_ip}" if client_ip else ""
        logger.info(
            f"WebSocket disconnected{ip_info}, "
            f"remaining connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/status")
async def websocket_status(websocket: WebSocket):
    """
    WebSocket 状态推送端点

    认证方式：query parameter `token`
    示例：ws://localhost:8000/api/v1/ws/status?token=xxx

    客户端连接后会收到：
    - 连接成功消息
    - 定期状态更新（每 5 秒）
    - 下载进度事件
    """
    # 从 app 获取状态（需要特殊处理，WebSocket 没有 Request）
    app_state: AppState = websocket.app.state.app_state

    # Token 验证（如果 API_KEY 已配置）
    if API_KEY is not None:
        token = websocket.query_params.get("token")

        if not token:
            await websocket.close(code=4401, reason="Token required")
            logger.warning("WebSocket connection rejected: missing token")
            return

        # 验证 token
        if app_state.auth_store is not None:
            auth_token = await app_state.auth_store.validate_token(token)
            if auth_token is None:
                await websocket.close(code=4401, reason="Invalid or expired token")
                logger.warning("WebSocket connection rejected: invalid token")
                return
        else:
            # AuthStore 未初始化，拒绝连接
            await websocket.close(code=4503, reason="Auth service unavailable")
            logger.error("WebSocket connection rejected: AuthStore not initialized")
            return

    # 接受连接
    client_ip = await manager.connect(websocket)

    # 订阅进度更新
    progress_queue = app_state.progress_registry.subscribe()

    try:
        # 发送欢迎消息（包含客户端 IP 信息）
        await websocket.send_json(
            {
                "type": "connected",
                "data": {
                    "message": "WebSocket connected successfully",
                    "client_ip": client_ip,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # 创建两个并发任务
        async def receive_messages():
            """接收客户端消息"""
            while True:
                try:
                    data = await websocket.receive_json()
                    # 处理客户端发送的消息（如心跳、请求等）
                    if data.get("type") == "ping":
                        await websocket.send_json(
                            {
                                "type": "pong",
                                "data": {},
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    logger.warning(f"WebSocket receive error: {e}")
                    break

        async def send_progress():
            """发送进度更新"""
            while True:
                try:
                    # 等待进度更新（带超时）
                    try:
                        event = await asyncio.wait_for(progress_queue.get(), timeout=5.0)
                        event["timestamp"] = datetime.utcnow().isoformat()
                        await websocket.send_json(event)
                    except asyncio.TimeoutError:
                        # 超时时发送心跳
                        await websocket.send_json(
                            {
                                "type": "heartbeat",
                                "data": {"uptime_seconds": app_state.uptime_seconds},
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    logger.warning(f"WebSocket send error: {e}")
                    break

        # 并发运行两个任务
        receive_task = asyncio.create_task(receive_messages())
        send_task = asyncio.create_task(send_progress())

        try:
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            # 取消所有任务
            receive_task.cancel()
            send_task.cancel()

    except WebSocketDisconnect:
        pass
    finally:
        # 取消订阅
        app_state.progress_registry.unsubscribe(progress_queue)
        manager.disconnect(websocket, client_ip)
