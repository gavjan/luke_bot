import discord
import re
from cons import *
from discord.utils import get

import yt_dlp as youtube_dl
import asyncio
import time


queues = {}
voice_clients = {}
now_playing_msg = {}


def parse_youtube_link(query):
    youtube_re = r'((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?'
    match = re.search(youtube_re, query)
    
    if match:
        parsed =  {
            "protocol": match.group(1),
            "subdomain": match.group(2),
            "domain": match.group(3),
            "is_nocookie": bool(match.group(4)),
            "path": match.group(5),
            "video_id": match.group(6),
            "query_string": match.group(7)
        }
        return f'https://www.youtube.com/watch?v={parsed["video_id"]}"'
    
    
    # Leave only search query
    match = re.match(r"^\s*\./play\s+", query)
    query = query[match.end():]

    return get_youtube_url(query)
    
def get_youtube_url(search_query):
    ydl_opts = {
        'default_search': 'ytsearch1',
        'format': 'bestaudio/best',
        'quiet': True
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(search_query, download=False)
        if 'entries' in search_results and search_results['entries']:
            video_url = search_results['entries'][0]['webpage_url']
            return video_url
        else:
            return None
def int_to_emojis(num):
    digit_emojis = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
    if 0 <= num < 10:
        return [digit_emojis[num]]
    return ['🔟', '➕']

async def play(client, message, voice):
    url = parse_youtube_link(message.content)
    id = message.guild.id

    if not url:
        return actions.ERR, discord.Embed(description=f"Couldn't find a song on youtube matching your query",)

    if id not in voice_clients or not voice_clients[id].is_connected:
        return await join(client, message, voice, url)
    await queues[id].put(url)

    return actions.REACT, ["📥"] + int_to_emojis(queues[id].qsize())


async def leave(client, message, _):
    id = message.guild.id

    if id in voice_clients:
        # Wake-up music player and tell him to kill himself
        await queues[id].put("kys")
        del voice_clients[id]

    # Disconnect from discord vc
    for x in client.voice_clients:
        if x.guild.id == id:
            await x.disconnect()
            return actions.IGNORE, None

    return actions.ERR, discord.Embed(description=f"I'm not in a VC",)
     

async def play_url(vc, url):    
    ydl_opts = {
        'format': 'best[height<=480]',
        'skip_download': True,
        'youtube_include_dash_manifest': False,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        audio_url = info_dict.get("url", None)

    audio_source = discord.FFmpegPCMAudio(audio_url)
    
    vc.play(audio_source)

async def join(client, message, voice, url_to_play=None):
        id = message.guild.id
        perms = voice.channel.permissions_for(message.guild.me)
        if not perms.connect:
            err_embed = discord.Embed(title="*No Permission*", description=f"I can't connect to `{voice.channel}`",)
            return actions.ERR, err_embed
        try:
            voice_clients[id] = await voice.channel.connect()
            
        except discord.ClientException:
            await leave(client, message, voice)
            voice_clients[id] = await voice.channel.connect()
        
        queues[id] = asyncio.Queue()
        if url_to_play is not None:
            await queues[id].put(url_to_play)
        
        while True:
            url = await queues[id].get()
            if url == "kys":
                return (actions.IGNORE, None)

            await play_url(voice_clients[id], url)
            now_playing = await message.channel.send(f" Now playing {url}")
            
            # Wait until playback finishes
            while id in voice_clients and voice_clients[id].is_playing():
                await asyncio.sleep(1) # Father forgive me for I have sinned
            await now_playing.delete()

        await leave()
        return actions.SEND, "Idle timeout; Leaving vc."
    

async def skip(client, message, voice):
    vc = voice_clients[message.guild.id]
    vc.stop()
    return actions.IGNORE, None

def get_help(commands, vc_commands):
    markdown = ""
    for pattern, _, description in vc_commands+commands:
        for c in ['\s', '*', '^', '\\', '+', '$']:
            pattern = pattern.replace(c, '')
        
        markdown += f"`{pattern}` - {description}\n"

    return actions.REPLY, markdown

async def handle_music(client, message):
    voice = message.author.voice
    commands = [
        (r"^\s*\./leave\s*$", leave, "Leave (mean)"),
        (r"^\s*\./join\s*$", join, "Join your voice channel"),
    ]
    vc_commands = [ 
         (r"^\s*\./play\s+", play, "Play song from [link] or Youtube Title"),
         (r"^\s*\./(skip|next)\s*$", skip, "Skip to next song in queue")
    ]
    for rgx, func, _ in commands:
        if re.match(rgx, message.content):
            return await func(client, message, voice)

    #if re.match(r"^\s*\./join\s*$", message.content):
        #asyncio.create_task(join(client, message, voice))
    #    return actions.IGNORE, _
    if re.match(r"^\s*\./help\s*$", message.content):
        return get_help(commands, vc_commands)

    not_in_voice = voice is None or not isinstance(voice, discord.member.VoiceState)
    for rgx, func, _ in vc_commands:
        if re.match(rgx, message.content):
            if not_in_voice:
                return actions.REPLY, "Join a voice channel first"
            else:
                return await func(client, message, voice)
        
    err_embed = discord.Embed(title="*wrong music syntax*", description="see: `./help`",)

    return actions.ERR, err_embed