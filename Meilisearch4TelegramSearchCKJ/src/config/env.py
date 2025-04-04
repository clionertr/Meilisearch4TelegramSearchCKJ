from Meilisearch4TelegramSearchCKJ.src.config.config import settings
from dynaconf import Dynaconf
###
###
### 你可以直接修改此文件，也可以使用settings.toml文件进行配置
###
###
#### 必填 ####
## Telegram API 设置
APP_ID = settings.required.app_id
APP_HASH = settings.required.app_hash
BOT_TOKEN = settings.required.bot_token

## MeiliSearch 设置
MEILI_HOST = settings.required.meili_host
MEILI_PASS = settings.required.meili_key

#### 可选 ####
### 建议设置 ###

## BOT 设置
# 允许下载和监听的频道 ID/用户ID/群组ID
# 若要下载所有消息，设置为空列表 []
WHITE_LIST = settings.bot.white_list

# 禁止下载和监听的频道 ID/用户ID/群组ID
# 开启白名单后（白名单不为空），黑名单失效
BLACK_LIST = settings.bot.black_list

# 机器人管理员ID，设置后，只有这些ID的用户可以使用机器人
OWNER_IDS = settings.bot.owner_ids

## 登录设置 ##
# 设置SESSION_STRING后，将使用此字符串登录，否则将使用文件登录
SESSION_STRING = settings.login.session_string or None


### 其他设置 ###
## 日志设置
# 20为INFO，25为NOTICE,30为WARNING，40为ERROR
LOGGING_LEVEL = settings.logging.level
LOGGING2FILE_LEVEL = settings.logging.file_level

## 网络设置
IPv6 = settings.network.ipv6
PROXY = settings.network.proxy or None

## 性能控制
# 每次上传消息到Meilisearch的数量
BATCH_MSG_NUM = settings.performance.batch_msg_num


# 不记录消息编辑的历史，True 为不记录，False 为记录
# 消息被删除后，Meilisearch 会自动删除
NOT_RECORD_MSG = settings.performance.not_record_msg

## 搜索设置
# 是否开启搜索记录缓存
# 如果开启，将会缓存搜索记录，减少 Meilisearch 的请求次数
SEARCH_CACHE = settings.search.search_cache_enabled
# 缓存过期时间，单位秒，默认 2 小时
CACHE_EXPIRE_SECONDS = settings.search.cache_expire_seconds

# 搜索结果设置
# 分页的最大页数，如果设置过大，可能造成内存过多占用（消息缓存）
MAX_PAGE = settings.search.max_page
# 每页显示的消息数量
# 默认每页显示5条消息，10 页就是搜索 50 条消息
# 如果设置过大，由于telegram限制，可能发送搜索结果失败（超链接包含字符过多）。这一限制在日常使用中不会出现，在搜索到一些长汉字时可能会出现，如长广告/垃圾信息/小说等
# 如果需要搜索大量消息，建议使用 Meilisearch 的Webui，包含高级搜索功能
RESULTS_PER_PAGE = settings.search.results_per_page


## 时区设置
# 控制meilisearch中的消息的时间显示
TIME_ZONE = settings.timezone.time_zone

## 机器人设置
# 这里计算了一些Telegram的表情符号的情感分数，计算后会加到消息的reactions_scores字段中
TELEGRAM_REACTIONS = settings.telegram_reactions

## Meilisearch 索引设置
# 用于创建Meilisearch索引的配置
INDEX_CONFIG = settings.meilisearch_index_config

BANNED_WORDS = settings.bot.banned_words
BANNED_IDS = settings.bot.banned_ids


def reload_config():
    """
    重新加载配置文件

    当settings.toml文件被修改后，调用此函数可以重新加载配置
    使配置变更生效
    """
    global WHITE_LIST, BLACK_LIST, OWNER_IDS, SESSION_STRING, LOGGING_LEVEL, LOGGING2FILE_LEVEL
    global IPv6, PROXY, BATCH_MSG_NUM, NOT_RECORD_MSG, SEARCH_CACHE, CACHE_EXPIRE_SECONDS
    global MAX_PAGE, RESULTS_PER_PAGE, TIME_ZONE, TELEGRAM_REACTIONS, INDEX_CONFIG
    global BANNED_WORDS, BANNED_IDS

    # 重新加载配置文件
    new_settings = Dynaconf(
        envvar_prefix="MTS",
        settings_files=['settings.toml', '.secrets.toml'],
        merge_enabled=True,
    )

    # 更新配置变量
    WHITE_LIST = new_settings.bot.white_list
    BLACK_LIST = new_settings.bot.black_list
    OWNER_IDS = new_settings.bot.owner_ids
    SESSION_STRING = new_settings.login.session_string or None
    LOGGING_LEVEL = new_settings.logging.level
    LOGGING2FILE_LEVEL = new_settings.logging.file_level
    IPv6 = new_settings.network.ipv6
    PROXY = new_settings.network.proxy or None
    BATCH_MSG_NUM = new_settings.performance.batch_msg_num
    NOT_RECORD_MSG = new_settings.performance.not_record_msg
    SEARCH_CACHE = new_settings.search.search_cache_enabled
    CACHE_EXPIRE_SECONDS = new_settings.search.cache_expire_seconds
    MAX_PAGE = new_settings.search.max_page
    RESULTS_PER_PAGE = new_settings.search.results_per_page
    TIME_ZONE = new_settings.timezone.time_zone
    TELEGRAM_REACTIONS = new_settings.telegram_reactions
    INDEX_CONFIG = new_settings.meilisearch_index_config
    BANNED_WORDS = new_settings.bot.banned_words
    BANNED_IDS = new_settings.bot.banned_ids
