import discord
import requests
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from cons import *

BACKGROUND_COLOR = (48,51,56)
TEXT_COLOR = (218,222,225)
DATE_COLOR = (147,155,163)
IMAGE_WIDTH = 450
IMAGE_HEIGHT = 70
pfp_size = 40
pfp_padding = 65
wrap = 40

text_font = ImageFont.truetype("dejavu-sans.ttf", 14)
username_font = ImageFont.truetype("dejavu-sans.ttf", 16)
date_font = ImageFont.truetype("dejavu-sans.ttf", 11)



def create_message_image(text, author, created_at):
    global BACKGROUND_COLOR, TEXT_COLOR, DATE_COLOR, IMAGE_WIDTH, IMAGE_HEIGHT, pfp_size, pfp_padding, wrap

    # Create a new image
    image = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color = BACKGROUND_COLOR)


    # Calculate overall height
    draw = ImageDraw.Draw(image)
    sum_height = 0
    lines = textwrap.wrap(text, width=wrap)
    for line in lines:
        sum_height += draw.textsize(line, font=text_font)[1]

    if len(lines) > 1:
        IMAGE_HEIGHT += sum_height
        image = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color = BACKGROUND_COLOR)

    # Load the profile picture
    response = requests.get(author.avatar.url)
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

    # Get the user's highest role
    highest_role = author.top_role

    # Get the role color
    role_color = highest_role.color.to_rgb()

    


    # Check if the role has a custom icon
    has_custom_icon = highest_role.display_icon is not None

    # Load the role icon if it exists
    if has_custom_icon and highest_role.display_icon.url:
        role_icon_url = highest_role.display_icon.url
        print(f"{role_icon_url=}")
        if "?size=" in role_icon_url:
            role_icon_url = role_icon_url[:role_icon_url.find("?size=")]
        

        response = requests.get(f"{role_icon_url}?size=20")
        role_icon = Image.open(BytesIO(response.content))
        role_icon_size = role_icon.size
        role_icon = role_icon.resize(role_icon_size)
    else:
        role_icon = None

    # Create a draw object for the image
    draw = ImageDraw.Draw(image)

    # Draw the username and message text onto the image
    username = author.display_name
    username_width = draw.textsize(username, font=username_font)[0]
    username_color = tuple(role_color)
    draw.text((pfp_padding, 10), username, font=username_font, fill=username_color)
    
    # Paste the role icon
    if role_icon:
        image.paste(role_icon, (pfp_padding + username_width + 4, 20 - role_icon.size[1]//2), role_icon)

    # Draw the date
    date = created_at.strftime('%m/%d/%Y %I:%M %p')
    draw.text((pfp_padding + username_width + 7 + (20 if role_icon else 0),14), date, font=date_font, fill=DATE_COLOR)

    text_lines = textwrap.wrap(text, width=wrap)
    sum_height = 0
    for line in text_lines:
        draw.text((pfp_padding+2, 35+sum_height), line + "\n", font=text_font, fill=TEXT_COLOR)
        sum_height += draw.textsize(line, font=text_font)[1]

    # Save the image
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
