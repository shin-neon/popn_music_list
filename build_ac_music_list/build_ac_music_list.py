import csv
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://p.eagate.573.jp/game/popn/popn29/music/list.html"
OUTPUT_PATH = Path(__file__).with_name("ac_master.csv")
FIELDNAMES = [
    "title",
    "genre",
    "artist",
    "version",
    "level_l",
    "level_n",
    "level_h",
    "level_ex",
]
REQUEST_INTERVAL_SECONDS = 0.35


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


class AcPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.records = []
        self.version_names = {}
        self.page_numbers = set()
        self._active_list = False
        self._list_items = []
        self._active_li = False
        self._active_p = False
        self._p_text = []
        self._p_level = None
        self._p_label = []
        self._active_span = False
        self._span_text = []
        self._active_select = None
        self._active_option = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()

        if tag == "select":
            self._active_select = attributes.get("id")
        elif tag == "option" and self._active_select in {"s_version", "s_page"}:
            self._active_option = (
                self._active_select,
                attributes.get("value", ""),
            )
            self._option_text = []
        elif tag == "ul" and "mu_list_table" in classes and "mu_head" not in classes:
            self._active_list = True
            self._list_items = []
        elif self._active_list and tag == "li":
            self._active_li = True
            self._list_items.append({"paragraphs": []})
        elif self._active_list and self._active_li and tag == "p":
            self._active_p = True
            self._p_text = []
            self._p_level = attributes.get("data-d")
            self._p_label = []
        elif self._active_p and tag == "span":
            self._active_span = True
            self._span_text = []
    def handle_endtag(self, tag):
        if tag == "span" and self._active_span:
            self._p_label.append("".join(self._span_text))
            self._active_span = False
        elif tag == "p" and self._active_p:
            self._list_items[-1]["paragraphs"].append(
                {
                    "text": clean_text("".join(self._p_text)),
                    "level": self._p_level,
                    "label": clean_text("".join(self._p_label)),
                }
            )
            self._active_p = False
        elif tag == "li" and self._active_li:
            self._active_li = False
        elif tag == "ul" and self._active_list:
            self._record_list()
            self._active_list = False
        elif tag == "option" and self._active_option:
            select_id, value = self._active_option
            text = clean_text("".join(self._option_text))
            if select_id == "s_version" and value.isdigit():
                self.version_names[int(value)] = text
            elif select_id == "s_page" and value.isdigit():
                self.page_numbers.add(int(value))
            self._active_option = None
        elif tag == "select":
            self._active_select = None

    def handle_data(self, data):
        if self._active_p:
            self._p_text.append(data)
        if self._active_span:
            self._span_text.append(data)
        if self._active_option:
            if not hasattr(self, "_option_text"):
                self._option_text = []
            self._option_text.append(data)

    def _record_list(self):
        current_record = None
        for item in self._list_items:
            paragraphs = item["paragraphs"]
            difficulty_paragraphs = [
                paragraph
                for paragraph in paragraphs
                if paragraph["label"].upper()
                in {"LIGHT", "NORMAL", "HYPER", "EX"}
            ]
            if difficulty_paragraphs:
                if current_record is None:
                    continue
                for paragraph in difficulty_paragraphs:
                    label = paragraph["label"].upper()
                    level = paragraph["level"]
                    if not level or not level.isdigit():
                        match = re.search(r"\d+", paragraph["text"])
                        level = match.group(0) if match else ""
                    column = {
                        "LIGHT": "level_l",
                        "NORMAL": "level_n",
                        "HYPER": "level_h",
                        "EX": "level_ex",
                    }[label]
                    current_record[column] = level
                continue

            if len(paragraphs) < 3:
                continue
            genre, title, artist = (paragraph["text"] for paragraph in paragraphs[:3])
            if not title:
                continue

            current_record = {
                "title": title,
                "genre": genre,
                "artist": artist,
                "level_l": "",
                "level_n": "",
                "level_h": "",
                "level_ex": "",
            }
            self.records.append(current_record)

    def parse(self, html):
        self._option_text = []
        self.feed(html)
        return self


def build_page_url(version, page):
    query = urlencode(
        {
            "page": page,
            "version": version,
            "lv": 0,
            "bemani": 0,
            "category": 0,
            "keyword": "",
            "sort": "music",
            "sort_type": "up",
        }
    )
    return f"{BASE_URL}?{query}"


def fetch_page(url):
    request = Request(
        url,
        headers={"User-Agent": "popn-music-list-builder/1.0 (+public page crawler)"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (OSError, URLError) as error:
        raise RuntimeError(f"ページを取得できませんでした: {url}\n{error}") from error


def crawl_version(version):
    first_url = build_page_url(version, 0)
    first_page = AcPageParser().parse(fetch_page(first_url))
    if not first_page.records:
        raise RuntimeError(
            "ACページから楽曲データを取得できませんでした。"
            f"ログイン不要で閲覧できるか確認してください: {first_url}"
        )

    page_numbers = sorted(first_page.page_numbers or {0})
    records = list(first_page.records)
    seen = {record["title"] + "\0" + record["artist"] for record in records}

    for page in page_numbers:
        if page == 0:
            continue
        time.sleep(REQUEST_INTERVAL_SECONDS)
        url = build_page_url(version, page)
        parsed = AcPageParser().parse(fetch_page(url))
        if not parsed.records:
            raise RuntimeError(
                f"ページ {page} から楽曲データを取得できませんでした: {url}"
            )
        for record in parsed.records:
            key = record["title"] + "\0" + record["artist"]
            if key not in seen:
                seen.add(key)
                records.append(record)

    return first_page.version_names.get(version, f"version {version}"), records


def main():
    all_records = []
    for version in range(30):
        version_name, records = crawl_version(version)
        for record in records:
            record["version"] = version_name
            all_records.append(record)
        print(f"[{version:02d}/29] version={version}: {len(records)} songs")
        time.sleep(REQUEST_INTERVAL_SECONDS)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_records)
    print(f"\nAC master: {OUTPUT_PATH} ({len(all_records)} songs)")


if __name__ == "__main__":
    main()
