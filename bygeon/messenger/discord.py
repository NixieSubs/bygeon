import threading
import time
import re
from io import BytesIO
from os.path import basename
from typing import cast, List, Dict, Any, Union, Optional

from websocket import WebSocketApp as WSApp

import requests
import orjson

import bygeon.util as util
from bygeon.message import Message, Attachment
from .messenger import Messenger, Hub
from .definition.discord import (
    MessageUpdateEvent,
    Opcode,
    EventName,
    WebsocketMessage,
    Endpoints,
    GuildMember,
)
from .definition.discord import (
    MessageCreateEvent,
    ReadyEvent,
    Hello,
    MessageDeleteEvent,
)


class Discord(Messenger):
    session_id: Optional[str]
    sequence: Optional[int]

    def __init__(self, bot_token: str, guild_id: str) -> None:
        self.token = bot_token
        self.sequence = None
        self.session_id = None
        self.guild_id = guild_id
        self.hubs = {}

        self.nickname_dict: Dict[str, Dict[str, str]] = {} 
        self.log = self.get_logger()

    def add_hub(self, c_id: str , hub: Hub):
        self.hubs[c_id] = hub

        self.nickname_dict[c_id] = self.get_nicknames(c_id)

    @property
    def headers(self):
        return {"Authorization": f"Bot {self.token}"}

    def on_open(self, ws) -> None:
        self._on_open(ws)

    def on_error(self, ws, e) -> None:
        self._on_error(ws, e)

    def on_close(self, ws, close_status_code, close_msg) -> None:
        self._on_close(ws, close_status_code, close_msg)
        self.reconnect()

    def heartbeat(self, ws: WSApp, interval: int) -> None:
        log = self.log.bind(Action="Heartbeat")
        payload = {
            "op": 1,
            "d": None,
        }
        while True:
            time.sleep(interval / 1000)
            if ws.sock is not None:
                log.debug("Sending heartbeat")
                ws.send(orjson.dumps(payload))
            else:
                break

    def on_message(self, ws: WSApp, message: str) -> None:

        ws_message: WebsocketMessage = orjson.loads(message)
        opcode = ws_message["op"]


        match opcode:
            case Opcode.HELLO:
                hello = cast(Hello, ws_message["d"])
                heartbeat_interval = hello["heartbeat_interval"]
                self.send_identity(ws)
                threading.Thread(
                    target=self.heartbeat, args=(ws, heartbeat_interval), daemon=True
                ).start()
            case Opcode.HEARTBEAT:
                # TODO
                pass
            case Opcode.DISPATCH:

                self.handle_dispatch(ws_message)
            case _:
                return None

    def handle_dispatch(self, ws_message: WebsocketMessage) -> None:
        t = ws_message["t"]
        self.sequence = ws_message["s"]

        match t:
            case EventName.MESSAGE_CREATE:
                create_event = cast(MessageCreateEvent, ws_message["d"])
                self.handle_message_create(create_event)

            case EventName.MESSAGE_DELETE:
                delete_event = cast(MessageDeleteEvent, ws_message["d"])
                self.handle_message_delete(delete_event)

            case EventName.READY:
                ready_event = cast(ReadyEvent, ws_message["d"])
                self.handle_ready(ready_event)

            case EventName.MESSAGE_UPDATE:
                update_event = cast(MessageUpdateEvent, ws_message["d"])
                self.handle_message_update(update_event)

            case _:
                return None

    def handle_message_update(self, d: MessageUpdateEvent):
        c_id = d["channel_id"]
        if (hub := self.hubs.get(c_id)) is None:
            return None

        text = d["content"]
        username = d["author"]["username"]
        m_id = d["id"]
        m = Message(self.name, c_id, m_id, None, username, text, [])
        hub.modify_hub_message(m)

    def handle_message_delete(self, d: MessageDeleteEvent):
        c_id = d["channel_id"]
        if (hub := self.hubs.get(c_id)) is None:
            return None

        hub.recall_hub_message(self.name, d["id"])

    def handle_ready(self, data: ReadyEvent) -> None:
        self.bot_id = data["user"]["id"]
        self.session_id = data["session_id"]

    def handle_modify(self, d: MessageUpdateEvent) -> None:
        c_id = d["channel_id"]
        if (hub := self.hubs.get(c_id)) is None:
            return None

        m_id = d["id"]

        author = d["author"]
        username = author["username"]
        text = d["content"]
        m = Message(self.name, c_id, m_id, None, username, text, [])
        hub.modify_hub_message(m)

    def modify_message(self, m: Message, c_id: str, m_id: str) -> None:
        url = Endpoints.EDIT_MESSAGE.format(c_id, m_id)

        payload = {
            "content": f"[{m.author_username}]: {m.text}",
        }

        requests.patch(url, headers=self.headers, json=payload)

    def handle_message_create(self, data: MessageCreateEvent) -> None:
        c_id = data["channel_id"]
        hub = self.hubs.get(c_id)

        if hub is None:
            return None
        elif data["author"].get("id") == self.bot_id:
            return None

        m_id = data["id"]

        text = data["content"]
        self.log.info("Received message: %s", text)

        author = data["author"]
        username = self.nickname_dict[c_id].get(author["id"], author["username"])
        attachments: List[Attachment] = []
        for attachment in data["attachments"]:
            url = attachment["url"]

            fn = attachment["id"]
            filename = f"{self.name}_{fn}"

            full_type = attachment.get("content_type")

            path = self.generate_cache_path(self.name)
            file_path = util.download_to_cache(url, path, filename)
            attachments.append(Attachment(fn, full_type, file_path))

        emoji_regex = r"<:(.+):(\d+)>"
        emoji_re = re.compile(emoji_regex)
        emoji_list = emoji_re.findall(text)

        a_emoji_regex = r"<a:(.+):(\d+)>"
        a_emoji_re = re.compile(a_emoji_regex)
        a_emoji_list = a_emoji_re.findall(text)
        for a_emoji_name, a_emoji_id in a_emoji_list:
            fn = f"{a_emoji_name}_{a_emoji_id}.gif"
            url = Endpoints.GET_EMOJI.format(a_emoji_id) + ".gif"
            path = self.generate_cache_path(self.name)
            file_path = util.download_to_cache(url, path, fn)
            full_type = "image/gif"
            attachments.append(Attachment(fn, full_type, file_path))
            text = text.replace(f"<a:{a_emoji_name}:{a_emoji_id}>", "")

        for emoji_name, emoji_id in emoji_list:
            fn = f"{emoji_name}_{emoji_id}.png"
            url = Endpoints.GET_EMOJI.format(emoji_id) + ".png"
            path = self.generate_cache_path(self.name)
            file_path = util.download_to_cache(url, path, fn)
            full_type = "image/png"
            attachments.append(Attachment(fn, full_type, file_path))
            text = text.replace(f"<:{emoji_name}:{emoji_id}>", "")

        if (sticker_items := data.get("sticker_items")) is not None:
            for sticker in sticker_items:
                fn = sticker["id"]
                match sticker["format_type"]:
                    case 1:
                        fn += ".png"
                        full_type = "image/png"
                    case 2:
                        fn += ".apng"
                        full_type = "image/apng"
                    case 3:
                        continue
                        # fn += ".lottie"
                        # full_type = "application/json"
                path = self.generate_cache_path(self.name)
                file_path = util.download_to_cache(url, path, filename)
                attachments.append(Attachment(fn, full_type, file_path))

        ref_id = None
        if (ref_message := data["referenced_message"]) is not None:
            ref_id = ref_message["id"]
        
        m = Message(self.name, c_id, m_id, ref_id, username, text, attachments)
        hub.new_hub_message(m)

    def recall_message(self, m_id: str, c_id: None | str) -> None:
        r = requests.delete(
            Endpoints.DELETE_MESSAGE.format(c_id, m_id),
            headers=self.headers,
        )
        self.log_response(r)

    def send_message(self, m: Message, c_id: str, ref_id=None) -> None:
        hub = self.hubs[c_id]

        payload: dict[str, Union[str, dict]] = {
            "content": f"[{m.author_username}]: {m.text}"
        }
        if ref_id is not None:
            payload["message_reference"] = {
                "channel_id": c_id,
                "message_id": ref_id,
            }

        files = []
        for (i, attachment) in enumerate(m.attachments):
            fn = basename(attachment.file_path)
            a_type = attachment.type
            files.append(
                (f"files[{i}]", (fn, open(attachment.file_path, "rb"), a_type))
            )

        if len(files) > 0:
            # XXX
            payload_io = BytesIO(orjson.dumps(payload))
            files.append(
                (
                    "payload_json",
                    (None, payload_io, "application/json"),
                )  # type: ignore[arg-type]
            )
            r = requests.post(
                Endpoints.SEND_MESSAGE.format(c_id),
                headers=self.headers,
                files=files,
            )
        else:
            r = requests.post(
                Endpoints.SEND_MESSAGE.format(c_id),
                json=payload,
                headers=self.headers,
            )

        self.log_response(r)

        message_id: str = r.json().get("id")
        hub.update_entry(m, self.name, message_id)

    def send_identity(self, ws: WSApp) -> None:
        payload = self.identity_payload
        ws.send(payload)

    @property
    def identity_payload(self) -> bytes:
        # XXX
        payload: Dict[str, Union[dict, Any]] = {
            "op": Opcode.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {
                    "os": "linux",
                    "browser": "bygeon",
                    "device": "bygeon",
                },
                "large_threshold": 250,
                "compress": False,
                "intents": (1 << 15) + (1 << 9),
            },
        }

        if self.sequence is not None:
            payload["sequence"] = self.sequence
        if self.session_id is not None:
            payload["d"]["session_id"] = self.session_id

        return orjson.dumps(payload)

    def log_response(self, r: requests.Response) -> None:
        if r.status_code != 200:
            self.log.error(r.text)
        else:
            self.log.debug(r.text)

    def reconnect(self) -> None:
        # XXX
        self.ws.close()
        self.start()
        self.join()

    def get_nicknames(self, c_id) -> Dict[str, str]:
        log = self.log.bind(Action="Get Nicknames")

        r = requests.get(
            Endpoints.GET_CHANNEL.format(c_id), headers=self.headers
        )

        guild_id = r.json()["guild_id"]

        r = requests.get(
            Endpoints.LIST_GUILD_MEMBERS.format(self.guild_id), headers=self.headers
        )
        nickname_dict: Dict[str, str] = {}
        guild_members: List[GuildMember] = orjson.loads(r.text)
        log.debug(str(guild_members))

        for member in guild_members:
            if member.get("nick") is None:
                continue
            nickname_dict[member["user"]["id"]] = cast(str, member["nick"])

        log.debug(str(nickname_dict))
        return nickname_dict

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
