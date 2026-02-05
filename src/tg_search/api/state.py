"""
状态管理模块

提供进度追踪和 WebSocket 订阅管理
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Set


@dataclass
class ProgressInfo:
    """进度信息"""

    dialog_id: int
    dialog_title: str
    current: int
    total: int
    status: str  # 'downloading' | 'completed' | 'failed'
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.current / self.total) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dialog_id": self.dialog_id,
            "dialog_title": self.dialog_title,
            "current": self.current,
            "total": self.total,
            "percentage": self.percentage,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ProgressRegistry:
    """
    进度注册表

    管理下载进度并支持 WebSocket 订阅推送
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._progress: Dict[int, ProgressInfo] = {}
        self._lock = asyncio.Lock()

    def subscribe(self) -> asyncio.Queue:
        """订阅进度更新"""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """取消订阅"""
        self._subscribers.discard(queue)

    async def publish(self, event: Dict[str, Any]) -> None:
        """发布事件到所有订阅者"""
        for queue in self._subscribers.copy():
            try:
                await queue.put(event)
            except Exception:
                # 队列可能已关闭
                self._subscribers.discard(queue)

    async def update_progress(
        self,
        dialog_id: int,
        dialog_title: str,
        current: int,
        total: int,
        status: str = "downloading",
    ) -> None:
        """更新进度"""
        async with self._lock:
            if dialog_id in self._progress:
                info = self._progress[dialog_id]
                info.current = current
                info.total = total
                info.status = status
                info.updated_at = datetime.utcnow()
            else:
                info = ProgressInfo(
                    dialog_id=dialog_id,
                    dialog_title=dialog_title,
                    current=current,
                    total=total,
                    status=status,
                )
                self._progress[dialog_id] = info

        # 发布进度事件
        await self.publish(
            {
                "type": "progress",
                "data": info.to_dict(),
            }
        )

    async def complete_progress(self, dialog_id: int) -> None:
        """标记进度为完成"""
        async with self._lock:
            if dialog_id in self._progress:
                info = self._progress[dialog_id]
                info.status = "completed"
                info.current = info.total
                info.updated_at = datetime.utcnow()
                await self.publish(
                    {
                        "type": "progress",
                        "data": info.to_dict(),
                    }
                )

    async def fail_progress(self, dialog_id: int, error: str) -> None:
        """标记进度为失败"""
        async with self._lock:
            if dialog_id in self._progress:
                info = self._progress[dialog_id]
                info.status = "failed"
                info.updated_at = datetime.utcnow()
                await self.publish(
                    {
                        "type": "progress",
                        "data": {**info.to_dict(), "error": error},
                    }
                )

    def get_progress(self, dialog_id: int) -> Optional[ProgressInfo]:
        """获取指定对话的进度"""
        return self._progress.get(dialog_id)

    def get_all_progress(self) -> Dict[int, ProgressInfo]:
        """获取所有进度"""
        return self._progress.copy()

    def clear_completed(self) -> None:
        """清除已完成的进度"""
        self._progress = {k: v for k, v in self._progress.items() if v.status != "completed"}


class AppState:
    """
    应用状态容器

    在 FastAPI lifespan 中初始化，通过 app.state 访问
    """

    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.meili_client: Optional[Any] = None
        self.telegram_client: Optional[Any] = None
        self.bot_handler: Optional[Any] = None
        self.bot_task: Optional[asyncio.Task] = None
        self.progress_registry: ProgressRegistry = ProgressRegistry()
        self.api_only: bool = False

    @property
    def uptime_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        return (datetime.utcnow() - self.start_time).total_seconds()

    @property
    def is_bot_running(self) -> bool:
        return self.bot_task is not None and not self.bot_task.done()
