from cons import *
from query import parse_query, daily_verse, todays_holiday, process_reaction
from datetime import datetime, time, timedelta
from discord.ext import commands
from discord.utils import get
import asyncio
import discord


def main():
    WHEN_VERSE = time(16, 0, 0)  # 4 PM UTC
    WHEN_HOLIDAY = time(4, 0, 0)  # 4 AM UTC
    default_channel_id = 456178384016244738

    client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

    @client.event
    async def on_ready():
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Holy Music"))
        print(f"started {client}")

    players = {}

    @client.event
    async def on_raw_reaction_add(payload):
        await process_reaction(client, players, payload)

    @client.event
    async def on_message(message):
        try:
            if message.author == client.user:
                return
            for action, response in await parse_query(message, client):
                if action == actions.SEND:
                    await message.channel.send(response)
                elif action == actions.REPLY:
                    await message.reply(response)
                elif action == actions.ERR:
                    await message.reply(embed=response)
                elif action == actions.EMBED:
                    await message.channel.send(embed=response)
                elif action == actions.DM:
                    await message.author.send(embed=response)
                    await message.add_reaction("🇩")
                    await message.add_reaction("🇲")
                elif action == actions.REACT:
                    for emoji_id in response:
                        emoji = get(client.emojis, name=emoji_id)
                        await message.add_reaction(emoji or emoji_id)
                elif action == actions.BUTTONS:
                    sent = await message.reply(embed=response["embed"])
                    for k in to_remove_vals(players, message.author.id):
                        await rm_message(client, k[0], k[1])

                    players[(sent.channel.id, sent.id)] = (message.author.id, message.id)
                    for emoji_id in response["emojis"]:
                        emoji = get(client.emojis, name=emoji_id)
                        await sent.add_reaction(emoji or emoji_id)
                elif action == actions.REMOVE:
                    await rm_message(client, message.channel.id, message.id)
                elif action == actions.EXIT:
                    await message.reply(response)
                    exit(0)
        except Exception as e:
            if ignore_errors.has(e.code):
                return

            err_exit(e)


    client.run(getenv("bot_token"))


if __name__ == "__main__":
    main()
