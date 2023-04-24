import re
import textwrap
from datetime import timezone
from io import BytesIO
from discord.utils import get

import discord
import pytz
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from cons import *

BACKGROUND_COLOR = (48, 51, 56)
TEXT_COLOR = (218, 222, 225)
DATE_COLOR = (147, 155, 163)
IMAGE_WIDTH = 450
IMAGE_HEIGHT = 70
EMOJI_WIDTH = 5
pfp_size = 40
pfp_padding = 65
wrap = 40

text_font = ImageFont.truetype("dejavu-sans.ttf", 14)
username_font = ImageFont.truetype("dejavu-sans.ttf", 16)
date_font = ImageFont.truetype("dejavu-sans.ttf", 11)


def resize_to_20(image):
    width, height = image.size
    print(image.size)
    ratio = 20 / max(width, height)
    width = int(width * ratio)
    height = int(height * ratio)
    image = image.resize((width, height))
    return image, width, height

def draw_image_url(image, url, x, y):
    size = 20
    draw = ImageDraw.Draw(image)
    emoji_width = draw.textsize(' ' * EMOJI_WIDTH, font=text_font)[0]

    response = requests.get(url, f"{url}?size={size}")
    emoji_image = Image.open(BytesIO(response.content)).convert("RGBA")
    
    emoji_image, width, height = resize_to_20(emoji_image)

    mask = emoji_image.split()[-1]
    emoji_image.putalpha(mask)

    x += (10 - width // 2)
    y += (10 - height // 2)

    image.paste(emoji_image, (x-emoji_width, y), emoji_image)


def parse_text(client, message, emojis=None):
    emojis = {} if emojis is None else emojis
    global IMAGE_HEIGHT
    image_height = IMAGE_HEIGHT
    text = message.content
    
    # Parse Mentions
    while True:
        match = re.search(r"<@([0-9]+)>", text)
        if not match:
            break

        user = message.guild.get_member(int(match[1]))
        text = text.replace(match[0], f"@{user.nick or user.name}")
    
    # Parse Emojis
    while True:
        match = re.search(r"<a?:([0-9a-zA-Z_-]+):([0-9]+)>", text)
        if not match:
            break

        name = match[1]
        emoji = get(client.emojis, name=name)
        emojis[name] = emoji.url

        text = text.replace(match[0], f":{name}:")

    # Wrap text and parse newlines
    image = Image.new('RGB', (IMAGE_WIDTH, image_height), color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    sum_height = 0
    text_lines = []
    for line in text.split('\n'):
        wrapped = textwrap.wrap(line, width=wrap)
        if not wrapped:
            wrapped.append(" ")
        print(wrapped)
        for wrapped_line in wrapped:
            text_lines.append(wrapped_line)
            sum_height += draw.textsize(wrapped_line, font=text_font)[1]
    
    # Update image_height
    if len(text_lines) > 1:
        image_height += sum_height
    
    return text_lines, image_height


def paste_profile_pic(image, url, author_id):
    response = requests.get(url)

    if author_id == OLD_TUS_ID:
        response = requests.get(OLD_TUS_PFP_URL)
    profile_picture = Image.open(BytesIO(response.content))

    # Add alpha channel to the image
    profile_picture = profile_picture.convert("RGBA")

    # Create a circular mask
    mask = Image.new('L', (pfp_size, pfp_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, pfp_size, pfp_size), fill=255)

    # Apply the mask to the profile picture
    profile_picture = ImageOps.fit(profile_picture, mask.size, centering=(pfp_size/100, pfp_size/100))
    profile_picture.putalpha(mask)

    # Paste the profile picture onto the image
    image.paste(profile_picture, (10, 10), mask)


def draw_role_and_date(image, author, created_at):
    # Get the user's highest role
    highest_role = author.top_role

    # Get the role color
    role_color = highest_role.color.to_rgb()

    # Check if the role has a custom icon
    has_custom_icon = highest_role.display_icon is not None

    # Load the role icon if it exists
    role_icon = None
    if has_custom_icon:
        url = None
        if isinstance(highest_role.display_icon, discord.asset.Asset):    
            role_icon_url = highest_role.display_icon.url
            if "?size=" in role_icon_url:
                role_icon_url = role_icon_url[:role_icon_url.find("?size=")]
            url = f"{role_icon_url}?size=20"
            
        else: # it's probably emoji string then
            hex_emoji_api = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72"
            base = highest_role.display_icon.encode('unicode_escape').decode()
            hex_emoji = ""
            for word in re.findall(r'\\U([0-9a-f]+)', base):
                hex_emoji += word.lstrip('0') + "-"
            hex_emoji = hex_emoji.rstrip("-")
            url = f"{hex_emoji_api}/{hex_emoji}.png"
        
        response = requests.get(url)
        role_icon = Image.open(BytesIO(response.content)).convert("RGBA")
        role_icon, _, _ = resize_to_20(role_icon)

  

    # Create a draw object for the image
    draw = ImageDraw.Draw(image)

    # Draw the username and message text onto the image
    username = author.display_name
    if author.id == OLD_TUS_ID:
        username = "Թուս the Gray Մոմենտ"
    username_width = draw.textsize(username, font=username_font)[0]
    username_color = tuple(role_color)
    draw.text((pfp_padding, 10), username, font=username_font, fill=username_color)
    
    # Paste the role icon
    if role_icon:
        image.paste(role_icon, (pfp_padding + username_width + 4, 20 - role_icon.size[1]//2), role_icon)

    # Draw the date
    date = created_at.strftime('%m/%d/%Y %I:%M %p')
    draw.text((pfp_padding + username_width + 7 + (20 if role_icon else 0), 14), date, font=date_font, fill=DATE_COLOR)


def draw_message(image, text_lines, emoji_map):
    sum_height = 0
    draw = ImageDraw.Draw(image)
    for line in text_lines:
        line_height = draw.textsize(line, font=text_font)[1]
        left_padding = 0
        while True:
            match = re.search(r":([0-9a-zA-Z_-]+):", line)
            if not match:
                break
            
            name = match[1]
            url = emoji_map[name]

            # Cut everyting before emoji, and leave everything after it
            before_text, line = line.split(f":{name}:", 1)

            # Draw text before emoji leaving blank space for emoji
            before_text += (EMOJI_WIDTH * ' ')
            draw.text((left_padding + pfp_padding+2, 35+sum_height), before_text, font=text_font, fill=TEXT_COLOR)
            left_padding += draw.textsize(before_text, font=text_font)[0]

            # Paste emoji
            draw_image_url(image, url, left_padding + pfp_padding + 2, 35 + sum_height)

        draw.text((left_padding + pfp_padding+2, 35+sum_height), line + "\n", font=text_font, fill=TEXT_COLOR)
        sum_height += line_height


def create_message_image(client, message):
    global BACKGROUND_COLOR, TEXT_COLOR, DATE_COLOR, IMAGE_WIDTH, pfp_size, pfp_padding, wrap
    created_at = message.created_at.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone("Asia/Yerevan"))
    author = message.author
    if author.id == OLD_TUS_ID:
        author = message.guild.get_member(TUS_ID)
    emoji_map = {}
    text_lines, image_height = parse_text(client, message, emoji_map)
    
    image = Image.new('RGB', (IMAGE_WIDTH, image_height), color=BACKGROUND_COLOR)

    paste_profile_pic(image, author.avatar.url, message.author.id)

    draw_role_and_date(image, author, created_at)

    draw_message(image, text_lines, emoji_map)

    image.save('message.png')


if __name__ == "__main__":
    client = discord.Client(intents=discord.Intents.all())


    @client.event
    async def on_ready():
        print('Logged in as')
        print(client.user.name)
        print(client.user.id)
        print('------')


    @client.event
    async def on_message(message):
        if message.author.id == 213341816324489217:
            print(message.content)
            create_message_image(f"{message.content}", message.author, message.created_at)
            with open('message.png', 'rb') as f:
                await message.channel.send(file=discord.File(f))
        
    client.run(getenv("bot_token"))
