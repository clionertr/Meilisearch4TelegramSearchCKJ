# import meilisearch
# search_results_cache = {}
# from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS
# from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
#
# meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
# meili.create_index()
# result = meili.search( "hello","telegram",limit=1)
# search_results_cache["helllo"] = result["hits"][0]
# results = search_results_cache["helllo"]

# print(dict1)
# print(search_results_cache)
# print(result)
# print(results)

dict1 = {"hello": [{"id": 1, "text": "hello world"}]}
print(dict1.get("hello"))
dict1["hello"].extend([{"id": 2, "text": "hello world2"}])
print(dict1.get("hello"))