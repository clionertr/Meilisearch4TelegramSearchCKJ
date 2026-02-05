from tg_search.core.logger import setup_logger

logger = setup_logger()
logger.debug('This is a debug message.')
logger.info('This is an info message.')
logger.warning('This is a warning message.')
logger.error('This is an error message.')
logger.critical('This is a critical message.')
logger.log(25, 'This is an 25 message.')
