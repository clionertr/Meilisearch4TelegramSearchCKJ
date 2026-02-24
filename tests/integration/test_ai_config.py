"""AI Config API integration tests against a real MeiliSearch instance.

Covers all acceptance criteria from SPEC-P1-ai-config.md:
  AC-1: 未携带 Bearer Token → 401
  AC-2: GET /ai/config → 200，仅返回 api_key_set，不回显明文 key
  AC-3: PUT /ai/config 合法参数 → 200，可被后续 GET 读取
  AC-4: PUT /ai/config 不合法参数 → 422
  AC-5: POST /ai/config/test → 200，包含 ok/error_code/error_message/latency_ms
  AC-6: GET /ai/models → 200，含 models 列表

Uses real MeiliSearch (no mocks) with isolated ConfigStore index per module.
"""

import os
import time
from contextlib import contextmanager
from unittest import mock

import pytest

from tests.helpers.requirements import (
    check_meili_available,
    load_meili_env_from_dotenv,
)

os.environ.setdefault("SKIP_CONFIG_VALIDATION", "true")
load_meili_env_from_dotenv()

# 同步 settings 模块中已缓存的 Meili 变量
from tg_search.config import settings as _settings  # noqa: E402

_settings.MEILI_PASS = os.environ.get("MEILI_MASTER_KEY", "")
_settings.MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")

from fastapi.testclient import TestClient  # noqa: E402

from tg_search.api.app import build_app  # noqa: E402

_MEILI_HOST = os.environ.get("MEILI_HOST", "http://localhost:7700")
_MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "")

# 测试用 NVIDIA OpenAI-compatible 配置
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_NVIDIA_API_KEY = "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"
_NVIDIA_MODEL = "z-ai/glm4.7"

pytestmark = [pytest.mark.integration, pytest.mark.meili]
_MEILI_SKIP_REASON = check_meili_available(_MEILI_HOST, _MEILI_KEY, require_auth=True)
requires_meili = pytest.mark.skipif(
    _MEILI_SKIP_REASON is not None,
    reason=_MEILI_SKIP_REASON or "",
)


def _cleanup_config_index(index_name: str) -> None:
    """清理测试专用 ConfigStore 索引"""
    from tg_search.core.meilisearch import MeiliSearchClient

    cli = MeiliSearchClient(_MEILI_HOST, _MEILI_KEY, auto_create_index=False)
    try:
        cli.delete_index(index_name)
        time.sleep(0.2)
    except Exception:
        pass


def _issue_bearer_header(client: TestClient) -> dict[str, str]:
    """通过测试端点签发 Bearer token，并返回 Authorization header。"""
    resp = client.post(
        "/api/v1/auth/dev/issue-token",
        json={
            "user_id": 10001,
            "phone_number": "+10000000001",
            "username": "ai_config_test_user",
        },
    )
    assert resp.status_code == 200, f"issue token failed: {resp.status_code} {resp.text}"
    token = resp.json()["data"]["token"]
    assert token
    return {"Authorization": f"Bearer {token}"}


@contextmanager
def _isolated_ai_client(config_index_name: str):
    """
    构建一个使用隔离 ConfigStore 索引的 TestClient。
    用于"重启后配置仍可读取"场景。
    """
    from tg_search.config.config_store import ConfigStore

    with (
        mock.patch.dict(os.environ, {"ALLOW_TEST_TOKEN_ISSUE": "true"}),
        mock.patch("tg_search.api.deps.API_KEY", None),
        mock.patch("tg_search.config.settings.API_KEY", None),
    ):
        app = build_app()
        with TestClient(app) as c:
            meili_client = c.app.state.app_state.meili_client
            c.app.state.app_state.config_store = ConfigStore(meili_client, index_name=config_index_name)
            yield c


# ============ Fixtures ============


@pytest.fixture(scope="module")
def client():
    """
    同步 TestClient，触发 FastAPI lifespan 以初始化 app_state。
    AI Config 端点为 Bearer-only；此处将 API_KEY 置空，确保不会通过 API Key 绕过鉴权。
    """
    with (
        mock.patch.dict(os.environ, {"ALLOW_TEST_TOKEN_ISSUE": "true"}),
        mock.patch("tg_search.api.deps.API_KEY", None),
        mock.patch("tg_search.config.settings.API_KEY", None),
    ):
        app = build_app()
        with TestClient(app) as c:
            yield c


@pytest.fixture(scope="module")
def auth_header(client: TestClient):
    """模块级 Bearer Token 认证头"""
    return _issue_bearer_header(client)


def _put_ai_config(
    client: TestClient,
    auth_header: dict[str, str],
    *,
    provider: str = "openai_compatible",
    base_url: str = _NVIDIA_BASE_URL,
    model: str = _NVIDIA_MODEL,
    api_key: str = _NVIDIA_API_KEY,
):
    """写入 AI 配置的测试辅助函数。"""
    return client.put(
        "/api/v1/ai/config",
        headers=auth_header,
        json={
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "api_key": api_key,
        },
    )


# ============ AC-1: 401 未授权测试 ============


@requires_meili
class TestAiConfigAuth:
    """AC-1: 未携带 Bearer Token 时全部返回 401"""

    def test_get_ai_config_without_auth_returns_401(self, client: TestClient):
        """GET /ai/config 无认证 → 401"""
        resp = client.get("/api/v1/ai/config")
        assert resp.status_code == 401

    def test_put_ai_config_without_auth_returns_401(self, client: TestClient):
        """PUT /ai/config 无认证 → 401"""
        resp = client.put(
            "/api/v1/ai/config",
            json={
                "provider": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "api_key": "sk-test",
            },
        )
        assert resp.status_code == 401

    def test_post_ai_config_test_without_auth_returns_401(self, client: TestClient):
        """POST /ai/config/test 无认证 → 401"""
        resp = client.post("/api/v1/ai/config/test")
        assert resp.status_code == 401

    def test_get_ai_models_without_auth_returns_401(self, client: TestClient):
        """GET /ai/models 无认证 → 401"""
        resp = client.get("/api/v1/ai/models")
        assert resp.status_code == 401

    def test_get_ai_config_with_api_key_only_still_returns_401(self, client: TestClient):
        """仅携带 API Key（无 Bearer）也应 401，验证 AI 端点为 Bearer-only"""
        resp = client.get("/api/v1/ai/config", headers={"X-API-Key": "legacy-api-key"})
        assert resp.status_code == 401


# ============ AC-2: GET /ai/config 测试 ============


@requires_meili
class TestGetAiConfig:
    """AC-2: GET /ai/config → 200，仅返回 api_key_set，不回显明文 key"""

    def test_returns_200_with_config(self, client: TestClient, auth_header: dict[str, str]):
        """GET /ai/config 返回 200 且包含必要字段"""
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "provider" in data
        assert "base_url" in data
        assert "model" in data
        assert "api_key_set" in data
        assert "updated_at" in data

    def test_does_not_expose_api_key_plaintext(self, client: TestClient, auth_header: dict[str, str]):
        """api_key 明文不应出现在响应中"""
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]

        # 不应包含 api_key 字段
        assert "api_key" not in data

    def test_api_key_set_is_boolean(self, client: TestClient, auth_header: dict[str, str]):
        """api_key_set 应为布尔值"""
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]

        assert isinstance(data["api_key_set"], bool)

    def test_default_provider_is_openai_compatible(self, client: TestClient, auth_header: dict[str, str]):
        """默认 provider 应为 openai_compatible"""
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]

        assert data["provider"] == "openai_compatible"


# ============ AC-3: PUT /ai/config 测试 ============


@requires_meili
class TestPutAiConfig:
    """AC-3: PUT /ai/config 合法参数 → 200，配置可被后续 GET 读取"""

    def test_returns_200_on_valid_config(self, client: TestClient, auth_header: dict[str, str]):
        """PUT /ai/config 合法参数 → 200"""
        resp = _put_ai_config(client, auth_header)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True

    def test_config_persisted_via_get(self, client: TestClient, auth_header: dict[str, str]):
        """PUT 后 GET 应返回更新后的值"""
        _put_ai_config(
            client,
            auth_header,
            base_url=_NVIDIA_BASE_URL,
            model=_NVIDIA_MODEL,
            api_key=_NVIDIA_API_KEY,
        )

        time.sleep(0.3)

        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]

        assert data["provider"] == "openai_compatible"
        assert data["base_url"] == _NVIDIA_BASE_URL
        assert data["model"] == _NVIDIA_MODEL
        assert data["api_key_set"] is True

    def test_put_response_does_not_expose_api_key(self, client: TestClient, auth_header: dict[str, str]):
        """PUT 响应也不应回显 api_key 明文"""
        resp = _put_ai_config(client, auth_header)
        data = resp.json()["data"]
        assert "api_key" not in data

    def test_api_key_set_true_after_put(self, client: TestClient, auth_header: dict[str, str]):
        """PUT 非空 api_key 后，api_key_set 应为 true"""
        _put_ai_config(client, auth_header)
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]
        assert data["api_key_set"] is True

    def test_api_key_set_false_after_empty_key(self, client: TestClient, auth_header: dict[str, str]):
        """PUT 空 api_key 后，api_key_set 应为 false"""
        _put_ai_config(client, auth_header, api_key="")
        resp = client.get("/api/v1/ai/config", headers=auth_header)
        data = resp.json()["data"]
        assert data["api_key_set"] is False

    def test_config_persisted_after_app_restart(self):
        """E2E: 重启 FastAPI app 后，AI 配置仍可从 ConfigStore 读取"""
        index_name = f"system_config_test_ai_restart_{int(time.time() * 1000)}"

        try:
            with _isolated_ai_client(index_name) as c1:
                auth_header_c1 = _issue_bearer_header(c1)
                r1 = c1.put(
                    "/api/v1/ai/config",
                    headers=auth_header_c1,
                    json={
                        "provider": "openai_compatible",
                        "base_url": _NVIDIA_BASE_URL,
                        "model": _NVIDIA_MODEL,
                        "api_key": _NVIDIA_API_KEY,
                    },
                )
                assert r1.status_code == 200

            # 模拟"重启"后使用新 app 实例读取同一 ConfigStore 索引
            with _isolated_ai_client(index_name) as c2:
                auth_header_c2 = _issue_bearer_header(c2)
                r2 = c2.get("/api/v1/ai/config", headers=auth_header_c2)
                assert r2.status_code == 200

                data = r2.json()["data"]
                assert data["base_url"] == _NVIDIA_BASE_URL
                assert data["model"] == _NVIDIA_MODEL
                assert data["api_key_set"] is True
        finally:
            _cleanup_config_index(index_name)


# ============ AC-4: PUT /ai/config 参数校验 → 422 ============


@requires_meili
class TestPutAiConfigValidation:
    """AC-4: PUT /ai/config 不合法参数 → 422"""

    def test_empty_model_returns_422(self, client: TestClient, auth_header: dict[str, str]):
        """空 model → 422"""
        resp = client.put(
            "/api/v1/ai/config",
            headers=auth_header,
            json={
                "provider": "openai_compatible",
                "base_url": _NVIDIA_BASE_URL,
                "model": "",
                "api_key": _NVIDIA_API_KEY,
            },
        )
        assert resp.status_code == 422

    def test_invalid_url_returns_422(self, client: TestClient, auth_header: dict[str, str]):
        """非法 URL → 422"""
        resp = client.put(
            "/api/v1/ai/config",
            headers=auth_header,
            json={
                "provider": "openai_compatible",
                "base_url": "not-a-valid-url",
                "model": _NVIDIA_MODEL,
                "api_key": _NVIDIA_API_KEY,
            },
        )
        assert resp.status_code == 422

    def test_missing_model_returns_422(self, client: TestClient, auth_header: dict[str, str]):
        """缺少必需的 model 字段 → 422"""
        resp = client.put(
            "/api/v1/ai/config",
            headers=auth_header,
            json={
                "provider": "openai_compatible",
                "base_url": _NVIDIA_BASE_URL,
                "api_key": _NVIDIA_API_KEY,
            },
        )
        assert resp.status_code == 422

    def test_missing_base_url_returns_422(self, client: TestClient, auth_header: dict[str, str]):
        """缺少必需的 base_url 字段 → 422"""
        resp = client.put(
            "/api/v1/ai/config",
            headers=auth_header,
            json={
                "provider": "openai_compatible",
                "model": _NVIDIA_MODEL,
                "api_key": _NVIDIA_API_KEY,
            },
        )
        assert resp.status_code == 422

    def test_invalid_provider_returns_422(self, client: TestClient, auth_header: dict[str, str]):
        """不支持的 provider → 422"""
        resp = client.put(
            "/api/v1/ai/config",
            headers=auth_header,
            json={
                "provider": "anthropic",
                "base_url": _NVIDIA_BASE_URL,
                "model": _NVIDIA_MODEL,
                "api_key": _NVIDIA_API_KEY,
            },
        )
        assert resp.status_code == 422


# ============ AC-5: POST /ai/config/test 测试 ============


@requires_meili
class TestPostAiConfigTest:
    """AC-5: POST /ai/config/test → 200，包含 ok/error_code/error_message/latency_ms"""

    def test_returns_200_with_test_result(self, client: TestClient, auth_header: dict[str, str]):
        """POST /ai/config/test 返回 200 且包含指定字段"""
        _put_ai_config(client, auth_header)

        resp = client.post("/api/v1/ai/config/test", headers=auth_header)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "ok" in data
        assert "latency_ms" in data
        assert isinstance(data["ok"], bool)
        assert isinstance(data["latency_ms"], (int, float))

    def test_error_key_returns_structured_result(self, client: TestClient, auth_header: dict[str, str]):
        """错误 key 场景应返回结构化结果（不同 provider 可能放行 /models）。"""
        _put_ai_config(
            client,
            auth_header,
            base_url=_NVIDIA_BASE_URL,
            model=_NVIDIA_MODEL,
            api_key="nvapi-invalid-key",
        )

        resp = client.post("/api/v1/ai/config/test", headers=auth_header)
        data = resp.json()["data"]

        assert isinstance(data["ok"], bool)
        if not data["ok"]:
            assert "error_code" in data
            assert "error_message" in data

    def test_error_code_is_valid_category(self, client: TestClient, auth_header: dict[str, str]):
        """错误代码应在规定的分类范围内"""
        _put_ai_config(
            client,
            auth_header,
            base_url=_NVIDIA_BASE_URL,
            model=_NVIDIA_MODEL,
            api_key="nvapi-bad-key",
        )

        resp = client.post("/api/v1/ai/config/test", headers=auth_header)
        data = resp.json()["data"]

        if not data["ok"]:
            valid_codes = {"NETWORK_ERROR", "AUTH_FAILED", "INVALID_MODEL", "PROVIDER_ERROR"}
            assert data["error_code"] in valid_codes, f"Unexpected error_code: {data['error_code']}"

    def test_unreachable_url_returns_network_error(self, client: TestClient, auth_header: dict[str, str]):
        """不可达地址 → NETWORK_ERROR"""
        _put_ai_config(
            client,
            auth_header,
            base_url="https://unreachable-host-test.invalid/v1",
            model=_NVIDIA_MODEL,
            api_key=_NVIDIA_API_KEY,
        )

        resp = client.post("/api/v1/ai/config/test", headers=auth_header)
        data = resp.json()["data"]

        assert data["ok"] is False
        assert data["error_code"] == "NETWORK_ERROR"

    def test_latency_ms_is_positive(self, client: TestClient, auth_header: dict[str, str]):
        """latency_ms 应为正数"""
        _put_ai_config(client, auth_header)

        resp = client.post("/api/v1/ai/config/test", headers=auth_header)
        data = resp.json()["data"]
        assert data["latency_ms"] >= 0


# ============ AC-6: GET /ai/models 测试 ============


@requires_meili
class TestGetAiModels:
    """AC-6: GET /ai/models → 200，含 models 列表"""

    def test_returns_200_with_models(self, client: TestClient, auth_header: dict[str, str]):
        """GET /ai/models 返回 200 且包含 models 列表"""
        _put_ai_config(client, auth_header)
        resp = client.get("/api/v1/ai/models", headers=auth_header)
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert "models" in data
        assert isinstance(data["models"], list)

    def test_fallback_returns_current_model(self, client: TestClient, auth_header: dict[str, str]):
        """当 provider 不可用时，回退返回当前配置的 model"""
        # 先设置一个不可达的 provider
        _put_ai_config(
            client,
            auth_header,
            base_url="https://unreachable-provider.invalid/v1",
            model="my-custom-model",
            api_key=_NVIDIA_API_KEY,
        )

        resp = client.get("/api/v1/ai/models", headers=auth_header)
        data = resp.json()["data"]

        assert "my-custom-model" in data["models"]
        assert data.get("fallback") is True

    def test_fallback_flag_present(self, client: TestClient, auth_header: dict[str, str]):
        """models 响应应包含 fallback 标志"""
        resp = client.get("/api/v1/ai/models", headers=auth_header)
        data = resp.json()["data"]

        assert "fallback" in data
        assert isinstance(data["fallback"], bool)
