"""
API 真实环境集成测试模块

使用真实的 MeiliSearch 实例测试 FastAPI 端点
运行前请确保 MeiliSearch 服务已启动
"""

import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

# Integration tests must not run by default in CI/unit-test environments.
# Enable explicitly via: RUN_INTEGRATION_TESTS=true
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip("Integration tests are disabled. Set RUN_INTEGRATION_TESTS=true to enable.", allow_module_level=True)

# 设置环境变量用于真实环境测试
# 注意：需要确保 MEILI_HOST 和 MEILI_MASTER_KEY 已正确配置
os.environ.setdefault("SKIP_CONFIG_VALIDATION", "false")
os.environ.setdefault("API_ONLY", "true")
os.environ.setdefault("DEBUG", "true")


def get_real_test_client():
    """获取使用真实 MeiliSearch 的测试客户端"""
    from tg_search.api.app import build_app

    app = build_app()
    return TestClient(app)


class TestRealEnvironmentIntegration:
    """真实环境集成测试"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端 (使用真实环境)"""
        client = get_real_test_client()
        with client:
            yield client

    # ============ 健康检查测试 ============

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        print(f"\n[GET /health] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        return data

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        print(f"\n[GET /] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Telegram Search API"
        assert data["version"] == "0.2.0"
        assert data["docs"] == "/docs"
        return data

    # ============ 搜索 API 测试 ============

    def test_search_api_basic(self, client):
        """测试基本搜索功能"""
        # 使用一个通用的搜索词
        response = client.get("/api/v1/search", params={"q": "test"})
        print(f"\n[GET /api/v1/search?q=test] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "hits" in data["data"]
        assert "query" in data["data"]
        assert "total_hits" in data["data"]
        assert "processing_time_ms" in data["data"]
        return data

    def test_search_api_with_filters(self, client):
        """测试带过滤条件的搜索"""
        params = {
            "q": "hello",
            "limit": 5,
            "offset": 0,
            "chat_type": "group",
        }
        response = client.get("/api/v1/search", params=params)
        print(f"\n[GET /api/v1/search with filters] Status: {response.status_code}")
        print(f"Params: {params}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["limit"] == 5
        assert data["data"]["offset"] == 0
        return data

    def test_search_api_chinese(self, client):
        """测试中文搜索"""
        response = client.get("/api/v1/search", params={"q": "你好"})
        print(f"\n[GET /api/v1/search?q=你好] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        return data

    def test_search_stats(self, client):
        """测试搜索统计端点"""
        response = client.get("/api/v1/search/stats")
        print(f"\n[GET /api/v1/search/stats] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "total_documents" in data["data"]
        assert "is_indexing" in data["data"]
        return data

    # ============ 配置 API 测试 ============

    def test_get_config(self, client):
        """测试获取配置"""
        response = client.get("/api/v1/config")
        print(f"\n[GET /api/v1/config] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        config = data["data"]
        assert "white_list" in config
        assert "black_list" in config
        assert "owner_ids" in config
        assert "batch_msg_num" in config
        assert "results_per_page" in config
        assert "max_page" in config
        assert "search_cache" in config
        assert "cache_expire_seconds" in config
        return data

    def test_add_to_whitelist(self, client):
        """测试添加白名单"""
        test_ids = [9999999]  # 使用一个不太可能存在的测试 ID
        response = client.post(
            "/api/v1/config/whitelist",
            json={"ids": test_ids},
        )
        print(f"\n[POST /api/v1/config/whitelist] Status: {response.status_code}")
        print(f"Request body: {{'ids': {test_ids}}}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "updated_list" in data["data"]
        assert "added" in data["data"]
        return data

    def test_add_to_blacklist(self, client):
        """测试添加黑名单"""
        test_ids = [8888888]  # 使用一个不太可能存在的测试 ID
        response = client.post(
            "/api/v1/config/blacklist",
            json={"ids": test_ids},
        )
        print(f"\n[POST /api/v1/config/blacklist] Status: {response.status_code}")
        print(f"Request body: {{'ids': {test_ids}}}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        return data

    # ============ 状态 API 测试 ============

    def test_get_system_status(self, client):
        """测试获取系统状态"""
        response = client.get("/api/v1/status")
        print(f"\n[GET /api/v1/status] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        status = data["data"]
        assert "uptime_seconds" in status
        assert "meili_connected" in status
        assert "bot_connected" in status
        assert "telegram_connected" in status
        assert "indexed_messages" in status
        assert "memory_usage_mb" in status
        assert "version" in status
        return data

    def test_get_dialogs(self, client):
        """测试获取对话列表"""
        response = client.get("/api/v1/status/dialogs")
        print(f"\n[GET /api/v1/status/dialogs] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "dialogs" in data["data"]
        assert "total" in data["data"]
        return data

    def test_get_download_progress(self, client):
        """测试获取下载进度"""
        response = client.get("/api/v1/status/progress")
        print(f"\n[GET /api/v1/status/progress] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "progress" in data["data"]
        assert "count" in data["data"]
        return data

    # ============ 控制 API 测试 ============

    def test_get_client_status(self, client):
        """测试获取客户端状态"""
        response = client.get("/api/v1/client/status")
        print(f"\n[GET /api/v1/client/status] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "is_running" in data["data"]
        return data

    def test_stop_client(self, client):
        """测试停止客户端 (在 API-only 模式下应返回 already_stopped)"""
        response = client.post("/api/v1/client/stop")
        print(f"\n[POST /api/v1/client/stop] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        return data

    # ============ 错误处理测试 ============

    def test_search_validation_error(self, client):
        """测试搜索参数验证错误"""
        # 空查询应该返回 422
        response = client.get("/api/v1/search", params={"q": ""})
        print(f"\n[GET /api/v1/search?q=] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        # FastAPI 应该返回 422 Unprocessable Entity
        assert response.status_code == 422
        return response.json()

    def test_search_limit_validation(self, client):
        """测试搜索 limit 参数验证"""
        # limit 超过最大值应该返回 422
        response = client.get("/api/v1/search", params={"q": "test", "limit": 200})
        print(f"\n[GET /api/v1/search?q=test&limit=200] Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 422
        return response.json()


class TestAPIResponseFormat:
    """API 响应格式审核测试"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端"""
        client = get_real_test_client()
        with client:
            yield client

    def test_success_response_format(self, client):
        """验证成功响应的格式"""
        response = client.get("/api/v1/config")
        data = response.json()

        print("\n=== 成功响应格式审核 ===")
        print(f"包含 success 字段: {'success' in data}")
        print(f"success 值为 True: {data.get('success') is True}")
        print(f"包含 data 字段: {'data' in data}")
        print(f"包含 timestamp 字段: {'timestamp' in data}")

        # 验证必需字段
        assert "success" in data, "响应缺少 success 字段"
        assert data["success"] is True, "成功响应的 success 应为 True"
        assert "data" in data, "响应缺少 data 字段"
        assert "timestamp" in data, "响应缺少 timestamp 字段"

    def test_search_result_format(self, client):
        """验证搜索结果的格式"""
        response = client.get("/api/v1/search", params={"q": "test"})
        data = response.json()

        print("\n=== 搜索结果格式审核 ===")
        search_result = data.get("data", {})
        print(f"包含 hits: {'hits' in search_result}")
        print(f"包含 query: {'query' in search_result}")
        print(f"包含 processing_time_ms: {'processing_time_ms' in search_result}")
        print(f"包含 total_hits: {'total_hits' in search_result}")
        print(f"包含 limit: {'limit' in search_result}")
        print(f"包含 offset: {'offset' in search_result}")

        # 验证搜索结果字段
        assert "hits" in search_result
        assert "query" in search_result
        assert "processing_time_ms" in search_result
        assert "total_hits" in search_result
        assert "limit" in search_result
        assert "offset" in search_result

        # 如果有结果，验证消息格式
        if search_result["hits"]:
            hit = search_result["hits"][0]
            print("\n消息格式审核:")
            print(f"  包含 id: {'id' in hit}")
            print(f"  包含 chat: {'chat' in hit}")
            print(f"  包含 date: {'date' in hit}")
            print(f"  包含 text: {'text' in hit}")
            print(f"  包含 from_user: {'from_user' in hit}")
            print(f"  包含 reactions: {'reactions' in hit}")

            assert "id" in hit
            assert "chat" in hit
            assert "date" in hit
            assert "text" in hit

    def test_error_response_format(self, client):
        """验证错误响应的格式"""
        response = client.get("/api/v1/search", params={"q": ""})
        data = response.json()

        print("\n=== 错误响应格式审核 ===")
        print(f"HTTP Status: {response.status_code}")
        print(f"响应内容: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # FastAPI 验证错误返回 422 和 detail 字段
        assert response.status_code == 422
        assert "detail" in data


def run_integration_tests():
    """运行所有集成测试并生成报告"""
    print("=" * 60)
    print("API 真实环境集成测试")
    print("=" * 60)
    print(f"运行时间: {datetime.now().isoformat()}")
    print()

    # 使用 pytest 运行测试
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
    ])

    return exit_code


if __name__ == "__main__":
    sys.exit(run_integration_tests())
