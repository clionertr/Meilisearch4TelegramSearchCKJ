import ast
import os
from typing import List, Optional


class ConfigurationError(Exception):
    """配置错误异常"""
    pass


# 示例值列表，用于检测是否使用了示例配置
_EXAMPLE_VALUES = {
    "APP_ID": ["23010002", ""],
    "APP_HASH": ["d1f1d1f1d1f1d1f1d1f1d1f1d1f1d1f1", ""],
    "BOT_TOKEN": ["123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", ""],
    "MEILI_HOST": ["https://username-spacename.hf.space", ""],
    "MEILI_MASTER_KEY": ["eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", ""],
}


def _get_required_env(name: str, example_values: Optional[List[str]] = None) -> str:
    """
    获取必填环境变量，如果缺失或使用示例值则抛出异常

    Args:
        name: 环境变量名
        example_values: 示例值列表，如果配置值在此列表中则视为无效

    Returns:
        环境变量值

    Raises:
        ConfigurationError: 环境变量缺失或使用了示例值
    """
    value = os.getenv(name)

    if value is None:
        raise ConfigurationError(
            f"必填环境变量 '{name}' 未设置。请在环境变量或 .env 文件中配置。"
        )

    if example_values and value in example_values:
        raise ConfigurationError(
            f"环境变量 '{name}' 使用了示例值 '{value}'。请设置真实的配置值。"
        )

    return value


def validate_config() -> None:
    """
    验证所有必填配置项

    Raises:
        ConfigurationError: 配置验证失败
    """
    errors = []

    for var_name, example_vals in _EXAMPLE_VALUES.items():
        value = os.getenv(var_name)
        if value is None:
            errors.append(f"  - {var_name}: 未设置")
        elif value in example_vals:
            errors.append(f"  - {var_name}: 使用了示例值")

    if errors:
        raise ConfigurationError(
            "配置验证失败，以下必填项存在问题:\n" + "\n".join(errors) +
            "\n\n请检查环境变量或 .env 文件配置。"
        )


# 是否跳过配置验证（用于测试环境）
_SKIP_VALIDATION = os.getenv("SKIP_CONFIG_VALIDATION", "").lower() in ("true", "1", "yes")

if not _SKIP_VALIDATION:
    validate_config()


#### 必填 ####
## Telegram API 设置
APP_ID = os.getenv("APP_ID", "")
APP_HASH = os.getenv("APP_HASH", "")
TOKEN = os.getenv("BOT_TOKEN", "")

## MeiliSearch 设置
MEILI_HOST = os.getenv("MEILI_HOST", "")
MEILI_PASS = os.getenv("MEILI_MASTER_KEY", "")

#### 可选 ####
### 建议设置 ###

## BOT 设置
# 允许下载和监听的频道 ID/用户ID/群组ID
# 若要下载所有消息，设置为空列表 []
WHITE_LIST = ast.literal_eval(os.getenv("WHITE_LIST", "[1]"))

# 禁止下载和监听的频道 ID/用户ID/群组ID
# 开启白名单后（白名单不为空），黑名单失效
BLACK_LIST = ast.literal_eval(os.getenv("BLACK_LIST", "[]"))

# 机器人管理员ID，设置后，只有这些ID的用户可以使用机器人
OWNER_IDS = ast.literal_eval(os.getenv("OWNER_IDS", "[]"))

## 登录设置 ##
# 设置SESSION_STRING后，将使用此字符串登录，否则将使用文件登录
SESSION_STRING = os.getenv("SESSION_STRING", None)


### 其他设置 ###
## 日志设置
# 20为INFO，25为NOTICE,30为WARNING，40为ERROR
LOGGING_LEVEL = int(os.getenv("LOGGING_LEVEL", 25))
LOGGING2FILE_LEVEL = int(os.getenv("LOGGING2FILE_LEVEL", 30))

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
        "typo",
        "proximity",
        "attribute",
        "sort",
        "exactness",
        "date:desc",
        "reactions_scores:desc"
    ],
    "stopWords": [
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
} if not os.getenv("INDEX_CONFIG") else ast.literal_eval(os.getenv("INDEX_CONFIG"))
