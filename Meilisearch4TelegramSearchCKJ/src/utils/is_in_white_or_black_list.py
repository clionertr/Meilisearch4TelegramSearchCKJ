import logging
from Meilisearch4TelegramSearchCKJ.src.config.env import WHITE_LIST, BLACK_LIST


def is_allowed(chat_id: int, sync_white_list=None, sync_black_list=None) -> bool:
    """
    Check if the chat id is in the white list or not in the black list
    White list has the highest priority
    """
    sync_white_list = sync_white_list or WHITE_LIST
    sync_black_list = sync_black_list or BLACK_LIST

    if (sync_white_list and chat_id not in sync_white_list) or (chat_id in sync_black_list):
        return False

    return True


def check_is_allowed():
    def wrapper(func):
        def inner(*args, **kwargs):
            if is_allowed(args[0]):
                return func(*args, **kwargs)
            else:
                logging.error("Chat id %s is not allowed" % args[0])

        return inner

    return wrapper


