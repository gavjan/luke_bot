import discord
import re
from cons import *
import yt_dlp as youtube_dl
import asyncio
from discord.utils import get
import edge_tts

# Spotipy
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
SP_CLIENT_ID = getenv("spotify_id")
SP_CLIENT_SECRET = getenv("spotify_secret")


queues = {}
voice_clients = {}
now_playing_controls = {}  # (channel_id, msg_id) -> guild_id
song_selections = {}  # (channel_id, msg_id) -> {"author_id": int, "urls": [str], "original_msg_id": int}
SONG_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
CONTROL_SKIP = '⏩'
CONTROL_STOP = '⏹️'

async def make_tts(text):
    voice = "en-US-EmmaMultilingualNeural"

    communicate = edge_tts.Communicate(text, voice, volume="+100%")
    await communicate.save("tts.mp3")

def yt_playlist_to_urls(playlist_id):
    """Extract playlist URLs using yt-dlp."""
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            playlist = ydl.extract_info(playlist_url, download=False)
            if playlist and 'entries' in playlist:
                return [f"https://www.youtube.com/watch?v={e['id']}" for e in playlist['entries'] if e and e.get('id')]
    except Exception as e:
        print(f"Playlist extraction failed: {e}")
    return []


def parse_youtube_link(query):
    youtube_re = r'((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu\.be))(\/(?:[\w\-]+\?(v|list)=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?'
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

    return [f'https://www.youtube.com/watch?v={parsed["val_id"]}']


def parse_spotify_link(query, spotify_re):
    auth_manager = SpotifyClientCredentials(client_id=SP_CLIENT_ID, client_secret=SP_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    sp_match = re.search(spotify_re, query)
    if not sp_match:
        return None
    path = sp_match.group(1)
    playlist_id = sp_match.group(2)
    try:
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
    except SpotifyException as e:
        return None # Invalid link

    arr = []
    for track in tracks:
        track_name = track['name']
        artists = [artist['name'] for artist in track['artists']]
        arr.append(f"{track_name} {' '.join(artists)}")

    return arr


def parse_query(query):
    # Parse Spotify link
    spotify_re = r'(?:https?\:\/\/)?open\.spotify\.com\/(playlist|album|track)\/([A-Za-z0-9]+)'
    match = re.search(spotify_re, query)
    if match:
        return parse_spotify_link(query, spotify_re)

    # Parse youtube link
    yt_urls = parse_youtube_link(query)
    if yt_urls: return yt_urls

    # Parse music search query - return ("SEARCH", query) for selection
    match = re.match(r"^\s*\./play\s+", query)
    if match:
        query = query[match.end():]
        return ("SEARCH", query)

def _search_music_sync(query, max_results=5):
    """Sync search - run in thread to avoid blocking."""
    ydl_opts = {
        'extract_flat': True,  # Only get IDs/titles, not full info
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query} audio", download=False)
            if results and 'entries' in results:
                return [
                    (f"https://www.youtube.com/watch?v={e['id']}", e.get('title', 'Unknown'))
                    for e in results['entries'] if e and e.get('id')
                ]
    except Exception as e:
        print(f"Search failed: {e}")
    return []


async def search_music(query, max_results=5):
    """Search YouTube for music, return list of (url, title) tuples."""
    return await asyncio.to_thread(_search_music_sync, query, max_results)


async def get_music_url(query):
    """Get first music result URL (used as fallback)."""
    results = await search_music(query, max_results=1)
    return results[0][0] if results else None
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
    result = parse_query(message.content)
    id = message.guild.id

    # Handle search query - show selection
    if isinstance(result, tuple) and result[0] == "SEARCH":
        search_query = result[1]
        results = await search_music(search_query, max_results=5)
        if not results:
            return actions.ERR, discord.Embed(description=f"No results for '{search_query}' 🥺")
        
        # Build selection embed
        desc = "\n".join([f"{SONG_EMOJIS[i]} {title[:60]}" for i, (url, title) in enumerate(results)])
        desc += "\n\n👇React with the corresponding emoji to select a song."
        embed = discord.Embed(title=f"🔍 {search_query[:50]}", description=desc, color=discord.Color.blue())
        embed.set_footer(text="hint: you can also just type 1-5 to make a selection")
        
        sent = await message.channel.send(embed=embed)
        urls = [url for url, _ in results]
        song_selections[(sent.channel.id, sent.id)] = {
            "author_id": message.author.id,
            "urls": urls,
            "original_msg_id": message.id,
            "guild_id": id,
            "voice": voice
        }
        try:
            for i in range(len(results)):
                await sent.add_reaction(SONG_EMOJIS[i])
        except discord.NotFound:
            pass  # Message was deleted (user already selected)
        return actions.IGNORE, None

    urls = result
    if not urls:
        return actions.ERR, discord.Embed(description=f"Couldn't find song or playlist matching your query, sorry 🥺",)

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
     

async def tts(client, message, voice):
    id = message.guild.id

    match = re.match(r"^\s*\./tts\s+", message.content)
    tts_text = message.content[match.end():]
    url = "tts://" + tts_text

    if id not in voice_clients or not voice_clients[id].is_connected:
        return await join(client, message, voice, [url])

    await queues[id].put(url)

    return actions.REACT, ['📥'] + int_to_emojis(queues[id].qsize())

def play_local_file(vc):
    try:
        vc.play(discord.FFmpegPCMAudio("tts.mp3"))
        return True
    except Exception as e:
        print(e)
        return False

async def play_url(vc, url):    
    if not url:
        return play_local_file(vc)
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
        'quiet': True,
        'no_warnings': True,
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
        except Exception as e:
            return False
        audio_url = info_dict.get("url", None)
        if not audio_url:
            print(f"[luke] No audio URL extracted for {url}")
            return False

    def after_callback(error):
        if error:
            print(f"[luke] Playback error: {error}")

    audio_source = discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", options="-vn -buffer_size 64K")
    
    vc.play(audio_source, after=after_callback)
    return True

async def join(client, message, voice, urls_to_play=None):
        id = message.guild.id
        perms = voice.channel.permissions_for(message.guild.me)
        if not perms.connect:
            err_embed = discord.Embed(title="*No Permission*", description=f"I can't connect to `{voice.channel}`",)
            return actions.ERR, err_embed

        retry_cnt = 0
        max_retry = 1
        while(retry_cnt < max_retry):
            try:
                voice_clients[id] = await asyncio.wait_for(voice.channel.connect(), timeout=7)
                break

            except Exception as e:
                await leave(client, message, None)
                retry_cnt += 1
                if retry_cnt >= max_retry:
                    err_embed = discord.Embed(title="Can't connect to your vc", description=f"{e}")
                    return actions.ERR, err_embed
        
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
            if url.startswith("tts://"):
                await make_tts(url[6:])
                url = None
            if url and not url.startswith("https://www.youtube.com/watch?v="):
                url = await get_music_url(url)

            if await play_url(voice_clients[id], url):
                if not url: url = "Text to Speech"
                now_playing = await message.channel.send(f" Now playing {url}")
                # Add playback controls
                now_playing_controls[(now_playing.channel.id, now_playing.id)] = id
                try:
                    await now_playing.add_reaction(CONTROL_STOP)
                    await now_playing.add_reaction(CONTROL_SKIP)
                except discord.NotFound:
                    pass
            else:
                err_text = f"Caused by: {url}\nPossible problems:\n- 🔞 Age-Restricted video\n- ⛔ Unsupported format\n- 🥺 YouTube hates me"
                err = discord.Embed(title="Player Crashed. Restarting.", description=err_text)
                err.color = discord.Color.red()
                await message.channel.send(embed=err)

                await leave(client, message, None)
                return await join(client, message, voice)

            # Wait until playback finishes
            while id in voice_clients and voice_clients[id].is_playing():
                await asyncio.sleep(1) # Father forgive me for I have sinned
            # Clean up controls tracking
            now_playing_controls.pop((now_playing.channel.id, now_playing.id), None)
            try:
                await now_playing.delete()
            except discord.NotFound:
                pass

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
    await asyncio.sleep(1.01) # Sorry
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


async def handle_playback_controls(client, payload):
    """Handle ⏩ skip and ⏹️ stop reactions on Now Playing message."""
    # Ignore bot's own reactions
    if payload.user_id == client.user.id:
        return
    
    k = (payload.channel_id, payload.message_id)
    
    if k not in now_playing_controls:
        return
    
    emoji = str(payload.emoji)
    if emoji not in (CONTROL_SKIP, CONTROL_STOP):
        return
    
    guild_id = now_playing_controls.get(k)
    if not guild_id:
        return
    
    # Remove immediately to prevent spam
    now_playing_controls.pop(k, None)
    
    if guild_id not in voice_clients:
        return
    
    vc = voice_clients[guild_id]
    
    if emoji == CONTROL_SKIP:
        vc.stop()  # This will trigger the next song in queue
    elif emoji == CONTROL_STOP:
        await queues[guild_id].put("kys")
        if guild_id in voice_clients:
            del voice_clients[guild_id]
        for x in client.voice_clients:
            if x.guild.id == guild_id:
                await x.disconnect()
                break


async def handle_song_selection(client, payload):
    """Handle reaction on song selection message."""
    k = (payload.channel_id, payload.message_id)
    
    if k not in song_selections:
        return
    
    selection = song_selections[k]
    
    # Only original author can select
    if payload.user_id != selection["author_id"]:
        return
    
    # Check if valid song emoji
    emoji = str(payload.emoji)
    if emoji not in SONG_EMOJIS:
        return
    
    idx = SONG_EMOJIS.index(emoji)
    if idx >= len(selection["urls"]):
        return
    
    # Remove from selections immediately to prevent duplicate processing from spam
    url = selection["urls"][idx]
    guild_id = selection["guild_id"]
    voice = selection["voice"]
    original_msg_id = selection["original_msg_id"]
    del song_selections[k]
    
    # Delete selection message
    try:
        msg = await client.get_channel(k[0]).fetch_message(k[1])
        await msg.delete()
    except:
        pass  # Already deleted
    
    # Get original message for context
    try:
        original_msg = await client.get_channel(k[0]).fetch_message(original_msg_id)
    except:
        return
    
    # Queue the song
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected:
        await join(client, original_msg, voice, [url])
    else:
        await queues[guild_id].put(url)
        for emoji in ['📥'] + int_to_emojis(queues[guild_id].qsize()):
            await original_msg.add_reaction(emoji)


async def handle_text_selection(client, message):
    """Handle 1-5 text messages as song selection."""
    content = message.content.strip()
    if content not in ('1', '2', '3', '4', '5'):
        return False
    
    idx = int(content) - 1
    channel_id = message.channel.id
    author_id = message.author.id
    
    # Find pending selection for this user in this channel
    selection_key = None
    selection = None
    for k, v in list(song_selections.items()):
        if k[0] == channel_id and v["author_id"] == author_id:
            selection_key = k
            selection = v
            break
    
    if not selection_key or not selection:
        return False
    
    if idx >= len(selection["urls"]):
        return False
    
    # Remove from selections immediately to prevent race with emoji selection
    # Use pop to handle case where emoji handler already removed it
    selection = song_selections.pop(selection_key, None)
    if not selection:
        return False  # Already processed by emoji handler
    
    url = selection["urls"][idx]
    guild_id = selection["guild_id"]
    voice = selection["voice"]
    original_msg_id = selection["original_msg_id"]
    
    # Delete the "1-5" message
    try:
        await message.delete()
    except:
        pass
    
    # Delete selection embed message
    try:
        selection_msg = await client.get_channel(selection_key[0]).fetch_message(selection_key[1])
        await selection_msg.delete()
    except:
        pass  # Already deleted
    
    # Get original message for context
    try:
        original_msg = await client.get_channel(channel_id).fetch_message(original_msg_id)
    except:
        return True  # Still consumed the message
    
    # Queue the song
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected:
        await join(client, original_msg, voice, [url])
    else:
        await queues[guild_id].put(url)
        for emoji in ['📥'] + int_to_emojis(queues[guild_id].qsize()):
            await original_msg.add_reaction(emoji)
    
    return True  # Message was handled


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
#       (r"^\s*\./queue\s*$", get_queue, "See the songs queue"),
        (r"^\s*\./(skip|next)\s*$", skip, "Skip to next song in queue"),
        (r"^\s*\./tts\s+", tts, "Play tts text"),
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