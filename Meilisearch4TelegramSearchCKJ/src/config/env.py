import os
import ast
# Telegram API 设置
APP_ID = os.getenv("APP_ID", "23010002")
APP_HASH = os.getenv("APP_HASH", "d1f1d1f1d1f1d1f1d1f1d1f1d1f1d1f1")
TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

SESSION_STRING = os.getenv("SESSION_STRING", None)

# 同步ID设置
# 同步历史消息的群组/对话/用户 ID，如果为只有一个ID，请在末尾加上逗号。如果为空，设置为()
# 开启白名单后，黑名单失效
WHITE_LIST = ast.literal_eval(os.getenv("WHITE_LIST","()"))
BLACK_LIST = ast.literal_eval(os.getenv("BLACK_LIST", "()"))

# MeiliSearch 设置
MEILI_HOST = os.getenv("MEILI_HOST", "https://username-spacename.hf.space")
MEILI_PASS = os.getenv("MEILI_MASTER_KEY", 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')

# BOT设置
OWNER_IDS = ast.literal_eval(os.getenv("OWNER_IDS","[]"))

# 网络设置
IPv6 = ast.literal_eval(os.getenv("IPv6", "False"))
PROXY = os.getenv("PROXY", None)
# 性能控制
QUEUE_2_MEILI_SLEEP = int(os.getenv("QUEUE_2_MEILI_SLEEP", 5))
BATCH_MSG_UNM = int(os.getenv("BATCH_MSG_UNM", 100))

# 不记录编辑消息的历史，True 为不记录，False 为记录
NOT_RECORD_MSG = ast.literal_eval(os.getenv("NOT_RECORD_MSG", "True"))

# 分页的最大页数，如果设置过大，可能造成内存过多占用（消息缓存）
# 默认每页显示5条消息，10 页就是 50 条消息，这个数量是可以接受的，512MB 内存足够长期单人使用
#MAX_PAGE = 10
# 是否开启消息缓存
SEARCH_CACHE = ast.literal_eval(os.getenv("SEARCH_CACHE", "True"))
RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", 5))

TIME_ZONE=os.getenv("TIME_ZONE", "Asia/Shanghai")

TELEGRAM_REACTIONS = {
    # 正面情感 (Positive)
    '👍': 1.0,    # 基准正面
    '❤️': 1.5,    # 强烈喜爱
    '🔥': 1.4,    # 热门/精彩
    '🎉': 1.3,    # 庆祝
    '🤩': 1.4,    # 非常喜欢
    '👏': 1.2,    # 赞赏
    '♥️': 1.5,    # 喜爱
    '🥰': 1.5,

    # 中性/思考 (Neutral)
    '🤔': 0.0,    # 思考
    '🤯': 0.0,    # 震惊

    # 负面情感 (Negative)
    '👎': -1.0,   # 基准负面
    '😱': -0.5,   # 惊恐
    '😢': -0.8,   # 悲伤
    '🤬': -1.2,   # 愤怒
    '💩': -1.5,   # 强烈否定
} if os.getenv("TELEGRAM_REACTIONS") is None else ast.literal_eval(os.getenv("TELEGRAM_REACTIONS"))

INDEX_CONFIG = {
              "displayedAttributes": [
                "*"
              ],
              "searchableAttributes": [
                "text",
                "id"
              ],
              "filterableAttributes": [
                "chat.type",
                "date",
                "from_user",
                "reactions_scores"
              ],
              "sortableAttributes": [
                "date",
                "id"
              ],
              "rankingRules": [
                "typo",
                "words",
                "date:desc",
                "reactions_scores:desc"
              ],
            # 这个配置可以设置广告词过滤
              "stopWords": [
                "亚太实体赌场"
              ],
              "nonSeparatorTokens": [],
              "separatorTokens": [],
              "dictionary": [],
              "synonyms": {},
              "distinctAttribute": None,
              "proximityPrecision": "byWord",
              "typoTolerance": {
                "enabled": True,
                "minWordSizeForTypos": {
                  "oneTypo": 5,
                  "twoTypos": 9
                },
                "disableOnWords": [],
                "disableOnAttributes": []
              },
              "faceting": {
                "maxValuesPerFacet": 100,
                "sortFacetValuesBy": {
                  "*": "alpha"
                }
              },
              "pagination": {
                "maxTotalHits": 500
              },
              "searchCutoffMs": None,
              "localizedAttributes": None
} if not os.getenv("INDEX_CONFIG") else ast.literal_eval(os.getenv("INDEX_CONFIG"))