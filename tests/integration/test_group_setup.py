"""
测试群组创建模块

使用 Telethon 创建测试群组并发送若干条测试消息。
如果 .test_groups.json 已存在且指定了群组列表，则直接跳过。

用法：
    python -m tests.integration.test_group_setup
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any

from tests.integration.config import (
    PROJECT_ROOT,
    TEST_GROUP_PREFIX,
    TEST_GROUPS_FILE,
    load_test_groups,
    save_test_groups,
)

# 预定义的测试消息
TEST_MESSAGES = [
    # 中文消息
    "这是一条中文测试消息，用于验证 MeiliSearch 中文分词搜索。",
    "你好世界！集成测试正在运行。",
    "搜索引擎测试：MeiliSearch 支持中日韩语言。",
    # 英文消息
    "This is an English test message for integration testing.",
    "Hello World! MeiliSearch search engine test.",
    "Integration test: verifying full-text search capabilities.",
    # 日文消息
    "これはテストメッセージです。日本語の検索テスト。",
    # 韩文消息
    "이것은 테스트 메시지입니다. 한국어 검색 테스트.",
    # 长文本
    (
        "这是一条较长的测试消息。MeiliSearch 是一个开源的全文搜索引擎，"
        "具有高性能、易于使用的特点。它支持中文、日文、韩文等 CJK 语言的分词搜索。"
        "本项目利用 MeiliSearch 为 Telegram 消息提供搜索功能，解决 Telegram 官方搜索"
        "对中文支持不佳的问题。"
    ),
    # 带 emoji
    "🔍 搜索测试 emoji 消息 👍🎉🔥",
]

# 每次运行都会发送一组“探针消息”，用于强保证校验
PROBE_MARKER_PREFIX = "e2eprobe"
PROBE_KEYWORD_PREFIX = "e2eauditkw"


def _build_probe_messages(marker: str, keyword: str) -> list[str]:
    """构造本次运行专属探针消息"""
    return [
        f"[{marker}] E2E EN probe message for search format audit. keyword={keyword}",
        f"[{marker}] E2E 中文探针：搜索结果格式审核，关键词 {keyword}",
        f"[{marker}] E2E pagination and highlight verification message. keyword={keyword}",
    ]


def _print(msg: str) -> None:
    print(f"[test_group_setup] {msg}", flush=True)


def _build_client():
    """构造 Telethon 客户端（字符串会话优先）"""
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    from tg_search.config.settings import APP_HASH, APP_ID, SESSION_STRING

    if SESSION_STRING:
        return TelegramClient(StringSession(SESSION_STRING), APP_ID, APP_HASH)

    session_dir = PROJECT_ROOT / "session"
    session_file = str(session_dir / "user_bot_session")
    return TelegramClient(session_file, APP_ID, APP_HASH)


async def create_test_group() -> dict:
    """
    使用 Telethon 创建测试群组并发送测试消息。

    Returns:
        包含 group_id, group_title, message_ids 等信息的字典
    """
    client = _build_client()

    await client.start()
    _print("Telethon client started")

    try:
        # 获取自己的用户信息
        me = await client.get_me()
        _print(f"Logged in as: {me.username or me.first_name} (ID: {me.id})")

        # 创建群组
        timestamp = int(time.time())
        group_title = f"{TEST_GROUP_PREFIX}{timestamp}"

        _print(f"Creating group: {group_title}")

        from telethon.tl.functions.messages import CreateChatRequest

        result = await client(CreateChatRequest(
            users=[me.username or "me"],
            title=group_title,
        ))

        # 提取群组信息
        # CreateChatRequest 返回 Updates 对象，其中 .chats 包含新建群组
        chat = None
        chats = getattr(result, "chats", [])
        for c in chats:
            if getattr(c, "title", None) == group_title:
                chat = c
                break

        if chat is None:
            # fallback: 从最近对话中查找
            _print("  Falling back to iter_dialogs to find created group...")
            async for dialog in client.iter_dialogs(limit=10):
                if getattr(dialog.entity, "title", None) == group_title:
                    chat = dialog.entity
                    break

        if chat is None:
            raise RuntimeError(f"Failed to find created group: {group_title}")

        group_id = chat.id
        _print(f"Group created: {group_title} (ID: {group_id})")

        # 发送测试消息
        message_ids = []
        for i, text in enumerate(TEST_MESSAGES):
            msg = await client.send_message(chat, text)
            message_ids.append(msg.id)
            _print(f"  Sent message {i + 1}/{len(TEST_MESSAGES)}: {text[:40]}...")
            # 小延迟避免限流
            await asyncio.sleep(0.5)

        group_data = {
            "group_id": group_id,
            "group_title": group_title,
            "message_ids": message_ids,
            "message_count": len(message_ids),
            "created_at": datetime.now().isoformat(),
            "user_id": me.id,
        }

        _print(f"Test group ready: {len(message_ids)} messages sent")
        return group_data

    finally:
        await client.disconnect()


async def _resolve_group_entity(client: Any, group_data: dict) -> Any:
    """根据 group_id 或 group_title 解析群组实体"""
    group_id = group_data.get("group_id")
    group_title = group_data.get("group_title")

    if group_id is not None:
        try:
            return await client.get_entity(group_id)
        except Exception:
            _print(f"get_entity({group_id}) failed, fallback to iter_dialogs")

    if group_title:
        async for dialog in client.iter_dialogs(limit=100):
            if getattr(dialog.entity, "title", None) == group_title:
                return dialog.entity

    raise RuntimeError(f"Cannot resolve target group: id={group_id}, title={group_title}")


async def append_probe_messages(group_data: dict) -> dict:
    """
    向测试群组发送本次运行专属探针消息，并写入 marker/keyword。

    这些消息用于后续测试强校验，避免历史索引数据导致“假通过”。
    """
    client = _build_client()
    await client.start()
    _print("Telethon client started for probe message injection")

    try:
        marker = f"{PROBE_MARKER_PREFIX}{int(time.time())}"
        keyword = f"{PROBE_KEYWORD_PREFIX}{int(time.time())}"
        probe_messages = _build_probe_messages(marker, keyword)

        target = await _resolve_group_entity(client, group_data)
        probe_message_ids: list[int] = []

        _print(f"Injecting probe messages into group: {group_data.get('group_title')} (ID: {group_data.get('group_id')})")
        for i, text in enumerate(probe_messages, start=1):
            msg = await client.send_message(target, text)
            probe_message_ids.append(msg.id)
            _print(f"  Probe {i}/{len(probe_messages)} sent: {text[:80]}...")
            await asyncio.sleep(0.4)

        group_data["probe_marker"] = marker
        group_data["probe_keyword"] = keyword
        group_data["probe_messages"] = probe_messages
        group_data["probe_message_ids"] = probe_message_ids
        group_data["probe_message_count"] = len(probe_message_ids)
        group_data["last_probe_at"] = datetime.now().isoformat()

        _print(f"Probe messages injected: {len(probe_message_ids)} (marker={marker})")
        return group_data
    finally:
        await client.disconnect()


async def setup_test_groups(force: bool = False) -> dict:
    """
    准备测试群组。如果已有群组数据且不强制重建，直接复用。

    Args:
        force: 是否强制重新创建

    Returns:
        测试群组信息字典
    """
    existing = load_test_groups()

    if existing and not force:
        _print(f"Using existing test group: {existing.get('group_title')} (ID: {existing.get('group_id')})")
        try:
            updated = await append_probe_messages(existing)
            save_test_groups(updated)
            _print(f"Test group info updated with probe data: {TEST_GROUPS_FILE}")
            return updated
        except Exception as e:
            _print(f"Existing group unavailable for probe injection: {e}")
            _print("Falling back to creating a new test group...")

    _print("Creating new test group...")
    group_data = await create_test_group()
    group_data = await append_probe_messages(group_data)
    save_test_groups(group_data)
    _print(f"Test group info saved to {TEST_GROUPS_FILE}")
    return group_data


def run_setup(force: bool = False) -> dict:
    """同步入口"""
    return asyncio.run(setup_test_groups(force=force))


if __name__ == "__main__":
    force = "--force" in sys.argv
    data = run_setup(force=force)
    print(json.dumps(data, indent=2, ensure_ascii=False))
