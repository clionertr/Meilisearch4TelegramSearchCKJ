import coloredlogs
import logging


def setup_logger():
    # 创建文件handler
    file_handler = logging.FileHandler('log_file.log', encoding='utf-8')

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # 安装coloredlogs并设置级别
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
    coloredlogs.install(level="INFO", level_styles=level_styles,
                        fmt='%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s',
                        encodings='utf-8')

    # 获取logger 并添加文件handler
    logger = logging.getLogger()
    #logger.addHandler(file_handler)

    # 移除默认StreamHandler
    logger.removeHandler(logging.StreamHandler())

    return logger
