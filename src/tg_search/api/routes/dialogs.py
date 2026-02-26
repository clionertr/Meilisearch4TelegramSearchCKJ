"""
Dialog Sync API 路由

提供会话同步管理端点：
  GET    /api/v1/dialogs/available         - 可用会话列表（带 120s 缓存）
  GET    /api/v1/dialogs/synced            - 已同步会话列表
  POST   /api/v1/dialogs/sync             - 批量开启同步
  PATCH  /api/v1/dialogs/{id}/sync-state  - 修改同步状态
  DELETE /api/v1/dialogs/{id}/sync        - 删除同步（可选 purge_index）

鉴权策略：Bearer-only（ADR-DS-001），不接受 API Key。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from tg_search.api.deps import get_app_state, get_config_store, verify_bearer_token
from tg_search.api.models import (
    ApiResponse,
    AvailableDialogItem,
    AvailableDialogsData,
    AvailableDialogsMeta,
    AvailableDialogsResponse,
    DeleteSyncResult,
    PatchSyncStateRequest,
    PatchSyncStateResult,
    SyncedDialogItem,
    SyncedDialogsData,
    SyncRequest,
    SyncResult,
)
from tg_search.api.state import AppState
from tg_search.core.logger import setup_logger

if TYPE_CHECKING:
    from tg_search.api.auth_store import AuthToken
    from tg_search.config.config_store import ConfigStore

logger = setup_logger()

router = APIRouter()

# ══════════════════════════════════════════════════════════════════════════
# Available Cache (T-P0-DS-03，缓存策略 §3.3)
# ══════════════════════════════════════════════════════════════════════════

_AVAILABLE_CACHE_TTL_SEC = 120


class _AvailableCache:
    """
    进程内 available dialogs 缓存。

    失效条件（§3.3）：
      - TTL 到期
      - POST/PATCH/DELETE /dialogs/* 成功后主动调用 invalidate()
      - 服务重启（内存对象消失）

    注意：实例绑定到 AppState.dialog_available_cache，
    不再使用模块级全局单例（Fix-4：避免跨 app 实例缓存串扰）。
    """

    def __init__(self, ttl_sec: int = _AVAILABLE_CACHE_TTL_SEC) -> None:
        self._ttl = ttl_sec
        self._items: list[AvailableDialogItem] | None = None
        self._loaded_at: float = 0.0

    def get(self) -> list[AvailableDialogItem] | None:
        if self._items is not None and (time.monotonic() - self._loaded_at) < self._ttl:
            return self._items
        return None

    def set(self, items: list[AvailableDialogItem]) -> None:
        self._items = items
        self._loaded_at = time.monotonic()

    def invalidate(self) -> None:
        self._items = None
        self._loaded_at = 0.0


def _get_cache(app_state: AppState) -> _AvailableCache:
    """从 AppState 获取缓存实例（Fix-4：绑定到 app 生命周期）"""
    cache = getattr(app_state, "dialog_available_cache", None)
    if cache is None:
        # 延迟初始化（兼容未经 lifespan 初始化的测试场景）
        cache = _AvailableCache()
        app_state.dialog_available_cache = cache  # type: ignore[attr-defined]
    return cache


# ══════════════════════════════════════════════════════════════════════════
# Exceptions (Fix-2)
# ══════════════════════════════════════════════════════════════════════════


class TelegramFetchError(Exception):
    """Telegram 拉取失败（网络异常、client 断开等）"""


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_available_from_telegram(
    app_state: AppState,
    config_store: "ConfigStore",
) -> list[AvailableDialogItem]:
    """
    从 Telegram 获取可用 dialog 列表。

    API-only 模式或无 telegram_client 时返回空列表。
    Telegram 异常时 raise TelegramFetchError（Fix-2：不再静默吞掉）。
    """
    tg = app_state.telegram_client
    if tg is None:
        logger.warning("[dialogs/available] telegram_client is None, returning empty list")
        return []

    global_config = config_store.load_config()
    synced_ids = set(global_config.sync.dialogs.keys())

    items: list[AvailableDialogItem] = []
    try:
        async for dialog in tg.iter_dialogs():
            dialog_id = dialog.id
            # 判定 telegram dialog 类型
            if getattr(dialog, "is_group", False):
                dtype = "group"
            elif getattr(dialog, "is_channel", False):
                dtype = "channel"
            else:
                dtype = "private"

            sync_state = "inactive"
            str_id = str(dialog_id)
            if str_id in synced_ids:
                sync_state = global_config.sync.dialogs[str_id].sync_state

            items.append(
                AvailableDialogItem(
                    id=dialog_id,
                    title=getattr(dialog, "title", "") or "",
                    type=dtype,
                    message_count=None,  # ADR-DS-002
                    sync_state=sync_state,
                )
            )
    except Exception as exc:
        logger.error("[dialogs/available] Failed to iter_dialogs: %s", exc)
        raise TelegramFetchError(f"Telegram 会话列表拉取失败: {exc}") from exc

    return items


def _build_dialog_lookup(
    items: list[AvailableDialogItem],
) -> dict[int, AvailableDialogItem]:
    """构建 dialog_id → AvailableDialogItem 查找表"""
    return {item.id: item for item in items}


def _collect_doc_ids_by_chat_id(index, dialog_id: int, page_size: int = 500) -> list[int]:
    """
    兼容旧版 Meili SDK：当缺少 delete_documents_by_filter 时，
    通过 filter 搜索收集文档 id，再批量删除。
    """
    filter_expr = f"chat.id = {dialog_id}"
    offset = 0
    doc_ids: list[int] = []

    while True:
        result = index.search(
            "",
            {
                "filter": filter_expr,
                "limit": page_size,
                "offset": offset,
                "attributesToRetrieve": ["id"],
            },
        )
        hits = result.get("hits", [])
        if not hits:
            break

        for hit in hits:
            doc_id = hit.get("id")
            if isinstance(doc_id, int):
                doc_ids.append(doc_id)

        if len(hits) < page_size:
            break
        offset += len(hits)

    return doc_ids


# ══════════════════════════════════════════════════════════════════════════
# T-P0-DS-03: GET /available
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/available",
    response_model=None,  # 手动构造响应（兼容非标准 meta 字段）
    summary="获取可用会话列表",
    description="返回 Telegram 可用会话列表，120s 缓存，refresh=true 强制刷新",
)
async def get_available_dialogs(
    refresh: bool = Query(default=False, description="是否强制绕过缓存"),
    limit: int = Query(default=200, ge=1, le=500, description="返回数量上限"),
    app_state: AppState = Depends(get_app_state),
    config_store: "ConfigStore" = Depends(get_config_store),
    _token: "AuthToken" = Depends(verify_bearer_token),
) -> AvailableDialogsResponse:
    """T-P0-DS-03: 获取可用会话列表"""
    cache = _get_cache(app_state)
    cached_hit = False

    try:
        if not refresh:
            cached_items = cache.get()
            if cached_items is not None:
                cached_hit = True
                items = cached_items
            else:
                items = await _fetch_available_from_telegram(app_state, config_store)
                cache.set(items)
        else:
            items = await _fetch_available_from_telegram(app_state, config_store)
            cache.set(items)
    except TelegramFetchError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "TELEGRAM_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc

    # Fix-5: limit 截断
    total = len(items)
    limited_items = items[:limit]

    return AvailableDialogsResponse(
        data=AvailableDialogsData(dialogs=limited_items, total=total),
        meta=AvailableDialogsMeta(cached=cached_hit, cache_ttl_sec=_AVAILABLE_CACHE_TTL_SEC),
    )


# ══════════════════════════════════════════════════════════════════════════
# T-P0-DS-04: GET /synced
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/synced",
    response_model=ApiResponse[SyncedDialogsData],
    summary="获取已同步会话列表",
    description="返回所有已纳入同步的会话，含状态和最后同步时间",
)
async def get_synced_dialogs(
    app_state: AppState = Depends(get_app_state),
    config_store: "ConfigStore" = Depends(get_config_store),
    _token: "AuthToken" = Depends(verify_bearer_token),
) -> ApiResponse[SyncedDialogsData]:
    """T-P0-DS-04: 获取已同步会话列表"""
    global_config = config_store.load_config()
    progress_map = app_state.progress_registry.get_all_progress()
    cache = _get_cache(app_state)

    # Fix-3: 缓存未命中时主动拉取 Telegram 以填充 title/type
    available_items = cache.get()
    if available_items is None:
        try:
            available_items = await _fetch_available_from_telegram(app_state, config_store)
            cache.set(available_items)
        except TelegramFetchError:
            # Telegram 不可用时降级为空 lookup
            logger.warning("[dialogs/synced] Telegram unavailable, title/type will be unknown")
            available_items = []

    lookup = _build_dialog_lookup(available_items)

    items: list[SyncedDialogItem] = []
    for str_id, dialog_state in global_config.sync.dialogs.items():
        try:
            dialog_id = int(str_id)
        except ValueError:
            continue

        progress = progress_map.get(dialog_id)
        is_syncing = progress is not None and progress.status == "downloading"

        # 从 lookup 推断 title/type（Fix-3：不再仅依赖可能过期的缓存）
        cached_item = lookup.get(dialog_id)
        title = cached_item.title if cached_item else ""
        dtype = cached_item.type if cached_item else "unknown"

        items.append(
            SyncedDialogItem(
                id=dialog_id,
                title=title,
                type=dtype,
                sync_state=dialog_state.sync_state,
                last_synced_at=dialog_state.last_synced_at,
                is_syncing=is_syncing,
                updated_at=dialog_state.updated_at,
            )
        )

    return ApiResponse(data=SyncedDialogsData(dialogs=items, total=len(items)))


# ══════════════════════════════════════════════════════════════════════════
# T-P0-DS-05: POST /sync
# ══════════════════════════════════════════════════════════════════════════


@router.post(
    "/sync",
    response_model=ApiResponse[SyncResult],
    summary="批量开启会话同步",
    description="将指定 dialog 加入同步。返回 accepted/ignored/not_found 三个列表",
)
async def post_sync_dialogs(
    request: SyncRequest,
    app_state: AppState = Depends(get_app_state),
    config_store: "ConfigStore" = Depends(get_config_store),
    _token: "AuthToken" = Depends(verify_bearer_token),
) -> ApiResponse[SyncResult]:
    """T-P0-DS-05: 批量开启会话同步"""
    cache = _get_cache(app_state)

    # 元素去重（保序）
    seen: set[int] = set()
    deduped: list[int] = []
    for did in request.dialog_ids:
        if did not in seen:
            seen.add(did)
            deduped.append(did)

    global_config = config_store.load_config()

    # 获取 available 列表（用于判断 not_found）
    # Fix-2: Telegram 不可用时返回 503（而非静默 200 + 全部 not_found）
    items = cache.get()
    if items is None:
        try:
            items = await _fetch_available_from_telegram(app_state, config_store)
            cache.set(items)
        except TelegramFetchError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "TELEGRAM_UNAVAILABLE",
                    "message": str(exc),
                },
            ) from exc
    available_ids: set[int] = {item.id for item in items}

    accepted: list[int] = []
    ignored: list[int] = []
    not_found: list[int] = []

    new_dialogs = dict(global_config.sync.dialogs)  # 浅拷贝

    for did in deduped:
        str_id = str(did)
        if str_id in new_dialogs:
            ignored.append(did)
        elif did in available_ids:
            accepted.append(did)
            from tg_search.config.config_store import DialogSyncState

            new_dialogs[str_id] = DialogSyncState(
                sync_state=request.default_sync_state,
                last_synced_at=None,
                updated_at=_now_iso(),
            )
        else:
            not_found.append(did)

    if accepted:
        config_store.update_section("sync", {"dialogs": {k: v.model_dump() for k, v in new_dialogs.items()}})

    # 缓存失效（§3.3：POST/PATCH/DELETE /dialogs/* 成功后清除）
    cache.invalidate()

    return ApiResponse(data=SyncResult(accepted=accepted, ignored=ignored, not_found=not_found))


# ══════════════════════════════════════════════════════════════════════════
# T-P0-DS-06: PATCH /{dialog_id}/sync-state
# ══════════════════════════════════════════════════════════════════════════


@router.patch(
    "/{dialog_id}/sync-state",
    response_model=ApiResponse[PatchSyncStateResult],
    summary="修改会话同步状态",
    description="将已同步会话的状态修改为 active 或 paused",
)
async def patch_sync_state(
    dialog_id: int,
    request: PatchSyncStateRequest,
    app_state: AppState = Depends(get_app_state),
    config_store: "ConfigStore" = Depends(get_config_store),
    _token: "AuthToken" = Depends(verify_bearer_token),
) -> ApiResponse[PatchSyncStateResult]:
    """T-P0-DS-06: 修改同步状态"""
    global_config = config_store.load_config()
    str_id = str(dialog_id)

    if str_id not in global_config.sync.dialogs:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "DIALOG_NOT_SYNCED",
                "message": f"Dialog {dialog_id} is not in the sync list.",
            },
        )

    # 更新状态
    new_dialogs = {k: v.model_dump() for k, v in global_config.sync.dialogs.items()}
    new_dialogs[str_id]["sync_state"] = request.sync_state
    new_dialogs[str_id]["updated_at"] = _now_iso()

    config_store.update_section("sync", {"dialogs": new_dialogs})
    # 缓存失效
    cache = _get_cache(app_state)
    cache.invalidate()

    updated_at = new_dialogs[str_id]["updated_at"]
    return ApiResponse(
        data=PatchSyncStateResult(
            id=dialog_id,
            sync_state=request.sync_state,
            updated_at=updated_at,
        )
    )


# ══════════════════════════════════════════════════════════════════════════
# T-P0-DS-07: DELETE /{dialog_id}/sync
# ══════════════════════════════════════════════════════════════════════════


@router.delete(
    "/{dialog_id}/sync",
    response_model=ApiResponse[DeleteSyncResult],
    summary="删除会话同步",
    description="移除同步配置，默认同时删除 MeiliSearch 历史索引",
)
async def delete_sync(
    dialog_id: int,
    purge_index: bool = Query(default=True, description="是否删除 MeiliSearch 历史索引"),
    app_state: AppState = Depends(get_app_state),
    config_store: "ConfigStore" = Depends(get_config_store),
    _token: "AuthToken" = Depends(verify_bearer_token),
) -> ApiResponse[DeleteSyncResult]:
    """T-P0-DS-07: 删除同步配置（可选 purge_index）"""
    global_config = config_store.load_config()
    str_id = str(dialog_id)

    if str_id not in global_config.sync.dialogs:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "DIALOG_NOT_SYNCED",
                "message": f"Dialog {dialog_id} is not in the sync list.",
            },
        )

    # 移除同步配置
    new_dialogs = {k: v.model_dump() for k, v in global_config.sync.dialogs.items()}
    del new_dialogs[str_id]
    config_store.update_section("sync", {"dialogs": new_dialogs})

    # 缓存失效（§3.3）
    cache = _get_cache(app_state)
    cache.invalidate()

    purge_error: Optional[str] = None

    if purge_index and app_state.meili_client is not None:
        # 删除该 chat 对应的 MeiliSearch 索引
        # 索引命名约定：telegram 或 telegram_{chat_id}（当前主索引为 "telegram"）
        index_name = "telegram"  # 如未来按 chat_id 分索引，此处改为 f"telegram_{dialog_id}"
        try:
            # 尝试删除该 dialog 下的所有文档（而非整个索引）
            meili = app_state.meili_client
            idx = meili.client.index(index_name)
            # 优先使用 delete-by-filter；若 SDK 不支持则回退为“先查 id 再删”
            delete_by_filter = getattr(idx, "delete_documents_by_filter", None)
            if callable(delete_by_filter):
                delete_by_filter(f"chat.id = {dialog_id}")
            else:
                doc_ids = _collect_doc_ids_by_chat_id(idx, dialog_id)
                if doc_ids:
                    idx.delete_documents(doc_ids)
            logger.info("[dialogs/delete] purged documents for dialog_id=%d", dialog_id)
        except Exception as exc:
            # ADR-DS-004: 索引删除失败不回滚同步配置删除
            purge_error = str(exc)
            logger.warning("[dialogs/delete] purge_index failed for dialog_id=%d: %s", dialog_id, exc)

    return ApiResponse(
        data=DeleteSyncResult(
            removed=True,
            purge_index=purge_index,
            purge_error=purge_error,
        )
    )
