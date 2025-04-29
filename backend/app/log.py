import logging
import json
from datetime import datetime


# Configure logging with JSON formatter
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "@timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "service": "fastapi-app",  # Service name for easy filtering in Kibana
        }
        # Add all extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "exc_info", "exc_text", "msg", "message", "levelname", "module", "created", "msecs",
                           "relativeCreated", "levelno", "pathname", "filename", "funcName", "lineno", "asctime"]:
                log_record[key] = value

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


# Configure logger
logger = logging.getLogger("fastapi_app")
logger.setLevel(logging.INFO)

# File handler for Filebeat to pick up
# file_handler = logging.FileHandler("/var/log/fastapi/app.json")  # Path where Filebeat will look
# file_handler.setFormatter(JSONFormatter())
# logger.addHandler(file_handler)

# Console handler for development
console_handler = logging.StreamHandler()
console_handler.setFormatter(JSONFormatter())
logger.addHandler(console_handler)

# _logger = logging.getLogger(__name__)
# _logger.setLevel(logging.DEBUG)
#
# _formatter = logging.Formatter(
#     "%(asctime)s - %(name)s - %(levelname)s - "
#     "[PID:%(process)d TID:%(thread)d] - "
#     "%(module)s.%(funcName)s.%(lineno)s - %(message)s"
# )
#
# _console_handler = logging.StreamHandler()
# _console_handler.setLevel(logging.DEBUG)
# _console_handler.setFormatter(_formatter)
# _logger.addHandler(_console_handler)
#
# logger = _logger
