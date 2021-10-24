from cons import *
from query import parse_query
import discord


def main():
    client = discord.Client()

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Holy Music"))
        print(f"started {client}")

    @client.event
    async def on_message(message):
        try:
            if message.author == client.user:
                return
            action, response = parse_query(message)
            if action == actions.SEND:
                await message.channel.send(response)
            elif action == actions.REPLY:
                await message.reply(response)
            elif action == actions.ERR:
                await message.reply(embed=response)
            elif action == actions.EMBED:
                await message.channel.send(embed=response)
            elif action == actions.EXIT:
                await message.reply(response)
                exit(0)
        except Exception as e:
            err_exit(e)

    client.run(getenv("bot_token"))


if __name__ == "__main__":
    main()
