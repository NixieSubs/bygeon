from typing import List, TypedDict
from typing_extensions import NotRequired


class Endpoints:
    POST_MESSAGE = "https://slack.com/api/chat.postMessage"
    USERS_INFO = "https://slack.com/api/users.info"
    CONNECTIONS_OPEN = "https://slack.com/api/apps.connections.open"
    CHAT_DELETE = "https://slack.com/api/chat.delete"
    BOTS_INFO = "https://slack.com/api/bots.info"
    AUTH_TEST = "https://slack.com/api/auth.test"
    FILE_UPLOAD = "https://slack.com/api/files.upload"
    CHAT_UPDATE = "https://slack.com/api/chat.update"


class WSMessageType:
    HELLO = "hello"
    DISCONNECT = "disconnect"
    EVENTS_API = "events_api"


class EventType:
    MESSAGE = "message"


class MessageEventSubtype:
    BOT_MESSAGE = "bot_message"
    MESSAGE_CHANGED = "message_changed"
    MESSAGE_DELETED = "message_deleted"

    # Non-existent in WebSocket event
    MESSAGE_REPLIED = "message_replied"
    NO_SUBTYPE = "no_subtype"
    FILE_SHARE = "file_share"


class File(TypedDict):
    id: str
    mimetype: str
    name: str
    title: str
    url_private_download: str


class Event(TypedDict):
    type: str
    event_ts: str
    user: str

    # Use this to create a reply thread
    ts: str


class MessageEvent(Event):
    channel: str
    text: NotRequired[str]
    thread_ts: NotRequired[str]


class FileShareEvent(MessageEvent):
    subtype: str
    files: List[File]


class BotMessageEvent(MessageEvent):
    bot_id: str
    username: NotRequired[str]
    icons: NotRequired[dict]


class MessageDeletedEvent(MessageEvent):
    subtype: str
    deleted_ts: str


class MessageChangedMessage(TypedDict):
    type: str
    user: str
    text: str
    ts: str
    edited: dict


class MessageChangedEvent(MessageEvent):
    message: MessageChangedMessage


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
    api_app_id: str
    event: Event
    type: str
    authorizations: List[str]
    event_context: str
    event_id: str
    event_time: int


class WSMessage(TypedDict):
    envelope_id: str
    payload: Payload
    type: str
