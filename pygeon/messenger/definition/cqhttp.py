from typing import TypedDict, List
from typing_extensions import NotRequired
from enum import Enum


class PostType(Enum):
    META_EVENT = "meta_event"
    MESSAGE = "message"
    NOTICE = "notice"


class CQType(Enum):
    TEXT = "text"
    IMAGE = "image"
    RECORD = "record"
    VIDEO = "video"


ATTACHMENT_TYPES = [CQType.IMAGE, CQType.VIDEO, CQType.RECORD]


class MetaEventType(Enum):
    HEARTBEAT = "heartbeat"


class MessageType(Enum):
    GROUP = "group"


class Sender(TypedDict):
    nickname: str
    user_id: int


class CQData(TypedDict):
    id: str
    text: NotRequired[str]
    file: NotRequired[str]


class CQMessage(TypedDict):
    type: str
    data: CQData


class WSMessage(TypedDict):
    post_type: str
    meta_event_type: str
    message_type: str
    sender: Sender
    message_id: str
    message: List[CQMessage]
