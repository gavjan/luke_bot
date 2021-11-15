import glob
import re
from cons import load_html, save_json, print_json

name_map = {
    "2 Յովհաննէս": ["john2", "2 Յովհաննէս"],
    "Եբրայեցիներ": ["ebra", "Եբրայեցիներ"],
    "Փիլիպեցիներ": ["pilip", "Փիլիպեցիներ"],
    "3 Յովհաննէս": ["john3", "3 Յովհաննէս"],
    "Ղուկաս": ["luke", "Ղուկաս"],
    "Յակոբոս": ["jakob", "Յակոբոս"],
    "2 Տիմոթէոս": ["tim2", "2 Տիմոթէոս"],
    "2 Պետրոս": ["petros2", "2 Պետրոս"],
    "Յուդա": ["juda", "Յուդա"],
    "2 Կորնթացիներ": ["kor2", "2 Կորնթացիներ"],
    "1 Թեսաղոնիկեցիներ": ["tes1", "1 Թեսաղոնիկեցիներ"],
    "Փիլիմոն": ["pilimon", "Փիլիմոն"],
    "2 Թեսաղոնիկեցիներ": ["tes2", "2 Թեսաղոնիկեցիներ"],
    "1 Կորնթացիներ": ["kor1", "1 Կորնթացիներ"],
    "Հռոմէացիներ": ["romans", "Հռոմէացիներ"],
    "Տիտոս": ["titos", "Տիտոս"],
    "1 Պետրոս": ["petros1", "1 Պետրոս"],
    "Յովհաննէս": ["john", "Յովհաննէս"],
    "Եփեսացիներ": ["epes", "Եփեսացիներ"],
    "Գաղատացիներ": ["galat", "Գաղատացիներ"],
    "1 Տիմոթէոս": ["tim1", "1 Տիմոթէոս"],
    "Գործք": ["acts", "Գործք"],
    "Կողոսացիներ": ["koxos", "Կողոսացիներ"],
    "ԱՒԵՏԱՐԱՆ ԸՍՏ ՄԱՏԹԷՈՍԻ": ["matthew", "Մատթեոս"],
    "Մարկոս": ["mark", "Մարկոս"],
    "Յայտնութիւն": ["rev", "Յայտնութիւն"],
    "1 Յովհաննէս": ["john1", "1 Յովհաննէս"],

    "Զաքարիա": ["zaqaria", "Զաքարիա"],
    "Նէեմի": ["neemi", "Նէեմի"],
    "Երեմիա": ["eremia", "Երեմիա"],
    "Ամբակում": ["ambakum", "Ամբակում"],
    "Դանիէլ": ["daniel", "Դանիէլ"],
    "4 Թագաւորաց": ["kings4", "4 Թագաւորաց"],
    "Ամոս": ["amos", "Ամոս"],
    "ԳԻՐՔ ԾՆՆԴՈՑ": ["genesis", "Գիրք Ծննդոց"],
    "Յուդիթ": ["judit", "Յուդիթ"],
    "1 Եզրաս": ["ezras1", "1 Եզրաս"],
    "Երգ Երգոց": ["songs", "Երգ Երգոց"],
    "Մաղաքիա": ["maxaqia", "Մաղաքիա"],
    "Ողբ": ["voxb", "Ողբ"],
    "ԹՈՒԵՐ": ["numbers", "Թուեր"],
    "3 Թագաւորաց": ["kings3", "3 Թագաւորաց"],
    "Անգէ": ["ange", "Անգէ"],
    "Յեսու": ["joshua", "Յեսու"],
    "Հռութ": ["ruth", "Հռութ"],
    "1 Մակաբայեցիներ": ["macab1", "1 Մակաբայեցիներ"],
    "3 Մակաբայեցիներ": ["macab3", "3 Մակաբայեցիներ"],
    "Աբդիու": ["abdiu", "Աբդիու"],
    "Միքիա": ["micia", "Միքիա"],
    "2 Մակաբայեցիներ": ["macab2", "2 Մակաբայեցիներ"],
    "Իմաստութիւն Սողոմոնի": ["wisdom", "Իմաստութիւն Սողոմոնի"],
    "ԵՐԿՐՈՐԴ ՕՐԷՆՔ": ["second_law", "Երկրորդ Օրենք"],
    "Յովնան": ["hovnan", "Յովնան"],
    "Ժողովող": ["eccel", "Ժողովող"],
    "Օսէէ": ["osse", "Օսէէ"],
    "Յովել": ["hovel", "Յովել"],
    "2 Մնացորդաց": ["chronicles2", "2 Մնացորդաց"],
    "Առակներ": ["proverbs", "Առակներ"],
    "Նաւում": ["naum", "Նաւում"],
    "Տոբիթ": ["tobit", "Տոբիթ"],
    "2 Թագաւորաց": ["kings2", "2 Թագաւորաց"],
    "1 Մնացորդաց": ["chronicles1", "1 Մնացորդաց"],
    "Յոբ": ["job", "Յոբ"],
    "ՂԵՒՏԱԿԱՆ": ["leviticus", "Ղևտական"],
    "Բարուք": ["baruq", "Բարուք"],
    "Եսթեր": ["ester", "Եսթեր"],
    "Եսայի": ["esai", "Եսայի"],
    "Սոփոնիա": ["soponia", "Սոփոնիա"],
    "Եզեկիէլ": ["ezekiel", "Եզեկիէլ"],
    "Սիրաք": ["siraq", "Սիրաք"],
    "Դատաւորներ": ["judes", "Դատաւորներ"],
    "1 Թագաւորաց": ["kings1", "1 Թագաւորաց"],
    "ԵԼՔ": ["exod", "Ելք"],
    "2 Եզրաս": ["ezras2", "2 Եզրաս"],
    "Սաղմոս": ["psalms", "Սաղմոս"],
}


def parse_gospel(name):
    page = load_html(name)
    gospel_name = re.sub(r"</?h1>", "", str(page.body.div.h1))
    gospel = {"name": name_map[gospel_name][1]}

    data = str(page.body.div) + "<strong>"
    arr_regex = r"\d{1,3}</strong>.*?<strong>"
    clean_regex = r"</?(div|hr|br)/?>"

    group_no = 0
    for arr in re.findall(arr_regex, data, re.DOTALL):
        group_no += 1
        group = {}
        arr = re.sub(clean_regex, " ", arr)
        i = 0
        arr = arr.replace("strong>", "sup>")
        for num, verse in re.findall(r"(\d{1,3})(</sup>.*?<sup>)", arr, re.DOTALL):
            i += 1
            group[i] = re.sub(r"(\s*</?sup>\s*)", "", verse)
            group[i] = group[i].replace("\n", " ")

        gospel[group_no] = group

    return name_map[gospel_name][0], gospel


def parse(which):
    bible = {}
    for gospel in glob.glob(f"../html_bible/{which}/*.html"):
        name, gospel = parse_gospel(gospel)
        bible[name] = gospel

    print_json(bible)
    save_json(f"{which}_bible", bible)


def main():
    parse("new")
    parse("old")


if __name__ == "__main__":
    main()
