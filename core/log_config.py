import logging
from logging.handlers import RotatingFileHandler
import structlog
from config import BASE_DIR

def setup_logging():
    log_path = BASE_DIR / "ytplayer.log"
    _log_handler = RotatingFileHandler(
        log_path,
        maxBytes=1 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8"
    )
    logging.basicConfig(
        format="%(message)s",
        level=logging.WARNING,
        handlers=[_log_handler]
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
