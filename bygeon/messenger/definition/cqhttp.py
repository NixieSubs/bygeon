from typing import TypedDict, List
from typing_extensions import NotRequired


class Endpoints:
    SEND_GROUP_MESSAGE = "send_group_msg"
    DELETE_MESSAGE = "delete_msg"


class PostType:
    META_EVENT = "meta_event"
    MESSAGE = "message"
    NOTICE = "notice"


class CQType:
    TEXT = "text"
    IMAGE = "image"
    RECORD = "record"
    VIDEO = "video"


ATTACHMENT_TYPES = [CQType.IMAGE, CQType.VIDEO, CQType.RECORD]


class MetaEventType:
    HEARTBEAT = "heartbeat"


class MessageType:
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
    self_id: NotRequired[int]
    user_id: NotRequired[int]
