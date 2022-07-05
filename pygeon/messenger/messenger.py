from typing import Protocol, Tuple
from message import Message


class Messenger(Protocol):
    async def send_message(self, message: Message) -> Tuple[str, str]:
        ...

    async def reply_to_message(self, message: str, reply_to: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...
