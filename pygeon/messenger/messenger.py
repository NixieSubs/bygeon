from typing import Protocol
from message import Message
import os


class Messenger(Protocol):
    @property
    def file_cache_path(self) -> str:
        return os.path.join(os.getcwd(), "file_cache")

    def generate_cache_file_path(self, filename: str) -> str:
        return os.path.join(self.file_cache_path, filename)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def send_message(self, message: Message) -> None:
        ...

    def send_reply(self, message: Message, ref_id: str) -> None:
        ...

    def recall_message(self, message_id: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...
