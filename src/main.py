from cons import env, err_exit
import discord
import os

def main():
    client = discord.Client()

    @client.event
    async def on_ready():
        print(f"vjjjjjjjjjjj {client}")

    @client.event
    async def on_message(message):
        try:

            if message.author == client.user:
                return

            if message.content.startswith("/hello"):
                await message.channel.send("Astcu barev")
        except Exception as e:
            err_exit(e)

    client.run(os.getenv("bot_token"))


if __name__ == "__main__":
    main()
