"""
API 测试模块

使用 pytest + httpx 测试 FastAPI 端点
"""

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_app_state():
    """创建模拟的 AppState"""
    from tg_search.api.state import AppState

    state = AppState()
    state.start_time = datetime.utcnow()
    state.api_only = True
    return state


@pytest.fixture(scope="module")
def mock_meili_client():
    """Mock MeiliSearch 客户端"""
    # Avoid MagicMock here: FastAPI runs MeiliSearch calls in a worker thread,
    # and MagicMock can behave poorly across threads in some environments.

    @dataclass
    class FakeIndexStats:
        number_of_documents: int = 1000
        is_indexing: bool = False

    class FakeMeiliClient:
        def search(self, query, index_name="telegram", **kwargs):
            return {
                "hits": [
                    {
                        "id": "123-456",
                        "chat": {"id": 123, "type": "group", "title": "Test Group"},
                        "date": "2026-01-01T00:00:00+08:00",
                        "text": "Hello World",
                        "from_user": {"id": 789, "username": "testuser"},
                        "reactions": {"👍": 5},
                        "reactions_scores": 5.0,
                        "text_len": 11,
                    }
                ],
                "processingTimeMs": 10,
                "estimatedTotalHits": 1,
            }

        def get_index_stats(self, index_name="telegram"):
            return FakeIndexStats()

    return FakeMeiliClient()


@pytest.fixture(autouse=True)
def _reset_config_lists():
    """
    Reset mutable settings between tests.

    The API config endpoints mutate module-level lists (WHITE_LIST/BLACK_LIST/etc).
    Without resetting, tests become order-dependent.
    """
    from tg_search.config import settings

    white_list = settings.WHITE_LIST.copy()
    black_list = settings.BLACK_LIST.copy()
    owner_ids = settings.OWNER_IDS.copy()
    yield
    settings.WHITE_LIST[:] = white_list
    settings.BLACK_LIST[:] = black_list
    settings.OWNER_IDS[:] = owner_ids


@pytest.fixture(scope="module")
async def test_client(mock_meili_client):
    """
    创建带有正确模拟状态的测试客户端。

    Note: starlette/fastapi TestClient 在某些受限环境里会卡死（线程/portal相关），
    这里用 httpx.AsyncClient + ASGITransport 并显式运行 FastAPI lifespan。
    """
    with patch("tg_search.api.app.MeiliSearchClient", return_value=mock_meili_client):
        from tg_search.api.app import build_app, lifespan

        app = build_app()
        async with lifespan(app):
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                # lifespan 会被执行，app_state 会被创建；确保 meili_client 为 mock
                app.state.app_state.meili_client = mock_meili_client
                yield client


class TestHealthCheck:
    """健康检查端点测试"""

    async def test_health_check(self, test_client):
        """测试健康检查端点"""
        response = await test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    async def test_root_endpoint(self, test_client):
        """测试根端点"""
        response = await test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Telegram Search API"
        assert data["version"] == "0.2.0"
        assert data["docs"] == "/docs"


class TestSearchAPI:
    """搜索 API 测试"""

    async def test_search_messages(self, test_client):
        """测试消息搜索"""
        response = await test_client.get("/api/v1/search?q=hello")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_search_with_filters(self, test_client):
        """测试带过滤条件的搜索"""
        response = await test_client.get(
            "/api/v1/search",
            params={
                "q": "test",
                "chat_type": "group",
                "limit": 10,
                "offset": 0,
            },
        )
        assert response.status_code == 200

    async def test_search_stats(self, test_client):
        """测试搜索统计"""
        response = await test_client.get("/api/v1/search/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestConfigAPI:
    """配置 API 测试"""

    async def test_get_config(self, test_client):
        """测试获取配置"""
        response = await test_client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "white_list" in data["data"]
        assert "black_list" in data["data"]

    async def test_add_to_whitelist(self, test_client):
        """测试添加白名单"""
        response = await test_client.post(
            "/api/v1/config/whitelist",
            json={"ids": [123456, 789012]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_add_to_blacklist(self, test_client):
        """测试添加黑名单"""
        response = await test_client.post(
            "/api/v1/config/blacklist",
            json={"ids": [999999]},
        )
        assert response.status_code == 200


class TestStatusAPI:
    """状态 API 测试"""

    async def test_get_system_status(self, test_client):
        """测试获取系统状态"""
        response = await test_client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "uptime_seconds" in data["data"]
        assert "meili_connected" in data["data"]

    async def test_get_dialogs(self, test_client):
        """测试获取对话列表"""
        response = await test_client.get("/api/v1/status/dialogs")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "dialogs" in data["data"]

    async def test_get_download_progress(self, test_client):
        """测试获取下载进度"""
        response = await test_client.get("/api/v1/status/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestControlAPI:
    """控制 API 测试"""

    async def test_get_client_status(self, test_client):
        """测试获取客户端状态"""
        response = await test_client.get("/api/v1/client/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "is_running" in data["data"]

    async def test_stop_client_when_not_running(self, test_client):
        """测试停止未运行的客户端"""
        response = await test_client.post("/api/v1/client/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "already_stopped"


class TestAuthAPI:
    """认证 API 测试"""

    async def test_signin_reuses_send_code_session(self, test_client):
        """send-code 与 signin 必须复用同一 Telegram 文件会话"""
        from tg_search.api.routes import auth as auth_routes

        captured: dict[str, str | None] = {"signin_session": None}

        class FakeTelegramClient:
            def __init__(self, session, *args, **kwargs):
                self.session = session

            async def connect(self):
                return None

            async def disconnect(self):
                return None

            async def send_code_request(self, phone, force_sms=False):
                return SimpleNamespace(phone_code_hash="hash-123")

            async def sign_in(self, phone=None, code=None, phone_code_hash=None, password=None):
                captured["signin_session"] = (
                    self.session if isinstance(self.session, str) else getattr(self.session, "value", None)
                )
                return SimpleNamespace(
                    id=10001,
                    username="tester",
                    first_name="Test",
                    last_name="User",
                )

        with patch.object(auth_routes, "TelegramClient", FakeTelegramClient):
            send_resp = await test_client.post(
                "/api/v1/auth/send-code",
                json={"phone_number": "+8613800138000"},
            )
            assert send_resp.status_code == 200
            auth_session_id = send_resp.json()["data"]["auth_session_id"]

            signin_resp = await test_client.post(
                "/api/v1/auth/signin",
                json={
                    "auth_session_id": auth_session_id,
                    "phone_number": "+8613800138000",
                    "code": "12345",
                },
            )
            assert signin_resp.status_code == 200
            signin_data = signin_resp.json()["data"]
            assert signin_data["token_type"] == "Bearer"
            assert signin_data["user"]["id"] == 10001
            assert captured["signin_session"] == auth_routes.API_AUTH_SESSION_FILE


class TestModels:
    """Pydantic 模型测试"""

    def test_api_response_model(self):
        """测试 ApiResponse 模型"""
        from tg_search.api.models import ApiResponse

        response = ApiResponse(data={"test": "value"}, message="Success")
        assert response.success is True
        assert response.data == {"test": "value"}
        assert response.message == "Success"

    def test_error_response_model(self):
        """测试 ErrorResponse 模型"""
        from tg_search.api.models import ErrorResponse

        response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
        )
        assert response.success is False
        assert response.error_code == "TEST_ERROR"

    def test_search_request_validation(self):
        """测试 SearchRequest 验证"""
        from tg_search.api.models import SearchRequest

        # 有效请求
        request = SearchRequest(query="test", limit=10)
        assert request.query == "test"
        assert request.limit == 10

        # 空查询应该失败
        with pytest.raises(Exception):
            SearchRequest(query="", limit=10)

    def test_message_model(self):
        """测试 MessageModel"""
        from tg_search.api.models import ChatInfo, MessageModel, UserInfo

        msg = MessageModel(
            id="123-456",
            chat=ChatInfo(id=123, type="group", title="Test"),
            date=datetime.utcnow(),
            text="Hello",
            from_user=UserInfo(id=789, username="user"),
        )
        assert msg.id == "123-456"
        assert msg.chat.type == "group"


class TestProgressRegistry:
    """进度注册表测试"""

    @pytest.mark.asyncio
    async def test_update_progress(self):
        """测试更新进度"""
        from tg_search.api.state import ProgressRegistry

        registry = ProgressRegistry()
        await registry.update_progress(
            dialog_id=123,
            dialog_title="Test Dialog",
            current=50,
            total=100,
        )

        progress = registry.get_progress(123)
        assert progress is not None
        assert progress.current == 50
        assert progress.total == 100
        assert progress.percentage == 50.0

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        import asyncio

        from tg_search.api.state import ProgressRegistry

        registry = ProgressRegistry()
        queue = registry.subscribe()

        # 发布事件
        await registry.publish({"type": "test", "data": "value"})

        # 接收事件
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "test"

        # 取消订阅
        registry.unsubscribe(queue)
        assert queue not in registry._subscribers

    @pytest.mark.asyncio
    async def test_complete_progress(self):
        """测试完成进度"""
        from tg_search.api.state import ProgressRegistry

        registry = ProgressRegistry()
        await registry.update_progress(123, "Test", 50, 100)
        await registry.complete_progress(123)

        progress = registry.get_progress(123)
        assert progress.status == "completed"
        assert progress.current == progress.total
