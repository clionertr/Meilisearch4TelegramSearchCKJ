#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
permissions.py - Permission handling utilities
"""
from typing import Any, Callable, Coroutine
from Meilisearch4TelegramSearchCKJ.src.config.env import OWNER_IDS
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger # Or pass logger if needed

# Assuming logger can be accessed globally or passed if needed.
# If not global, the decorator needs adjustment or logger passed to handlers.
logger = setup_logger()

def set_permission(func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    权限检查装饰器：仅允许 OWNER_IDS 中的用户使用

    Args:
        func: 需要进行权限检查的异步函数 (must be a method of a class with a logger attribute)

    Returns:
        装饰后的异步函数
    """
    async def wrapper(handler_instance, event, *args, **kwargs):
        """装饰器内部函数"""
        user_id = event.sender_id
        # Ensure the handler instance has a logger attribute
        instance_logger = getattr(handler_instance, 'logger', logger)

        if not OWNER_IDS or user_id in OWNER_IDS:
            try:
                await func(handler_instance, event, *args, **kwargs)
            except Exception as e:
                instance_logger.error(f"执行 {func.__name__} 时出错: {e}", exc_info=True)
                # Attempt to reply using the event object directly
                try:
                    await event.reply(f"执行命令时发生错误: {e}")
                except Exception as reply_err:
                    instance_logger.error(f"回复错误消息失败: {reply_err}")
        else:
            instance_logger.info(f"用户 {user_id} 无权使用指令 {event.text}")
            try:
                await event.reply("你没有权限使用此指令。")
            except Exception as reply_err:
                 instance_logger.error(f"回复无权限消息失败: {reply_err}")

    return wrapper