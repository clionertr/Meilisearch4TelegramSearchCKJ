"""
MeiliSearch Handler 单元测试

覆盖 CRUD 操作和异常处理。
"""

# 确保环境变量在导入前设置
import os
from unittest.mock import MagicMock, patch

import meilisearch.errors
import pytest
import requests.exceptions

os.environ["SKIP_CONFIG_VALIDATION"] = "true"

from tg_search.core.meilisearch import (
    MeiliSearchAPIError,
    MeiliSearchClient,
    MeiliSearchConnectionError,
    MeiliSearchTimeoutError,
)


class TestMeiliSearchClientInit:
    """测试 MeiliSearchClient 初始化"""

    def test_init_success(self, mock_meilisearch_client):
        """测试成功初始化"""
        with patch(
            "tg_search.core.meilisearch.Client", return_value=mock_meilisearch_client
        ):
            client = MeiliSearchClient("http://localhost:7700", "test_key", auto_create_index=False)
            assert client.host == "http://localhost:7700"
            assert client.client is not None

    def test_init_connection_error(self):
        """测试初始化时连接错误"""
        with patch("tg_search.core.meilisearch.Client") as mock_client:
            mock_client.side_effect = ConnectionError("Connection refused")
            with pytest.raises(MeiliSearchConnectionError):
                MeiliSearchClient("http://localhost:7700", "test_key", auto_create_index=False)

    def test_init_timeout_error(self):
        """测试初始化时超时错误"""
        with patch("tg_search.core.meilisearch.Client") as mock_client:
            mock_client.side_effect = requests.exceptions.Timeout("Request timed out")
            with pytest.raises(MeiliSearchTimeoutError):
                MeiliSearchClient("http://localhost:7700", "test_key", auto_create_index=False)


class TestMeiliSearchClientCRUD:
    """测试 CRUD 操作"""

    @pytest.fixture
    def meili_client(self, mock_meilisearch_client):
        """创建测试用客户端"""
        with patch(
            "tg_search.core.meilisearch.Client", return_value=mock_meilisearch_client
        ):
            return MeiliSearchClient("http://localhost:7700", "test_key", auto_create_index=False)

    def test_create_index(self, meili_client, mock_meilisearch_client):
        """测试创建索引"""
        meili_client.create_index("test_index")
        mock_meilisearch_client.create_index.assert_called_once()

    def test_create_index_already_exists(self, meili_client, mock_meilisearch_client):
        """测试索引已存在的情况"""
        # 创建一个正确格式的 response mock，确保 str(e) 包含 index_already_exists
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"message": "Index test_index already exists", "code": "index_already_exists"}'
        error = meilisearch.errors.MeilisearchApiError("index_already_exists", mock_response)
        mock_meilisearch_client.create_index.side_effect = error
        # 索引已存在时会尝试更新设置（不应抛出异常）
        meili_client.create_index("test_index")
        # 验证尝试更新设置
        mock_meilisearch_client.index.return_value.update_settings.assert_called()

    def test_add_documents(self, meili_client, sample_documents, mock_meilisearch_client):
        """测试添加文档"""
        meili_client.add_documents(sample_documents)
        mock_meilisearch_client.index.return_value.add_documents.assert_called_once_with(sample_documents)

    def test_add_documents_empty_list(self, meili_client, mock_meilisearch_client):
        """测试添加空文档列表"""
        meili_client.add_documents([])
        mock_meilisearch_client.index.return_value.add_documents.assert_called_once_with([])

    def test_search(self, meili_client, mock_meilisearch_client):
        """测试搜索"""
        mock_meilisearch_client.index.return_value.search.return_value = {
            "hits": [{"id": "1", "text": "test"}],
            "query": "test",
            "processingTimeMs": 5,
        }
        result = meili_client.search("test query")
        assert "hits" in result
        mock_meilisearch_client.index.return_value.search.assert_called_once()

    def test_search_empty_query(self, meili_client, mock_meilisearch_client):
        """测试空查询"""
        meili_client.search(None)
        mock_meilisearch_client.index.return_value.search.assert_called_once()

    def test_delete_index(self, meili_client, mock_meilisearch_client):
        """测试删除索引"""
        meili_client.delete_index("test_index")
        mock_meilisearch_client.delete_index.assert_called_once_with("test_index")

    def test_get_index_stats(self, meili_client, mock_meilisearch_client):
        """测试获取索引统计"""
        meili_client.get_index_stats("test_index")
        mock_meilisearch_client.index.return_value.get_stats.assert_called_once()

    def test_update_documents(self, meili_client, sample_documents, mock_meilisearch_client):
        """测试更新文档（内部调用 add_documents）"""
        meili_client.update_documents(sample_documents)
        mock_meilisearch_client.index.return_value.add_documents.assert_called_once_with(sample_documents)

    def test_delete_documents(self, meili_client, mock_meilisearch_client):
        """测试删除文档"""
        doc_ids = ["123-1", "123-2"]
        meili_client.delete_documents(doc_ids)
        mock_meilisearch_client.index.return_value.delete_documents.assert_called_once_with(doc_ids)


class TestMeiliSearchExceptionHandling:
    """测试异常处理"""

    @pytest.fixture
    def meili_client(self, mock_meilisearch_client):
        """创建测试用客户端"""
        with patch(
            "tg_search.core.meilisearch.Client", return_value=mock_meilisearch_client
        ):
            return MeiliSearchClient("http://localhost:7700", "test_key", auto_create_index=False)

    def test_add_documents_connection_error(self, meili_client, sample_documents, mock_meilisearch_client):
        """测试添加文档时连接错误"""
        mock_meilisearch_client.index.return_value.add_documents.side_effect = ConnectionError("Connection lost")
        with pytest.raises(MeiliSearchConnectionError):
            meili_client.add_documents(sample_documents)

    def test_add_documents_timeout_error(self, meili_client, sample_documents, mock_meilisearch_client):
        """测试添加文档时超时错误（tenacity 会重试 3 次后抛出）"""
        mock_meilisearch_client.index.return_value.add_documents.side_effect = requests.exceptions.Timeout("Timeout")
        with pytest.raises(MeiliSearchTimeoutError):
            meili_client.add_documents(sample_documents)
        # 由于 tenacity 重试，应该调用 3 次
        assert mock_meilisearch_client.index.return_value.add_documents.call_count == 3

    def test_add_documents_api_error(self, meili_client, sample_documents, mock_meilisearch_client):
        """测试添加文档时 API 错误"""
        # 创建正确格式的 response mock
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"message": "Invalid document", "code": "invalid_document"}'
        mock_meilisearch_client.index.return_value.add_documents.side_effect = meilisearch.errors.MeilisearchApiError(
            "Invalid document", mock_response
        )
        with pytest.raises(MeiliSearchAPIError):
            meili_client.add_documents(sample_documents)

    def test_search_connection_error(self, meili_client, mock_meilisearch_client):
        """测试搜索时连接错误"""
        mock_meilisearch_client.index.return_value.search.side_effect = ConnectionError("Connection lost")
        with pytest.raises(MeiliSearchConnectionError):
            meili_client.search("test")


class TestMeiliSearchAPIErrorDetails:
    """测试自定义异常的详细信息"""

    def test_api_error_with_status_code(self):
        """测试 API 错误包含状态码"""
        error = MeiliSearchAPIError("Test error", status_code=404, error_code="index_not_found")
        assert error.status_code == 404
        assert error.error_code == "index_not_found"
        assert "Test error" in str(error)

    def test_api_error_without_status_code(self):
        """测试 API 错误不含状态码"""
        error = MeiliSearchAPIError("Test error")
        assert error.status_code is None
        assert error.error_code is None
