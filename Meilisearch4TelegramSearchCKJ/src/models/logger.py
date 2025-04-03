#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志模块

该模块提供日志记录功能，支持彩色终端输出和文件记录。
使用coloredlogs库实现彩色日志，并配置了自定义的日志级别和格式。
"""

# 标准库导入
import logging

# 第三方库导入
import coloredlogs

# 本地模块导入
from Meilisearch4TelegramSearchCKJ.src.config.env import LOGGING_LEVEL, LOGGING2FILE_LEVEL


def setup_logger():
    """
    配置并返回日志记录器

    配置日志系统，包括：
    1. 创建文件处理器，将日志写入文件
    2. 设置彩色终端输出
    3. 自定义日志格式和级别

    返回:
        logging.Logger: 配置好的日志记录器对象
    """
    # 创建文件处理器，用于将日志写入文件
    file_handler = logging.FileHandler('log_file.log', encoding='utf-8')
    file_handler.setLevel(LOGGING2FILE_LEVEL)  # 设置文件日志级别

    # 设置日志格式（时间、模块、函数、级别、消息）
    log_format = '%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    # 添加自定义日志级别 NOTICE (级别25，介于INFO和WARNING之间)
    logging.addLevelName(25, "NOTICE")

    # 配置彩色日志样式
    level_styles = dict(
        spam=dict(color='magenta', faint=True),
        debug=dict(color='cyan'),
        verbose=dict(color='blue'),
        info=dict(color='green'),
        notice=dict(color='magenta'),
        warning=dict(color='yellow'),
        success=dict(color='green', bold=True),
        error=dict(color='red'),
        critical=dict(color='red', bold=True),
    )

    # 安装彩色日志并设置终端输出级别和格式
    coloredlogs.install(
        level=LOGGING_LEVEL,
        level_styles=level_styles,
        fmt=log_format,
        encoding='utf-8'
    )

    # 获取根日志记录器并添加文件处理器
    logger = logging.getLogger()
    logger.addHandler(file_handler)

    # 移除默认的流处理器，避免日志重复输出
    logger.removeHandler(logging.StreamHandler())

    return logger
