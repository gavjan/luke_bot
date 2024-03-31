import random
import re
from datetime import date, datetime
from itertools import groupby
import subprocess
from terminal import handle as handle_term
import discord
from discord.utils import get

from cons import (DISCORD_MSG_LIMIT, load_json, actions, ADMIN_IDS, TUS_ID, TUS_THREAD_ID, SEED, COUNT_ID, START_DATE, GUGL_ID, err_exit,
                  load_page, rm_message)
from screenshot import create_message_image
from music import handle_music
new_embed = None
old_embed = None
counter = None


def add_keys(embed, bible, to_embed=True):
    def has_numbers(text):
        return any(char.isdigit() for char in text)

    gosp = {}
    for gospel in sorted(bible):
        if has_numbers(gospel):
            gosp[gospel[1:]] = {}
            gosp[gospel[1:]]["name"] = bible[gospel]["name"][1:]
            gosp[gospel[1:]]["end"] = int(gospel[:1])
        else:
            gosp[gospel] = {}
            gosp[gospel]["name"] = bible[gospel]["name"]
            gosp[gospel]["end"] = 0

    for key in gosp:
        name = key
        value = gosp[key]["name"]
        if gosp[key]["end"] != 0:
            name = f'[1-{gosp[key]["end"]}]{name}'
            value = f'[1-{gosp[key]["end"]}] {value}'
        if to_embed:
            embed.add_field(name=name, value=value, inline=True)
        else:
            embed += f'{name} ⟶ {value}\n'

    return embed


def get_help():
    title = "*/verse [gospel_alias] [section].[start]-[end]*"
    desc = "example:```/verse 2tes 2.9-11```\n"
    desc += "To get the list of New Testament aliases type ```/verse new```\n"
    desc += "To get the list of Old Testament aliases type ```/verse old```\n"

    return discord.Embed(title=title, description=desc, color=discord.Color.green())


def get_old():
    global old_embed
    if old_embed is None:
        old_embed = discord.Embed(
            title="Old Testament Aliases",
            description=add_keys("", old, to_embed=False),
            color=discord.Color.green()
        )

    return old_embed


def get_new():
    global new_embed
    if new_embed is None:
        new_embed = discord.Embed(
            title="New Testament Aliases",
            description="",
            color=discord.Color.green()
        )
        new_embed = add_keys(embed=new_embed, bible=new, to_embed=True)

    return new_embed


def get_verse(bible, gospel, group, start, end):
    title = f'*({bible[gospel]["name"]} {group}.{start}{"" if start == end else f"-{end}"})*'
    desc = ""
    start_i = int(start)
    end_i = int(end)
    for verse in range(start_i, end_i + 1):
        desc += f'**{verse}**\t{bible[gospel][group][f"{verse}"]}\n\n'

    embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
    return actions.EMBED, embed


def random_verse():
    def rand_key(json):
        arr = list(json.keys())
        if "name" in arr:
            arr.remove("name")
        return random.choice(arr)

    bible = random.choice([new, old])
    gospel = rand_key(bible)
    group = rand_key(bible[gospel])
    verse = rand_key(bible[gospel][group])
    return get_verse(bible, gospel, group, verse, verse)


old = load_json("old_bible")
new = load_json("new_bible")


def parse_verse(query):
    err = ""

    if re.match(r"^\s*/verse\s+help\s*$", query):
        return actions.EMBED, get_help()
    if re.match(r"^\s*/verse\s+old\s*$", query):
        return actions.DM, get_old()
    if re.match(r"^\s*/verse\s+new\s*$", query):
        return actions.DM, get_new()
    tokenized = re.findall(r"/verse\s+([a-z0-9_]{1,10})\s+(\d{1,3})[.:](\d{1,3})(-\d{0,3})?\s*$", query)
    for gospel, group, start, end in tokenized:
        end = end[1:]
        bible = new if gospel in new else old
        if gospel not in new and gospel not in old:
            err = f"no such gospel {gospel}"
        elif group not in bible[gospel]:
            err = f'gospel {bible[gospel]["name"]} doesn\'t have a section {group}'
        elif start not in bible[gospel][group]:
            err = f'{bible[gospel]["name"]} {group} doesn\'t have a verse {start}'
        elif end == "":
            end = start
        elif end not in bible[gospel][group]:
            err = f'{bible[gospel]["name"]} {group} doesn\'t have a verse {end}'

        if err != "":
            return actions.ERR, discord.Embed(title="*/verse error*", description=err, color=discord.Color.red())
        else:
            return get_verse(bible, gospel, group, start, end)
    err_embed = discord.Embed(title="*/verse wrong syntax*", description="for correct syntax see: ```/verse help```",
                              color=discord.Color.red())

    return actions.ERR, err_embed


def daily_verse():
    all_verses = []

    def add_verses(arr, _bible):
        for _gospel in _bible:
            for _section in _bible[_gospel]:
                if _section != "name":
                    for _verse in _bible[_gospel][_section]:
                        arr.append({"gospel": _gospel, "section": _section, "verse": _verse})

    add_verses(all_verses, new)
    add_verses(all_verses, old)

    random.seed(SEED)
    random.shuffle(all_verses)

    start = datetime.date(datetime.strptime(START_DATE, "%Y-%m-%d"))
    delta = date.today() - start
    today_i = delta.days

    todays = all_verses[today_i]
    gospel = todays["gospel"]
    section = todays["section"]
    verse = todays["section"]
    bible = None
    if gospel in new:
        bible = new
    elif gospel in old:
        bible = old
    else:
        err_exit(f"{gospel} is neither in old nor in new bible wtf???")
    action, embed = get_verse(bible, gospel, section, verse, verse)
    embed.title = "Այսօրվա համար՝ " + embed.title
    return actions.EMBED, embed

def calc_easter(year):
    # Based O(1) algorithm for calculating easter
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return year, month, day

def hisus_bd_reply():
    t = date.today()
    if (t.day, t.month, t) in [(5, 1), (6, 1)]:
        return actions.REPLY, "Ձեզ և մեզ մեծ Ավետիս"
    else:
        return actions.IGNORE, None
def zatik_reply():
    t = date.today()
    if (t.year, t.month, t.day) == calculate_easter(t.year):
        return actions.REPLY, "Օրհնյալ է Հարությունը Քրիստոսի"
    else:
        return actions.IGNORE, None



async def process_reaction(client, players, payload):
    if payload.emoji.name == "🔁" and payload.member.id in ADMIN_IDS:
        msg = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if any("✅" == r.emoji for r in msg.reactions):
            return
        await msg.add_reaction("🔁")
        await msg.add_reaction("✅")
        exit(0)

    k = (payload.channel_id, payload.message_id)

    if k not in players:
        return

    if not payload.member:
        return
    pick = payload.emoji.name
    if pick not in ["ghush", "gir"]:
        return

    if players[k][0] != payload.user_id:
        return

    await rm_message(client, k[0], k[1])
    original_message = await client.get_channel(k[0]).fetch_message(players[k][1])
    del players[k]

    drawn = random.choice(["ghush", "gir"])
    name = payload.member.nick or payload.member.name
    pick_txt = ["Ղուշ", "Գիր"][pick == "gir"]
    if pick == drawn:
        text = f"Ապրես {name} դու ճշտաբար ընտրեցիր *{pick_txt}*"
        color = discord.Color.green()
    else:
        text = f"Ափսոս {name} դու թյուրաբար ընտրեցիր *{pick_txt}*"
        color = discord.Color.red()

    embed = discord.Embed(description=text, color=color)

    link = ["https://i.imgur.com/gLT4OND.gif", "https://i.imgur.com/hdJynZe.gif"][drawn == "gir"]
    embed.set_image(url=link)
    await original_message.reply(embed=embed)


def banned_word(query):
    if type(query.channel) == discord.channel.DMChannel:
        return actions.IGNORE, None

    desc = "Դուք օգտագործեցիք արգելված բառ։ \n" \
           "Ըստ ԿՈՒՂԲ≈ † =∞ ֊ի սահմանադրության, դուք պետք է պարգևատրվեք կամ պատժվեք։\n" \
           "Ընտրեք Ղուշ կամ Գիր սկսելու համար։\nԱստված ձեզ հետ։\nԱմեն🙏"
    color = discord.Color.blue()
    return actions.BUTTONS, {"emojis": ["ghush", "gir"], "embed": discord.Embed(description=desc, color=color)}


def gav(num, author):
    return (num == 6000) and (f"{author}" != "212246620945776651")


def assert_count(txt, author):
    global counter
    if not counter:
        num = re.match(r"^\d+", txt)
        if not num:
            return actions.REACT, ["❓"]
        if gav(int(num[0]), author):
            return actions.REACT, ["🇲", "🇪", "🇸", "⬛", "🇴", "🇳", "🇱", "🇾", "⛔"]
        counter = (int(num[0]), author)

        return actions.REACT, ["♻️"]

    nums = [int(''.join(i)) for is_digit, i in groupby(txt, str.isdigit) if is_digit]
    if ((counter[0] + 1 not in nums) and ("gif" not in txt)) or author == counter[1]:
        return actions.REACT, "😡"
    if gav(counter[0] + 1, author):
        return actions.REACT, ["🇬", "🇦", "🇻", "⬛", "🇴", "🇳", "🇱", "🇾", "⛔"]
    counter = (counter[0] + 1, author)
    return actions.IGNORE, None


async def count_stats(client):
    thread = await client.fetch_channel(COUNT_ID)
    return actions.REPLY, "yes"
    stats = {}
    async for message in thread.history():
        user = message.author.name
        if user not in stats:
            stats[user] = 1
        else:
            stats[user] += 1
    msg = ""
    for k in stats:
        msg += f"{k}: {stats[k]}\n"
    return actions.REPLY, msg


def pray(text):
    embed = discord.Embed(title="Anonymous Prayer", description=text, color=discord.Color.blue())
    return actions.SEND, embed


async def tus_moment(client, message):
    if not message.author.top_role.permissions.administrator:
        return actions.REACT, ["🚫"]
    if message.reference is None:
        return actions.REACT, ["❓"]

    ref_message = await message.channel.fetch_message(message.reference.message_id)
    create_message_image(client, ref_message)

    tus_thread = await client.fetch_channel(TUS_THREAD_ID)
    with open('message.png', 'rb') as f:
        sent_msg = await tus_thread.send(ref_message.jump_url, file=discord.File(f))

    emoji = get(client.emojis, name="tus")
    await sent_msg.add_reaction(emoji)

    return actions.REMOVE, None


async def parse_query(query, client, debug=False):
    content = query if debug else query.content
    ret = []
    # if query.channel.id == COUNT_ID:
    #    ret.append(assert_count(content, query.author.id))
    handle_ret, response = handle_term(content, query.author.id)
    if handle_ret:
        response = f"$ {content}\n{response}" if content != "bash" else response
        return [(actions.SEND, f'```{response[-DISCORD_MSG_LIMIT:]}```')]
    if re.match(r"^\s*/count_stats\s*$", content):
        ret.append((await count_stats(client)))
    if re.match(r"^\s*\./", content):
        ret.append((await handle_music(client, query)))
    if re.match(r"^\s*/pray\s*$", content):
        ret.append((pray(content)))
    if re.match(r"^\s*/tus_moment\s*$", content):
        ret.append((await tus_moment(client, query)))
    if re.match(r"^\s*/test_holiday\s*$", content) and query.author.id in ADMIN_IDS:
        ret.append((todays_holiday()))
    if re.match(r"^\s*/test_verse\s*$", content) and query.author.id in ADMIN_IDS:
        ret.append((daily_verse()))
    if re.match(r"^\s*/verse\s*$", content):
        ret.append((random_verse()))
    if re.match(r"^\s*/verse\s+", content):
        ret.append((parse_verse(content)))
    if re.search(r"\b(amen|ամեն)\b", content, re.IGNORECASE):
        ret.append((actions.REPLY, "Ամեն :pray:"))
    if re.search(r"\b(qristos|քրիստոս)\s+(հարյավ|հարեավ|haryav|hareav)\s*(ի|i)\s+(մեռելոց|mereloc)\b",
                 content, re.IGNORECASE):
        ret.append((hisus_bd_reply()))
    if re.search(r"\b(qristos|քրիստոս)\s+(ծնվեց|tsnvec|cnvec|ծնավ|tsnav|cnav)\s*(և|ev|եւ)\s+(հայտնեցավ|haytnecav)\b",
                content, re.IGNORECASE):
        ret.append((zatik_reply()))
    if re.search(r"\b(nigger|նիգգեռ)\b", content, re.IGNORECASE):
        ret.append((banned_word(query)))
    if re.search(r"(\W|_|\d|^)(gm|գմ|gmgm|գմգմ)(\W|_|\d|$)", content, flags=re.UNICODE | re.IGNORECASE):
        ret.append((actions.REACT, ["🇬", "🇲", "baj"]))
    if query.author.id == TUS_ID:
        ret.append((actions.REACT, ["tus"]))
    if query.channel.id == TUS_THREAD_ID:
        ret.append((actions.REMOVE, None))
    elif re.search(r"(\W|_|\d|^)(gn|գն|bg|բգ|gngn|գնգն|bgbg|բգբգ)(\W|_|\d|$)", content, flags=re.UNICODE | re.IGNORECASE):
        ret.append((actions.REACT, ["🇬", "🇳", "gandz"]))
    if re.match(r"^\s*/whitelist\s+", content):
        ret.append((whitelist(client, query)))
    if re.match(r"^\s*/restart_luke\s*$", content) and query.author.id in ADMIN_IDS:
        ret.append((actions.EXIT, "ok"))

    return ret

def whitelist(client, query):
    channel = client.get_channel(GUGL_ID)
    if not channel: return actions.REPLY, "error: #գուգլ was deleted, the universe must be no more"
      
    ids = [member.id for member in channel.members]
    if not query.author.id in ids: return actions.ERR, discord.Embed(description="You don't have permission to do this")

    match = re.search(r"^\s*/whitelist\s+([a-zA-Z0-9_]{2,16})\s*$", query.content)
    if not match:
        return actions.ERR, discord.Embed(description="Invalid Minecraft username")
    user = match.group(1)
    p = subprocess.run(['mcrcon', '-H', 'localhost', '-P', '25575', '-p', 'hisus',f'whitelist add {user}'],
                        shell=False, capture_output=True, text=True)
    if p.returncode != 0:
        return actions.REPLY, p.stderr

    return actions.REPLY, p.stdout


def holiday_on(_date):
    url = f"https://www.qahana.am/am/holidays/{_date}/1"
    page = load_page(url)

    holiday_div = page.find("div", {"class": "holidayBox"})
    if not holiday_div:
        print("No Holiday today")
        return actions.IGNORE, ""

    today = re.sub(r"</?span.*?>", "", str(holiday_div.span)).strip()
    title = re.sub(r"</?h2.*?>", "", str(holiday_div.h2)).strip()
    desc = re.sub(r"<strong>.*?</strong>", "", str(holiday_div.div.div))
    desc = re.sub(r"</?(div|strong|p)>", "", desc)
    desc = re.sub(r"</?(font|p).*?>", "", desc)
    desc = desc.replace("`", "\\`")
    desc = desc.strip().splitlines()[0]

    embed = discord.Embed(title=title, url=url, description=desc, color=discord.Color.blue())
    embed.set_author(name=today)
    embed.description += f"\n[Ավելին]({url})"
    return actions.EMBED, embed


def todays_holiday():
    return holiday_on(date.today())
