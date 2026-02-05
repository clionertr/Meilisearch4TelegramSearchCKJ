"""
WebSocket 路由

提供实时状态推送
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from tg_search.api.deps import get_app_state
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger

logger = setup_logger()

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected, total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected, remaining connections: {len(self.active_connections)}")

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

    客户端连接后会收到：
    - 连接成功消息
    - 定期状态更新（每 5 秒）
    - 下载进度事件
    """
    await manager.connect(websocket)

    # 从 app 获取状态（需要特殊处理，WebSocket 没有 Request）
    app_state: AppState = websocket.app.state.app_state

    # 订阅进度更新
    progress_queue = app_state.progress_registry.subscribe()

    try:
        # 发送欢迎消息
        await websocket.send_json(
            {
                "type": "connected",
                "data": {"message": "WebSocket connected successfully"},
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
        manager.disconnect(websocket)
