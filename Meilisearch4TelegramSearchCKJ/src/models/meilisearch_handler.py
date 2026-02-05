"""
MeiliSearch 客户端封装

提供对 MeiliSearch 的索引管理和文档操作，包含：
- 细化的异常处理（区分连接/超时/API错误）
- 基于 tenacity 的重试机制
"""
import time
from typing import Dict, List, Optional

import meilisearch.errors
import requests.exceptions
from meilisearch import Client
from meilisearch.models.index import IndexStats
from meilisearch.models.task import TaskInfo
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from Meilisearch4TelegramSearchCKJ.src.config.env import INDEX_CONFIG
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

logger = setup_logger()


# ============ 自定义异常 ============

class MeiliSearchConnectionError(Exception):
    """MeiliSearch 连接错误"""
    pass


class MeiliSearchTimeoutError(Exception):
    """MeiliSearch 超时错误"""
    pass


class MeiliSearchAPIError(Exception):
    """MeiliSearch API 错误"""

    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


# ============ 可重试的异常类型 ============

RETRYABLE_EXCEPTIONS = (
    MeiliSearchConnectionError,
    MeiliSearchTimeoutError,
    ConnectionError,
    TimeoutError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


def _handle_meilisearch_exception(e: Exception, operation: str, index_name: Optional[str] = None) -> None:
    """
    统一处理 MeiliSearch 异常并转换为自定义异常

    Args:
        e: 原始异常
        operation: 操作名称（用于日志）
        index_name: 索引名称（可选）

    Raises:
        MeiliSearchConnectionError: 连接错误
        MeiliSearchTimeoutError: 超时错误
        MeiliSearchAPIError: API 错误
    """
    context = f" on index '{index_name}'" if index_name else ""

    # 超时错误（需要在连接错误之前检查，因为 Timeout 可能是 OSError 的子类）
    if isinstance(e, (TimeoutError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout)):
        logger.error(f"[{operation}] Timeout error{context}: {str(e)}")
        raise MeiliSearchTimeoutError(f"MeiliSearch 请求超时: {str(e)}") from e

    # 连接错误
    if isinstance(e, (ConnectionError, requests.exceptions.ConnectionError, OSError)):
        logger.error(f"[{operation}] Connection error{context}: {str(e)}")
        raise MeiliSearchConnectionError(f"无法连接到 MeiliSearch: {str(e)}") from e

    # MeiliSearch API 错误
    if isinstance(e, meilisearch.errors.MeilisearchApiError):
        status_code = getattr(e, 'status_code', None)
        error_code = getattr(e, 'code', None)
        logger.error(f"[{operation}] API error{context}: {str(e)} (status={status_code}, code={error_code})")
        raise MeiliSearchAPIError(
            f"MeiliSearch API 错误: {str(e)}",
            status_code=status_code,
            error_code=error_code
        ) from e

    # 其他未知错误
    logger.error(f"[{operation}] Unexpected error{context}: {type(e).__name__}: {str(e)}")
    raise


class MeiliSearchClient:
    """MeiliSearch 客户端封装类"""

    def __init__(self, host: str, api_key: str, auto_create_index: bool = True):
        """
        初始化 MeiliSearch 客户端

        Args:
            host: MeiliSearch 服务器地址
            api_key: API密钥
            auto_create_index: 是否自动创建默认索引（测试时可设为 False）
        """
        self.host = host
        self._api_key = api_key

        try:
            self.client = Client(host, api_key)
            logger.info(f"Connecting to MeiliSearch at {host}")
        except meilisearch.errors.MeilisearchApiError as e:
            logger.error(f"Failed to connect to MeiliSearch: {str(e)}")
            raise MeiliSearchAPIError(f"API 错误: {str(e)}") from e
        except (ConnectionError, requests.exceptions.ConnectionError) as e:
            logger.error(f"Failed to connect to MeiliSearch: {str(e)}")
            raise MeiliSearchConnectionError(f"无法连接到 MeiliSearch: {str(e)}") from e
        except (TimeoutError, requests.exceptions.Timeout) as e:
            logger.error(f"Connection to MeiliSearch timed out: {str(e)}")
            raise MeiliSearchTimeoutError(f"连接超时: {str(e)}") from e

        if auto_create_index:
            logger.info(self.create_index())

    def create_index(self, index_name: str = 'telegram', primary_key: Optional[str] = "id") -> TaskInfo:
        """
        创建索引

        Args:
            index_name: 索引名称
            primary_key: 主键字段名

        Returns:
            TaskInfo: 创建任务信息

        Raises:
            MeiliSearchAPIError: API 错误
            MeiliSearchConnectionError: 连接错误
            MeiliSearchTimeoutError: 超时错误
        """
        try:
            result = self.client.create_index(index_name, {'primaryKey': primary_key})
            self.client.index(index_name).update_settings(INDEX_CONFIG)
            logger.info(f"Successfully send created index TaskInfo '{index_name}'")
            return result
        except meilisearch.errors.MeilisearchApiError as e:
            # 索引已存在不视为错误（检查错误码或错误消息）
            error_code = getattr(e, 'code', '')
            if 'index_already_exists' in str(e).lower() or error_code == 'index_already_exists':
                logger.info(f"Index '{index_name}' already exists, updating settings")
                self.client.index(index_name).update_settings(INDEX_CONFIG)
                return None
            _handle_meilisearch_exception(e, "create_index", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "create_index", index_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, 25),  # NOTICE level
        reraise=True,
    )
    def add_documents(self, documents: List[Dict], index_name: str = 'telegram') -> TaskInfo:
        """
        添加文档（带重试机制）

        MeiliSearch 以文档 id 进行覆盖，因此重试是幂等的。

        Args:
            documents: 要添加的文档列表
            index_name: 索引名称

        Returns:
            TaskInfo: 添加任务信息

        Raises:
            MeiliSearchAPIError: API 错误（不可重试）
            MeiliSearchConnectionError: 连接错误（已重试后仍失败）
            MeiliSearchTimeoutError: 超时错误（已重试后仍失败）
        """
        try:
            index = self.client.index(index_name)
            result = index.add_documents(documents)
            logger.info(f"Successfully added {len(documents)} documents to index '{index_name}'")
            return result
        except meilisearch.errors.MeilisearchApiError as e:
            _handle_meilisearch_exception(e, "add_documents", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "add_documents", index_name)

    def search(self, query: str | None, index_name: str = 'telegram', **kwargs) -> Dict:
        """
        搜索文档

        Args:
            query: 搜索查询
            index_name: 索引名称
            **kwargs: 其他搜索参数

        Returns:
            Dict: 搜索结果

        Raises:
            MeiliSearchAPIError: API 错误
            MeiliSearchConnectionError: 连接错误
            MeiliSearchTimeoutError: 超时错误
        """
        try:
            index = self.client.index(index_name)
            result = index.search(query, kwargs)
            logger.info(f"Search performed in index '{index_name}' with query '{query}'")
            return result
        except meilisearch.errors.MeilisearchApiError as e:
            _handle_meilisearch_exception(e, "search", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "search", index_name)

    def delete_index(self, index_name: str) -> TaskInfo:
        """
        删除索引

        Args:
            index_name: 索引名称

        Returns:
            TaskInfo: 删除任务信息

        Raises:
            MeiliSearchAPIError: API 错误
            MeiliSearchConnectionError: 连接错误
            MeiliSearchTimeoutError: 超时错误
        """
        try:
            result = self.client.delete_index(index_name)
            logger.info(f"Successfully deleted index '{index_name}'")
            return result
        except meilisearch.errors.MeilisearchApiError as e:
            _handle_meilisearch_exception(e, "delete_index", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "delete_index", index_name)

    def get_index_stats(self, index_name: str) -> IndexStats:
        """
        获取索引统计信息

        Args:
            index_name: 索引名称

        Returns:
            IndexStats: 索引统计信息

        Raises:
            MeiliSearchAPIError: API 错误
            MeiliSearchConnectionError: 连接错误
            MeiliSearchTimeoutError: 超时错误
        """
        try:
            index = self.client.index(index_name)
            stats = index.get_stats()
            logger.info(f"Successfully retrieved stats for index '{index_name}'")
            return stats
        except meilisearch.errors.MeilisearchApiError as e:
            _handle_meilisearch_exception(e, "get_index_stats", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "get_index_stats", index_name)

    def update_documents(self, documents: List[Dict], index_name: str = 'telegram') -> TaskInfo:
        """
        更新文档（带重试机制）

        Args:
            documents: 要更新的文档列表
            index_name: 索引名称

        Returns:
            TaskInfo: 更新任务信息
        """
        return self.add_documents(documents, index_name)

    def delete_documents(self, document_ids: List[str], index_name: str = 'telegram') -> TaskInfo:
        """
        删除文档

        Args:
            document_ids: 要删除的文档 ID 列表
            index_name: 索引名称

        Returns:
            TaskInfo: 删除任务信息
        """
        try:
            index = self.client.index(index_name)
            result = index.delete_documents(document_ids)
            logger.info(f"Successfully deleted {len(document_ids)} documents from index '{index_name}'")
            return result
        except meilisearch.errors.MeilisearchApiError as e:
            _handle_meilisearch_exception(e, "delete_documents", index_name)
        except Exception as e:
            _handle_meilisearch_exception(e, "delete_documents", index_name)
