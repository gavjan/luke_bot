from cons import err_exit
import discord
import os

ADMIN_ID = 213341816324489217
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
            elif message.content.startswith("/hello"):
                await message.channel.send("Astcu barev")
            elif message.content.startswith("/restart_luke") and message.author.id == ADMIN_ID:
              await message.reply("ok")
              exit(0)
        except Exception as e:
            err_exit(e)

    client.run(os.getenv("bot_token"))


if __name__ == "__main__":
    main()
