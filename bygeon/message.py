from typing import NamedTuple, List
from enum import Enum

class AttachmentType(Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class Attachment(NamedTuple):
    name: str
    type: str | None
    file_path: str

class Message(NamedTuple):
    origin: str
    origin_c_id: str
    origin_m_id: str
    origin_ref_id: None | str
    author_username: str
    text: str
    attachments: List[Attachment]
