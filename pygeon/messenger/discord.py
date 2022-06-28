from tkinter import EventType
import websocket
import threading
import requests
import json
import hub
import time
import logging

import colorlog

from typing import TypedDict

from enum import Enum

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)s:%(name)s:%(message)s")
)


class ReferencedMessage(TypedDict):
    type: int
    id: str


class GatewayEvent(TypedDict):
    type: int
    referenced_message: ReferencedMessage
    channel_id: str
    content: str
    id: str


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


websocket.enableTrace(True)
logger = colorlog.getLogger("Discord")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class Discord:
    url = "wss://gateway.discord.gg/?v=10&encoding=json"

    def __init__(self, token: str) -> None:
        self.token = token
        # self.hub = hub

    def on_open(self, ws):
        print("opened")

    def on_error(self, ws, e):
        print("error")
        print(e)

    def on_close(self, ws, close_status_code, close_msg):
        print("closed")
        print(close_msg)

    def on_message(self, ws: websocket.WebSocketApp, message: str):
        def heartbeat(ws, interval):
            payload = {
                "op": 1,
                "d": None,
            }
            while True:
                time.sleep(interval / 1000)
                ws.send(json.dumps(payload))

        message: WebsocketMessage = json.loads(message)
        print(json.dumps(message, indent=4))

        opcode = message["op"]
        match Opcode(opcode):
            # opcode 10 hello
            case Opcode.HELLO:
                heartbeat_interval = message["d"]["heartbeat_interval"]
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
                type = message["t"]
                match type:
                    case EventName.MESSAGE_CREATE:
                        logger.error("Message: %s", message["d"]["content"])
            case _:
                pass

    def send_message():
        pass

    def send_identity(self, ws: websocket.WebSocketApp) -> None:
        payload = self.get_identity_payload()
        print(payload)
        ws.send(payload)

    def get_identity_payload(self):
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
        return json.dumps(payload)

    def reconnect(self) -> None:
        # TODO
        pass

    def start(self) -> None:
        self.ws = websocket.WebSocketApp(
            self.url,
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
