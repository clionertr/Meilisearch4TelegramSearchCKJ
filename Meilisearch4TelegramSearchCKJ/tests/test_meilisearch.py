import meilisearch

from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS
from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient

meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
meili.create_index()
result = meili.search("telegram", "hello",limit=1)
print(result)
