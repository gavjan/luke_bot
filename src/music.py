import discord
import re
from cons import *
from discord.utils import get
import yt_dlp as youtube_dl


async def leave(client, message, _):
     for x in client.voice_clients:
        if(x.server_id == message.guild.id):
            await x.disconnect()
        return actions.REACT, "✅"
     

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
            
async def play_url(client, message, voice):
    ret = await join(client, message, voice)
    if not isinstance(ret, discord.voice_client.VoiceClient):
        return ret
    voice_client = ret
    url = message.content.replace("./play_url ", "")


    # Download the audio using youtube_dl
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
    return actions.REPLY, "./play is under development. pls use ./play_url for now"
    ret = await join(client, message, voice)
    if not isinstance(ret, discord.voice_client.VoiceClient):
        return ret
    voice_client = ret
    
    audio_source = discord.FFmpegPCMAudio('/home/cgev/Desktop/song.mp3')
    voice_client.play(audio_source)
    
    
    return actions.REACT, "✅"


async def handle_music(client, message):
    voice = message.author.voice
    if voice is None or not isinstance(voice, discord.member.VoiceState):
         return actions.REPLY, "Join a voice channel first"
    
    commands = [
         (r"^\s*\./leave\s*$", leave),
         (r"^\s*\./join\s*$", join),
         (r"^\s*\./play\s+", play),
         (r"^\s*\./play_url\s+", play_url),
    ]

    for rgx, func in commands:
        if re.match(rgx, message.content):
            return await func(client, message, voice)
    
    err_embed = discord.Embed(title="*wrong music syntax*", description="see: `?help`",)

    return actions.ERR, err_embed