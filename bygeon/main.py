import tomli
# from .messenger.slack import Slack
from .messenger.discord import Discord
from .messenger.cqhttp import CQHttp
from .messenger.messenger import Messenger, Hub
from typing import List


def main() -> None:
    with open("bygeon.toml", "rb") as f:
        config = tomli.load(f)

    client_configs = config["Clients"]

    clients: List[Messenger] = []

    if discord_config := client_configs.get("Discord"):
        discord = Discord(
            discord_config["bot_token"],
            discord_config["guild_id"]
        )
        clients.append(discord)

    """
    if slack_config := client_configs.get("Slack"):
        slack = Slack(
            slack_config["app_token"],
            slack_config["bot_token"],
            slack_config["channel_id"]
        )
        clients.append(slack)
    """

    if cqhttp_config := client_configs.get("CQHttp"):
        ws_url = cqhttp_config.get("ws_url", "ws://localhost:8080/")
        http_url = cqhttp_config.get("http_url", "http://localhost:5700/")

        cqhttp = CQHttp(
            ws_url,
            http_url
        )
        clients.append(cqhttp)
    
    hub_configs = config["Hubs"]
    for (i, hub_config) in enumerate(hub_configs):
        hub_name = hub_config.get("name", f"HUB-{i}")
        keep_data = hub_config.get("keep_data", True)
        hub = Hub(hub_name, keep_data)
        """
        if hub_slack := hub_config.get("Slack"):
            c_id = hub_slack["channel_id"]
            slack.add_hub(c_id, hub)
            hub.add_linkee(slack, c_id)
        """
        if hub_discord := hub_config.get("Discord"):
            c_id = hub_discord["channel_id"]
            discord.add_hub(c_id, hub)
            hub.add_linkee(discord, c_id)
        if hub_cqhttp := hub_config.get("CQHttp"):
            c_id = hub_cqhttp["group_id"]
            discord.add_hub(c_id, hub)
            hub.add_linkee(cqhttp, c_id)
        hub.init_database(keep_data)

    for client in clients:
        client.start()
        client.join()
