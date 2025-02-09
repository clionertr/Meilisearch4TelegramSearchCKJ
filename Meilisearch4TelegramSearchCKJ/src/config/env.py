from Meilisearch4TelegramSearchCKJ.src.config.config import settings
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
