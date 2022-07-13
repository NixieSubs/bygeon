import threading
from typing import Union, cast
from urllib.parse import urljoin

from websocket import WebSocketApp as WSApp

import orjson
import requests

import bygeon.util as util
from bygeon.hub import Hub
from bygeon.message import Message, Attachment
from .definition.cqhttp import WSMessage, PostType, Endpoints
from .messenger import Messenger


class CQHttp(Messenger):
    @property
    def send_url(self) -> str:
        return urljoin(self.http_url, Endpoints.SEND_GROUP_MESSAGE)

    @property
    def recall_url(self) -> str:
        return urljoin(self.http_url, Endpoints.DELETE_MESSAGE)

    def __init__(self, group_id: str, hub: Hub, ws_url: str, http_url: str) -> None:
        self.group_id = int(group_id)
        self.hub = hub
        self.logger = self.get_logger()
        self.ws_url = ws_url
        self.http_url = http_url

    def on_open(self, ws) -> None:
        self._on_open(ws)

    def on_error(self, ws, e) -> None:
        self._on_error(ws, e)

    def on_close(self, ws, close_status_code, close_msg) -> None:
        self._on_close(ws, close_status_code, close_msg)
        self.reconnect()

    def on_message(self, ws: WSApp, message: str) -> None:
        ws_message: WSMessage = orjson.loads(message)
        post_type = ws_message["post_type"]
        is_reply = False
        message_group_id = ws_message.get("group_id")
        match post_type:
            case PostType.MESSAGE:
                if message_group_id != self.group_id:
                    return None
                if ws_message["self_id"] == ws_message["user_id"]:
                    return None
                message_id = ws_message["message_id"]

                self.logger.info("Received message: " + str(message_id))

                author = ws_message["sender"]["nickname"]

                data = ws_message["message"]
                text = ""
                attachments = []
                for d in data:
                    if d["type"] == "reply":
                        is_reply = True
                        ref_id = d["data"]["id"]

                        self.logger.info("Reply to: " + str(ref_id))
                    elif d["type"] == "text":
                        text += d["data"]["text"]
                    elif d["type"] == "image":
                        url = d["data"].get("url", "")
                        url = cast(str, url)
                        fn = d["data"]["file"]
                        filename = f"{self.name}_{fn}"
                        path = self.generate_cache_path(self.hub.name)
                        file_path = util.download_to_cache(url, path, filename)
                        attachments.append(Attachment(fn, "image", file_path))
                m = Message(self.name, message_id, author, text, attachments)
                if is_reply:
                    self.hub.reply_message(m, ref_id)
                else:
                    self.hub.new_message(m)
            case PostType.NOTICE:
                if ws_message["self_id"] == ws_message["user_id"]:
                    return None
                recalled_id = ws_message["message_id"]
                self.hub.recall_message(self.name, recalled_id)

    def recall_message(self, message_id: str) -> None:
        payload = {
            "message_id": message_id,
        }
        r = requests.post(self.recall_url, json=payload)
        self.logger.info("Trying to recall: " + message_id)
        self.logger.info(r.json())

    def modify_message(self, m: Message, m_id: str) -> None:
        self.recall_message(m_id)

        self.send_message(m)
        ...

    def reconnect(self) -> None:
        self.ws.close()
        self.start()
        self.join()
        ...

    def send_message(self, m: Message, ref_id=None) -> None:
        payload: dict[str, Union[str, int]] = {
            "group_id": self.group_id,
            "message": "",
        }
        message_string = ""
        for attachment in m.attachments:
            main_type = attachment.type.split("/")[0]
            message_string += f"[CQ:{main_type},file=file:{attachment.file_path}]"

        self.logger.info(ref_id)
        if ref_id is not None:
            message_string += f"[CQ:reply,id={ref_id}]"
        message_string += f"[{m.author_username}]: {m.text}"
        self.logger.info(f"Sending message with CQCode: {message_string}")
        payload["message"] = message_string
        self.logger.info(payload)

        r = requests.post(self.send_url, json=payload)
        self.logger.info(r.text)

        response = r.json()
        message_id = response.get("data").get("message_id")
        self.hub.update_entry(m, self.name, message_id)

    def start(self) -> None:
        self.ws = WSApp(
            self.ws_url,
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
