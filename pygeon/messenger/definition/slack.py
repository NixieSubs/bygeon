from enum import Enum
from typing import List, TypedDict


class Endpoints:
    POST_MESSAGE = "https://slack.com/api/chat.postMessage"
    USER_INFO = "https://slack.com/api/users.info"
    CONNECTIONS_OPEN = "https://slack.com/api/apps.connections.open"
    CHAT_DELETE = "https://slack.com/api/chat.delete"


class Events(Enum):
    MESSAGE = "MESSAGE"


class Event(TypedDict):
    type: str
    subtype: str
    text: str
    user: str
    channel: str
    event_ts: str
    channel_type: str
    thread_ts: str
    ts: str
    deleted_ts: str


class Element(TypedDict):
    type: str
    text: str


class Block(TypedDict):
    type: str
    block_id: str
    elements: List[Element]


class Payload(TypedDict):
    token: str
    team_id: str
    event: Event
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
    event: Event
    type: str
