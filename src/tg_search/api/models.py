"""
Pydantic 模型定义

定义所有 API 请求/响应模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

# sync_state 允许值（输入校验用）
SyncStateInput = Literal["active", "paused"]

T = TypeVar("T")


# ============ 通用响应模型 ============


class ApiResponse(BaseModel, Generic[T]):
    """通用 API 响应"""

    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int


# ============ 用户/聊天信息 ============


class UserInfo(BaseModel):
    """用户信息"""

    id: int
    username: Optional[str] = None


class ChatInfo(BaseModel):
    """聊天信息"""

    id: int
    type: str  # 'private' | 'group' | 'channel'
    title: Optional[str] = None
    username: Optional[str] = None


# ============ 消息模型 ============


class MessageModel(BaseModel):
    """消息模型"""

    id: str
    chat: ChatInfo
    date: datetime
    text: str
    from_user: Optional[UserInfo] = None
    reactions: Dict[str, int] = Field(default_factory=dict)
    reactions_scores: float = 0.0
    text_len: int = 0
    # 高亮字段（来自 MeiliSearch _formatted）
    formatted: Optional[Dict[str, Any]] = Field(default=None, description="MeiliSearch _formatted 原始对象")
    formatted_text: Optional[str] = Field(default=None, description="高亮后的文本（带 HTML 标签）")


# ============ 搜索相关 ============


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(..., min_length=1, max_length=500, description="搜索关键词")
    chat_id: Optional[int] = Field(None, description="限定聊天 ID")
    chat_type: Optional[str] = Field(None, description="聊天类型过滤")
    date_from: Optional[datetime] = Field(None, description="开始时间")
    date_to: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")


class SearchResult(BaseModel):
    """搜索结果"""

    hits: List[MessageModel]
    query: str
    processing_time_ms: int
    total_hits: int
    limit: int
    offset: int


class SearchStats(BaseModel):
    """搜索统计"""

    total_documents: int
    index_size_bytes: int
    last_update: Optional[datetime] = None
    is_indexing: bool = False


# ============ 状态相关 ============


class SystemStatus(BaseModel):
    """系统状态"""

    uptime_seconds: float
    meili_connected: bool
    bot_connected: bool
    telegram_connected: bool
    indexed_messages: int
    memory_usage_mb: float
    version: str = "0.2.0"


class DialogInfo(BaseModel):
    """对话信息"""

    id: int
    title: str
    type: str  # 'private' | 'group' | 'channel'
    message_count: int = 0
    last_synced: Optional[datetime] = None
    is_syncing: bool = False


class DialogListResponse(BaseModel):
    """对话列表响应"""

    dialogs: List[DialogInfo]
    total: int


# ============ 配置相关 ============


class ConfigModel(BaseModel):
    """配置模型"""

    white_list: List[int]
    black_list: List[int]
    owner_ids: List[int]
    batch_msg_num: int
    results_per_page: int
    max_page: int
    search_cache: bool
    cache_expire_seconds: int


class ListUpdateRequest(BaseModel):
    """列表更新请求"""

    ids: List[int] = Field(..., description="ID 列表")


class ListUpdateResponse(BaseModel):
    """列表更新响应"""

    updated_list: List[int]
    added: List[int] = Field(default_factory=list)
    removed: List[int] = Field(default_factory=list)


# ============ 控制相关 ============


class ClientControlResponse(BaseModel):
    """客户端控制响应"""

    status: str  # 'started' | 'stopped' | 'already_running' | 'already_stopped'
    message: str


# ============ WebSocket 消息 ============


class WSMessage(BaseModel):
    """WebSocket 消息"""

    type: str  # 'status' | 'progress' | 'error' | 'message'
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProgressEvent(BaseModel):
    """进度事件"""

    dialog_id: int
    dialog_title: str
    current: int
    total: int
    percentage: float
    status: str  # 'downloading' | 'completed' | 'failed'


# ============ 认证相关 ============


class AuthUserInfo(BaseModel):
    """认证用户信息"""

    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class SendCodeRequest(BaseModel):
    """发送验证码请求"""

    phone_number: str = Field(..., description="手机号（国际格式，如 +8613800138000）")
    force_sms: bool = Field(default=False, description="强制使用短信发送")


class SendCodeResponse(BaseModel):
    """发送验证码响应"""

    auth_session_id: str = Field(..., description="认证会话 ID")
    expires_in: int = Field(..., description="会话过期时间（秒）")
    phone_number_masked: str = Field(..., description="脱敏后的手机号")


class SignInRequest(BaseModel):
    """登录请求"""

    auth_session_id: str = Field(..., description="认证会话 ID")
    phone_number: str = Field(..., description="手机号")
    code: str = Field(..., description="验证码")
    password: Optional[str] = Field(default=None, description="两步验证密码（如果启用）")


class SignInResponse(BaseModel):
    """登录响应"""

    token: str = Field(..., description="Bearer Token")
    token_type: str = Field(default="Bearer", description="Token 类型")
    expires_in: int = Field(..., description="Token 过期时间（秒）")
    user: AuthUserInfo = Field(..., description="用户信息")


class MeResponse(BaseModel):
    """当前用户信息响应"""

    user: AuthUserInfo = Field(..., description="用户信息")
    token_expires_at: datetime = Field(..., description="Token 过期时间")


class LogoutResponse(BaseModel):
    """登出响应"""

    revoked: bool = Field(..., description="是否成功撤销")


# ============ Dialog Sync 相关（P0-DS）============


class AvailableDialogItem(BaseModel):
    """GET /available 中单个可用对话条目"""

    id: int
    title: str
    type: str  # group | channel | private
    message_count: Optional[int] = None  # ADR-DS-002: Telegram 无低成本接口，返回 null
    sync_state: str = "inactive"


class AvailableDialogsData(BaseModel):
    """GET /available 响应 data 字段"""

    dialogs: List[AvailableDialogItem]
    total: int


class AvailableDialogsMeta(BaseModel):
    """GET /available 响应 meta 字段"""

    cached: bool
    cache_ttl_sec: int


class AvailableDialogsResponse(BaseModel):
    """GET /available 完整响应"""

    success: bool = True
    data: AvailableDialogsData
    meta: AvailableDialogsMeta


class SyncedDialogItem(BaseModel):
    """GET /synced 中单个已同步对话条目"""

    id: int
    title: str
    type: str
    sync_state: str
    last_synced_at: Optional[str] = None
    is_syncing: bool = False
    updated_at: str


class SyncedDialogsData(BaseModel):
    """GET /synced 响应 data 字段"""

    dialogs: List[SyncedDialogItem]
    total: int


class SyncRequest(BaseModel):
    """POST /sync 请求体"""

    dialog_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="要同步的 dialog ID 列表（1-200 个，自动去重）",
    )
    default_sync_state: SyncStateInput = Field(default="active", description="初始同步状态: active | paused")


class SyncResult(BaseModel):
    """POST /sync 响应 data 字段"""

    accepted: List[int]
    ignored: List[int]
    not_found: List[int]


class PatchSyncStateRequest(BaseModel):
    """PATCH /{dialog_id}/sync-state 请求体"""

    sync_state: SyncStateInput = Field(..., description="同步状态: active | paused")


class PatchSyncStateResult(BaseModel):
    """PATCH /{dialog_id}/sync-state 响应 data 字段"""

    id: int
    sync_state: str
    updated_at: str


class DeleteSyncResult(BaseModel):
    """DELETE /{dialog_id}/sync 响应 data 字段"""

    removed: bool
    purge_index: bool
    purge_error: Optional[str] = None


# ============ Storage 相关 (P1-ST) ============


class StorageStatsData(BaseModel):
    """GET /storage/stats 响应 data"""

    total_bytes: Optional[int] = None
    index_bytes: Optional[int] = None
    media_bytes: None = None  # 当前版本固定 null
    cache_bytes: None = None  # 当前版本固定 null
    media_supported: bool = False
    cache_supported: bool = False
    notes: List[str] = Field(default_factory=list)


class AutoCleanRequest(BaseModel):
    """PATCH /storage/auto-clean 请求"""

    enabled: bool
    media_retention_days: int = 30


class AutoCleanData(BaseModel):
    """PATCH /storage/auto-clean 响应 data"""

    enabled: bool
    media_retention_days: int


class CacheCleanupData(BaseModel):
    """POST /storage/cleanup/cache 响应 data"""

    targets_cleared: List[str]
    freed_bytes: None = None


class MediaCleanupData(BaseModel):
    """POST /storage/cleanup/media 响应 data"""

    not_applicable: bool = True
    reason: str = "MEDIA_STORAGE_DISABLED"
    freed_bytes: int = 0
