import discord
import re
from cons import *
from discord.utils import get
import yt_dlp as youtube_dl


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
     for x in client.voice_clients:
        print(x)
        if x.server_id == message.guild.id:
            await x.disconnect()
        return actions.REACT, "✅"
     return actions.ERR, discord.Embed(description=f"I'm not in a VC",)
     

async def join(client, message, voice):
        perms = voice.channel.permissions_for(message.guild.me)
        if not perms.connect:
            err_embed = discord.Embed(title="*No Permission*", description=f"I can't connect to `{voice.channel}`",)
            return actions.ERR, err_embed
        try:
            return await voice.channel.connect()
            
        except discord.ClientException:
            await leave(client, message, voice)
            return await voice.channel.connect()
            
async def play_url(client, message, voice, url):
    ret = await join(client, message, voice)
    if not isinstance(ret, discord.voice_client.VoiceClient):
        return ret
    voice_client = ret

    ydl_opts = {
        'format': 'bestaudio/best'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        audio_url = info_dict.get("url", None)

    audio_source = discord.FFmpegPCMAudio(audio_url)
    voice_client.play(audio_source)
    
    
    return actions.REACT, "✅"

async def play(client, message, voice):
    parsed = parse_youtube_link(message.content)
    if parsed:
        url = f'https://www.youtube.com/watch?v={parsed["video_id"]}"'
        return await play_url(client, message, voice, url)
    
    # Leave only search query
    query = message.content
    match = re.match(r"^\s*\./play\s+", message.content)
    query = query[match.end():]

    url = get_youtube_url(query)
    if not url:
        return actions.ERR, discord.Embed(description=f"Couldn't find a youtube video matching your query",)
    
    url = correct_levitating(query, url)

    ret = await play_url(client, message, voice, url)
    if ret[0] == actions.ERR:
        return ret
    return actions.REPLY, f"Playing {query}"


async def get_queue(client, message, voice):
    return actions.REPLY, "TODO"


async def handle_music(client, message):
    voice = message.author.voice
    commands = [
        (r"^\s*\./leave\s*$", leave),
        (r"^\s*\./queue\s*$", get_queue),
    ]
    for rgx, func in commands:
        if re.match(rgx, message.content):
            return await func(client, message, voice)

    
    vc_commands = [
         (r"^\s*\./join\s*$", join),
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