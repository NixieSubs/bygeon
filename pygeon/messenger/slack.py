import websocket
import threading
import requests
import orjson
import logging

from enum import Enum
from typing import List, TypedDict

from hub import Hub
from message import Message
from .messenger import Messenger

import colorlog as cl

handler = cl.StreamHandler()
handler.setFormatter(
    cl.ColoredFormatter("%(log_color)s%(levelname)s: %(name)s: %(message)s")
)
logger = cl.getLogger("Slack")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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


class Slack(Messenger):
    def __init__(
        self, app_token: str, bot_token: str, channel_id: str, hub: Hub
    ) -> None:
        self.app_token = app_token
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.hub = hub

    def on_open(self, ws) -> None:
        print("opened")

    def on_error(self, ws, e) -> None:
        print("error")
        print(e)

    def on_close(self, ws, close_status_code, close_msg) -> None:
        print("closed")
        print(close_msg)

    def on_message(self, ws: websocket.WebSocketApp, message: str):
        ws_message: WSMessage = orjson.loads(message)

        match ws_message["type"]:
            case "hello":
                pass
            case "disconnect":
                self.reconnect()
            case _:
                payload = ws_message["payload"]
                self.send_ack(ws, ws_message)
                subtype = payload["event"].get("subtype")
                if subtype == "message_deleted":

                    deleted_ts = payload["event"]["deleted_ts"]
                    logger.info("Deleted message: {}".format(deleted_ts))
                    self.hub.recall_message(self.name, deleted_ts)
                elif subtype != "bot_message":
                    username = self.get_username(payload["event"]["user"])
                    message_id = payload["event"]["ts"]
                    text = payload["event"]["text"]
                    m = Message(self.name, message_id, username, text)

                    if payload["event"].get("thread_ts") is not None:
                        ref_id = payload["event"]["thread_ts"]
                        self.hub.reply_message(m, ref_id)
                    else:
                        self.hub.new_message(m)

    def send_ack(self, ws: websocket.WebSocketApp, message: WSMessage) -> None:
        envelope_id = message["envelope_id"]
        payload = message["payload"]
        ws.send(orjson.dumps({"envelope_id": envelope_id, "payload": payload}))

    def get_username(self, id: str) -> str:
        headers = self.get_headers(self.bot_token)
        r = requests.get(Endpoints.USER_INFO + "?user=" + id, headers=headers)
        username = r.json()["user"]["name"]
        logger.info(r.json())
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
            logger.error("Could not get websocket url")
            raise Exception("Could not get websocket url")
        else:
            logger.info("Successfully got websocket url")
        return websocket_url

    async def send_reply(self, message: Message, ref_id: str) -> None:
        logger.info("Sending message: {}".format(message.text))
        r = requests.post(
            Endpoints.POST_MESSAGE,
            data=self.get_message_payload(message, ref_id),
            headers=self.get_headers(self.bot_token),
        )
        response = r.json()
        logger.info(r.json())

        self.hub.update_entry(message, self.name, response["ts"])

    async def send_message(self, message: Message) -> None:

        logger.info("Sending message: {}".format(message.text))
        r = requests.post(
            Endpoints.POST_MESSAGE,
            data=self.get_message_payload(message),
            headers=self.get_headers(self.bot_token),
        )
        response = r.json()
        if r.status_code != 200:
            logger.error(r.json())
        else:
            logger.info(r.json())

        self.hub.update_entry(message, self.name, response["ts"])

    async def recall_message(self, message_id: str) -> None:
        payload = {
            "token": self.bot_token,
            "channel": self.channel_id,
            "ts": message_id,
        }
        r = requests.post(
            Endpoints.CHAT_DELETE,
            json=payload,
            headers=self.get_headers(self.bot_token),
        )
        logger.info("Trying to recall: " + message_id)
        logger.info(r.json())

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

    def get_message_payload(self, message: Message, ref_id: str = None) -> bytes:
        payload = {
            "type": "message",
            "username": message.author_username,
            "channel": self.channel_id,
            "text": message.text,
        }
        if ref_id is not None:
            payload["thread_ts"] = ref_id
        return orjson.dumps(payload)

    def get_headers(self, token) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        }

    def join(self) -> None:
        self.thread.join()
