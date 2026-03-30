import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """
    A production-grade logger that outputs JSON formatted logs for observability.
    """

    def __init__(self, service_name: str = "autonomous-engineer"):
        self.service_name = service_name
        self._logger = logging.getLogger(service_name)
        self._logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            self._logger.addHandler(handler)

    def _format_message(self, level: str, msg: str, extra: Dict[str, Any]) -> str:
        """Formats the log entry as a JSON string."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "service": self.service_name,
            "message": msg,
            **extra
        }
        return json.dumps(log_entry)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Logs an info level message."""
        print(self._format_message("INFO", msg, kwargs))

    def error(self, msg: str, **kwargs: Any) -> None:
        """Logs an error level message."""
        print(self._format_message("ERROR", msg, kwargs))

    def warn(self, msg: str, **kwargs: Any) -> None:
        """Logs a warning level message."""
        print(self._format_message("WARN", msg, kwargs))

if __name__ == "__main__":
    logger = StructuredLogger()
    logger.info("System initialized", version="V40", env="production")
    logger.error("Database connection failed", retry_count=3, timeout=5000)
    