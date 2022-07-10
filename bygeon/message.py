from typing import NamedTuple, List
from enum import Enum

class AttachmentType(Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class Attachment(NamedTuple):
    name: str
    type: str
    file_path: str

class Message(NamedTuple):
    origin: str
    origin_id: str
    author_username: str
    text: str
    attachments: List[Attachment]
