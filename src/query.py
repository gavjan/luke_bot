from cons import load_json, actions, eprint, ADMIN_ID
import re
import discord
import random

help_embed = None
old_embed = None


def add_keys(embed, bible, to_embed=True):
    def has_numbers(text):
        return any(char.isdigit() for char in text)

    gosp = {}
    for gospel in sorted(bible):
        if has_numbers(gospel):
            gosp[gospel[:-1]] = {}
            gosp[gospel[:-1]]["name"] = bible[gospel]["name"][:-1]
            gosp[gospel[:-1]]["end"] = int(gospel[-1:])
        else:
            gosp[gospel] = {}
            gosp[gospel]["name"] = bible[gospel]["name"]
            gosp[gospel]["end"] = 0

    for key in gosp:
        name = key
        value = gosp[key]["name"]
        if gosp[key]["end"] != 0:
            name += f'[1-{gosp[key]["end"]}]'
            value += f' [1-{gosp[key]["end"]}]'
        if to_embed:
            embed.add_field(name=name, value=value, inline=True)
        else:
            embed += f'{name} ⟶ {value}\n'

    return embed


def get_help(new):
    global help_embed
    if help_embed is None:
        title = "*/verse [gospel_alias] [section].[start]-[end]*"
        desc = "example:```/verse tes2 2.9-11```\n"
        desc += "to get the list of Old Testament aliases type ```/verse old```\n New Testament aliases:"
        help_embed = discord.Embed(title=title, description=desc, color=discord.Color.green())
        help_embed = add_keys(embed=help_embed, bible=new, to_embed=True)

    return help_embed


def get_old(old):
    global old_embed
    if old_embed is None:
        old_embed = discord.Embed(
            title="Old Testament Aliases",
            description=add_keys("", old, to_embed=False),
            color=discord.Color.green()
        )

    return old_embed


def get_verse(bible, gospel, group, start, end):
    title = f'*({bible[gospel]["name"]} {group}.{start}{"" if start == end else f"-{end}"})*'
    desc = ""
    start_i = int(start)
    end_i = int(end)
    for verse in range(start_i, end_i + 1):
        desc += f'**{verse}**\t{bible[gospel][group][f"{verse}"]}\n\n'

    embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
    return actions.EMBED, embed


def random_verse(new, old):
    def rand_key(json):
        key, val = random.choice(list(json.items()))
        return key

    bible = random.choice([new, old])
    gospel = rand_key(bible)
    group = rand_key(bible[gospel])
    verse = rand_key(bible[gospel][group])
    return get_verse(bible, gospel, group, verse, verse)


def parse_verse(query):
    old = load_json("old_bible")
    new = load_json("new_bible")
    err = ""

    if re.match(r"^\s*/verse\s*$", query):
        return random_verse(new, old)

    if re.match(r"^\s*/verse\s+help\s*", query):
        return actions.EMBED, get_help(new)
    if re.match(r"^\s*/verse\s+old\s*", query):
        return actions.EMBED, get_old(old)
    tokenized = re.findall(r"/verse\s+([a-z0-9]{1,10})\s+(\d{1,3})[.:](\d{1,3})(-\d{0,3})?\s*$", query)
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


def parse_query(query, debug=False):
    content = query if debug else query.content
    if re.match(r"^\s*/verse\s*", content):
        return parse_verse(content)
    if re.search(r"\b(amen|ամեն)\b", content, re.IGNORECASE):
        return actions.REPLY, "Ամեն :pray:"
    if re.match(r"^s*/restart_luke\s*", content) and query.author.id == ADMIN_ID:
        return actions.EXIT, "ok"

    return actions.IGNORE, ""


def main():
    print("/verse [gospel] [section]․[start]-[end]")
    while True:
        action, response = parse_query(input(), debug=True)
        if action == action.SEND or action.REPLY:
            print(response)
        else:
            eprint(response)


if __name__ == "__main__":
    main()
