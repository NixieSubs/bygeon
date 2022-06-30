import tomli
from messenger import slack
from messenger import discord
from hub import Hub

if __name__ == "__main__":
    with open("pygeon.toml", "rb") as f:
        config = tomli.load(f)
    slack_bot_token = config["Slack"]["token"]
    slack_app_token = config["Slack"]["app_token"]
    slack_channel_id = config["Slack"]["group_id"]
    discord_token = config["Discord"]["token"]
    discord_channel_id = config["Discord"]["group_id"]

    hub = Hub()

    hub.add_client(slack.Slack(slack_app_token, slack_bot_token, slack_channel_id,hub))
    hub.add_client(discord.Discord(discord_token, discord_channel_id,hub))
    hub.start()
