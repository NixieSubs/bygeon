from typing import Protocol
from message import Message


class Messenger(Protocol):
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


