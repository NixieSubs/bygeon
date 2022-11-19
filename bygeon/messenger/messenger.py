import os
import colorlog as cl
import logging
import structlog


from websocket import WebSocketApp as WSApp

from bygeon.message import Message

from typing import Protocol, List, Dict, Tuple, NamedTuple

from pypika import Query, Column, Table
from sqlite3 import Connection as SQLConn, Cursor as SQLCur

from bygeon.message import Message

import bygeon.util as util

logger_format = "%(log_color)s%(levelname)s: %(name)s: %(message)s"

class Link(NamedTuple):
    conn: SQLConn
    link_to: Dict["Messenger", str]


class Messenger(Protocol):
    logger: structlog.stdlib.BoundLogger

    links: Dict[str, Link]

    def get_logger(self):
        handler = cl.StreamHandler()
        handler.setFormatter(cl.ColoredFormatter(logger_format))

        logger = cl.getLogger(self.name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return logger

    def __init__(self, connect: SQLConn):
        pass

    @property
    def file_cache_path(self) -> str:
        return os.path.join(os.getcwd(), "cache")

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def get_linked_clients(self, c_id):
        return self.links[c_id].link_to.keys()

    def get_link(self, c_id):
        return self.links[c_id].link_to

    def get_connection(self, c_id):
        return self.links[c_id][0]

    def generate_cache_path(self, hub_name: str) -> str:
        return os.path.join(self.file_cache_path, hub_name)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self):
        return self.name == self.name

    def _on_open(self, ws) -> None:
        self.logger.info("Opened WebSocket connection")

    def _on_error(self, ws, e) -> None:
        self.logger.error(f"WebSocket encountered error: {e}")

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        self.logger.error(f"WebSocket closed: {close_msg}")

    def on_message(self, ws: WSApp, message: str) -> None:
        ...

    def send_message(self, m: Message, c_id: str, ref_id=None) -> None:
        ...

    def reply_message(self, m: Message, c_id: str, reply_to: str) -> None:
        self.new_entry(m)
        orig = m.origin
        sql = f'SELECT * FROM "messages" WHERE "{orig}" = \'{reply_to}\''
        cur = self.cur.execute(sql)

        if cur.rowcount == 0:
            self.new_message(m)
            return None

        for row in cur:
            for i, client in enumerate(self.get_linked_clients(c_id)):
                if client.name != orig:
                    util.run_in_thread(client.send_message, (m, c_id, row[i]))

    def modify_message(self, m: Message, m_id: str) -> None:
        ...

    def recall_message(self, m_id: str) -> None:
        ...

    def start(self) -> None:
        ...

    def join(self) -> None:
        ...

    def add_link(self, c_id: str, msgr: "Messenger", link_c_id: str) -> None:
        self.links[msgr] = link_c_id

    def cache_prefix(self, id="") -> str:
        return f"{self.name}_{id}."

    """
    def __init__(self, name: str) -> None:
        self.clients: List[Messenger] = []
        self.con = sqlite3.connect(f"{name}.db", check_same_thread=False)
        self.cur = self.con.cursor()
        self.name = name
    """

    @property
    def client_names(self) -> List[str]:
        return [client.name for client in self.clients]

    def join(self):
        # TODO
        pass

    def new_message(self, m: Message):
        for client in self.get_linked_clients(m.origin_id):
            client.send_message(m, self.links[client])

    def new_entry(self, m: Message) -> None:
        origin_id = m.origin_m_id
        origin = m.origin

        conn = self.get_connection(m.origin_c_id)
        entry = (origin_id if origin == s else None for s in self.client_names)
        q = Query.into(self.table).insert(*tuple(entry))
        util.update_db(conn, str(q))

    # FIXME
    def update_entry(self, conn: SQLConn, m: Message, sent_id: str) -> None:  # noqa

        sql = f'UPDATE "messages" SET "{self.name}" = \'{sent_id}\' WHERE "{m.origin}" = \'{m.origin_m_id}\''  # noqa
        # q = Query.update(self.table).set(sent_messenger, sent_id).where(m.origin == m.origin_id) # noqa
        util.update_db(conn, sql)

    def add_client(self, client):
        self.clients.append(client)

    def modify_message(self, m: Message) -> None:
        orig = m.origin
        sent_id = m.origin_m_id
        sql = f'SELECT * FROM "messages" WHERE "{orig}" = \'{sent_id}\''
        cur = self.cur.execute(sql)
        for row in cur:
            for i, client in enumerate(self.clients):
                if client.name != orig:
                    util.run_in_thread(client.modify_message, (m, row[i]))
        ...

    def recall_message(self, orig: str, recalled_id: str) -> None:
        sql = f'SELECT * FROM "messages" WHERE "{orig}" = \'{recalled_id}\''
        cur = self.cur.execute(sql)
        for row in cur:
            for i, client in enumerate(self.clients):
                if client.name != orig:
                    util.run_in_thread(client.recall_message, (row[i],))

    def init_database(self, keep_data=True):
        columns = tuple(
            Column(s, "VARCHAR(255)", nullable=True) for s in self.client_names
        )
        if not keep_data:
            self.execute_sql('DROP TABLE IF EXISTS "messages"')
            create_table = Query.create_table("messages").columns(*columns)
            self.execute_sql(str(create_table))
        self.table = Table("messages")
