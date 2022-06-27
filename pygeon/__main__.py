import tomli
from messenger import slack
from messenger import discord

if __name__ == "__main__":
    with open("pygeon.toml", "rb") as f:
        config = tomli.load(f)

    slack_token = config["Slack"]["app_token"]
    slack_app = slack.Slack(slack_token)

    discord_token = config["Discord"]["token"]
    discord_app = discord.Discord(discord_token)

    #discord_app.start()
    slack_app.start()

    #discord_app.join()
    slack_app.join()
