def is_allowed(chat_id: int, sync_white_list=None, sync_black_list=None) -> bool:
    """
    检查是否允许访问
    """
    if (sync_white_list and chat_id not in sync_white_list) or (chat_id in sync_black_list):
        return False

    return True


