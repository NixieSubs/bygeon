from typing import Protocol


class Messenger(Protocol):
    async def send_message(self, message: str) -> str:
        ...

    def start(self) -> None:
        ...
