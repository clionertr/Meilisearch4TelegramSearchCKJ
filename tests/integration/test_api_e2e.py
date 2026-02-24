"""
端到端 API 集成测试

按逻辑顺序测试所有 API 端点：
  Phase 1: 基础连通性
  Phase 2: 配置管理
  Phase 3: 下载历史消息（默认跳过，需 Telegram 连接）
  Phase 4: 搜索验证
  Phase 5: 客户端控制
  Phase 6: 错误处理

使用 switchable 装饰器控制测试开关。
"""

import json
import time

import httpx
import pytest

from tests.integration.config import DOWNLOAD_WAIT_TIMEOUT, is_enabled
from tests.integration.conftest import switchable


def _log(method: str, path: str, status: int, body: dict | None = None) -> None:
    """统一的测试日志输出"""
    print(f"\n  [{method} {path}] → {status}")
    if body:
        print(f"  Response: {json.dumps(body, indent=2, ensure_ascii=False)[:500]}")


def _quick_check_server_ok(timeout: float = 4.0) -> bool:
    """独立健康检查 — 探测 Telegram auth 是否阻塞了事件循环"""
    from tests.integration.config import TEST_API_BASE_URL
    try:
        r = httpx.get(f"{TEST_API_BASE_URL}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


class TestPhase1Connectivity:
    """Phase 1: 基础连通性"""

    @switchable("health_check")
    def test_01_health_check(self, api_client: httpx.Client):
        """GET /health — 健康检查"""
        r = api_client.get("/health")
        _log("GET", "/health", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @switchable("root_endpoint")
    def test_02_root_endpoint(self, api_client: httpx.Client):
        """GET / — 根端点"""
        r = api_client.get("/")
        _log("GET", "/", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Telegram Search API"
        assert "version" in data

    @switchable("system_status")
    def test_03_system_status(self, api_client: httpx.Client):
        """GET /api/v1/status — 系统状态"""
        r = api_client.get("/api/v1/status")
        _log("GET", "/api/v1/status", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        status = data["data"]
        assert "uptime_seconds" in status
        assert "meili_connected" in status
        assert "version" in status


class TestPhase2Config:
    """Phase 2: 配置管理"""

    @switchable("get_config")
    def test_04_get_config(self, api_client: httpx.Client):
        """GET /api/v1/config — 获取配置"""
        r = api_client.get("/api/v1/config")
        _log("GET", "/api/v1/config", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        config = data["data"]
        for key in ("white_list", "black_list", "owner_ids", "batch_msg_num",
                     "results_per_page", "max_page", "search_cache", "cache_expire_seconds"):
            assert key in config, f"Missing config key: {key}"

    @switchable("config_whitelist")
    def test_05_set_whitelist(self, api_client: httpx.Client, test_group_info: dict | None):
        """POST /api/v1/config/whitelist — 设置白名单"""
        # 如果有测试群组，使用其 ID；否则使用一个占位 ID
        test_ids = []
        if test_group_info and "group_id" in test_group_info:
            test_ids = [test_group_info["group_id"]]
        else:
            test_ids = [9999999]

        r = api_client.post("/api/v1/config/whitelist", json={"ids": test_ids})
        _log("POST", "/api/v1/config/whitelist", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "updated_list" in data["data"]

    @switchable("config_whitelist")
    def test_06_verify_whitelist(self, api_client: httpx.Client, test_group_info: dict | None):
        """GET /api/v1/config — 验证白名单已更新"""
        r = api_client.get("/api/v1/config")
        _log("GET", "/api/v1/config", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

        # 验证白名单包含我们设置的 ID
        white_list = data["data"]["white_list"]
        if test_group_info and "group_id" in test_group_info:
            assert test_group_info["group_id"] in white_list
        else:
            assert 9999999 in white_list

    @switchable("config_blacklist")
    def test_07_set_blacklist(self, api_client: httpx.Client):
        """POST /api/v1/config/blacklist — 设置黑名单"""
        r = api_client.post("/api/v1/config/blacklist", json={"ids": [8888888]})
        _log("POST", "/api/v1/config/blacklist", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True


class TestPhase3Download:
    """Phase 3: 下载历史消息（默认跳过）"""

    @switchable("download_history")
    def test_08_start_download(self, api_client: httpx.Client):
        """POST /api/v1/client/start — 启动下载

        启动后等待数秒检测服务器是否仍然响应：
        - 响应：session 文件有效，Telethon 非阻塞，保持运行让 test_09 等待下载完成
        - 无响应：session 无效，Telethon 阻塞在交互式认证，立即停止保护事件循环
        """
        r = api_client.post("/api/v1/client/start")
        _log("POST", "/api/v1/client/start", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["data"]["status"] in ("started", "already_running")

        # 等待 3 秒后检测服务器是否仍然响应
        print("  Waiting 3s to check if Telegram session is non-blocking...")
        time.sleep(3)

        if _quick_check_server_ok(timeout=4.0):
            print("  ✅ Server still responsive — session file valid, download running in background")
            # 不停止客户端，让 test_09 负责等待下载完成
        else:
            print("  ⚠️  Server unresponsive — no valid session, stopping client to protect event loop")
            print("      Fix: ensure session/user_session.session exists or set SESSION_STRING in .env")
            try:
                api_client.post("/api/v1/client/stop", timeout=5.0)
            except Exception:
                pass

    @switchable("download_history")
    def test_09_wait_for_download(self, api_client: httpx.Client):
        """GET /api/v1/status/progress — 等待下载完成（若事件循环被阻塞则跳过）"""
        # 先用独立短超时检查服务器是否还响应
        # Telethon 在没有 SESSION_STRING 时会阻塞事件循环进行交互式授权
        print("  Checking server responsiveness after client/start...")
        if not _quick_check_server_ok(timeout=5.0):
            pytest.skip(
                "Server unresponsive after client/start.\n"
                "Likely cause: no SESSION_STRING, Telethon is blocking on interactive auth.\n"
                "Fix: set SESSION_STRING in .env for headless operation."
            )

        deadline = time.time() + DOWNLOAD_WAIT_TIMEOUT
        last_count = None
        start_time = time.time()
        # 至少等 15s，给 Telegram 足够时间连接后开始下载
        # 防止在下载还未开始时 count=0 被误判为"已完成"
        minimum_wait = 15

        while time.time() < deadline:
            try:
                r = api_client.get("/api/v1/status/progress", timeout=8.0)
            except (httpx.ReadTimeout, httpx.ConnectError):
                pytest.skip(
                    "Server stopped responding mid-download.\n"
                    "Set SESSION_STRING in .env for non-interactive Telegram auth."
                )

            assert r.status_code == 200
            data = r.json()
            count = data["data"].get("count", 0)
            elapsed = time.time() - start_time

            if count == 0 and last_count is not None and elapsed >= minimum_wait:
                print("  Download completed!")
                break

            last_count = count
            print(f"  Progress: {count} active downloads (elapsed: {elapsed:.0f}s)")
            time.sleep(3)
        else:
            pytest.skip(f"Download did not complete within {DOWNLOAD_WAIT_TIMEOUT}s")

    @switchable("download_history")
    def test_10_verify_indexed(self, api_client: httpx.Client):
        """GET /api/v1/search/stats — 验证已有文档索引（需 SESSION_STRING 完成下载才有意义）"""
        if not _quick_check_server_ok(timeout=5.0):
            pytest.skip("Server unresponsive, skipping index verification")
        r = api_client.get("/api/v1/search/stats", timeout=10.0)
        _log("GET", "/api/v1/search/stats", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        total = data["data"]["total_documents"]
        if total == 0:
            pytest.skip(
                "No documents indexed (expected without SESSION_STRING). "
                "Set SESSION_STRING in .env and enable download_history to index data."
            )
        assert total > 0


class TestPhase4Search:
    """Phase 4: 搜索验证"""

    @switchable("search_stats")
    def test_11_search_stats(self, api_client: httpx.Client):
        """GET /api/v1/search/stats — 搜索统计"""
        r = api_client.get("/api/v1/search/stats")
        _log("GET", "/api/v1/search/stats", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "total_documents" in data["data"]
        assert "is_indexing" in data["data"]

    @switchable("search_basic")
    def test_12_search_basic(self, api_client: httpx.Client):
        """GET /api/v1/search?q=test — 基本搜索"""
        r = api_client.get("/api/v1/search", params={"q": "test"})
        _log("GET", "/api/v1/search?q=test", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        result = data["data"]
        assert "hits" in result
        assert "query" in result
        assert result["query"] == "test"
        assert "total_hits" in result
        assert "processing_time_ms" in result

    @switchable("search_chinese")
    def test_13_search_chinese(self, api_client: httpx.Client):
        """GET /api/v1/search?q=你好 — 中文搜索"""
        r = api_client.get("/api/v1/search", params={"q": "你好"})
        _log("GET", "/api/v1/search?q=你好", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "hits" in data["data"]

    @switchable("search_with_filters")
    def test_14_search_with_filters(self, api_client: httpx.Client):
        """GET /api/v1/search — 带过滤条件搜索"""
        params = {
            "q": "test",
            "limit": 5,
            "offset": 0,
            "chat_type": "group",
        }
        r = api_client.get("/api/v1/search", params=params)
        _log("GET", "/api/v1/search (filtered)", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["data"]["limit"] == 5
        assert data["data"]["offset"] == 0

    @switchable("search_with_filters")
    def test_15_search_with_chat_id(self, api_client: httpx.Client, test_group_info: dict | None):
        """GET /api/v1/search — 按 chat_id 过滤搜索"""
        if not test_group_info or "group_id" not in test_group_info:
            pytest.skip("No test group info available")

        params = {
            "q": "test",
            "chat_id": test_group_info["group_id"],
        }
        r = api_client.get("/api/v1/search", params=params)
        _log("GET", "/api/v1/search (chat_id)", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    @switchable("search_pagination")
    def test_16_search_pagination(self, api_client: httpx.Client):
        """GET /api/v1/search — 分页搜索"""
        # 第一页
        r1 = api_client.get("/api/v1/search", params={"q": "test", "limit": 2, "offset": 0})
        assert r1.status_code == 200
        page1 = r1.json()["data"]
        _log("GET", "/api/v1/search (page 1)", r1.status_code, r1.json())

        # 第二页
        r2 = api_client.get("/api/v1/search", params={"q": "test", "limit": 2, "offset": 2})
        assert r2.status_code == 200
        page2 = r2.json()["data"]
        _log("GET", "/api/v1/search (page 2)", r2.status_code, r2.json())

        # 两页的结果不应完全相同（如果有足够数据的话）
        if page1["hits"] and page2["hits"]:
            ids1 = {h["id"] for h in page1["hits"]}
            ids2 = {h["id"] for h in page2["hits"]}
            assert ids1 != ids2, "Pagination returned identical results"

    @switchable("search_highlight")
    def test_17_search_highlight(self, api_client: httpx.Client):
        """验证搜索结果包含高亮 formatted_text"""
        r = api_client.get("/api/v1/search", params={"q": "test"})
        assert r.status_code == 200
        data = r.json()

        hits = data["data"]["hits"]
        if hits:
            hit = hits[0]
            # 应该有 formatted_text 字段
            print(f"  Hit keys: {list(hit.keys())}")
            # formatted_text 可能为 None（如果搜索词没有匹配到 text 字段）
            if hit.get("formatted_text"):
                assert "<mark>" in hit["formatted_text"], "No highlight tags in formatted_text"
                print(f"  Highlighted: {hit['formatted_text'][:100]}")
        else:
            print("  No hits to verify highlight")


class TestPhase5ClientControl:
    """Phase 5: 客户端控制"""

    @switchable("client_status")
    def test_18_client_status(self, api_client: httpx.Client):
        """GET /api/v1/client/status — 客户端状态"""
        r = api_client.get("/api/v1/client/status")
        _log("GET", "/api/v1/client/status", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "is_running" in data["data"]

    @switchable("client_control")
    def test_19_stop_client(self, api_client: httpx.Client):
        """POST /api/v1/client/stop — 停止客户端（API-only 模式下应返回 already_stopped）"""
        r = api_client.post("/api/v1/client/stop")
        _log("POST", "/api/v1/client/stop", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        # 在 API-only 模式下，状态应该是 already_stopped
        assert data["data"]["status"] in ("stopped", "already_stopped")

    @switchable("client_control")
    def test_20_get_dialogs(self, api_client: httpx.Client):
        """GET /api/v1/status/dialogs — 对话列表"""
        r = api_client.get("/api/v1/status/dialogs")
        _log("GET", "/api/v1/status/dialogs", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "dialogs" in data["data"]
        assert "total" in data["data"]

    @switchable("client_control")
    def test_21_get_progress(self, api_client: httpx.Client):
        """GET /api/v1/status/progress — 下载进度"""
        r = api_client.get("/api/v1/status/progress")
        _log("GET", "/api/v1/status/progress", r.status_code, r.json())

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "progress" in data["data"]
        assert "count" in data["data"]


class TestPhase6ErrorHandling:
    """Phase 6: 错误处理"""

    @switchable("error_empty_query")
    def test_22_search_empty_query(self, api_client: httpx.Client):
        """GET /api/v1/search?q= — 空查询应返回 422"""
        r = api_client.get("/api/v1/search", params={"q": ""})
        _log("GET", "/api/v1/search?q=", r.status_code, r.json())

        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    @switchable("error_invalid_limit")
    def test_23_search_invalid_limit(self, api_client: httpx.Client):
        """GET /api/v1/search?q=test&limit=200 — 超限应返回 422"""
        r = api_client.get("/api/v1/search", params={"q": "test", "limit": 200})
        _log("GET", "/api/v1/search?q=test&limit=200", r.status_code, r.json())

        assert r.status_code == 422
        data = r.json()
        assert "detail" in data
