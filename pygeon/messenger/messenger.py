from typing import Protocol
from message import Message
import os
import colorlog as cl
import logging


logger_format = "%(log_color)s%(levelname)s: %(name)s: %(message)s"


class Messenger(Protocol):
    logger: logging.Logger

    def get_logger(self):
        handler = cl.StreamHandler()
        handler.setFormatter(cl.ColoredFormatter(logger_format))

        logger = cl.getLogger(self.name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    @property
    def file_cache_path(self) -> str:
        return os.path.join(os.getcwd(), "cache")

    def generate_cache_path(self, hub_name: str) -> str:
        return os.path.join(self.file_cache_path, hub_name)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def send_message(self, m: Message, ref_id=None) -> None:
        ...

    def recall_message(self, message_id: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...

    def cache_prefix(self, id="") -> str:
        return f"{self.name}_{id}."
