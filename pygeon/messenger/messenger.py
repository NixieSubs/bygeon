from typing import Protocol


class Messenger(Protocol):
    def send_message(self, message: str):
        ...
