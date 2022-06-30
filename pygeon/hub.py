import tomli

class Hub:
    def __init__(self):
        self.clients = []

    def start(self):
        for client in self.clients:
            client.start()
        for client in self.clients:
            client.join()

    def new_message(self, message, source):
        for client in self.clients:
            if client is source:
                continue
            client.send_message(message)

    def add_client(self, client):
        self.clients.append(client)
