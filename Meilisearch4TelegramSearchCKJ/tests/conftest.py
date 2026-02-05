"""
Pytest 配置和公共 Fixtures

提供测试所需的 mock 对象和配置。
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 在导入项目模块前设置测试环境变量
os.environ["SKIP_CONFIG_VALIDATION"] = "true"
os.environ["ENABLE_TRACEMALLOC"] = "false"

# 设置必填的环境变量（测试用假值）
os.environ.setdefault("APP_ID", "12345678")
os.environ.setdefault("APP_HASH", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
os.environ.setdefault("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
os.environ.setdefault("MEILI_HOST", "http://localhost:7700")
os.environ.setdefault("MEILI_MASTER_KEY", "test_master_key_12345")


@pytest.fixture
def mock_meilisearch_client():
    """Mock MeiliSearch Client"""
    with patch("meilisearch.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock index
        mock_index = MagicMock()
        mock_client.index.return_value = mock_index
        mock_client.create_index.return_value = MagicMock(task_uid=1)

        # Mock index methods
        mock_index.add_documents.return_value = MagicMock(task_uid=2)
        mock_index.search.return_value = {"hits": [], "query": "", "processingTimeMs": 1}
        mock_index.get_stats.return_value = MagicMock(number_of_documents=100)
        mock_index.update_settings.return_value = MagicMock(task_uid=3)

        yield mock_client


@pytest.fixture
def mock_index():
    """Mock MeiliSearch Index"""
    mock = MagicMock()
    mock.add_documents.return_value = MagicMock(task_uid=1)
    mock.search.return_value = {"hits": [], "query": "", "processingTimeMs": 1}
    mock.get_stats.return_value = MagicMock(number_of_documents=100)
    mock.delete_documents.return_value = MagicMock(task_uid=2)
    return mock


@pytest.fixture
def sample_documents():
    """示例文档数据"""
    return [
        {
            "id": "123-1",
            "chat": {"id": 123, "type": "channel", "title": "Test Channel"},
            "date": "2024-01-01T12:00:00+08:00",
            "text": "Hello World",
            "from_user": {"id": 456, "username": "testuser"},
            "reactions": None,
            "reactions_scores": None,
            "text_len": 11,
        },
        {
            "id": "123-2",
            "chat": {"id": 123, "type": "channel", "title": "Test Channel"},
            "date": "2024-01-01T12:01:00+08:00",
            "text": "你好世界",
            "from_user": {"id": 456, "username": "testuser"},
            "reactions": {"👍": 5},
            "reactions_scores": 5.0,
            "text_len": 4,
        },
    ]


@pytest.fixture
def mock_logger():
    """Mock Logger"""
    with patch("Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler.logger") as mock:
        yield mock


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram Client"""
    mock = AsyncMock()
    mock.start = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.iter_messages = AsyncMock(return_value=iter([]))
    return mock


# Pytest 配置
def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "slow: mark test as slow running")
