"""Centralised logger — uses loguru; falls back to stdlib logging with loguru-style {} formatting."""
import sys
import logging
from pathlib import Path

try:
    from loguru import logger as _loguru_logger

    def get_logger(name: str = "aurumfx"):
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                   "<cyan>{name}</cyan> - {message}",
            level="DEBUG",
            colorize=True,
        )
        try:
            from config import settings
            log_path = settings.LOG_FILE
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            _loguru_logger.add(
                log_path,
                rotation="10 MB",
                retention="14 days",
                level="INFO",
                encoding="utf-8",
            )
        except Exception:
            pass
        return _loguru_logger.bind(name=name)

except ImportError:
    # Stdlib fallback: wrap Logger so {}-style calls work identically to loguru
    class _BraceLogger:
        """Thin wrapper around stdlib Logger that supports {}-style format strings."""

        def __init__(self, logger: logging.Logger):
            self._logger = logger

        def _fmt(self, msg, args):
            try:
                return str(msg).format(*args) if args else str(msg)
            except Exception:
                return str(msg)

        def debug(self, msg, *args, **kw):
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug(self._fmt(msg, args))

        def info(self, msg, *args, **kw):
            if self._logger.isEnabledFor(logging.INFO):
                self._logger.info(self._fmt(msg, args))

        def warning(self, msg, *args, **kw):
            self._logger.warning(self._fmt(msg, args))

        def error(self, msg, *args, **kw):
            self._logger.error(self._fmt(msg, args))

        def critical(self, msg, *args, **kw):
            self._logger.critical(self._fmt(msg, args))

    def get_logger(name: str = "aurumfx"):  # type: ignore[misc]
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            stream=sys.stdout,
        )
        return _BraceLogger(logging.getLogger(name))
