import logging
import os
import sys

from loguru import logger

from core.conf import settings
from utils.request_id import clear_request_id as _clear_request_id
from utils.request_id import get_request_id
from utils.request_id import set_request_id as _set_request_id

set_request_id = _set_request_id
clear_request_id = _clear_request_id


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Skip internal logging stack frames
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ---------------- Utils ----------------
_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def _to_level(level: str) -> str:
    return str(level or "INFO").upper()


def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _format(json_mode: bool):
    # Return a callable so we can inject request_id into each record
    def _human_format(record):
        rid = get_request_id()
        return (
            f"{record['time'].strftime('%Y-%m-%d %H:%M:%S')} "
            f"{record['level'].name:<8} "
            f"{record['name']}:{record['line']} "
            f"[req={rid}] - {record['message']}\n"
        )

    def _json_format(record):
        rid = get_request_id()
        # The message is already rendered in record["message"]
        return (
            f'{{"t":"{record["time"].strftime("%Y-%m-%dT%H:%M:%S")}",'
            f'"lvl":"{record["level"].name}","loc":"{record["name"]}:{record["line"]}",'
            f'"req":"{rid}","msg":{record["message"]}}}\n'
        )

    return _json_format if json_mode else _human_format


def _quiet_noisy_libs(sqlalchemy_level: str) -> None:
    # Reduce noise from third-party loggers (especially SQLAlchemy).
    noisy = settings.NOISY_LOGGERS
    if isinstance(noisy, str):
        noisy = tuple(n.strip() for n in noisy.split(",") if n.strip())
    for name in noisy:
        lvl = sqlalchemy_level if name.startswith("sqlalchemy") else "WARNING"
        logging.getLogger(name).setLevel(_LEVEL_MAP.get(lvl.upper(), logging.WARNING))


class Logger:
    _initialized: bool = False

    def __init__(self) -> None:
        self.log_dir = settings.LOG_DIR
        self.stdout_filename = settings.LOG_STDOUT_FILENAME
        self.stderr_filename = settings.LOG_STDERR_FILENAME

        self.level = _to_level(settings.LOG_STDOUT_LEVEL)
        self.json_mode = bool(settings.LOG_JSON)
        self.enable_console = bool(settings.LOG_ENABLE_CONSOLE)
        self.file_disable = bool(settings.LOG_FILE_DISABLE)
        self.sqlalchemy_level = _to_level(settings.SQLALCHEMY_LOG_LEVEL)

        # Rotation/retention/compression similar to the original code
        self.rotation = "10 MB"
        self.retention = "15 days"
        self.compression = "tar.gz"

    def _setup_once(self) -> None:
        if Logger._initialized:
            return

        logger.remove()

        fmt_callable = _format(self.json_mode)

        if not self.file_disable:
            _ensure_dir(self.log_dir)
            stdout_path = os.path.join(self.log_dir, self.stdout_filename)
            stderr_path = os.path.join(self.log_dir, self.stderr_filename)

        if self.enable_console:
            # INFO & WARNING -> stdout
            logger.add(
                sys.stdout,
                level=self.level,
                filter=lambda r: r["level"].no < 40,  # < ERROR
                enqueue=True,
                format=fmt_callable,
            )
            # ERROR+ -> stderr
            logger.add(
                sys.stderr,
                level="ERROR",
                enqueue=True,
                format=fmt_callable,
            )

        if not self.file_disable:
            logger.add(
                stdout_path,
                level=self.level,
                rotation=self.rotation,
                retention=self.retention,
                compression=self.compression,
                enqueue=True,
                format=fmt_callable,
                filter=lambda r: r["level"].no < 40,  # <= WARNING
                backtrace=False,
                diagnose=False,
            )
            logger.add(
                stderr_path,
                level="ERROR",
                rotation=self.rotation,
                retention=self.retention,
                compression=self.compression,
                enqueue=True,
                format=fmt_callable,
                backtrace=False,  # set True only for deep debugging
                diagnose=False,
            )

        # ---- Intercept stdlib logging ----
        logging.root.handlers = [InterceptHandler()]
        logging.root.setLevel(logging.NOTSET)

        # Reduce noise from third-party loggers (especially SQLAlchemy)
        _quiet_noisy_libs(self.sqlalchemy_level)

        Logger._initialized = True

    def get_logger(self):
        self._setup_once()
        return logger


log = Logger().get_logger()
