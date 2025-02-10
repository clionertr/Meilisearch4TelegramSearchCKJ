# meilisearch_handler.py
import time
from typing import Optional, List, Dict

import meilisearch.errors
from meilisearch import Client
from meilisearch.models.index import IndexStats
from meilisearch.models.task import TaskInfo

from Meilisearch4TelegramSearchCKJ.src.config.env import INDEX_CONFIG, BANNED_WORDS
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

logger = setup_logger()


class MeiliSearchClient:
    def __init__(self, host: str, api_key: str):
        try:
            self.client = Client(host, api_key)
            logger.info(f"连接到 MeiliSearch: {host}")
        except meilisearch.errors.MeilisearchApiError as e:
            logger.error(f"连接 MeiliSearch 失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接 MeiliSearch 时出错: {e}")
            raise
        # 创建索引
        self.create_index()

    def create_index(self, index_name: str = 'telegram', primary_key: Optional[str] = "id") -> TaskInfo:
        try:
            result = self.client.create_index(index_name, {'primaryKey': primary_key})
            self.client.index(index_name).update_settings(INDEX_CONFIG)
            logger.info(f"成功创建索引 '{index_name}'，TaskInfo: {result}")
            return result
        except Exception as e:
            logger.error(f"创建索引 '{index_name}' 失败: {e}")
            raise

    def add_documents(self, documents: List[Dict], index_name: str = 'telegram', max_retry=5) -> TaskInfo:
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

    def search(self, query: str | None, index_name: str = 'telegram', **kwargs) -> Dict:
        try:
            index = self.client.index(index_name)
            result = index.search(query, kwargs)
            logger.info(f"在索引 '{index_name}' 中执行搜索: '{query}'")
            return result
        except Exception as e:
            logger.error(f"索引 '{index_name}' 搜索失败: {e}")
            raise

    def delete_index(self, index_name: str) -> TaskInfo:
        try:
            result = self.client.delete_index(index_name)
            logger.info(f"成功删除索引 '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"删除索引 '{index_name}' 失败: {e}")
            raise

    def get_index_stats(self, index_name: str) -> IndexStats:
        try:
            index = self.client.index(index_name)
            stats = index.get_stats()
            logger.info(f"获取索引 '{index_name}' 统计信息成功")
            return stats
        except Exception as e:
            logger.error(f"获取索引 '{index_name}' 统计信息失败: {e}")
            raise

    def delete_all_contain_keyword(self, target_keyword: str, index_name: str = 'telegram'):
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
                logger.debug(search_results["hits"])
                document_ids.extend(batch_ids)

                # 判断是否还有更多结果
                if len(batch_ids) < limit:
                    break
                offset += limit

            # 执行批量删除
            if document_ids:
                task = index.delete_documents(document_ids)
                logger.info(f"✅ 删除了 {len(document_ids)} 篇包含关键词{target_keyword}的文档 | 任务ID: {task.task_uid}")
            else:
                logger.info("ℹ️ 未找到包含关键词的文档")

        except Exception as e:
            logger.info(f"❌ 操作失败: {e}")