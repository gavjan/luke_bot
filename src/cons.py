import enum
import json
import os
import sys
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup as soup

BOT_IDS = [901444128515182693, 1006534832827932832]
ADMIN_IDS = [
    213341816324489217, # Gav
    209687706349993985, # Hrach
    696471041958084648, # Tikowo
    493482354917113878, # Dav
    212246620945776651, # Mes
    248490582152970241, # Vurd
]
TUS_ID = 1013336977359245397
OLD_TUS_ID = 456226577798135808
OLD_TUS_PFP_URL = "https://github.com/gavjan/luke_bot/blob/main/src/old_tus_pfp.jpg?raw=true"
TUS_THREAD_ID = 1093110043886485574
START_DATE = "2021-10-24"
SEED = "LUKE"
COUNT_ID = 1002183766682390539
GUGL_ID = 456178384016244738
DISCORD_MSG_LIMIT = 1994
GAMES = [
    {"role_id": 555400264790835230,  "names": ["cs", "ցս"]},
    {"role_id": 651841632286670869,  "names": ["dota", "դոտա"]},
    {"role_id": 456441520351084550,  "names": ["warzone", "ոռզոն", "fortnite", "ֆորտնայթ"]},
    {"role_id": 1195070490306429008, "names": ["fifa", "ֆիֆա"]},
    {"role_id": 1286419763328847922, "names": ["deadlock", "դեդլոք"]},
]
names = []
roles = []
for game in GAMES:
    roles.append(f'<@&{game["role_id"]}>')
    names += game["names"]

roles_pattern = '|'.join(re.escape(role) for role in roles)
names_pattern = '|'.join(re.escape(name) for name in names)
names_pattern = r"(\W|_|\d|^)" + f"({names_pattern})" + r"(\W|_|\d|$)"

roles_re = re.compile(roles_pattern)
names_re = re.compile(names_pattern, re.UNICODE | re.IGNORECASE)

class IgnoreErrors(enum.Enum):
    PERM_ERR_CODE = 50013
    DM_ERR = 50007
    OS_ERR = 5

    @classmethod
    def has(cls, value):
        return value in [item.value for item in cls]


class actions(enum.Enum):
    SEND = 1
    REPLY = 2
    ERR = 3
    IGNORE = 4
    EMBED = 5
    EXIT = 6
    DM = 7
    REACT = 8
    BUTTONS = 9
    REMOVE = 10


def getenv(name):
    assert_folder("../.env")
    f = open(f"../.env/{name}.env", "r")
    val = f.read()
    f.close()
    return val.strip()


def assert_folder(name):
    if not os.path.exists(name):
        os.mkdir(name)


def print_json(_json, intend="", comma=False, left_bracket=True):
    if isinstance(_json, list):
        print(intend + "[")

        for i in range(len(_json)):
            print_json(_json[i], intend + "\t", comma=(i < len(_json) - 1))
        print(intend + "]")
        return

    def colored(color, text):
        return "\033[38;2;{};{};{}m{}\033[38;2;255;255;255m".format(color[0], color[1], color[2], text)

    green = [0, 255, 0]
    cyan = [0, 255, 255]
    if left_bracket:
        print(intend + "{")
    i = 0
    for key in _json:
        val = _json[key]
        if isinstance(_json[key], dict):
            print(f"{intend}\t{colored(green, key)}: {'{'}")
            print_json(_json[key], intend + "\t", left_bracket=False, comma=(i < len(_json) - 1))
        else:
            if isinstance(_json[key], str):
                val = f"\"{val}\"".replace("\n", "\\n")
            val_comma = "," if i < len(_json) - 1 else ""
            print(f"{intend}\t{colored(green, key)}: {colored(cyan, val)}{val_comma}")
        i += 1
    print(intend + "}" + ("," if comma else ""))


def load_json(name):
    data = {}
    try:
        f = open(f"../json/{name}.json", "r")
        data = json.load(f)
        f.close()
    except FileNotFoundError:
        err_exit(f"file ../json/{name}.json doesn't exist")
    return data


def save_json(name, data):
    assert_folder("../json")
    f = open(f'../json/{name}.json', 'w')
    json.dump(data, f)
    f.close()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def err_exit(*args, **kwargs):
    eprint("[ERROR] ", end="")
    print(*args, file=sys.stderr, **kwargs)
    exit(1)


def load_html(file_name):
    data = ""
    try:
        file = open(file_name)
        data = file.read()
        file.close()

    except FileNotFoundError:
        err_exit(f"file {file_name} doesn't exist")

    return soup(data, "html.parser")


def load_page(url, attempt=1):
    def is_ascii(s):
        return all(ord(c) < 128 for c in s)

    if not is_ascii(url):
        for x in url:
            if not is_ascii(x):
                url = url.sub(x, quote(x))

    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    try:
        web_byte = urlopen(req).read()
    except:
        return load_page(url, attempt + 1) if attempt < 5 else soup("", "html.parser")

    webpage = web_byte.decode('utf-8')
    page = soup(webpage, "html.parser")
    return page


def to_remove_vals(m, val):
    ret = []
    to_del = []
    for k, v in m.items():
        if v[0] == val:
            to_del.append(k)
            ret.append(k)
    for x in to_del:
        del m[x]

    return ret


async def rm_message(client, channel_id, message_id):
    msg = await client.get_channel(channel_id).fetch_message(message_id)
    await msg.delete()
