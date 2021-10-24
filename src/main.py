from cons import *
from query import parse_query, daily_verse
from datetime import datetime, time, timedelta
import asyncio
import discord


def main():
    client = discord.Client()
    WHEN = time(4, 0, 0)  # 4:00 AM UTC
    default_channel_id = 456178384016244738

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

    async def called_once_a_day():
        await client.wait_until_ready()
        channel = client.get_channel(default_channel_id)
        await channel.send(embed=daily_verse())

    async def background_task():
        now = datetime.utcnow()
        if now.time() > WHEN:
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
            seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(seconds)
        while True:
            now = datetime.utcnow()
            target_time = datetime.combine(now.date(), WHEN)
            seconds_until_target = (target_time - now).total_seconds()
            await asyncio.sleep(seconds_until_target)
            await called_once_a_day()
            tomorrow = datetime.combine(now.date() + timedelta(days=1), time(0))
            seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(seconds)

    client.loop.create_task(background_task())
    client.run(getenv("bot_token"))


if __name__ == "__main__":
    main()
