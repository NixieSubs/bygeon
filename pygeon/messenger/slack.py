import websocket
from websocket import WebSocketApp as WSApp
import threading
import requests
import orjson

from hub import Hub
from message import Message
from .messenger import Messenger
from .definition.slack import Endpoints, Payload, WSMessage, WSMessageType
from .definition.slack import MessageEventSubtype, MessageEvent, EventType

import colorlog as cl

class Slack(Messenger):
    def __init__(
        self, app_token: str, bot_token: str, channel_id: str, hub: Hub
    ) -> None:
        super.__init__()

        self.app_token = app_token
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.hub = hub

        self.bot_user_id = self.get_bot_user_id()

    def on_open(self, ws) -> None:
        print("opened")

    def on_error(self, ws, e) -> None:
        print("error")
        print(e)

    def on_close(self, ws, close_status_code, close_msg) -> None:
        print("closed")
        print(close_msg)

    def on_message(self, ws: WSApp, message: str):
        ws_message: WSMessage = orjson.loads(message)
        ws_type = ws_message["type"]

        match WSMessageType(ws_type):
            case WSMessageType.HELLO:
                pass
            # FIXME
            case WSMessageType.DISCONNECT:
                self.reconnect()
            case WSMessageType.EVENTS_API:
                payload = ws_message["payload"]
                self.send_ack(ws, ws_message)
                self.handle_event(payload)

    # Payload is needed to decide event type later
    def handle_event(self, payload: Payload) -> None:
        event_type = payload["event"]["type"]
        match EventType(event_type):
            case EventType.MESSAGE:
                event: MessageEvent = payload["event"]
                self.handle_message(event)
            case _:
                pass

    def handle_message(self, event: MessageEvent) -> None:
        # XXX
        subtype = event.get("subtype", "no_subtype")
        message_id = event["ts"]
        text = event["text"]
        user_id = event["user"]
        # username = self.get_username(user_id)
        match MessageEventSubtype(subtype):
            case MessageEventSubtype.MESSAGE_DELETED:
                deleted_ts = event["deleted_ts"]
                self.logger.info("Deleted message: {}".format(deleted_ts))
                self.hub.recall_message(self.name, deleted_ts)
            case MessageEventSubtype.BOT_MESSAGE:
                if user_id == self.bot_user_id:
                    return None
            case MessageEventSubtype.NO_SUBTYPE:
                username = self.get_username(user_id)
                m = Message(self.name, message_id, username, text)
                if (ref_id := event.get("thread_ts")) is not None:
                    self.hub.reply_message(m, ref_id)
                else:
                    self.hub.new_message(m)

    def send_ack(self, ws: WSApp, message: WSMessage) -> None:
        envelope_id = message["envelope_id"]
        # payload = message["payload"]
        ws.send(orjson.dumps({"envelope_id": envelope_id}))

    def get_username(self, id: str) -> str:
        headers = self.get_headers(self.bot_token)
        r = requests.get(Endpoints.USERS_INFO + "?user=" + id, headers=headers)
        username = r.json()["user"]["name"]
        self.logger.info(r.json())
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
            self.logger.error("Could not get websocket url")
            raise Exception("Could not get websocket url")
        else:
            self.logger.info("Successfully got websocket url")
        return websocket_url

    def send_reply(self, message: Message, ref_id: str) -> None:
        self.logger.info("Sending message: {}".format(message.text))
        r = requests.post(
            Endpoints.POST_MESSAGE,
            data=self.get_message_payload(message, ref_id),
            headers=self.get_headers(self.bot_token),
        )
        response = r.json()
        self.logger.info(r.json())

        self.hub.update_entry(message, self.name, response["ts"])

    def send_message(self, message: Message) -> None:

        self.logger.info("Sending message: {}".format(message.text))
        r = requests.post(
            Endpoints.POST_MESSAGE,
            data=self.get_message_payload(message),
            headers=self.get_headers(self.bot_token),
        )
        response = r.json()
        if r.status_code != 200:
            self.logger.error(r.json())
        else:
            self.logger.info(r.json())

        self.hub.update_entry(message, self.name, response["ts"])

    def recall_message(self, message_id: str) -> None:
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
        self.logger.info("Trying to recall: " + message_id)
        self.logger.info(r.json())

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

    def get_bot_user_id(self) -> str:
        headers = self.get_headers(self.bot_token)
        r = requests.get(Endpoints.BOTS_INFO, headers=headers)
        bot_info = orjson.loads(r.text)
        return bot_info["bot"]["user_id"]

    def get_message_payload(self, m: Message, ref_id: str = None) -> bytes:
        payload = {
            "type": "message",
            "username": m.author_username,
            "channel": self.channel_id,
            "text": m.text,
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
