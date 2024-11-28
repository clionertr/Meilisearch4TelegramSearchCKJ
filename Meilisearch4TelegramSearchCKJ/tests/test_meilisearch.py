import meilisearch

from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
meili.create_index()


def rename_index_copy_delete(client, old_index_uid, new_index_uid):
    """
    使用复制和删除的方式重命名索引
    """
    try:
        # 复制索引
        client.index(old_index_uid).copy(new_index_uid)

        # 验证新索引 (可选，根据您的需求进行验证)
        # 例如：检查新索引的文档数量是否与旧索引相同
        if client.index(old_index_uid).get_stats()['numberOfDocuments'] == client.index(new_index_uid).get_stats()[
            'numberOfDocuments']:
            print(f"Index '{old_index_uid}' successfully copied to '{new_index_uid}'.")
        else:
            print(f"Warning: Document count mismatch between '{old_index_uid}' and '{new_index_uid}'.")

        # 删除旧索引
        client.delete_index(old_index_uid)
        print(f"Index '{old_index_uid}' deleted.")

    except Exception as e:
        print(f"Error renaming index: {e}")


# 使用示例
old_index_name = "telegram_messages"
new_index_name = "telegram"
rename_index_copy_delete(meili.client, old_index_name, new_index_name)
