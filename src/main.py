from cons import *
from query import parse_query, daily_verse, todays_holiday, process_reaction
from datetime import datetime, time, timedelta
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord.ext import commands
from discord.utils import get
import asyncio
import discord


def main():
    WHEN_VERSE = time(16, 0, 0)  # 4 PM UTC
    WHEN_HOLIDAY = time(4, 0, 0)  # 4 AM UTC
    default_channel_id = 456178384016244738

    client = commands.Bot(command_prefix="!")
    slash = SlashCommand(client, sync_commands=True)

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
            for action, response in parse_query(message):
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

                elif action == actions.EXIT:
                    await message.reply(response)
                    exit(0)
        except Exception as e:
            if ignore_errors.has(e.code):
                return

            err_exit(e)

    async def daily_verse_task():
        await client.wait_until_ready()
        channel = client.get_channel(default_channel_id)
        action, response = daily_verse()
        await channel.send(embed=response)

    async def daily_holiday_task():
        await client.wait_until_ready()
        channel = client.get_channel(default_channel_id)
        action, response = todays_holiday()
        if action == actions.EMBED:
            await channel.send(embed=response)

    async def background_task(func, when):
        now = datetime.utcnow()
        if now.time() > when:
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
            seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(seconds)
        while True:
            now = datetime.utcnow()
            target_time = datetime.combine(now.date(), when)
            seconds_until_target = (target_time - now).total_seconds()
            await asyncio.sleep(seconds_until_target)
            await func()
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
            seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(seconds)

    @slash.slash(
        name="pray",
        description="Pray to God",
        guild_ids=[839493198371356672, 456178384016244736],
        options=[
            create_option(
                name="text",
                description="Your prayer",
                required=True,
                option_type=3
            )
        ]
    )
    async def pray(ctx: SlashContext, text: str):
        embed = discord.Embed(title="Anonymous Prayer", description=text, color=discord.Color.blue())
        prayer = await ctx.channel.send(embed=embed)
        await ctx.send(content="Prayer Sent!", delete_after=0.01)
        await prayer.add_reaction("🙏")

    client.loop.create_task(background_task(daily_verse_task, WHEN_VERSE))
    client.loop.create_task(background_task(daily_holiday_task, WHEN_HOLIDAY))
    client.run(getenv("bot_token"))


if __name__ == "__main__":
    main()
