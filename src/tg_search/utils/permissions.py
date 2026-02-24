import logging
from collections.abc import Sequence


def _normalize_chat_id(chat_id: int) -> set[int]:
    """
    归一化 chat_id 的常见表示形式。

    Telegram 在不同上下文里可能出现：
    - 用户/群组: 123 / -123
    - 频道/超级群: -100123... / 100123... / 123...
    """
    raw = int(chat_id)
    abs_id = abs(raw)
    forms = {raw, abs_id, -abs_id}

    s = str(abs_id)
    if s.startswith("100") and len(s) > 3:
        base = int(s[3:])
        forms.update({base, -base})

    return forms


def _id_matches(chat_id: int, candidate_id: int) -> bool:
    return bool(_normalize_chat_id(chat_id) & _normalize_chat_id(int(candidate_id)))


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
    if any(_id_matches(chat_id, blocked_id) for blocked_id in black_list):
        return False

    # 白名单非空时，仅允许白名单内的 chat_id
    if white_list and not any(_id_matches(chat_id, allowed_id) for allowed_id in white_list):
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
