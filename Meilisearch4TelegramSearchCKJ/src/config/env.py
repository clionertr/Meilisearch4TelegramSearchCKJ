import os
import ast

#### 必填 ####
## Telegram API 设置
APP_ID = os.getenv("APP_ID", "23010002")
APP_HASH = os.getenv("APP_HASH", "d1f1d1f1d1f1d1f1d1f1d1f1d1f1d1f1")
TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

## MeiliSearch 设置
MEILI_HOST = os.getenv("MEILI_HOST", "https://username-spacename.hf.space")
MEILI_PASS = os.getenv("MEILI_MASTER_KEY", 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')

#### 可选 ####
### 建议设置 ###

## BOT 设置
# 允许下载和监听的频道 ID/用户ID/群组ID
# 空列表表示下载所有消息
WHITE_LIST = ast.literal_eval(os.getenv("WHITE_LIST", "[1]"))

# 禁止下载和监听的频道 ID/用户ID/群组ID
# 开启白名单后，黑名单失效
BLACK_LIST = ast.literal_eval(os.getenv("BLACK_LIST", "[]"))

# 机器人管理员ID，设置后，只有这些ID的用户可以使用机器人
OWNER_IDS = ast.literal_eval(os.getenv("OWNER_IDS", "[]"))

## 登录设置 ##
# 设置SESSION_STRING后，将使用此字符串登录，否则将使用文件登录
SESSION_STRING = os.getenv("SESSION_STRING", None)


### 其他设置 ###

## 网络设置
IPv6 = ast.literal_eval(os.getenv("IPv6", "False"))
PROXY = os.getenv("PROXY", None)

## 性能控制
# 每次上传消息到Meilisearch的数量
BATCH_MSG_UNM = int(os.getenv("BATCH_MSG_UNM", 200))


# 不记录消息编辑的历史，True 为不记录，False 为记录
# 消息被删除后，Meilisearch 会自动删除
NOT_RECORD_MSG = ast.literal_eval(os.getenv("NOT_RECORD_MSG", "True"))

## 搜索设置
# 是否开启搜索记录缓存
# 如果开启，将会缓存搜索记录，减少 Meilisearch 的请求次数
SEARCH_CACHE = ast.literal_eval(os.getenv("SEARCH_CACHE", "True"))
# 缓存过期时间，单位秒，默认 2 小时
CACHE_EXPIRE_SECONDS = int(os.getenv("CACHE_EXPIRE_SECONDS", 60 * 60 * 2))

# 搜索结果设置
# 分页的最大页数，如果设置过大，可能造成内存过多占用（消息缓存）
MAX_PAGE = int(os.getenv("MAX_PAGE", 10))
# 每页显示的消息数量
# 默认每页显示5条消息，10 页就是搜索 50 条消息
# 如果设置过大，由于telegram限制，可能发送搜索结果失败（超链接包含字符过多）。这一限制在日常使用中不会出现，在搜索到一些长汉字时可能会出现，如长广告/垃圾信息/小说等
# 如果需要搜索大量消息，建议使用 Meilisearch 的Webui，包含高级搜索功能
RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", 5))


## 时区设置
# 控制meilisearch中的消息的时间显示
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Shanghai")

## 机器人设置
# 这里计算了一些Telegram的表情符号的情感分数，计算后会加到消息的reactions_scores字段中
TELEGRAM_REACTIONS = {
    # 正面情感 (Positive)
    '👍': 1.0,  # 基准正面
    '❤️': 1.5,  # 强烈喜爱
    '🔥': 1.4,  # 热门/精彩
    '🎉': 1.3,  # 庆祝
    '🤩': 1.4,  # 非常喜欢
    '👏': 1.2,  # 赞赏
    '♥️': 1.5,  # 喜爱
    '🥰': 1.5,

    # 中性/思考 (Neutral)
    '🤔': 0.0,  # 思考
    '🤯': 0.0,  # 震惊

    # 负面情感 (Negative)
    '👎': -1.0,  # 基准负面
    '😱': -0.5,  # 惊恐
    '😢': -0.8,  # 悲伤
    '🤬': -1.2,  # 愤怒
    '💩': -1.5,  # 强烈否定
} if os.getenv("TELEGRAM_REACTIONS") is None else ast.literal_eval(os.getenv("TELEGRAM_REACTIONS"))

## Meilisearch 索引设置
# 用于创建Meilisearch索引的配置
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
        "words",
        "date:desc",
        "typo",
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
