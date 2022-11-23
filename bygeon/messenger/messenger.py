import os

from websocket import WebSocketApp as WSApp

from bygeon.message import Message

from typing import Protocol, List, Dict, Tuple, NamedTuple, cast

from pypika import Query, Column, Table
from sqlite3 import Connection as SQLConn, Cursor as SQLCur, Row as SQLRow,connect

from bygeon.message import Message
from structlog.typing import BindableLogger

import bygeon.util as util
import bygeon.logger as logger


class Hub:
    links: Dict["Messenger", str]
    log: BindableLogger

    def __init__(self, name: str, keep_data=False):
        self.conn: SQLConn = connect(
            f"{name}.db",
            check_same_thread=False,
            isolation_level=None,
        )
        self.conn.row_factory = SQLRow
        self.name = name
        self.links = {}

        self.init_database(keep_data)
        self.log = logger.log.bind(Hub=self.name)

    def add_linkee(self, msgr: "Messenger", c_id: str):
        self.links[msgr] = c_id

    @property
    def clients(self):
        return self.links.keys()

    @property
    def client_names(self):
        return [c.name for c in self.clients]

    def execute_sql(self, query: str):
        cur = self.conn.cursor()
        cur.execute(query)
        return cur

    def init_database(self, keep_data):
        columns = tuple(
            Column(s, "VARCHAR(255)", nullable=True) for s in self.client_names
        )
        if not keep_data:
            self.execute_sql('DROP TABLE IF EXISTS "messages"')
            create_table = Query.create_table("messages").columns(*columns)
            self.execute_sql(str(create_table))
        self.table = Table("messages")

    def new_hub_message(self, m: Message):
        ref = m.origin_ref_id
        ref_id = None
        self.new_entry(m)
        for client in self.clients:
            to_c_id = self.links[client]
            if m.origin != client.name:
                if ref is not None:
                    self.log.debug(f"Find ref_id in original message: {ref}")
                    self.log.debug(f"Trying to find corresponding ref_id for {client.name}")
                    ref_id = self.find_id(m.origin, ref, client.name)
                    if ref_id is not None:
                        self.log.debug(f"Found corresponding ref_id {ref_id}")

                client.send_message(m, to_c_id, ref_id)

    def modify_hub_message(self, m: Message) -> None:
        for client in self.clients:
            if client.name != m.origin:
                to_c_id = self.links[client]
                m_id = self.find_id(m.origin, m.origin_m_id, client.name)
                util.run_in_thread(client.modify_message, (m, to_c_id, m_id))

    def recall_hub_message(self, orig: str, recalled_id: str) -> None:
        for client in self.clients:
            if client.name != orig:
                to_c_id = self.links[client]
                m_id = self.find_id(orig, recalled_id, client.name)
                util.run_in_thread(client.recall_message, (m_id, to_c_id))

    def find_row(self, fname, m_id) -> SQLRow :

        select_string = ", ".join([f"\"{n}\" AS {n}" for n in self.client_names])

        sql = f'SELECT {select_string} FROM "messages" WHERE "{fname}" = \'{m_id}\''
        cur = self.execute_sql(sql)
        res = cur.fetchone()

        return res

    def find_id(self, fname: str, m_id: str, tname: str) -> str | None:
        res = self.find_row(fname, m_id)
        return res[tname] if res is not None else None


    

    def new_entry(self, m: Message) -> None:
        origin_id = m.origin_m_id
        origin = m.origin

        entry = (origin_id if origin == s else None for s in self.client_names)
        q = Query.into(self.table).insert(*tuple(entry))
        self.execute_sql(str(q))

    # XXX
    def update_entry(self, m: Message, client_name: str, sent_id: str) -> None:  # noqa
        sql = f'UPDATE "messages" SET "{client_name}" = \'{sent_id}\' WHERE "{m.origin}" = \'{m.origin_m_id}\''  # noqa
        # q = Query.update(self.table).set(sent_messenger, sent_id).where(m.origin == m.origin_id) # noqa
        self.execute_sql(sql)


class Messenger(Protocol):
    log: BoundLogger
    hubs: Dict[str, Hub]

    def get_logger(self):
        self.log = logger.log.bind(Client=self.name)
        return self.log

    def __hash__(self):
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def add_hub(self, c_id: str , hub: Hub):
        self.hubs[c_id] = hub

    @property
    def file_cache_path(self) -> str:
        return os.path.join(os.getcwd(), "cache")

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def generate_cache_path(self, hub_name: str) -> str:
        return os.path.join(self.file_cache_path, hub_name)

    def _on_open(self, ws) -> None:
        self.log.info("Opened WebSocket connection")

    def _on_error(self, ws, e) -> None:
        self.log.error(f"WebSocket encountered error: ", e)

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        self.log.error(f"WebSocket closed: {close_msg}")

    def on_message(self, ws: WSApp, message: str) -> None:
        ...

    def send_message(self, m: Message, c_id: str, ref_id=None) -> None:
        ...

    def modify_message(self, m: Message, c_id, m_id: str) -> None:
        ...

    def recall_message(self, m_id: str, c_id: None | str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...

    def cache_prefix(self, id="") -> str:
        return f"{self.name}_{id}."
