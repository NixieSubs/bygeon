import websocket
import threading
import requests
import orjson
import time
import logging

from enum import Enum
from typing import TypedDict, Tuple

from hub import Hub
from message import Message
from .messenger import Messenger

import colorlog as cl


class Endpoints:
    GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"
    SEND_MESSAGE = "https://discordapp.com/api/channels/{}/messages"


handler = cl.StreamHandler()
handler.setFormatter(
    cl.ColoredFormatter("%(log_color)s%(levelname)s: %(name)s: %(message)s")
)


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


websocket.enableTrace(True)
logger = cl.getLogger("Discord")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class Discord(Messenger):
    def __init__(self, token: str, channel_id, hub: Hub) -> None:
        self.token = token
        self.channel_id = channel_id
        self.hub = hub

    def on_open(self, ws):
        print("opened")

    def on_error(self, ws, e):
        print("error")
        print(e)

    def on_close(self, ws, close_status_code, close_msg):
        print("closed")
        print(close_msg)

    def on_message(self, ws: websocket.WebSocketApp, message: str):
        def heartbeat(ws: websocket.WebSocketApp, interval: int):
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
            # opcode 10 hello
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

                        m = Message(username, text)

                        author = ws_message["d"]["author"]
                        if not author.get("bot"):
                            self.hub.new_message(m, self)
            case _:
                pass

    async def send_message(self, message: Message) -> Tuple[str, str]:
        payload = {
            "embeds": [
                {
                    "author": {"name": message.author_username},
                    "title": "says",
                    "description": message.text,
                }
            ],
        }
        headers = {
            "Authorization": f"Bot {self.token}",
        }
        r = requests.post(
            Endpoints.SEND_MESSAGE.format(self.channel_id),
            json=payload,
            headers=headers,
        )
        if r.status_code != 200:
            logger.error(r.json())
        else:
            logger.info(r.json())

        return (type(self).__name__, r.json()["id"])

    def send_identity(self, ws: websocket.WebSocketApp) -> None:
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
        self.ws = websocket.WebSocketApp(
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
