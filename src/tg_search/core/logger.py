import logging

import coloredlogs

from tg_search.config.settings import LOGGING2FILE_LEVEL, LOGGING_LEVEL


_ROOT_CONFIGURED = False


def _has_file_handler(logger: logging.Logger, filename: str) -> bool:
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None):
            if h.baseFilename.endswith(filename):
                return True
    return False


def setup_logger(name: str | None = None) -> logging.Logger:
    """
    Configure the root logger once and return a logger.

    This project imports `setup_logger()` from many modules; configuration must be idempotent
    to avoid duplicate handlers, duplicated log lines, and leaking file descriptors.
    """
    global _ROOT_CONFIGURED

    root = logging.getLogger()
    if not _ROOT_CONFIGURED:
        logging.addLevelName(25, "NOTICE")

        # File handler (WARNING+ by default, configurable via env)
        if not _has_file_handler(root, "log_file.log"):
            file_handler = logging.FileHandler("log_file.log", encoding="utf-8")
            file_handler.setLevel(LOGGING2FILE_LEVEL)
            formatter = logging.Formatter("%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

        # Colored console logs. `coloredlogs.install()` attaches a StreamHandler to the root logger.
        level_styles = dict(
            spam=dict(color="magenta", faint=True),
            debug=dict(color="cyan"),
            verbose=dict(color="blue"),
            info=dict(color="green"),
            notice=dict(color="magenta"),
            warning=dict(color="yellow"),
            success=dict(color="green", bold=True),
            error=dict(color="red"),
            critical=dict(color="red", bold=True),
        )
        coloredlogs.install(
            level=LOGGING_LEVEL,
            level_styles=level_styles,
            fmt="%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s",
            encodings="utf-8",
        )

        _ROOT_CONFIGURED = True

    return logging.getLogger(name) if name else root
