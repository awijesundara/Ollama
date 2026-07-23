import logging.config
from pathlib import Path

import yaml

from src.request_context import RequestContextFilter


def configure_logging(config_path: str = "config/logging.yaml") -> None:
    path = Path(config_path)
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            logging.config.dictConfig(yaml.safe_load(stream))
    else:
        logging.basicConfig(level=logging.INFO)
    context_filter = RequestContextFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(context_filter)
