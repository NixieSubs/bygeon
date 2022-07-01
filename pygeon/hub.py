import sqlite3
from messenger.messenger import Messenger

import asyncio

from typing import List


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
