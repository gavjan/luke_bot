from cons import *
from query import parse_query, daily_verse, todays_holiday
from datetime import datetime, time, timedelta
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord.ext import commands
from discord.utils import get
import asyncio
import discord
import subprocess

def main():
    subprocess.call(["pip3", "uninstall", "discord"])
    subprocess.call(["pip3", "uninstall", "discord.py"])
    subprocess.call(["pip3", "install", "discord"])
    # client = discord.Client()
    WHEN_VERSE = time(16, 0, 0)  # 4:00 PM UTC
    WHEN_HOLIDAY = time(4, 0, 0)  # 4:00 AM UTC
    default_channel_id = 456178384016244738

    client = commands.Bot(command_prefix="!")
    slash = SlashCommand(client, sync_commands=True)

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
            elif action == actions.DM:
                await message.author.send(embed=response)
                await message.add_reaction("🇩")
                await message.add_reaction("🇲")
            elif action == actions.REACT:
                for emoji_id in response:
                    emoji = get(client.emojis, name=emoji_id)
                    await message.add_reaction(emoji or emoji_id)
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
        await channel.send(embed=daily_verse())

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
