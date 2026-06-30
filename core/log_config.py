import sys
import logging
from logging.handlers import RotatingFileHandler
import structlog
from config import BASE_DIR

def simple_renderer(logger, name, event_dict):
    ts = event_dict.pop("timestamp", "")
    level = event_dict.pop("level", "").upper()
    event = event_dict.pop("event", "")
    
    # Extract any extra keys
    extras = []
    for k, v in event_dict.items():
        if k not in ("logger", "exc_info"):
            extras.append(f"{k}={v}")
    
    extra_str = f" ({', '.join(extras)})" if extras else ""
    return f"[{ts}] {level}: {event}{extra_str}"

def setup_logging():
    log_path = BASE_DIR / "ytplayer.log"
    _file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8"
    )
    _console_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[_file_handler, _console_handler]
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            simple_renderer
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
