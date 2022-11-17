import tomli
from .messenger.slack import Slack
from .messenger.discord import Discord
from .messenger.cqhttp import CQHttp
from .messenger import Hub
from typing import List


def main():
    with open("bygeon.toml", "rb") as f:
        config = tomli.load(f)

    client_configs = config["Clients"]
    hubs: List[Hub] = []

    if discord_config := client_configs.get("Discord") != None:
        discord = Discord(
            bot_token = discord_config["bot_token"],
        )

    if slack_config := client_configs.get("Slack") != None:
        slack = Discord(
            app_token = slack_config["app_token"],
            bot_token = slack_config["bot_token"],

        )

    if cqhttp_config := client_configs.get("CQHttp") != None:
        slack = Discord(
            bot_token = discord_config["bot_token"],
            channel_id = discord_config["channel_id"],
        )


    hub_configs = config["hubs"]
    for (i, hub_config) in enumerate(hub_configs):
        hub_name = hub_config.get("name", f"HUB-{i}")
        keep_data = hub_config["keep_data"]

        hub = Hub(hub_name)
        hubs.append(hub)

        
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
