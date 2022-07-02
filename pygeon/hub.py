import sqlite3
from messenger.messenger import Messenger

import asyncio

from typing import List

from pypika import Query, Column


class Hub:
    def __init__(self) -> None:
        self.clients: List[Messenger] = []
        self.con = sqlite3.connect("pygeon.db", check_same_thread=False)
        self.cur = self.con.cursor()

    def start(self):
        for client in self.clients:
            client.start()
        for client in self.clients:
            client.join()

    def new_message(self, message, source):
        for client in self.clients:
            if client is source:
                continue
            asyncio.run(client.send_message(message))

    def add_client(self, client):
        self.clients.append(client)

    def record_message(self, message):
        # TODO
        ...

    def init_database(self):
        columns = tuple(
            Column(type(c).__name__, "VARCHAR(255)", nullable=True)
            for c in self.clients
        )
        create_table = Query.create_table("messages").columns(columns)
        self.execute_sql(str(create_table))
        print(create_table)

    def execute_sql(self, query: str) -> None:
        self.cur.execute(query)
        self.con.commit()
