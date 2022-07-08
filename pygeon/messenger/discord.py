from websocket import WebSocketApp as WSApp
import threading
import requests
import orjson
import time
import logging

from hub import Hub
from message import Message
from .messenger import Messenger
from .definition.discord import Opcode, EventName, WebsocketMessage
from .definition.discord import MessageCreateEvent, ReadyEvent

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
            case Opcode.HEARTBEAT:
                # TODO
                pass
            case 1:
                # TODO
                pass
            case Opcode.DISPATCH:
                self.handle_dispatch(ws_message)
            case _:
                pass

    def handle_dispatch(self, ws_message: WebsocketMessage) -> None:
        type = ws_message["t"]
        match EventName(type):
            case EventName.MESSAGE_CREATE:
                self.handle_message_create(ws_message)
            case EventName.MESSAGE_DELETE:
                message_id = ws_message["d"]["id"]
                self.hub.recall_message(self.name, message_id)
            case EventName.READY:
                self.handle_ready(ws_message)

    def handle_ready(self, data: ReadyEvent) -> None:
        self.bot_id = data["user"]["id"]

    def handle_reply(self, m: Message, ref_id: str) -> None:
        self.hub.reply_message(m, ref_id)

    def handle_message_create(self, data: MessageCreateEvent) -> None:
        if data.get("channel_id") != self.channel_id:
            return None
        elif data["author"].get("id") == self.bot_id:
            return None

        origin_id = data["id"]

        text = data["content"]
        logger.info("Received message: %s", text)

        author = data["author"]
        username = author["username"]

        m = Message(self.name, origin_id, username, text)

        author = data["author"]
        if not author.get("bot"):
            if data["referenced_message"] is not None:
                ref_id = data["referenced_message"]["id"]
                self.handle_reply(m, ref_id)
            else:
                self.hub.new_message(m)

    def recall_message(self, message_id: str) -> None:
        r = requests.delete(
            Endpoints.DELETE_MESSAGE.format(self.channel_id, message_id),
            headers=self.headers,
        )
        logger.info("Trying to recall: " + message_id)
        logger.info(r.json())

    def send_reply(self, message: Message, ref_id: str) -> None:
        payload = {
            "content": f"[{message.author_username}]: {message.text}",
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
        payload = {"content": f"[{message.author_username}]: {message.text}"}
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
        payload = self.get_identity_payload
        print(payload)
        ws.send(payload)

    @property
    def get_identity_payload(self) -> bytes:
        payload = {
            "op": Opcode.IDENTIFY.value,
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
        # XXX
        self.ws.close()
        self.start()

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
