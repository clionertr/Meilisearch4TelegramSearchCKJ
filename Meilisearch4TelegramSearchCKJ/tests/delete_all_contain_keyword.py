import os

from meilisearch import Client
from meilisearch.errors import MeilisearchApiError

# 配置 Meilisearch 客户端
client = Client(
    os.getenv("MEILI_HOST", "http://127.0.0.1:7700"),  # Meilisearch 服务器地址
    os.getenv("MEILI_MASTER_KEY", "masterkey")  # 替换为你的 API 密钥
)

index_name = "telegram"  # 替换为你的索引名称
target_keyword_list = ['#更新日报', 'YT体育', '酒馆AI', '翻墙', "画境流媒体神器", "经典传奇", "账号合租",
                       "草榴"]  # 需要删除的关键词列表
target_keyword_list = [f'"{keyword}"' for keyword in target_keyword_list]


def delete_all_contain_keyword(index_name: str, target_keyword: str):
    try:
        # 获取索引对象
        index = client.index(index_name)

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
            print(search_results["hits"])
            document_ids.extend(batch_ids)

            # 判断是否还有更多结果
            if len(batch_ids) < limit:
                break
            offset += limit

        # 执行批量删除
        if document_ids:
            task = index.delete_documents(document_ids)
            print(f"✅ 删除了 {len(document_ids)} 篇包含关键词{target_keyword}的文档 | 任务ID: {task.task_uid}")
        else:
            print("ℹ️ 未找到包含关键词的文档")

    except MeilisearchApiError as e:
        print(f"❌ 操作失败: {e.message}")


for target_keyword in target_keyword_list:
    delete_all_contain_keyword(index_name, target_keyword)
