"""
环境管理器

负责启停 MeiliSearch 和 API 服务器进程。
可通过 --no-env 跳过自动管理（适合已有环境在跑的场景）。
"""

import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

from tests.integration.config import (
    API_STARTUP_TIMEOUT,
    PROJECT_ROOT,
    TEST_API_BASE_URL,
    TEST_MEILI_HOST,
    TEST_MEILI_KEY,
)

# 子进程句柄
_api_process: subprocess.Popen | None = None
_meili_process: subprocess.Popen | None = None


def _print(msg: str) -> None:
    print(f"[env_manager] {msg}", flush=True)


# ============ MeiliSearch ============


def check_meilisearch() -> bool:
    """检测 MeiliSearch 是否可达"""
    try:
        r = httpx.get(f"{TEST_MEILI_HOST}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def ensure_meilisearch() -> None:
    """
    确保 MeiliSearch 可用。
    如果不可用则尝试用 docker 启动一个临时实例。
    """
    global _meili_process

    if check_meilisearch():
        _print(f"MeiliSearch already running at {TEST_MEILI_HOST}")
        return

    _print("MeiliSearch not reachable, attempting to start via docker...")

    # 从 TEST_MEILI_HOST 提取端口
    from urllib.parse import urlparse
    parsed = urlparse(TEST_MEILI_HOST)
    port = parsed.port or 7700

    cmd = [
        "docker", "run", "--rm", "-d",
        "--name", "meili_integration_test",
        "-p", f"{port}:7700",
        "-e", f"MEILI_MASTER_KEY={TEST_MEILI_KEY}",
        "getmeili/meilisearch:latest",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            _print(f"Failed to start MeiliSearch via docker: {result.stderr}")
            _print("Please start MeiliSearch manually and retry.")
            sys.exit(1)
    except FileNotFoundError:
        _print("docker not found. Please start MeiliSearch manually.")
        sys.exit(1)

    # 等待 MeiliSearch 就绪
    for i in range(30):
        if check_meilisearch():
            _print("MeiliSearch started successfully via docker")
            return
        time.sleep(1)

    _print("MeiliSearch failed to become ready in 30s")
    sys.exit(1)


# ============ API Server ============


def check_api_server() -> bool:
    """检测 API 服务器是否可达"""
    try:
        r = httpx.get(f"{TEST_API_BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def start_api_server() -> None:
    """以子进程启动 API 服务器"""
    global _api_process

    if check_api_server():
        _print(f"API server already running at {TEST_API_BASE_URL}")
        return

    _print("Starting API server...")

    env = os.environ.copy()
    env["SKIP_CONFIG_VALIDATION"] = "true"
    # API_ONLY=false: 让 /api/v1/client/start 能正常工作（不会返回 400）
    env["API_ONLY"] = "false"
    # DISABLE_BOT_AUTOSTART=true: 不在启动时自动连接 Telegram（避免接口阻塞超时）
    # 由测试用例当需手动调用 /api/v1/client/start 触发
    env["DISABLE_BOT_AUTOSTART"] = "true"
    env.setdefault("DISABLE_AUTH_CLEANUP_TASK", "true")

    # 从 TEST_API_BASE_URL 提取 host 和 port
    from urllib.parse import urlparse
    parsed = urlparse(TEST_API_BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 8000)

    _api_process = subprocess.Popen(
        [
            sys.executable, "-m", "tg_search",
            "--mode", "all",
            "--host", host,
            "--port", port,
            "--skip-validation",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # 等待就绪
    deadline = time.time() + API_STARTUP_TIMEOUT
    while time.time() < deadline:
        if check_api_server():
            _print(f"API server started (pid={_api_process.pid})")
            return
        # 检查进程是否已退出
        if _api_process.poll() is not None:
            stdout = _api_process.stdout.read().decode() if _api_process.stdout else ""
            _print(f"API server process exited unexpectedly:\n{stdout}")
            sys.exit(1)
        time.sleep(0.5)

    _print(f"API server failed to become ready in {API_STARTUP_TIMEOUT}s")
    stop_api_server()
    sys.exit(1)


def stop_api_server() -> None:
    """停止 API 服务器"""
    global _api_process
    if _api_process is not None and _api_process.poll() is None:
        _print(f"Stopping API server (pid={_api_process.pid})...")
        _api_process.send_signal(signal.SIGTERM)
        try:
            _api_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _api_process.kill()
        _api_process = None


def stop_docker_meili() -> None:
    """停止通过 docker 启动的 MeiliSearch"""
    try:
        subprocess.run(
            ["docker", "stop", "meili_integration_test"],
            capture_output=True, timeout=15,
        )
        _print("Stopped docker MeiliSearch container")
    except Exception:
        pass


# ============ Orchestration ============


def start_all() -> None:
    """启动所有服务"""
    ensure_meilisearch()
    start_api_server()


def stop_all() -> None:
    """停止所有服务"""
    stop_api_server()
    # Note: 不自动停 MeiliSearch（可能是用户手动启动的）


def wait_for_ready() -> bool:
    """等待 API 和 MeiliSearch 都就绪"""
    return check_meilisearch() and check_api_server()


# 注册退出时清理
atexit.register(stop_all)
