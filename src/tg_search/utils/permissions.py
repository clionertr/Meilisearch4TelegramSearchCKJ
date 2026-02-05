import logging
from collections.abc import Sequence


def is_allowed(
    chat_id: int,
    sync_white_list: Sequence[int] | None = None,
    sync_black_list: Sequence[int] | None = None,
) -> bool:
    """
    检查是否允许访问
    """
    white_list = sync_white_list or ()
    black_list = sync_black_list or ()

    # 黑名单优先级更高：即使在白名单中，也会被拒绝
    if chat_id in black_list:
        return False

    # 白名单非空时，仅允许白名单内的 chat_id
    if white_list and chat_id not in white_list:
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
