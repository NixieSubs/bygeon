import tomli
from messenger.slack import Slack
from messenger.discord import Discord
from messenger.cqhttp import CQHttp
from hub import Hub

if __name__ == "__main__":
    with open("pygeon.toml", "rb") as f:
        config = tomli.load(f)
    slack_bot_token = config["Slack"]["token"]
    slack_app_token = config["Slack"]["app_token"]
    slack_channel_id = config["Slack"]["group_id"]

    discord_token = config["Discord"]["token"]
    discord_channel_id = config["Discord"]["group_id"]

    keep_data = config["Pygeon"]["keep_data"]

    #cqhttp_group_id = config["CQHttp"]["group_id"]

    hub = Hub()

    slack = Slack(slack_app_token, slack_bot_token, slack_channel_id, hub)
    discord = Discord(discord_token, discord_channel_id, hub)
    #cqhttp = CQHttp(cqhttp_group_id, hub)
    hub.add_client(slack)
    hub.add_client(discord)
    #hub.add_client(cqhttp)
    hub.init_database(keep_data=keep_data)
    hub.start()
