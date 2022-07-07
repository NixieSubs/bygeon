import sqlite3
from messenger.messenger import Messenger
from message import Message

import threading

import asyncio

from typing import List

from pypika import Query, Column, Table


class Hub:
    def __init__(self) -> None:
        self.clients: List[Messenger] = []
        self.con = sqlite3.connect("pygeon.db", check_same_thread=False)
        self.cur = self.con.cursor()

    @property
    def client_names(self) -> List[str]:
        return [client.name for client in self.clients]

    def start(self):
        for client in self.clients:
            client.start()
        for client in self.clients:
            client.join()

    def new_message(self, message: Message):
        self.new_entry(message)
        for client in self.clients:
            if client.name != message.origin:
                thread = threading.Thread(target=client.send_message, args=(message,))
                thread.start()

    def new_entry(self, message: Message) -> None:
        origin_id = message.origin_id
        origin = message.origin
        entry = (origin_id if origin == s else None for s in self.client_names)
        q = Query.into(self.table).insert(*tuple(entry))
        self.execute_sql(str(q))

    # FIXME
    def update_entry(self, message: Message, sent_messenger: str, sent_id: str) -> None: # noqa
        m = message
        sql = f"UPDATE \"messages\" SET \"{sent_messenger}\" = '{sent_id}' WHERE \"{message.origin}\" = '{m.origin_id}'" # noqa
        # q = Query.update(self.table).set(sent_messenger, sent_id).where(m.origin == m.origin_id) # noqa
        self.execute_sql(sql)

    def add_client(self, client):
        self.clients.append(client)

    def reply_message(self, message: Message, reply_to: str) -> None:
        self.new_entry(message)
        orig = message.origin
        sql = f"SELECT * FROM \"messages\" WHERE \"{orig}\" = '{reply_to}'"
        cur = self.cur.execute(sql)
        for row in cur:
            for i, client in enumerate(self.clients):
                if client.name != orig:
                    thread = threading.Thread(target=client.send_reply, args=(message, row[i])) # noqa
                    thread.start()
        print(self.cur.execute(sql))

    def recall_message(self, orig: str, recalled_id: str) -> None:
        sql = f"SELECT * FROM \"messages\" WHERE \"{orig}\" = '{recalled_id}'"
        cur = self.cur.execute(sql)
        for row in cur:
            for i, client in enumerate(self.clients):
                if client.name != orig:
                    thread = threading.Thread(target=client.recall_message, args=(row[i],)) # noqa
                    thread.start()

    def init_database(self, keep_data=True):
        columns = tuple(
            Column(s, "VARCHAR(255)", nullable=True) for s in self.client_names
        )
        if not keep_data:
            self.execute_sql("DROP TABLE IF EXISTS \"messages\"")
            create_table = Query.create_table("messages").columns(*columns)
            self.execute_sql(str(create_table))
        self.table = Table("messages")

    def execute_sql(self, query: str) -> None:
        print(query)
        self.cur.execute(query)
        self.con.commit()
