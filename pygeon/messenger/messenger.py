from typing import Protocol, Tuple
from message import Message


class Messenger(Protocol):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    async def send_message(self, message: Message) -> Tuple[Message, str, str]:
        ...

    async def reply_to_message(self, message: str, reply_to: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...
