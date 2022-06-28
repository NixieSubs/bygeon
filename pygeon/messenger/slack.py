from calendar import c
import websocket
import threading
import requests
import json
import hub
import logging

import colorlog
from typing import TypedDict

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)s:%(name)s:%(message)s")
)


websocket.enableTrace(True)
logger = colorlog.getLogger("Slack")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class Event(TypedDict):
    type: str
    text: str
    user: str
    channel: str


class Payload(TypedDict):
    event: Event

class Slack:
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
        message = json.loads(message)

        match message['type']:
            case 'hello':
                pass

            case 'disconnect':
                self.reconnect()
            case _:
                envelope_id = message["envelope_id"]
                payload = message["payload"]
                text = payload["event"]["text"]
                logger.info("Received message: {}".format(text))
                print(message)
                ws.send(json.dumps({"envelope_id": envelope_id, "payload": payload}))

    def reconnect(self) -> None:
        #TODO
        pass
    def get_websocket_url(self) -> str:
        header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.token,
        }
        r = requests.post("https://slack.com/api/apps.connections.open", headers=header)
        try:
            websocket_url = r.json()["url"]
        except KeyError:
            print(r.text)
            logger.error("Could not get websocket url")
            raise Exception("Could not get websocket url")
        else:
            logger.info("Successfully got websocket url")
        return websocket_url

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
    def join(self) -> None:
        self.thread.join()
