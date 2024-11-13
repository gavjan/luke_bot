import discord
import re
from cons import *
import yt_dlp as youtube_dl
import asyncio
from discord.utils import get
from ytmusicapi import YTMusic # https://github.com/sigma67/ytmusicapi
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
SP_CLIENT_ID = getenv("spotify_id")
SP_CLIENT_SECRET = getenv("spotify_secret")


queues = {}
voice_clients = {}
now_playing_msg = {}

def yt_playlist_to_urls(playlist_id):
    ytmusic = YTMusic()
    playlist = ytmusic.get_playlist(playlist_id)
    video_ids = [item['videoId'] for item in playlist['tracks']]
    
    video_urls = []
    for video_id in video_ids:
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        if video_id:
            video_urls.append(video_url)
    
    return video_urls


def parse_youtube_link(query):
    youtube_re = r'((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?(v|list)=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?'
    yt_match = re.search(youtube_re, query)
    if not yt_match:
        return None
    parsed =  {
        "protocol": yt_match.group(1),
        "subdomain": yt_match.group(2),
        "domain": yt_match.group(3),
        "is_nocookie": bool(yt_match.group(4)),
        "path": yt_match.group(5),
        "path_val": yt_match.group(6),
        "val_id": yt_match.group(7),
        "query_string": yt_match.group(8)
    }
    if parsed["path"] == "/playlist?list=":
        return yt_playlist_to_urls(parsed["val_id"])
    elif parsed["path"] == "/watch?v=":
        return [f'https://www.youtube.com/watch?v={parsed["val_id"]}"']


def parse_spotify_link(query):
    auth_manager = SpotifyClientCredentials(client_id=SP_CLIENT_ID, client_secret=SP_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    spotify_re = r'(?:https?\:\/\/)?open\.spotify\.com\/(playlist|album|track)\/([A-Za-z0-9]+)'
    sp_match = re.search(spotify_re, query)
    if not sp_match:
        return None
    path = sp_match.group(1)
    playlist_id = sp_match.group(2)
    
    tracks = []
    if path == "playlist":
        results = sp.playlist_tracks(playlist_id)
        for item in results['items']:
            tracks.append(item['track'])
    elif path == "album":
        results = sp.album_tracks(playlist_id)
        tracks = results['items']
    elif path == "track":
        tracks = [sp.track(playlist_id)]

    arr = []
    for track in tracks:
        track_name = track['name']
        artists = [artist['name'] for artist in track['artists']]
        arr.append(f"{track_name} {' '.join(artists)}")

    return arr


def parse_query(query):    
    yt_urls = parse_youtube_link(query)
    if yt_urls: return yt_urls
    
    sp_queries = parse_spotify_link(query)
    if sp_queries: return sp_queries

    # Parse video search query
    match = re.match(r"^\s*\./play_video\s+", query)
    if match:
        query = query[match.end():]
        return [get_youtube_url(query)]

    # Parse music search query
    match = re.match(r"^\s*\./play\s+", query)
    if match:
        query = query[match.end():]
        return [get_music_url(query)]

def get_music_url(query):
    try:
        ytmusic = YTMusic()
        search_results = ytmusic.search(query, filter="songs")

        if not search_results:
            # Fallback to video search
            get_youtube_url(query)

        video_id = search_results[0]['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_url

    except Exception as e:
        print("ERROR when searching with YTMusic. Using video search for fallback")
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
    if 10 <= num < 20:
        return ['🔟', '➕']
    if 20 <= num < 100:
        return [digit_emojis[num//10], '0️⃣', '➕']
    return ['💯', '➕']

async def play(client, message, voice):
    urls = parse_query(message.content)
    id = message.guild.id

    if not urls:
        return actions.ERR, discord.Embed(description=f"Couldn't find a song on youtube matching your query",)

    if id not in voice_clients or not voice_clients[id].is_connected:
        return await join(client, message, voice, urls)
    for url in urls:
        await queues[id].put(url) 

    return actions.REACT, ['📥'] + int_to_emojis(queues[id].qsize())


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
    if not url:
        return False
    ydl_opts = {
        'format': 'bestaudio/best[height<=480]',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'skip_download': True,
        'prefer_ffmpeg': True,
        'keepvideo': False,
        'youtube_include_dash_manifest': False,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
        except Exception as e:
            return False
        audio_url = info_dict.get("url", None)

    audio_source = discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn -buffer_size 64K")
    
    vc.play(audio_source)
    return True

async def join(client, message, voice, urls_to_play=None):
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
        if urls_to_play is not None and urls_to_play:
            emojis = ['✅']
            if len(urls_to_play) > 1:
                emojis += ['📥'] + int_to_emojis(len(urls_to_play) - 1)
            
            for emoji_id in emojis:
                emoji = get(client.emojis, name=emoji_id)
                await message.add_reaction(emoji or emoji_id)

            for url in urls_to_play:
                await queues[id].put(url)

        while True:
            url = await queues[id].get()
            if url == "kys":
                return (actions.IGNORE, None)
            if not url.startswith("https://www.youtube.com/watch?v="):
                url = get_music_url(url)

            if await play_url(voice_clients[id], url):
                now_playing = await message.channel.send(f" Now playing {url}")
            else:
                err = discord.Embed(description=f"Can't play {url}.\nUnsupported format\nKilling the player")
                err.color = discord.Color.red()
                await message.channel.send()

            # Wait until playback finishes
            while id in voice_clients and voice_clients[id].is_playing():
                await asyncio.sleep(1) # Father forgive me for I have sinned
            await now_playing.delete()

        return actions.SEND, "Idle timeout; Leaving vc."
    
async def handle_vc_change(client, member, before, after):
    if member != client.user:
        voice_client = discord.utils.get(client.voice_clients, guild=member.guild)
        if not voice_client or not voice_client.is_connected():
            return

        if len(voice_client.channel.members) == 1:
            voice_client.stop()
            await voice_client.disconnect()
            await handle_disconnect(client)
            print("I was abandoned, disconnecting.")

    if member == client.user and before.channel is not None and after.channel is None:
        print("I was disconnected")
        await handle_disconnect(client)

async def handle_disconnect(client):
    await asyncio.sleep(1.01) # I paid for my sin.
    # TODO: Write proper multi-threaded logic to synchronize
    # with player thread instead of using sleeps like a caveman
    to_del = []
    for id in voice_clients:
        for x in client.voice_clients:
            if x.guild.id == id:
                return # All good vc is still alive 

        # We were disconnected, wake up music player and tell him to kill himself
        await queues[id].put("kys")
        to_del.append(id)
    
    for id in to_del:
        del voice_clients[id]

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
    ]
    vc_commands = [
        (r"^\s*\./join\s*$", join, "Join your voice channel"),
        (r"^\s*\./play\s+", play, "Play song; Provide song name or Spotify/Youtube playlist or song links"),
        (r"^\s*\./play_video\s+", play, "Similar to ./play but search for YouTube video version instead"),
#       (r"^\s*\./queue\s*$", get_queue, "See the songs queue"),
        (r"^\s*\./(skip|next)\s*$", skip, "Skip to next song in queue")
    ]
    for rgx, func, _ in commands:
        if re.match(rgx, message.content):
            return await func(client, message, voice)

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