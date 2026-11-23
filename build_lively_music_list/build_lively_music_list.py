import csv
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

from urllib.error import URLError
from urllib.request import Request, urlopen


SOURCE_URL = "https://p.eagate.573.jp/game/eacpopn/lively/info/music.html"
AC_MASTER_PATH = (
    Path(__file__).resolve().parent.parent
    / "build_ac_music_list"
    / "ac_master.csv"
)
OUTPUT_PATH = Path(__file__).with_name("lively_master.csv")
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


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).casefold()


class LivelyPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self._active_table = False
        self._rows = []
        self._active_row = False
        self._cells = []
        self._active_cell = False
        self._cell_text = []
        self._cell_is_header = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._active_table = True
            self._rows = []
        elif self._active_table and tag == "tr":
            self._active_row = True
            self._cells = []
        elif self._active_row and tag in {"td", "th"}:
            self._active_cell = True
            self._cell_is_header = tag == "th"
            self._cell_text = []
        elif self._active_cell and tag == "br":
            self._cell_text.append(" ")

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._active_cell:
            self._cells.append(
                (clean_text("".join(self._cell_text)), self._cell_is_header)
            )
            self._active_cell = False
        elif tag == "tr" and self._active_row:
            if self._cells:
                self._rows.append(self._cells)
            self._active_row = False
        elif tag == "table" and self._active_table:
            self.tables.append(self._rows)
            self._active_table = False

    def handle_data(self, data):
        if self._active_cell:
            self._cell_text.append(data)

    def parse(self, html):
        self.feed(html)
        return self


def parse_lively_html(html):
    parser = LivelyPageParser().parse(html)
    songs = []
    for table in parser.tables:
        for row in table:
            if any(is_header for _, is_header in row):
                continue
            values = [value for value, _ in row]
            if len(values) >= 3:
                genre, title, artist = values[:3]
            elif len(values) == 2:
                genre, (title, artist) = "", values
            else:
                continue
            if title and artist:
                songs.append({"title": title, "genre": genre, "artist": artist})
    if not songs:
        raise RuntimeError("公式ページからLively楽曲一覧を読み取れませんでした。")
    return songs


def fetch_lively_html():
    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "popn-music-list-builder/1.0 (+public page crawler)"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (OSError, URLError) as error:
        raise RuntimeError(f"Lively公式ページを取得できませんでした: {error}") from error


def read_ac_master(path):
    if not path.exists():
        raise FileNotFoundError(
            f"ACマスタがありません: {path}\n"
            "先に build_ac_music_list\\run.bat を実行してください。"
        )
    with path.open(newline="", encoding="utf-8-sig") as input_file:
        return list(csv.DictReader(input_file))


def build_lively_master(lively_songs, ac_songs):
    by_title_artist = {}
    for song in ac_songs:
        title_key = normalize(song.get("title", ""))
        artist_key = normalize(song.get("artist", ""))
        if not title_key:
            continue
        by_title_artist.setdefault((title_key, artist_key), []).append(song)

    result = []
    exact_matches = 0
    for lively in lively_songs:
        title_key = normalize(lively["title"])
        artist_key = normalize(lively["artist"])
        matches = by_title_artist.get((title_key, artist_key), [])
        if matches:
            exact_matches += 1

        ac_song = matches[-1] if matches else {}
        result.append(
            {
                "title": lively["title"],
                "genre": lively["genre"] or ac_song.get("genre", ""),
                "artist": lively["artist"],
                "version": ac_song.get("version", ""),
                "level_l": ac_song.get("level_l", ""),
                "level_n": ac_song.get("level_n", ""),
                "level_h": ac_song.get("level_h", ""),
                "level_ex": ac_song.get("level_ex", ""),
            }
        )
    return result, exact_matches


def main():
    lively_songs = parse_lively_html(fetch_lively_html())
    ac_songs = read_ac_master(AC_MASTER_PATH)
    merged, exact_matches = build_lively_master(lively_songs, ac_songs)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged)

    print(f"Lively songs: {len(merged)}")
    print(f"Matched with AC master (title + artist): {exact_matches}")
    print(f"Unmatched: {len(merged) - exact_matches}")
    print(f"Lively master: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
