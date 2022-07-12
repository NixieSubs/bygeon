import tomli
from .messenger.slack import Slack
from .messenger.discord import Discord
from .messenger.cqhttp import CQHttp
from .hub import Hub
from typing import List


def main():
    with open("bygeon.toml", "rb") as f:
        config = tomli.load(f)

    hub_configs = config["Hubs"]
    hubs: List[Hub] = []

    for (i, hub_config) in enumerate(hub_configs):
        hub_name = hub_config.get("name", f"HUB-{i}")
        keep_data = hub_config["keep_data"]

        hub = Hub(hub_name)
        hubs.append(hub)

        if hub_config.get("Discord") != None:
            discord = Discord(
                bot_token=hub_config["Discord"]["bot_token"],
                channel_id=hub_config["Discord"]["channel_id"],
                hub=hub,
            )
            hub.add_client(discord)
        if hub_config.get("Slack") != None:
            slack = Slack(
                app_token=hub_config["Slack"]["app_token"],
                bot_token=hub_config["Slack"]["bot_token"],
                channel_id=hub_config["Slack"]["channel_id"],
                hub=hub,
            )
            hub.add_client(slack)
        if hub_config.get("CQHttp") != None:

            ws_url = hub_config["CQHttp"].get("ws_url", "ws://localhost:8080/")
            http_url = hub_config["CQHttp"].get("ws_url", "http://localhost:5700/")

            cqhttp = CQHttp(
                group_id=hub_config["CQHttp"]["group_id"],
                hub=hub,
                ws_url=ws_url,
                http_url=http_url,
            )

            hub.add_client(cqhttp)

        hub.init_database(keep_data=keep_data)
        hub.start()

    for hub in hubs:
        hub.join()
