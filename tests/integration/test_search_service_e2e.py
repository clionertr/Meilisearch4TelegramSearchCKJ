"""E2E integration tests for unified SearchService behavior."""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from tests.helpers.requirements import check_meili_available, load_meili_env_from_dotenv
from tg_search.config.settings import RESULTS_PER_PAGE
from tg_search.core.bot import BotHandler
from tg_search.core.logger import setup_logger
from tg_search.core.meilisearch import MeiliSearchClient
from tg_search.services.container import ServiceContainer, build_service_container
from tg_search.services.search_service import SearchQuery

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
load_meili_env_from_dotenv()

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.meili]
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


def _extract_task_uid(task: Any) -> int | None:
    if task is None:
        return None
    if isinstance(task, dict):
        for key in ("taskUid", "uid", "task_uid"):
            value = task.get(key)
            if isinstance(value, int):
                return value
        return None
    for key in ("task_uid", "uid", "taskUid"):
        value = getattr(task, key, None)
        if isinstance(value, int):
            return value
    return None


def _wait_for_task(meili_client: MeiliSearchClient, task_uid: int | None) -> None:
    if task_uid is None:
        time.sleep(0.8)
        return
    wait_fn = getattr(meili_client.client, "wait_for_task", None)
    if callable(wait_fn):
        try:
            wait_fn(task_uid, timeout_in_ms=12_000, interval_in_ms=80)
            return
        except TypeError:
            wait_fn(task_uid)
            return
        except Exception:
            pass
    time.sleep(0.8)


def _extract_ids_from_bot_text(text: str) -> list[str]:
    # Bot message contains URLs like https://t.me/c/<chat_id>/<message_id>
    pairs = re.findall(r"https://t\.me/c/(-?\d+)/(\d+)", text)
    return [f"{chat_id}-{message_id}" for chat_id, message_id in pairs]


class _FakeBotClient:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, buttons: Any = None) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text, "buttons": buttons})


class _FakeMessageEvent:
    def __init__(self, chat_id: int = 1000) -> None:
        self.chat_id = chat_id
        self.replies: list[str] = []

    async def reply(self, text: str) -> None:
        self.replies.append(text)


class _FakeCallbackEvent:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.edits: list[dict[str, Any]] = []
        self.answers: list[dict[str, Any]] = []

    async def edit(self, text: str, buttons: Any = None) -> None:
        self.edits.append({"text": text, "buttons": buttons})

    async def answer(self, text: str, alert: bool = False) -> None:
        self.answers.append({"text": text, "alert": alert})

    async def reply(self, text: str) -> None:
        self.answers.append({"text": text, "alert": False})


@pytest.fixture
def service_container() -> ServiceContainer:
    meili = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY)
    index_name = f"system_config_ss_e2e_{uuid.uuid4().hex[:8]}"
    container = build_service_container(meili_client=meili, config_index_name=index_name)
    try:
        yield container
    finally:
        try:
            meili.delete_index(index_name)
        except Exception:
            pass


@pytest.fixture
def seeded_search_docs(service_container: ServiceContainer):
    marker = f"ss_e2e_{uuid.uuid4().hex[:8]}"
    chat_id = 910000 + int(time.time()) % 10000
    docs: list[dict[str, Any]] = []
    doc_ids: list[str] = []
    total_docs = max(RESULTS_PER_PAGE + 2, 8)
    now = datetime.now(timezone.utc)

    for i in range(total_docs):
        message_id = 10000 + i
        doc_id = f"{chat_id}-{message_id}"
        doc_ids.append(doc_id)
        docs.append(
            {
                "id": doc_id,
                "chat": {"id": chat_id, "type": "group", "title": f"ss-chat-{marker}"},
                "date": now.isoformat().replace("+00:00", "Z"),
                "text": f"{marker} keyword message {i}",
                "from_user": {"id": 3000 + i, "username": f"user_{i}"},
                "reactions": {},
                "reactions_scores": 0.0,
                "text_len": 0,
            }
        )

    index = service_container.meili_client.client.index("telegram")
    add_task = index.add_documents(docs)
    _wait_for_task(service_container.meili_client, _extract_task_uid(add_task))

    yield {"marker": marker, "chat_id": chat_id, "doc_ids": doc_ids}

    del_task = index.delete_documents(doc_ids)
    _wait_for_task(service_container.meili_client, _extract_task_uid(del_task))


@pytest.fixture
async def api_client(service_container: ServiceContainer):
    from tg_search.api.app import build_app, lifespan

    app = build_app()
    async with lifespan(app):
        state = app.state.app_state
        state.service_container = service_container
        state.meili_client = service_container.meili_client
        state.config_store = service_container.config_store
        state.config_policy_service = service_container.config_policy_service
        state.search_service = service_container.search_service
        state.api_only = False

        headers: dict[str, str] = {}
        api_key = os.environ.get("API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=headers,
        ) as client:
            yield client


@pytest.fixture
def bot_harness(service_container: ServiceContainer):
    bot = BotHandler.__new__(BotHandler)
    bot.logger = setup_logger()
    bot.services = service_container
    bot.search_service = service_container.search_service
    bot.policy_service = service_container.config_policy_service
    bot.meili = service_container.meili_client
    bot.search_results_cache = {}
    bot.bot_client = _FakeBotClient()
    bot.main = lambda: None
    bot.download_task = None
    return bot


@requires_meili
@pytest.mark.asyncio
async def test_api_and_bot_first_page_hits_are_consistent(
    api_client: httpx.AsyncClient,
    bot_harness: BotHandler,
    seeded_search_docs: dict[str, Any],
):
    marker = seeded_search_docs["marker"]
    response = await api_client.get(
        "/api/v1/search",
        params={"q": marker, "limit": RESULTS_PER_PAGE, "offset": 0},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    api_ids = [item["id"] for item in body["data"]["hits"]]
    assert api_ids, "seeded hits must be searchable via API"

    event = _FakeMessageEvent()
    await bot_harness.search_handler(event, marker)
    assert event.replies == []
    assert bot_harness.bot_client.sent_messages, "bot should send first-page message"
    bot_text = bot_harness.bot_client.sent_messages[-1]["text"]
    bot_ids = _extract_ids_from_bot_text(bot_text)

    assert bot_ids == api_ids


@requires_meili
@pytest.mark.asyncio
async def test_bot_callback_pagination_supports_underscore_query(
    bot_harness: BotHandler,
    seeded_search_docs: dict[str, Any],
):
    marker = seeded_search_docs["marker"]
    event = _FakeMessageEvent()
    await bot_harness.search_handler(event, marker)
    assert bot_harness.bot_client.sent_messages

    sent = bot_harness.bot_client.sent_messages[-1]
    buttons = sent["buttons"] or []
    next_button = next((button for button in buttons if getattr(button, "text", "") == "下一页"), None)
    assert next_button is not None, "seeded docs should produce a next-page button"

    callback_event = _FakeCallbackEvent(data=next_button.data)
    await bot_harness.callback_query_handler(callback_event)

    assert not callback_event.answers, f"callback should not fail: {callback_event.answers}"
    assert any("第 2 页" in edit["text"] for edit in callback_event.edits)


@requires_meili
@pytest.mark.asyncio
async def test_empty_result_is_consistent_between_api_and_bot(
    api_client: httpx.AsyncClient,
    bot_harness: BotHandler,
):
    query = f"__no_result_{uuid.uuid4().hex}"

    response = await api_client.get(
        "/api/v1/search",
        params={"q": query, "limit": RESULTS_PER_PAGE, "offset": 0},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["hits"] == []

    event = _FakeMessageEvent()
    await bot_harness.search_handler(event, query)
    assert any("没有找到相关结果" in msg for msg in event.replies)


@requires_meili
@pytest.mark.asyncio
async def test_search_service_query_object_supports_filters(bot_harness: BotHandler, seeded_search_docs: dict[str, Any]):
    marker = seeded_search_docs["marker"]
    chat_id = seeded_search_docs["chat_id"]

    page = await bot_harness.search_service.search(
        SearchQuery(
            q=marker,
            chat_id=chat_id,
            limit=RESULTS_PER_PAGE,
            offset=0,
        )
    )

    assert page.total_hits >= len(page.hits) >= 1
    assert all(hit.chat.id == chat_id for hit in page.hits)


@requires_meili
@pytest.mark.asyncio
async def test_search_service_query_object_supports_sender_filters(bot_harness: BotHandler, seeded_search_docs: dict[str, Any]):
    marker = seeded_search_docs["marker"]
    chat_id = seeded_search_docs["chat_id"]

    page = await bot_harness.search_service.search(
        SearchQuery(
            q=marker,
            chat_id=chat_id,
            sender_username="user_2",
            limit=RESULTS_PER_PAGE,
            offset=0,
        )
    )

    assert page.total_hits == 1
    assert len(page.hits) == 1
    assert page.hits[0].from_user.username == "user_2"
