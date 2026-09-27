import json
import logging
import sys
from datetime import datetime, timezone

from app_service.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object.

    A structured format like this is what lets a log aggregator (e.g. the
    ELK stack, CloudWatch Logs Insights, or Loki) query, filter, and alert
    on fields such as request_id or level instead of grepping free text.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
