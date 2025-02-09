import logging


def is_allowed(chat_id: int, sync_white_list=None, sync_black_list=None) -> bool:
    """
    检查是否允许访问
    """
    if (sync_white_list and chat_id not in sync_white_list) or (chat_id in sync_black_list):
        return False

    return True


def check_is_allowed():
    """
    判断是否允许访问
    函数第一个参数需为 chat_id：Int
    :return: Function
    """

    def wrapper(func):
        async def inner(*args, **kwargs):  # 将 inner 定义为异步函数
            if is_allowed(args[0]):
                return await func(*args, **kwargs)  # 使用 await 等待 func 的执行
            else:
                logging.error("Chat id %s is not allowed" % args[0])
                return None  # 可以选择返回 None 或抛出异常

        return inner

    return wrapper
