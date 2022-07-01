import websocket
import threading
import requests
import json
import logging
from hub import Hub

from message import Message
from messenger import Messenger

import colorlog
from typing import List, TypedDict, Optional
from enum import Enum

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)s:%(name)s:%(message)s")
)


class Endpoints:
    POST_MESSAGE = "https://slack.com/api/chat.postMessage"
    USER_INFO = "https://slack.com/api/users.info"
    CONNECTIONS_OPEN = "https://slack.com/api/apps.connections.open"


class Events(Enum):
    MESSAGE = "MESSAGE"


websocket.enableTrace(True)
logger = colorlog.getLogger("Slack")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class Event(TypedDict):
    type: str
    subtype: Optional[str]
    text: str
    user: str
    channel: str
    event_ts: str
    channel_type: str


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


class Slack(Messenger):
    def __init__(
        self, app_token: str, bot_token: str, channel_id: str, hub: Hub
    ) -> None:
        self.app_token = app_token
        self.bot_token = bot_token
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
        ws_message: WSMessage = json.loads(message)

        match ws_message["type"]:
            case "hello":
                pass

            case "disconnect":
                self.reconnect()
            case _:
                payload = ws_message["payload"]
                text = payload["event"]["text"]
                logger.info("Received message: {}".format(text))
                self.send_ack(ws, ws_message)

                if payload["event"].get("subtype") != "bot_message":
                    username = self.get_username(payload["event"]["user"])
                    #logger.info("got username:" + username)
                    self.hub.new_message(Message(username, text), self)

    def send_ack(self, ws: websocket.WebSocketApp, message: WSMessage):
        envelope_id = message["envelope_id"]
        payload = message["payload"]
        ws.send(json.dumps({"envelope_id": envelope_id, "payload": payload}))

    def get_username(self, id: str) -> str:
        headers = self.get_headers(self.bot_token)
        r = requests.get(Endpoints.USER_INFO + "?user=" + id, headers=headers)
        username = r.json()["user"]["name"]
        logger.info(r.text)
        return username

    def reconnect(self) -> None:
        # TODO
        pass

    def get_websocket_url(self) -> str:
        header = self.get_headers(self.app_token)
        r = requests.post(Endpoints.CONNECTIONS_OPEN, headers=header)
        try:
            websocket_url = r.json()["url"]
        except KeyError:
            print(r.text)
            logger.error("Could not get websocket url")
            raise Exception("Could not get websocket url")
        else:
            logger.info("Successfully got websocket url")
        return websocket_url

    def send_message(self, message: Message) -> None:
        payload = {
            "type": "message",
            "username": message.author_username,
            "channel": self.channel_id,
            "text": message.text,
        }
        logger.error("Sending message: {}".format(message.text))
        r = requests.post(
            Endpoints.POST_MESSAGE,
            data=json.dumps(payload),
            headers=self.get_headers(self.bot_token),
        )
        logger.error(r.text)

    def start(self) -> None:
        self.ws = websocket.WebSocketApp(
            self.get_websocket_url(),
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def get_headers(self, token) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        }

    def join(self) -> None:
        self.thread.join()
