from websocket import WebSocketApp as WSApp
import threading
import requests
import orjson
import time
import logging

from enum import Enum
from typing import TypedDict

from hub import Hub
from message import Message
from .messenger import Messenger

import colorlog as cl


class Endpoints:
    GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"
    SEND_MESSAGE = "https://discordapp.com/api/channels/{}/messages"
    DELETE_MESSAGE = "https://discordapp.com/api/channels/{}/messages/{}"


handler = cl.StreamHandler()
handler.setFormatter(
    cl.ColoredFormatter("%(log_color)s%(levelname)s: %(name)s: %(message)s")
)
logger = cl.getLogger("Discord")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class ReferencedMessage(TypedDict):
    type: int
    id: str


class Author(TypedDict):
    id: str
    username: str
    avatar: str
    bot: bool


class EmbedAuthor(TypedDict):
    name: str
    url: str
    icon_url: str
    proxy_icon_url: str


class GatewayEvent(TypedDict):
    type: int
    referenced_message: ReferencedMessage
    channel_id: str
    content: str
    id: str
    author: Author
    heartbeat_interval: int


class WebsocketMessage(TypedDict):
    op: int
    t: str
    s: int
    d: GatewayEvent


class Opcode(Enum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE_UPDATE = 3
    RESUME = 6
    RECONNECT = 7
    HELLO = 10
    HEARTBEAT_ACK = 11


class EventName(Enum):
    MESSAGE_CREATE = "MESSAGE_CREATE"
    MESSAGE_UPDATE = "MESSAGE_UPDATE"
    MESSAGE_DELETE = "MESSAGE_DELETE"
    READY = "READY"


class Discord(Messenger):
    def __init__(self, token: str, channel_id, hub: Hub) -> None:
        self.token = token
        self.channel_id = channel_id
        self.hub = hub

    @property
    def headers(self):
        return {"Authorization": f"Bot {self.token}"}

    def on_open(self, ws):
        print("opened")

    def on_error(self, ws, e):
        print("error")
        print(e)

    def on_close(self, ws, close_status_code, close_msg):
        print("closed")
        print(close_msg)

    def on_message(self, ws: WSApp, message: str):
        def heartbeat(ws: WSApp, interval: int):
            payload = {
                "op": 1,
                "d": None,
            }
            while True:
                time.sleep(interval / 1000)
                ws.send(orjson.dumps(payload))

        ws_message: WebsocketMessage = orjson.loads(message)

        opcode = ws_message["op"]
        match Opcode(opcode):
            case Opcode.HELLO:
                heartbeat_interval = ws_message["d"]["heartbeat_interval"]
                self.send_identity(ws)
                threading.Thread(
                    target=heartbeat, args=(ws, heartbeat_interval)
                ).start()
            case 2:
                # TODO
                pass
            case 1:
                # TODO
                pass
            case Opcode.DISPATCH:
                type = ws_message["t"]
                match EventName(type):
                    case EventName.MESSAGE_CREATE:
                        text = ws_message["d"]["content"]
                        logger.info("Received message: %s", text)
                        username = ws_message["d"]["author"]["username"]
                        orig_id = ws_message["d"]["id"]
                        m = Message(self.name, orig_id, username, text)

                        author = ws_message["d"]["author"]
                        if not author.get("bot"):
                            if ws_message["d"]["referenced_message"] is not None:
                                referenced_id = ws_message["d"]["referenced_message"][
                                    "id"
                                ]
                                self.hub.reply_message(m, referenced_id)
                            else:
                                self.hub.new_message(m)
                    case EventName.MESSAGE_DELETE:
                        message_id = ws_message["d"]["id"]
                        self.hub.recall_message(self.name, message_id)

            case _:
                pass

    def recall_message(self, message_id: str) -> None:
        r = requests.delete(
            Endpoints.DELETE_MESSAGE.format(self.channel_id, message_id),
            headers=self.headers,
        )
        logger.info("Trying to recall: " + message_id)
        logger.info(r.json())

    def send_reply(self, message: Message, ref_id: str) -> None:
        payload = {
            "embeds": [
                {
                    "author": {"name": message.author_username},
                    "title": "says",
                    "description": message.text,
                }
            ],
            "message_reference": {
                "message_id": ref_id,
            },
        }
        r = requests.post(
            Endpoints.SEND_MESSAGE.format(self.channel_id),
            json=payload,
            headers=self.headers,
        )
        if r.status_code != 200:
            logger.error(r.json())
        else:
            logger.info(r.json())
        message_id: str = r.json()["id"]
        self.hub.update_entry(message, self.name, message_id)

    def send_message(self, message: Message) -> None:
        payload = {
            "embeds": [
                {
                    "author": {"name": message.author_username},
                    "title": "says",
                    "description": message.text,
                }
            ],
        }
        r = requests.post(
            Endpoints.SEND_MESSAGE.format(self.channel_id),
            json=payload,
            headers=self.headers,
        )
        if r.status_code != 200:
            logger.error(r.json())
        else:
            logger.info(r.json())

        message_id: str = r.json()["id"]
        self.hub.update_entry(message, self.name, message_id)

    def send_identity(self, ws: WSApp) -> None:
        payload = self.get_identity_payload()
        print(payload)
        ws.send(payload)

    def get_identity_payload(self) -> bytes:
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "os": "linux",
                    "browser": "pygeon",
                    "device": "pygeon",
                },
                "large_threshold": 250,
                "compress": False,
                "intents": (1 << 15) + (1 << 9),
            },
        }
        return orjson.dumps(payload)

    def reconnect(self) -> None:
        # TODO
        pass

    def start(self) -> None:
        self.ws = WSApp(
            Endpoints.GATEWAY,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def join(self) -> None:
        self.thread.join()
