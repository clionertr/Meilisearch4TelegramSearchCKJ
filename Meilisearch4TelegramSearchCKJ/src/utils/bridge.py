from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient


def add_documents2meilisearch(meilisearchclient, messages):
    meilisearchclient.add_documents('telegram_messages', messages)


