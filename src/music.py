import discord
import re
from cons import *
from discord.utils import get

import yt_dlp as youtube_dl
import asyncio
import time





queue = asyncio.Queue()
voice_client = None


def parse_youtube_link(url):
    youtube_re = r'((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?'
    match = re.search(youtube_re, url)
    
    if not match: return None
    
    return {
        "protocol": match.group(1),
        "subdomain": match.group(2),
        "domain": match.group(3),
        "is_nocookie": bool(match.group(4)),
        "path": match.group(5),
        "video_id": match.group(6),
        "query_string": match.group(7)
    }
    
def get_youtube_url(search_query):
    ydl_opts = {
        'default_search': 'ytsearch1',
        'format': 'bestaudio/best',
        'quiet': True
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(search_query, download=False)
        if 'entries' in search_results:
            video_url = search_results['entries'][0]['webpage_url']
            return video_url
        else:
            return None

def correct_levitating(query, url):
    if "levitating" in query.lower():
        return "https://www.youtube.com/watch?v=1j_XvebOg4c"
    return url


async def leave(client, message, _):
     global voice_client
     voice_client = None
     for x in client.voice_clients:
        if x.server_id == message.guild.id:
            await x.disconnect()
        return actions.REACT, "✅"
     return actions.ERR, discord.Embed(description=f"I'm not in a VC",)
     

async def join(client, message, voice, url_to_play=None):
        global voice_client
        perms = voice.channel.permissions_for(message.guild.me)
        if not perms.connect:
            err_embed = discord.Embed(title="*No Permission*", description=f"I can't connect to `{voice.channel}`",)
            return actions.ERR, err_embed
        try:
            voice_client = await voice.channel.connect()
            
        except discord.ClientException:
            await leave(client, message, voice)
            voice_client = await voice.channel.connect()
        
        if url_to_play is not None:
            await queue.put(url_to_play)
        
        while True:
            url = await queue.get()
            await play_url(voice_client, url)
            
            while voice_client.is_playing(): await asyncio.sleep(1) # Father forgive me for I have sinned

        await leave()
        return actions.SEND, "Idle timeout; Leaving vc."

async def add_url(client,message, voice, url):
    global voice_client
    if voice_client is None:
        return await join(client, message, voice, url)
    await queue.put(url)
    return actions.SEND, "Adding to queue for master"

async def play_url(vc, url):
    def after_playing(error):
        if error:
            print('Error while playing song:', error)
        else:
            print('Song finished playing')
        

    ydl_opts = {
        'format': 'best[height<=480]',
        'skip_download': True,
        'youtube_include_dash_manifest': False,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        audio_url = info_dict.get("url", None)

    audio_source = discord.FFmpegPCMAudio(audio_url)
    vc.play(audio_source, after=after_playing)
    
    return actions.REACT, "✅"

async def play(client, message, voice):
    parsed = parse_youtube_link(message.content)
    if parsed:
        url = f'https://www.youtube.com/watch?v={parsed["video_id"]}"'
        return await add_url(client, message, voice, url)
    
    # Leave only search query
    query = message.content
    match = re.match(r"^\s*\./play\s+", message.content)
    query = query[match.end():]

    url = get_youtube_url(query)
    if not url:
        return actions.ERR, discord.Embed(description=f"Couldn't find a youtube video matching your query",)
    
    url = correct_levitating(query, url)

    ret = await add_url(client, message, voice, url)
    if ret[0] == actions.ERR:
        return ret
    return actions.REPLY, f"Playing {query}"


async def test_push(client, message, voice):
    queue.put(message.content)
    return actions.REPLY, f"{queue.qsize()}"

async def test_pop(client, message, voice):
    return actions.REPLY, f"{queue.get()}"


async def get_queue(client, message, voice):
    global queue
    tmp = queue
    queue = message.content
    return actions.REPLY, tmp


async def handle_music(client, message):
    voice = message.author.voice
    commands = [
        (r"^\s*\./push\s+", test_push),
        (r"^\s*\./pop\s*", test_pop),
        (r"^\s*\./leave\s*$", leave),
        (r"^\s*\./queue\s*$", get_queue),
    ]
    for rgx, func in commands:
        if re.match(rgx, message.content):
            return await func(client, message, voice)

    if re.match(r"^\s*\./join\s*$", message.content):
        asyncio.create_task(join(client, message, voice))
        return actions.IGNORE, None

    vc_commands = [ 
         (r"^\s*\./play\s+", play),
    ]
    not_in_voice = voice is None or not isinstance(voice, discord.member.VoiceState)
    for rgx, func in vc_commands:

        if re.match(rgx, message.content):
            if not_in_voice:
                return actions.REPLY, "Join a voice channel first"
            else:
                return await func(client, message, voice)
        
    
    
    err_embed = discord.Embed(title="*wrong music syntax*", description="see: `?help`",)

    return actions.ERR, err_embed