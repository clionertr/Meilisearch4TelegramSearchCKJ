"""
集成测试配置模块

提供测试开关、API 地址、群组配置等。
用户可通过环境变量精细控制哪些测试执行/跳过。
"""

import json
import os
from pathlib import Path

# ============ 路径 ============

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = Path(__file__).resolve().parent
TEST_GROUPS_FILE = INTEGRATION_DIR / ".test_groups.json"

# ============ 环境 ============

TEST_API_BASE_URL = os.getenv("TEST_API_BASE_URL", "http://localhost:8000")
TEST_MEILI_HOST = os.getenv("TEST_MEILI_HOST") or os.getenv("MEILI_HOST", "http://localhost:7700")
TEST_MEILI_KEY = os.getenv("TEST_MEILI_KEY") or os.getenv("MEILI_MASTER_KEY", "")
TEST_API_KEY = os.getenv("TEST_API_KEY") or os.getenv("API_KEY")  # None means no auth

# 测试群组前缀
TEST_GROUP_PREFIX = os.getenv("TEST_GROUP_PREFIX", "__test_integ_")

# API 服务器启动超时（秒）
API_STARTUP_TIMEOUT = int(os.getenv("API_STARTUP_TIMEOUT", "30"))

# 下载等待超时（秒）
DOWNLOAD_WAIT_TIMEOUT = int(os.getenv("DOWNLOAD_WAIT_TIMEOUT", "120"))

# ============ 测试开关 ============

# 完整开关列表及默认值
_DEFAULT_SWITCHES: dict[str, bool] = {
    # Phase 1: 基础连通性
    "health_check": True,
    "root_endpoint": True,
    "system_status": True,
    # Phase 2: 配置管理
    "get_config": True,
    "config_whitelist": True,
    "config_blacklist": True,
    # Phase 3: 下载历史消息（需要真实 Telegram 连接，默认跳过）
    "download_history": True,
    # Phase 4: 搜索验证
    "search_stats": True,
    "search_basic": True,
    "search_chinese": True,
    "search_with_filters": True,
    "search_pagination": True,
    "search_highlight": True,
    # Phase 5: 客户端控制
    "client_status": True,
    "client_control": True,
    # Phase 6: 错误处理
    "error_empty_query": True,
    "error_invalid_limit": True,
}


def _parse_test_switches() -> dict[str, bool]:
    """
    解析测试开关。

    优先级: INTEGRATION_ONLY > INTEGRATION_SKIP > 默认值
    - INTEGRATION_ONLY=a,b   → 仅执行 a, b
    - INTEGRATION_SKIP=c,d   → 跳过 c, d（其他全开）
    """
    switches = _DEFAULT_SWITCHES.copy()

    only = os.getenv("INTEGRATION_ONLY", "").strip()
    skip = os.getenv("INTEGRATION_SKIP", "").strip()

    if only:
        # 先全部关闭，再只开启指定的
        names = {s.strip() for s in only.split(",") if s.strip()}
        for key in switches:
            switches[key] = key in names
    elif skip:
        names = {s.strip() for s in skip.split(",") if s.strip()}
        for name in names:
            if name in switches:
                switches[name] = False

    return switches


TEST_SWITCHES = _parse_test_switches()


def is_enabled(test_name: str) -> bool:
    """判断某项测试是否启用"""
    return TEST_SWITCHES.get(test_name, False)


# ============ 测试群组数据 ============


def load_test_groups() -> dict | None:
    """从 .test_groups.json 加载已创建的测试群组信息"""
    if TEST_GROUPS_FILE.exists():
        with open(TEST_GROUPS_FILE) as f:
            return json.load(f)
    return None


def save_test_groups(data: dict) -> None:
    """保存测试群组信息到 .test_groups.json"""
    with open(TEST_GROUPS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
