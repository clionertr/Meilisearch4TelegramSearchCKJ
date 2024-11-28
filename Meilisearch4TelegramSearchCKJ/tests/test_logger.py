import logging

from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

logger = setup_logger()
logger.error("This is an error message")
logger.info("This is an info message")
logger.debug("This is a debug message")

