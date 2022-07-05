from typing import NamedTuple


class Message(NamedTuple):
    origin: str
    origin_id: str
    author_username: str
    text: str
