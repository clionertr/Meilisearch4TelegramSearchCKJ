import time
from typing import Optional, List, Dict

import meilisearch.errors
from meilisearch import Client
from meilisearch.models.index import IndexStats
from meilisearch.models.task import TaskInfo

from Meilisearch4TelegramSearchCKJ.src.config.env import INDEX_CONFIG
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

logger = setup_logger()


class MeiliSearchClient:
    def __init__(self, host: str, api_key: str):
        """
        初始化 MeiliSearch 客户端

        Args:
            host: MeiliSearch 服务器地址
            api_key: API密钥
        """
        # 配置日志

        # 初始化 MeiliSearch 客户端
        try:
            self.client = Client(host, api_key)
            logger.info(f"Successfully connected to MeiliSearch at {host}")
        except meilisearch.errors.MeilisearchApiError as e:
            logger.error(f"Failed to connect to MeiliSearch: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to MeiliSearch: {str(e)}")
            raise
        logger.info(self.create_index())

    def create_index(self, index_name: str = 'telegram', primary_key: Optional[str] = "id") -> TaskInfo:
        """
        创建索引

        Args:
            index_name: 索引名称
            primary_key: 主键字段名

        Returns:
            Dict: 创建结果
        """


        try:
            result = self.client.create_index(index_name, {'primaryKey': primary_key})
            self.client.index(index_name).update_settings(INDEX_CONFIG)
            logger.info(f"Successfully send created index TaskInfo '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {str(e)}")
            raise

    def add_documents(self, documents: List[Dict], index_name: str = 'telegram',max_retry=5) -> TaskInfo:
        """
        添加文档

        Args:
            index_name: 索引名称
            documents: 要添加的文档列表
            max_retry: 最大重试次数

        Returns:
            Dict: 添加结果
        """
        try:
            index = self.client.index(index_name)
            result = index.add_documents(documents)
            logger.info(f"Successfully added {len(documents)} documents to index '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to add documents to index '{index_name}': {str(e)}")
            self.add_documents(documents, index_name, max_retry - 1) if max_retry > 0 else None
            time.sleep(1)
            raise

    def search(self, query: str|None,index_name: str ='telegram', **kwargs) -> Dict:
        """
        搜索文档

        Args:
            index_name: 索引名称
            query: 搜索查询
            **kwargs: 其他搜索参数

        Returns:
            Dict: 搜索结果
        """
        try:
            index = self.client.index(index_name)
            result = index.search(query, kwargs)
            logger.info(f"Search performed in index '{index_name}' with query '{query}'")
            return result
        except Exception as e:
            logger.error(f"Search failed in index '{index_name}': {str(e)}")
            raise

    def delete_index(self, index_name: str) -> TaskInfo:
        """
        删除索引

        Args:
            index_name: 索引名称

        Returns:
            Dict: 删除结果
        """
        try:
            result = self.client.delete_index(index_name)
            logger.info(f"Successfully deleted index '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to delete index '{index_name}': {str(e)}")
            raise

    def get_index_stats(self, index_name: str) -> IndexStats:
        """
        获取索引统计信息

        Args:
            index_name: 索引名称

        Returns:
            Dict: 索引统计信息
        """
        try:
            index = self.client.index(index_name)
            stats = index.get_stats()
            logger.info(f"Successfully retrieved stats for index '{index_name}'")
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats for index '{index_name}': {str(e)}")
            raise
