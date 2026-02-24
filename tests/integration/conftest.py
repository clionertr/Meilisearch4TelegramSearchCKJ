"""
集成测试 pytest fixtures

提供 HTTP 客户端、测试群组信息、以及 switchable 跳过机制。
"""

import os
import sys
from functools import wraps
from typing import Generator

import httpx
import pytest

# 确保项目根目录可导入
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from tests.integration.config import (
    TEST_API_BASE_URL,
    TEST_API_KEY,
    is_enabled,
    load_test_groups,
)

# ============ 标记：集成测试整体门控 ============

# 仅当 RUN_INTEGRATION_TESTS=true 时执行
if os.getenv("RUN_INTEGRATION_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip(
        "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
        allow_module_level=True,
    )


# ============ Fixtures ============


@pytest.fixture(scope="session")
def api_client() -> Generator[httpx.Client, None, None]:
    """
    会话级 HTTP 客户端，用于调用 API。
    自动附带 API Key header（如果配置了的话）。
    """
    headers = {}
    if TEST_API_KEY:
        headers["X-API-Key"] = TEST_API_KEY

    with httpx.Client(
        base_url=TEST_API_BASE_URL,
        headers=headers,
        timeout=8.0,
    ) as client:
        yield client


@pytest.fixture(scope="session")
def test_group_info() -> dict | None:
    """
    测试群组信息。
    从 .test_groups.json 加载；如果不存在则返回 None。
    """
    return load_test_groups()


# ============ switchable 装饰器 ============


def switchable(test_name: str):
    """
    装饰器：根据 TEST_SWITCHES 决定是否跳过某个测试。

    用法::

        @switchable("search_basic")
        def test_10_search_basic(self, api_client):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_enabled(test_name):
                pytest.skip(f"Test '{test_name}' is disabled via TEST_SWITCHES")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _case_title(item: pytest.Item) -> str:
    """提取测试用例标题（优先 docstring 首行）"""
    obj = getattr(item, "obj", None)
    doc = getattr(obj, "__doc__", None)
    if isinstance(doc, str):
        for line in doc.strip().splitlines():
            title = line.strip()
            if title:
                return title
    return item.name


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """
    输出审查式结果日志：
    - 审查项名称
    - 是否通过（✅️/❌/⏭️）
    """
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call":
        return

    title = _case_title(item)
    if rep.passed:
        print(f"  {title}✅️")
    elif rep.skipped:
        print(f"  {title}⏭️")
    else:
        print(f"  {title}❌")
