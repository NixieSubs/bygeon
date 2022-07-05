import sqlite3
from messenger.messenger import Messenger
from message import Message

import asyncio
from asyncio import Task

from typing import List, Tuple

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
                task = asyncio.create_task(client.send_message(message))
                task.add_done_callback(self.update_entry)

    def new_entry(self, message: Message) -> None:
        origin_id = message.origin_id
        origin = message.origin
        entry = (origin_id if origin == s else None for s in self.client_names)
        q = Query.into(self.table).insert(*tuple(entry))
        self.execute_sql(str(q))

    def update_entry(self, task: Task[Tuple[Message, str, str]]) -> None:
        result = task.result()
        m, c, mid = result
        q = Query.update(self.table).set(c, mid).where(m.origin == m.origin_id)
        self.execute_sql(str(q))

    def add_client(self, client):
        self.clients.append(client)

    def record_message(self, message):
        # TODO
        ...

    def init_database(self):
        columns = tuple(
            Column(s, "VARCHAR(255)", nullable=True) for s in self.client_names
        )
        create_table = Query.create_table("messages").columns(*columns)
        self.execute_sql(str(create_table))
        self.table = Table("messages")

    def execute_sql(self, query: str) -> None:
        print(query)
        self.cur.execute(query)
        self.con.commit()
