#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MeiliSearch 处理模块

该模块提供了与 MeiliSearch 搜索引擎交互的客户端类，用于管理索引、添加文档、执行搜索等操作。
作为 Telegram 消息搜索系统的核心组件，负责所有与搜索引擎相关的操作。

主要功能：
1. 创建和管理索引
2. 添加和删除文档
3. 执行搜索查询
4. 获取索引统计信息
5. 批量删除包含特定关键词的文档
"""

import time
from typing import Optional, List, Dict, Union, Any

import meilisearch.errors
from meilisearch import Client
from meilisearch.models.index import IndexStats
from meilisearch.models.task import TaskInfo

from Meilisearch4TelegramSearchCKJ.src.config.env import INDEX_CONFIG
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

# 初始化日志记录器
logger = setup_logger()


class MeiliSearchClient:
    """
    MeiliSearch 客户端类

    该类封装了与 MeiliSearch 搜索引擎交互的所有操作，提供了创建索引、添加文档、
    执行搜索等功能。初始化时会自动连接到 MeiliSearch 服务器并创建默认索引。
    """

    def __init__(self, host: str, api_key: str) -> None:
        """
        初始化 MeiliSearch 客户端

        Args:
            host: MeiliSearch 服务器地址
            api_key: MeiliSearch API 密钥

        Raises:
            MeilisearchApiError: 当连接 MeiliSearch 服务器失败时
            Exception: 其他连接错误
        """
        try:
            self.client = Client(host, api_key)
            logger.info(f"连接到 MeiliSearch: {host}")
        except meilisearch.errors.MeilisearchApiError as e:
            logger.error(f"连接 MeiliSearch 失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接 MeiliSearch 时出错: {e}")
            raise
        # 创建默认索引
        self.create_index()

    def create_index(self, index_name: str = 'telegram', primary_key: Optional[str] = "id") -> TaskInfo:
        """
        创建 MeiliSearch 索引

        Args:
            index_name: 索引名称，默认为 'telegram'
            primary_key: 主键字段名，默认为 'id'

        Returns:
            TaskInfo: 创建索引的任务信息

        Raises:
            Exception: 创建索引失败时抛出异常
        """
        try:
            result = self.client.create_index(index_name, {'primaryKey': primary_key})
            self.client.index(index_name).update_settings(INDEX_CONFIG)
            logger.info(f"成功创建索引 '{index_name}'，TaskInfo: {result}")
            return result
        except Exception as e:
            logger.error(f"创建索引 '{index_name}' 失败: {e}")
            raise

    def add_documents(self, documents: List[Dict[str, Any]], index_name: str = 'telegram', max_retry: int = 5) -> TaskInfo:
        """
        向索引中添加文档

        支持自动重试功能，当添加失败时会进行多次尝试。

        Args:
            documents: 要添加的文档列表
            index_name: 索引名称，默认为 'telegram'
            max_retry: 最大重试次数，默认为 5

        Returns:
            TaskInfo: 添加文档的任务信息

        Raises:
            Exception: 当超过最大重试次数仍然失败时抛出异常
        """
        attempt = 0
        while attempt < max_retry:
            try:
                index = self.client.index(index_name)
                result = index.add_documents(documents)
                logger.info(f"成功添加 {len(documents)} 条文档到索引 '{index_name}'")
                return result
            except Exception as e:
                attempt += 1
                logger.error(f"添加文档到索引 '{index_name}' 失败（尝试 {attempt}/{max_retry}）：{e}")
                time.sleep(1)
        raise Exception(f"超过最大重试次数，添加文档到索引 '{index_name}' 失败。")

    def search(self, query: Union[str, None], index_name: str = 'telegram', **kwargs) -> Dict[str, Any]:
        """
        在索引中执行搜索

        Args:
            query: 搜索查询字符串，可以为 None
            index_name: 索引名称，默认为 'telegram'
            **kwargs: 传递给 MeiliSearch 的其他搜索参数

        Returns:
            Dict[str, Any]: 搜索结果字典

        Raises:
            Exception: 搜索失败时抛出异常
        """
        try:
            index = self.client.index(index_name)
            result = index.search(query, kwargs)
            logger.info(f"在索引 '{index_name}' 中执行搜索: '{query}'")
            return result
        except Exception as e:
            logger.error(f"索引 '{index_name}' 搜索失败: {e}")
            raise

    def delete_index(self, index_name: str) -> TaskInfo:
        """
        删除指定的索引

        Args:
            index_name: 要删除的索引名称

        Returns:
            TaskInfo: 删除索引的任务信息

        Raises:
            Exception: 删除索引失败时抛出异常
        """
        try:
            result = self.client.delete_index(index_name)
            logger.info(f"成功删除索引 '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"删除索引 '{index_name}' 失败: {e}")
            raise

    def get_index_stats(self, index_name: str) -> IndexStats:
        """
        获取索引的统计信息

        Args:
            index_name: 索引名称

        Returns:
            IndexStats: 索引统计信息对象

        Raises:
            Exception: 获取统计信息失败时抛出异常
        """
        try:
            index = self.client.index(index_name)
            stats = index.get_stats()
            logger.info(f"获取索引 '{index_name}' 统计信息成功")
            return stats
        except Exception as e:
            logger.error(f"获取索引 '{index_name}' 统计信息失败: {e}")
            raise

    def delete_all_contain_keyword(self, target_keyword: str, index_name: str = 'telegram') -> None:
        """
        删除所有包含指定关键词的文档

        该方法会分页搜索所有包含目标关键词的文档，并批量删除它们。

        Args:
            target_keyword: 目标关键词
            index_name: 索引名称，默认为 'telegram'

        Returns:
            None
        """
        try:
            # 获取索引对象
            index = self.client.index(index_name)

            # 分页搜索所有包含关键词的文档（循环处理所有结果）
            document_ids = []
            offset = 0
            limit = 1000  # 每次最多获取 1000 条

            while True:
                search_results = index.search(
                    target_keyword,
                    {
                        "limit": limit,
                        "offset": offset,
                        "attributesToRetrieve": ["id"],  # 仅获取文档 ID
                        "showMatchesPosition": False  # 提升性能
                    }
                )

                # 提取文档 ID
                batch_ids = [hit["id"] for hit in search_results["hits"]]
                logger.debug(f"找到包含关键词 '{target_keyword}' 的文档: {len(batch_ids)} 条")
                document_ids.extend(batch_ids)

                # 判断是否还有更多结果
                if len(batch_ids) < limit:
                    break
                offset += limit

            # 执行批量删除
            if document_ids:
                task = index.delete_documents(document_ids)
                logger.info(f"✅ 删除了 {len(document_ids)} 篇包含关键词 '{target_keyword}' 的文档 | 任务ID: {task.task_uid}")
            else:
                logger.info(f"ℹ️ 未找到包含关键词 '{target_keyword}' 的文档")

        except Exception as e:
            logger.error(f"❌ 删除包含关键词 '{target_keyword}' 的文档失败: {e}")