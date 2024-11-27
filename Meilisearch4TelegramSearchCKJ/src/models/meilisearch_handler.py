import logging
from typing import Dict, Any, Optional, List
from meilisearch import Client
from datetime import datetime
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
        except Exception as e:
            logger.error(f"Failed to connect to MeiliSearch: {str(e)}")
            raise

    def create_index(self, index_name: str = 'telegram', primary_key: Optional[str] = None) -> Dict:
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
            logger.info(f"Successfully created index '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {str(e)}")
            raise

    def add_documents(self, index_name: str, documents: List[Dict]) -> Dict:
        """
        添加文档

        Args:
            index_name: 索引名称
            documents: 要添加的文档列表

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
            raise

    def search(self, index_name: str, query: str, **kwargs) -> Dict:
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
            result = index.search(query, **kwargs)
            logger.info(f"Search performed in index '{index_name}' with query '{query}'")
            return result
        except Exception as e:
            logger.error(f"Search failed in index '{index_name}': {str(e)}")
            raise

    def delete_index(self, index_name: str) -> Dict:
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

    def get_index_stats(self, index_name: str) -> Dict:
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
