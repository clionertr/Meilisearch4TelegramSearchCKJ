"""
AI Config API 路由 (P1-AI)

提供 AI 配置读写与连通性测试接口：
  GET  /ai/config      — 读取配置（不回显 api_key）
  PUT  /ai/config      — 写入配置
  POST /ai/config/test — 连通性测试
  GET  /ai/models      — 获取模型列表（动态拉取 + fallback）
"""

import time

import httpx
from fastapi import APIRouter, Depends

from tg_search.api.deps import get_config_store, run_sync_in_thread
from tg_search.api.models import (
    AiConfigData,
    AiConfigTestData,
    AiConfigUpdateRequest,
    AiModelsData,
    ApiResponse,
)
from tg_search.core.logger import setup_logger

logger = setup_logger()

router = APIRouter()

# 连通性测试超时（规格要求 10s）
_TEST_TIMEOUT_SEC = 10


def _classify_error(exc: Exception, status_code: int | None = None) -> tuple[str, str]:
    """
    根据异常和 HTTP 状态码分类错误。

    返回 (error_code, error_message)
    错误分类: NETWORK_ERROR | AUTH_FAILED | INVALID_MODEL | PROVIDER_ERROR
    """
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.ConnectTimeout)):
        return "NETWORK_ERROR", str(exc)

    if status_code is not None:
        if status_code in (401, 403):
            return "AUTH_FAILED", f"{status_code} unauthorized"
        if status_code == 404:
            return "INVALID_MODEL", f"{status_code} model/endpoint not found"

    return "PROVIDER_ERROR", str(exc) if isinstance(exc, Exception) else "Unknown error"


@router.get(
    "/config",
    response_model=ApiResponse[AiConfigData],
    summary="获取 AI 配置",
    description="返回当前 AI 配置（不回显 api_key 明文，仅返回 api_key_set 布尔值）",
)
async def get_ai_config(
    config_store=Depends(get_config_store),
) -> ApiResponse[AiConfigData]:
    """
    AC-2: 返回 200 且仅返回 api_key_set，不回显明文 key。
    """
    config = await run_sync_in_thread(config_store.load_config)

    data = AiConfigData(
        provider=config.ai.provider,
        base_url=config.ai.base_url,
        model=config.ai.model,
        api_key_set=bool(config.ai.api_key),
        updated_at=config.updated_at,
    )
    return ApiResponse(data=data)


@router.put(
    "/config",
    response_model=ApiResponse[AiConfigData],
    summary="更新 AI 配置",
    description="写入 AI 配置（provider/base_url/model/api_key），按 spec 不回显 api_key",
)
async def put_ai_config(
    body: AiConfigUpdateRequest,
    config_store=Depends(get_config_store),
) -> ApiResponse[AiConfigData]:
    """
    AC-3: 返回 200 且配置可被后续 GET 读取。
    AC-4: 参数不合法时由 Pydantic 自动返回 422。
    """
    patch = {
        "provider": body.provider,
        "base_url": body.base_url,
        "model": body.model,
        "api_key": body.api_key,
    }
    result = await run_sync_in_thread(config_store.update_section, "ai", patch)

    data = AiConfigData(
        provider=result.ai.provider,
        base_url=result.ai.base_url,
        model=result.ai.model,
        api_key_set=bool(result.ai.api_key),
        updated_at=result.updated_at,
    )
    return ApiResponse(data=data)


@router.post(
    "/config/test",
    response_model=ApiResponse[AiConfigTestData],
    summary="AI 连通性测试",
    description="调用 ${base_url}/models 进行连通性测试，返回 ok/error_code/error_message/latency_ms",
)
async def post_ai_config_test(
    config_store=Depends(get_config_store),
) -> ApiResponse[AiConfigTestData]:
    """
    AC-5: 返回 200 且包含 ok/error_code/error_message/latency_ms。
    """
    config = await run_sync_in_thread(config_store.load_config)
    ai = config.ai

    base_url = ai.base_url.rstrip("/")
    test_url = f"{base_url}/models"
    headers = {}
    if ai.api_key:
        headers["Authorization"] = f"Bearer {ai.api_key}"

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT_SEC) as client:
            resp = await client.get(test_url, headers=headers)

        latency_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code == 200:
            data = AiConfigTestData(ok=True, latency_ms=latency_ms)
        else:
            error_code, error_message = _classify_error(
                Exception(f"HTTP {resp.status_code}"),
                status_code=resp.status_code,
            )
            data = AiConfigTestData(
                ok=False,
                error_code=error_code,
                error_message=error_message,
                latency_ms=latency_ms,
            )
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        error_code, error_message = _classify_error(exc)
        data = AiConfigTestData(
            ok=False,
            error_code=error_code,
            error_message=error_message,
            latency_ms=latency_ms,
        )

    return ApiResponse(data=data)


@router.get(
    "/models",
    response_model=ApiResponse[AiModelsData],
    summary="获取可用模型列表",
    description="优先动态拉取 ${base_url}/models，拉取失败时回退 [current_config_model]",
)
async def get_ai_models(
    config_store=Depends(get_config_store),
) -> ApiResponse[AiModelsData]:
    """
    AC-6: 返回 200 且含 models 列表。
    优先动态拉取，拉取失败时回退 fallback=true。
    """
    config = await run_sync_in_thread(config_store.load_config)
    ai = config.ai

    base_url = ai.base_url.rstrip("/")
    models_url = f"{base_url}/models"
    headers = {}
    if ai.api_key:
        headers["Authorization"] = f"Bearer {ai.api_key}"

    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT_SEC) as client:
            resp = await client.get(models_url, headers=headers)

        if resp.status_code == 200:
            body = resp.json()
            # OpenAI-compatible API 返回 {"data": [{"id": "model-name", ...}, ...]}
            raw_models = body.get("data", [])
            if isinstance(raw_models, list) and len(raw_models) > 0:
                model_ids = []
                for m in raw_models:
                    if isinstance(m, dict) and "id" in m:
                        model_ids.append(m["id"])
                    elif isinstance(m, str):
                        model_ids.append(m)
                if model_ids:
                    return ApiResponse(data=AiModelsData(models=model_ids, fallback=False))
    except Exception as exc:
        logger.warning(f"[AI Config] Failed to fetch models from {models_url}: {exc}")

    # Fallback: 返回当前配置的 model
    fallback_models = [ai.model] if ai.model else []
    return ApiResponse(data=AiModelsData(models=fallback_models, fallback=True))
