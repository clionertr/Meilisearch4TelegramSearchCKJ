"""
认证路由模块

提供 Telegram 登录相关 API 端点
"""

import re
import os
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from tg_search.api.auth_store import AuthStore
from tg_search.api.deps import get_auth_store, verify_api_key, verify_bearer_token
from tg_search.api.models import (
    ApiResponse,
    AuthUserInfo,
    LogoutResponse,
    MeResponse,
    SendCodeRequest,
    SendCodeResponse,
    SignInRequest,
    SignInResponse,
)
from tg_search.config.settings import APP_HASH, APP_ID, PROXY, IPv6
from tg_search.core.logger import setup_logger

if TYPE_CHECKING:
    from tg_search.api.auth_store import AuthToken

logger = setup_logger()

router = APIRouter()


def mask_phone_number(phone: str) -> str:
    """
    脱敏手机号

    例如: +8613800138000 -> +86***8000
    """
    if len(phone) < 8:
        return phone[:2] + "***" + phone[-2:]
    return phone[:3] + "***" + phone[-4:]


def validate_phone_number(phone: str) -> bool:
    """验证手机号格式"""
    # 国际格式: +国家代码+号码
    pattern = r"^\+\d{7,15}$"
    return bool(re.match(pattern, phone))


@router.post("/send-code", response_model=ApiResponse[SendCodeResponse])
async def send_code(
    request_data: SendCodeRequest,
    auth_store: AuthStore = Depends(get_auth_store),
):
    """
    发送 Telegram 验证码

    步骤 1: 用户提供手机号，系统发送验证码
    """
    phone = request_data.phone_number.strip()

    # 验证手机号格式
    if not validate_phone_number(phone):
        raise HTTPException(
            status_code=400,
            detail="INVALID_PHONE",
        )

    # 创建临时 Telegram 客户端
    client = TelegramClient(
        StringSession(),
        APP_ID,
        APP_HASH,
        proxy=PROXY,
        use_ipv6=IPv6,
    )

    try:
        await client.connect()

        # 发送验证码
        sent_code = await client.send_code_request(
            phone,
            force_sms=request_data.force_sms,
        )

        # 创建会话
        session = await auth_store.create_session(
            phone_number=phone,
            phone_code_hash=sent_code.phone_code_hash,
            telegram_session_string=client.session.save(),
        )

        logger.info(f"Verification code sent to {mask_phone_number(phone)}")

        return ApiResponse(data=SendCodeResponse(
            auth_session_id=session.auth_session_id,
            expires_in=auth_store._session_ttl,
            phone_number_masked=mask_phone_number(phone),
        ))

    except PhoneNumberInvalidError:
        raise HTTPException(
            status_code=400,
            detail="INVALID_PHONE",
        )
    except FloodWaitError as e:
        raise HTTPException(
            status_code=429,
            detail=f"FLOOD_WAIT_{e.seconds}",
        )
    except Exception as e:
        logger.error(f"Send code error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail="TG_NETWORK_ERROR",
        )
    finally:
        await client.disconnect()


@router.post("/signin", response_model=ApiResponse[SignInResponse])
async def signin(
    request_data: SignInRequest,
    auth_store: AuthStore = Depends(get_auth_store),
):
    """
    验证码登录

    步骤 2: 用户提供验证码（和可选的 2FA 密码）完成登录
    """
    # 获取会话
    session = await auth_store.get_session(request_data.auth_session_id)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="SESSION_NOT_FOUND",
        )

    # 验证手机号一致
    if session.phone_number != request_data.phone_number.strip():
        raise HTTPException(
            status_code=400,
            detail="PHONE_MISMATCH",
        )

    # 增加尝试次数
    attempts = await auth_store.increment_session_attempts(request_data.auth_session_id)
    if attempts > 5:
        await auth_store.delete_session(request_data.auth_session_id)
        raise HTTPException(
            status_code=400,
            detail="TOO_MANY_ATTEMPTS",
        )

    # 使用发送验证码时的会话上下文继续登录，否则 phone_code_hash 可能失效
    client = TelegramClient(
        StringSession(session.telegram_session_string),
        APP_ID,
        APP_HASH,
        proxy=PROXY,
        use_ipv6=IPv6,
    )

    try:
        await client.connect()

        # 尝试登录
        try:
            user = await client.sign_in(
                phone=session.phone_number,
                code=request_data.code.strip(),
                phone_code_hash=session.phone_code_hash,
            )
        except SessionPasswordNeededError:
            # 需要 2FA 密码
            if not request_data.password:
                raise HTTPException(
                    status_code=400,
                    detail="PASSWORD_REQUIRED",
                )

            try:
                user = await client.sign_in(password=request_data.password)
            except PasswordHashInvalidError:
                raise HTTPException(
                    status_code=400,
                    detail="PASSWORD_INVALID",
                )

        # 登录成功，删除会话
        await auth_store.delete_session(request_data.auth_session_id)

        # 签发 Token
        auth_token = await auth_store.issue_token(
            user_id=user.id,
            phone_number=session.phone_number,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        logger.info(f"User {user.id} signed in successfully")

        return ApiResponse(data=SignInResponse(
            token=auth_token.token,
            token_type="Bearer",
            expires_in=auth_store._token_ttl,
            user=AuthUserInfo(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            ),
        ))

    except PhoneCodeInvalidError:
        raise HTTPException(
            status_code=400,
            detail="CODE_INVALID",
        )
    except PhoneCodeExpiredError:
        await auth_store.delete_session(request_data.auth_session_id)
        raise HTTPException(
            status_code=400,
            detail="CODE_EXPIRED",
        )
    except FloodWaitError as e:
        raise HTTPException(
            status_code=429,
            detail=f"FLOOD_WAIT_{e.seconds}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign in error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail="TG_NETWORK_ERROR",
        )
    finally:
        await client.disconnect()


@router.get("/me", response_model=ApiResponse[MeResponse])
async def get_me(
    auth_token: "AuthToken" = Depends(verify_bearer_token),
):
    """
    获取当前登录用户信息

    需要 Bearer Token 认证
    """
    return ApiResponse(data=MeResponse(
        user=AuthUserInfo(
            id=auth_token.user_id,
            username=auth_token.username,
            first_name=auth_token.first_name,
            last_name=auth_token.last_name,
        ),
        token_expires_at=auth_token.expires_at,
    ))


@router.post("/logout", response_model=ApiResponse[LogoutResponse])
async def logout(
    auth_store: AuthStore = Depends(get_auth_store),
    auth_token: "AuthToken" = Depends(verify_bearer_token),
):
    """
    登出（撤销 Token）

    需要 Bearer Token 认证
    """
    revoked = await auth_store.revoke_token(auth_token.token)

    logger.info(f"User {auth_token.user_id} logged out")

    return ApiResponse(data=LogoutResponse(revoked=revoked))


@router.post("/dev/issue-token", include_in_schema=False)
async def issue_dev_token(
    request: Request,
    auth_store: AuthStore = Depends(get_auth_store),
    _api_key: str | None = Depends(verify_api_key),
):
    """
    签发测试用 Bearer Token（仅集成测试）。

    仅当环境变量 ALLOW_TEST_TOKEN_ISSUE=true 时启用。
    """
    if os.getenv("ALLOW_TEST_TOKEN_ISSUE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    user_id = int(payload.get("user_id", 99999))
    phone_number = str(payload.get("phone_number", "+10000000000"))
    username = payload.get("username", "integration_tester")

    auth_token = await auth_store.issue_token(
        user_id=user_id,
        phone_number=phone_number,
        username=username,
    )

    return ApiResponse(data={
        "token": auth_token.token,
        "expires_at": auth_token.expires_at.isoformat(),
        "user_id": user_id,
    })
