"""
认证存储模块

提供内存存储登录会话和 Bearer Token 的功能
"""

import asyncio
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from tg_search.core.logger import setup_logger

logger = setup_logger()


# ============ 数据类定义 ============


@dataclass
class AuthSession:
    """Telegram 登录会话（验证码阶段）"""

    auth_session_id: str
    phone_number: str
    phone_code_hash: str
    telegram_session_string: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


@dataclass
class AuthToken:
    """Bearer Token 记录"""

    token: str
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_user_dict(self) -> dict:
        """返回用户信息字典"""
        return {
            "id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    def to_record(self) -> dict:
        """序列化为可持久化记录"""
        return {
            "token": self.token,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_record(cls, record: dict) -> "AuthToken":
        """从持久化记录反序列化"""
        return cls(
            token=str(record["token"]),
            user_id=int(record["user_id"]),
            username=record.get("username"),
            first_name=record.get("first_name"),
            last_name=record.get("last_name"),
            phone_number=str(record["phone_number"]),
            expires_at=datetime.fromisoformat(str(record["expires_at"])),
            created_at=datetime.fromisoformat(str(record["created_at"])),
        )


# ============ AuthStore 类 ============


class AuthStore:
    """
    认证存储

    管理登录会话和 Bearer Token 的内存存储
    支持 TTL 过期和清理

    注意：这是单进程内存存储，多 worker 模式下不共享
    """

    # 默认 TTL
    SESSION_TTL_SECONDS = 300  # 5 分钟（验证码有效期）
    TOKEN_TTL_SECONDS = 31536000  # 365 天

    def __init__(
        self,
        session_ttl: int = SESSION_TTL_SECONDS,
        token_ttl: int = TOKEN_TTL_SECONDS,
        token_store_file: Optional[str] = None,
    ):
        self._sessions: dict[str, AuthSession] = {}
        self._tokens: dict[str, AuthToken] = {}
        self._lock = asyncio.Lock()
        self._session_ttl = session_ttl
        self._token_ttl = token_ttl
        self._cleanup_task: Optional[asyncio.Task] = None
        self._token_store_file = token_store_file.strip() if token_store_file else None
        self._load_tokens_from_file()

    def _ensure_token_store_dir(self) -> None:
        if not self._token_store_file:
            return
        token_store_dir = os.path.dirname(self._token_store_file)
        if token_store_dir:
            os.makedirs(token_store_dir, exist_ok=True)

    def _persist_tokens_locked(self) -> None:
        """
        持久化 Token（调用方需持有 _lock）

        使用临时文件 + 原子替换，降低文件损坏风险。
        """
        if not self._token_store_file:
            return

        try:
            self._ensure_token_store_dir()
            payload = {
                "version": 1,
                "tokens": [token.to_record() for token in self._tokens.values()],
            }
            tmp_file = f"{self._token_store_file}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self._token_store_file)
        except Exception as e:
            logger.error(f"Failed to persist auth tokens: {type(e).__name__}: {e}")

    def _load_tokens_from_file(self) -> None:
        """启动时从文件恢复未过期 Token"""
        if not self._token_store_file:
            return

        try:
            with open(self._token_store_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except FileNotFoundError:
            return
        except Exception as e:
            logger.error(f"Failed to load auth tokens: {type(e).__name__}: {e}")
            return

        records = payload.get("tokens", []) if isinstance(payload, dict) else []
        if not isinstance(records, list):
            logger.warning("Invalid auth token file format: 'tokens' should be a list")
            return

        loaded = 0
        dropped_expired = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                token = AuthToken.from_record(record)
            except Exception as e:
                logger.warning(f"Skipped invalid token record: {type(e).__name__}: {e}")
                continue

            if token.is_expired:
                dropped_expired += 1
                continue

            self._tokens[token.token] = token
            loaded += 1

        if loaded:
            logger.info(f"Loaded {loaded} auth tokens from {self._token_store_file}")

        if dropped_expired:
            self._persist_tokens_locked()

    # ============ 会话管理 ============

    async def create_session(
        self,
        phone_number: str,
        phone_code_hash: str,
        telegram_session_string: str,
    ) -> AuthSession:
        """
        创建登录会话

        Args:
            phone_number: 手机号
            phone_code_hash: Telegram 返回的验证码哈希
            telegram_session_string: 发送验证码时的会话标识（StringSession 或会话文件路径）

        Returns:
            AuthSession 对象
        """
        async with self._lock:
            # 生成唯一会话 ID
            auth_session_id = secrets.token_urlsafe(16)

            session = AuthSession(
                auth_session_id=auth_session_id,
                phone_number=phone_number,
                phone_code_hash=phone_code_hash,
                telegram_session_string=telegram_session_string,
                expires_at=datetime.utcnow() + timedelta(seconds=self._session_ttl),
            )

            self._sessions[auth_session_id] = session
            logger.info(f"Created auth session for {phone_number[:4]}***")
            return session

    async def get_session(self, auth_session_id: str) -> Optional[AuthSession]:
        """获取登录会话"""
        async with self._lock:
            session = self._sessions.get(auth_session_id)
            if session is None:
                return None
            if session.is_expired:
                del self._sessions[auth_session_id]
                return None
            return session

    async def delete_session(self, auth_session_id: str) -> bool:
        """删除登录会话"""
        async with self._lock:
            if auth_session_id in self._sessions:
                del self._sessions[auth_session_id]
                return True
            return False

    async def increment_session_attempts(self, auth_session_id: str) -> int:
        """增加会话尝试次数，返回当前次数"""
        async with self._lock:
            session = self._sessions.get(auth_session_id)
            if session:
                session.attempts += 1
                return session.attempts
            return 0

    # ============ Token 管理 ============

    async def issue_token(
        self,
        user_id: int,
        phone_number: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> AuthToken:
        """
        签发 Bearer Token

        Args:
            user_id: Telegram 用户 ID
            phone_number: 手机号
            username: 用户名
            first_name: 名字
            last_name: 姓氏

        Returns:
            AuthToken 对象
        """
        async with self._lock:
            # 生成 token
            token = secrets.token_urlsafe(32)

            auth_token = AuthToken(
                token=token,
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                expires_at=datetime.utcnow() + timedelta(seconds=self._token_ttl),
            )

            self._tokens[token] = auth_token
            self._persist_tokens_locked()
            logger.info(f"Issued token for user {user_id}")
            return auth_token

    async def get_token(self, token: str) -> Optional[AuthToken]:
        """获取 Token 记录"""
        async with self._lock:
            auth_token = self._tokens.get(token)
            if auth_token is None:
                return None
            if auth_token.is_expired:
                del self._tokens[token]
                self._persist_tokens_locked()
                return None
            return auth_token

    async def validate_token(self, token: str) -> Optional[AuthToken]:
        """验证 Token，返回 Token 记录（如果有效）"""
        return await self.get_token(token)

    async def revoke_token(self, token: str) -> bool:
        """撤销 Token"""
        async with self._lock:
            if token in self._tokens:
                del self._tokens[token]
                self._persist_tokens_locked()
                logger.info("Token revoked")
                return True
            return False

    # ============ 清理过期数据 ============

    async def cleanup_expired(self) -> tuple[int, int]:
        """
        清理过期的会话和 Token

        Returns:
            (清理的会话数, 清理的 Token 数)
        """
        async with self._lock:
            now = datetime.utcnow()

            # 清理过期会话
            expired_sessions = [
                sid for sid, s in self._sessions.items() if s.expires_at < now
            ]
            for sid in expired_sessions:
                del self._sessions[sid]

            # 清理过期 Token
            expired_tokens = [
                t for t, tok in self._tokens.items() if tok.expires_at < now
            ]
            for t in expired_tokens:
                del self._tokens[t]

            if expired_tokens:
                self._persist_tokens_locked()

            if expired_sessions or expired_tokens:
                logger.info(
                    f"Cleaned up {len(expired_sessions)} sessions, {len(expired_tokens)} tokens"
                )

            return len(expired_sessions), len(expired_tokens)

    async def start_cleanup_task(self, interval: int = 300) -> None:
        """
        启动后台清理任务

        Args:
            interval: 清理间隔（秒），默认 5 分钟
        """
        if self._cleanup_task is not None:
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Auth cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """停止后台清理任务"""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Auth cleanup task stopped")

    # ============ 统计信息 ============

    @property
    def session_count(self) -> int:
        """当前会话数"""
        return len(self._sessions)

    @property
    def token_count(self) -> int:
        """当前 Token 数"""
        return len(self._tokens)
