import threading
from typing import Dict, Union, cast
from urllib.parse import urljoin

from websocket import WebSocketApp as WSApp

import orjson
import requests

import bygeon.util as util
from bygeon.message import Message, Attachment
from .definition.cqhttp import WSMessage, PostType, Endpoints
from .messenger import Messenger, Hub


class CQHttp(Messenger):
    @property
    def send_url(self) -> str:
        return urljoin(self.http_url, Endpoints.SEND_GROUP_MESSAGE)

    @property
    def recall_url(self) -> str:
        return urljoin(self.http_url, Endpoints.DELETE_MESSAGE)

    @property
    def member_list_url(self) -> str:
        return urljoin(self.http_url, Endpoints.GET_GROUP_MEMBER_LIST)

    def __init__(self, ws_url: str, http_url: str) -> None:
        self.log = self.get_logger()
        self.ws_url = ws_url
        self.http_url = http_url
        self.nickname_dict: Dict[str, Dict[int, str]] = {}

        self.hubs = {}

    def get_nicknames(self, c_id) -> dict:
        payload = {"group_id": int(c_id)}
        r = requests.post(self.member_list_url, json=payload)
        member_list = orjson.loads(r.text)["data"]
        nickname_dict: Dict[int, str] = {}
        for member in member_list:
            nickname_dict[member["user_id"]] = member["card"]
        return nickname_dict

    def on_open(self, ws) -> None:
        self._on_open(ws)

    def on_error(self, ws, e) -> None:
        self._on_error(ws, e)

    def on_close(self, ws, close_status_code, close_msg) -> None:
        self._on_close(ws, close_status_code, close_msg)
        self.reconnect()

    def on_message(self, ws: WSApp, message: str) -> None:
        ws_message: WSMessage = orjson.loads(message)
        self.log.debug(message)

        post_type = ws_message["post_type"]

        match post_type:
            case PostType.MESSAGE:
                self.handle_message(ws_message)
            case PostType.NOTICE:
                self.handle_notice(ws_message)
                

    def handle_notice(self, wsm: WSMessage):
        if (group_id := wsm.get("group_id")) is None:
            return None
        c_id = str(group_id)
        if (hub := self.hubs.get(c_id)) is None:
            return None
        if wsm["self_id"] == wsm["user_id"]:
            return None
        recalled_id = wsm["message_id"]
        hub.recall_hub_message(self.name, recalled_id)

    def handle_message(self, wsm: WSMessage):
        ref_id = None
        message_id = wsm["message_id"]
        self.log.info(f"Handling message {message_id}")
        if (group_id := wsm.get("group_id")) is None:
            return None
        c_id = str(group_id)
        if (hub := self.hubs.get(c_id)) is None:
            return None
        if wsm["self_id"] == wsm["user_id"]:
            return None
        m_id = wsm["message_id"]

        self.log.info("Received message: " + str(m_id))

        author_id = wsm["sender"]["user_id"]
        author = self.nickname_dict[c_id][author_id] or wsm["sender"]["nickname"]

        data = wsm["message"]
        text = ""
        attachments = []
        for d in data:
            if d["type"] == "reply":
                is_reply = True
                ref_id = d["data"]["id"]

                self.log.info("Reply to: " + str(ref_id))
            elif d["type"] == "text":
                text += d["data"]["text"]
            elif d["type"] == "image":
                url = d["data"].get("url", "")
                url = cast(str, url)
                fn = d["data"]["file"]
                filename = f"{self.name}_{fn}"
                path = self.generate_cache_path(self.name)
                file_path = util.download_to_cache(url, path, filename)
                attachments.append(Attachment(fn, "image", file_path))
        m = Message(self.name, c_id, m_id, ref_id, author, text, attachments)
        hub.new_hub_message(m)

    def recall_message(self, m_id: str, c_id: None | str) -> None:
        payload = {
            "message_id": m_id,
        }
        r = requests.post(self.recall_url, json=payload)
        self.log.info("Trying to recall: " + m_id)

    def modify_message(self, m: Message, c_id: str, m_id: str) -> None:
        self.recall_message(m_id, c_id)

        self.send_message(m, c_id)
        ...

    def reconnect(self) -> None:
        self.ws.close()
        self.start()


    def send_message(self, m: Message, c_id: str, ref_id=None) -> None:
        
        if (hub := self.hubs.get(c_id)) is None:
            return None

        payload: dict[str, Union[str, int]] = {
            "group_id": int(c_id),
            "message": "",
        }
        message_string = ""
        for attachment in m.attachments:
            main_type = attachment.type.split("/")[0]
            message_string += f"[CQ:{main_type},file=file:{attachment.file_path}]"

        if ref_id is not None:
            message_string += f"[CQ:reply,id={ref_id}]"
        message_string += f"[{m.author_username}]: {m.text}"
        self.log.info(f"Sending message with CQCode: {message_string}")
        payload["message"] = message_string
        

        r = requests.post(self.send_url, json=payload)
        

        response = r.json()
        message_id = response.get("data").get("message_id")
        hub.update_entry(m, self.name, message_id)
    def add_hub(self, c_id: str , hub: Hub):
        self.hubs[c_id] = hub

        self.nickname_dict[c_id] = self.get_nicknames(c_id)

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

