from cons import load_json
import re


def parse_verse(query):
    old = load_json("old_bible")
    new = load_json("new_bible")
    err = ""

    tokenized = re.findall(r"/verse\s+([a-z0-9]{1,10})\s+(\d{1,3})\.(\d{1,3})(-\d{0,3})?\s*$", query)
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
            return err
        else:
            ans = f'\n# ({bible[gospel]["name"]} {group}.{start}{"" if start == end else f"-{end}"})\n'
            start_i = int(start)
            end_i = int(end)
            for verse in range(start_i, end_i + 1):
                ans += f'{verse} {bible[gospel][group][f"{verse}"]}\n'
            return ans

    return "wrong /verse format"


def parse_query(query):
    if re.match(r"^\s*/verse\s+", query):
        return parse_verse(query)
    return "wrong command"


def main():
    print("/verse [gospel] [group]․[starting_verse]-[ending_verse]")
    while True:
        print(parse_query(input()))


if __name__ == "__main__":
    main()
