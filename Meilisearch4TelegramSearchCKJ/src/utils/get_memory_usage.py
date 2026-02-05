import tracemalloc


def get_memory_usage(logger):
        """获取内存使用情况"""
        current, peak = tracemalloc.get_traced_memory()
        logger.info(f"Current memory usage: {current / 10 ** 6}MB")
        logger.info(f"Peak memory usage: {peak / 10 ** 6}MB")
        return current, peak
