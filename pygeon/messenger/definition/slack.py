from enum import Enum
from typing import List, TypedDict, Union
from typing_extensions import NotRequired


class Endpoints:
    POST_MESSAGE = "https://slack.com/api/chat.postMessage"
    USER_INFO = "https://slack.com/api/users.info"
    CONNECTIONS_OPEN = "https://slack.com/api/apps.connections.open"
    CHAT_DELETE = "https://slack.com/api/chat.delete"


class WSMessageType(Enum):
    HELLO = "hello"
    DISCONNECT = "disconnect"
    EVENTS_API = "events_api"


class EventType(Enum):
    MESSAGE = "message"


class MessageEventSubtype(Enum):
    BOT_MESSAGE = "bot_message"
    MESSAGE_CHANGED = "message_changed"
    MESSAGE_DELETED = "message_deleted"

    # Non-existent in WebSocket event
    MESSAGE_REPLIED = "message_replied"
    OTHERS = "others"


class Attachment(TypedDict):
    pass


class MessageEvent(TypedDict):
    type: str
    subtype: NotRequired[str]
    channel: str
    user: str
    text: NotRequired[str]
    deleted_ts: NotRequired[str]

    # Use this to create a reply thread
    ts: str
    attachment: NotRequired[List[Attachment]]


class Element(TypedDict):
    type: str
    text: str


class Block(TypedDict):
    type: str
    block_id: str
    elements: List[Element]


class TeamJoinEvent:
    pass


class PinAddedEvent(TypedDict):
    pass


class UserProfileChangedEvent(TypedDict):
    pass


class Payload(TypedDict):
    token: str
    team_id: str
    event: Union[MessageEvent, PinAddedEvent, TeamJoinEvent]
    client_msg_id: str
    type: str
    text: str
    user: str
    # use ts to create new reply thread
    ts: str
    team: str
    blocks: Block


class WSMessage(TypedDict):
    envelope_id: str
    payload: Payload
    type: str
