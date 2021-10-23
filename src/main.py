from cons import env
import discord


def main():
    client = discord.Client()

    @client.event
    async def on_ready():
        print(f"vjjjjjjjjjjj {client}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith("/hello"):
            await message.channel.send("Astcu barev")

    client.run(env("bot_token"))


if __name__ == "__main__":
    main()
