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
from bygeon.hub import Hub
from bygeon.message import Message, Attachment
from .messenger import Messenger
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

    def __init__(self, bot_token: str, channel_id: str, hub: Hub) -> None:
        self.token = bot_token
        self.channel_id = channel_id
        self.hub = hub
        self.sequence = None
        self.session_id = None

        self.nickname_dict = self.get_nicknames()
        self.logger = self.get_logger()

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
        payload = {
            "op": 1,
            "d": None,
        }
        while True:
            time.sleep(interval / 1000)
            if ws.sock is not None:
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
                self.logger.debug(ws_message)
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
                message_id = delete_event["id"]
                self.hub.recall_message(self.name, message_id)
            case EventName.READY:
                ready_event = cast(ReadyEvent, ws_message["d"])
                self.handle_ready(ready_event)
            case EventName.MESSAGE_UPDATE:
                update_event = cast(MessageUpdateEvent, ws_message["d"])
                text = update_event["content"]
                username = update_event["author"]["username"]
                message_id = update_event["id"]
                m = Message(self.name, message_id, username, text, [])
                self.hub.modify_message(m)
            case _:
                return None

    def handle_ready(self, data: ReadyEvent) -> None:
        self.bot_id = data["user"]["id"]
        self.session_id = data["session_id"]

    def handle_reply(self, m: Message, ref_id: str) -> None:
        self.hub.reply_message(m, ref_id)

    def handle_modify(self, data: MessageUpdateEvent) -> None:
        message_id = data["id"]
        author = data["author"]
        username = author["username"]
        text = data["content"]
        m = Message(self.name, message_id, username, text, [])
        self.hub.modify_message(m)

    def modify_message(self, m: Message, m_id: str) -> None:
        url = Endpoints.EDIT_MESSAGE.format(self.channel_id, m_id)

        payload = {
            "content": f"[{m.author_username}]: {m.text}",
        }

        requests.patch(url, headers=self.headers, json=payload)

    def handle_message_create(self, data: MessageCreateEvent) -> None:
        if data.get("channel_id") != self.channel_id:
            return None
        elif data["author"].get("id") == self.bot_id:
            return None

        origin_id = data["id"]

        text = data["content"]
        self.logger.info("Received message: %s", text)

        author = data["author"]
        username = self.nickname_dict.get(author["id"], author["username"])
        attachments: List[Attachment] = []
        for attachment in data["attachments"]:
            url = attachment["url"]

            fn = attachment["id"]
            filename = f"{self.name}_{fn}"

            full_type = attachment["content_type"]

            path = self.generate_cache_path(self.hub.name)
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
            path = self.generate_cache_path(self.hub.name)
            file_path = util.download_to_cache(url, path, fn)
            full_type = "image/gif"
            attachments.append(Attachment(fn, full_type, file_path))
            text = text.replace(f"<a:{a_emoji_name}:{a_emoji_id}>", "")

        for emoji_name, emoji_id in emoji_list:
            fn = f"{emoji_name}_{emoji_id}.png"
            url = Endpoints.GET_EMOJI.format(emoji_id) + ".png"
            path = self.generate_cache_path(self.hub.name)
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
                path = self.generate_cache_path(self.hub.name)
                file_path = util.download_to_cache(url, path, filename)
                attachments.append(Attachment(fn, full_type, file_path))

        m = Message(self.name, origin_id, username, text, attachments)
        if (ref_message := data["referenced_message"]) is not None:
            ref_id = ref_message["id"]
            self.hub.reply_message(m, ref_id)
        else:
            self.hub.new_message(m)

    def recall_message(self, message_id: str) -> None:
        r = requests.delete(
            Endpoints.DELETE_MESSAGE.format(self.channel_id, message_id),
            headers=self.headers,
        )
        self.log_response(r)

    def send_message(self, m: Message, ref_id=None) -> None:
        payload: dict[str, Union[str, dict]] = {
            "content": f"[{m.author_username}]: {m.text}"
        }
        if ref_id is not None:
            payload["message_reference"] = {
                "channel_id": self.channel_id,
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
                Endpoints.SEND_MESSAGE.format(self.channel_id),
                headers=self.headers,
                files=files,
            )
        else:
            r = requests.post(
                Endpoints.SEND_MESSAGE.format(self.channel_id),
                json=payload,
                headers=self.headers,
            )

        self.log_response(r)

        message_id: str = r.json().get("id")
        self.hub.update_entry(m, self.name, message_id)

    def send_identity(self, ws: WSApp) -> None:
        payload = self.identity_payload
        print(payload)
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
            self.logger.error(r.text)
        else:
            self.logger.debug(r.text)

    def reconnect(self) -> None:
        # XXX
        self.ws.close()
        self.start()
        self.join()

    def get_nicknames(self) -> Dict[str, str]:
        r = requests.get(
            Endpoints.GET_CHANNEL.format(self.channel_id), headers=self.headers
        )

        guild_id = r.json()["guild_id"]

        r = requests.get(
            Endpoints.LIST_GUILD_MEMBERS.format(guild_id), headers=self.headers
        )
        print(r.text)
        nickname_dict: Dict[str, str] = {}
        guild_members: List[GuildMember] = orjson.loads(r.text)

        for member in guild_members:
            if member.get("nick") is None:
                continue
            nickname_dict[member["user"]["id"]] = cast(str, member["nick"])
        print(nickname_dict)
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
