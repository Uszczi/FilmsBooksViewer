import curses
import glob
import os
import re
from dataclasses import dataclass
from enum import Enum

HELP_ITEMS = [
    ("q", "Quit"),
    ("h/l", "Switch tab"),
    ("j/k", "Scroll"),
    ("u/d", "Scroll half page"),
    ("f,/", "Search"),
    ("a", "Add"),
    ("e", "Edit"),
    ("", ""),
    ("", ""),
]

BASE_PATH = os.path.expanduser("~/zetel/Zettelkasten/")


class TabsEnum(Enum):
    films = "Films"
    books = "Books"


TABS = (TabsEnum.films, TabsEnum.books)


@dataclass
class EntryBase:
    title: str
    is_valid: bool
    counter: int = 0


@dataclass(kw_only=True)
class FilmEntry(EntryBase):
    director: str
    watch_year: int
    production_year: int

    @classmethod
    def from_str(cls, text: str, year: int):
        # Format: Title (year) **Director**
        pattern = r"^(.+?)\s*\((\d{4})\)\s*\*\*\s*(.+)\*\*$"
        match = re.match(pattern, text.strip())

        if not match:
            return cls(
                title=text,
                director="",
                watch_year=year,
                production_year=0,
                is_valid=False,
            )

        title = match.group(1).strip()
        entry_year = int(match.group(2))
        director = match.group(3).strip()

        return cls(
            title=title,
            director=director,
            watch_year=year,
            production_year=entry_year,
            is_valid=True,
        )

    def display(self):
        return f"{self.title} {self.production_year} {self.director} {self.watch_year}"


@dataclass(kw_only=True)
class BookEntry(EntryBase):
    author: str
    read_year: int

    @classmethod
    def from_str(cls, text: str, year: int):
        # Format: Title **Author**
        pattern = r"^(.+?)\s*\*\*\s*(.+)$"
        match = re.match(pattern, text.strip())

        if not match:
            return cls(
                title=text,
                author="",
                read_year=0,
                is_valid=False,
            )

        title = match.group(1).strip()
        author = match.group(2).strip()

        return cls(
            title=title,
            author=author,
            read_year=year,
            is_valid=True,
        )

    def display(self):
        return f"{self.title} {self.author} {self.read_year}"


def create_main_win(stdscr: curses.window):
    max_height, max_width = stdscr.getmaxyx()
    win_h, win_w = max_height - 4, max_width - 2

    win = curses.newwin(win_h, win_w, 2, 1)

    win.border()

    return win


def draw_tabs(stdscr: curses.window, active_tab: int):
    _max_height, max_width = stdscr.getmaxyx()

    win_w = max_width - 2

    x0 = win_w // 2 - len(TabsEnum.films.value) - 2
    x1 = win_w // 2 + 2

    draw_tab(stdscr, 0, x0, TabsEnum.films.value, 0 == active_tab)
    draw_tab(stdscr, 0, x1, TabsEnum.books.value, 1 == active_tab)

    stdscr.refresh()


def draw_tab(win, y, x, label, active):
    tab_w = len(label) + 4
    tab_win = win.derwin(3, tab_w, y, x - 2)
    tab_win.border()
    if active:
        prop = curses.A_BOLD | curses.color_pair(3)
    else:
        prop = 0

    tab_win.addstr(1, 2, label, prop)
    return tab_win


def draw_help_bar(win):
    max_height, max_width = win.getmaxyx()

    mid = (len(HELP_ITEMS) + 1) // 2
    rows = [HELP_ITEMS[:mid], HELP_ITEMS[mid:]]

    for row_idx, row_items in enumerate(rows):
        y = max_height - 2 + row_idx

        win.attron(curses.A_REVERSE)
        win.addstr(y, 0, " " * (max_width - 1))

        x = 1
        for key, desc in row_items:
            if x + len(key) + len(desc) + 3 >= max_width:
                break
            win.attron(curses.A_BOLD | curses.A_REVERSE)
            win.addstr(y, x, key)
            win.attroff(curses.A_BOLD)
            win.addstr(y, x + len(key) + 1, desc)
            x += len(key) + len(desc) + 3

        win.attroff(curses.A_REVERSE)

    win.refresh()


def create_pad(win: curses.window, entries: list[FilmEntry | BookEntry]):
    win_h, win_w = win.getmaxyx()

    pad_height = max(len(entries), win_h - 4)
    pad = curses.newpad(pad_height + 1, win_w - 3)

    for idx, entry in enumerate(entries):
        text = entry.display()

        if entry.is_valid:
            pad.addstr(idx, 0, text)
        else:
            pad.addstr(idx, 0, text, curses.color_pair(1))

    return pad


def draw_pad(
    win: curses.window,
    pad: curses.window,
    scroll_offset: int,
):
    max_height, max_width = win.getmaxyx()

    pad.refresh(scroll_offset, 0, 3, 3, max_height, max_width)


def read_files(
    pattern: str, result_type: type[FilmEntry] | type[BookEntry]
) -> list[FilmEntry | BookEntry]:
    try:
        year = int(pattern.split(" ")[0])
    except ValueError:
        year = 0

    file_pattern = os.path.join(BASE_PATH, f"{pattern}.md")
    files = sorted(glob.glob(file_pattern))

    entries = []
    for file_path in files:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("-"):
                    entry = result_type.from_str(line, year=year)

                    entries.append(entry)

    return entries


def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)


def main(stdscr: curses.window):
    init_colors()
    stdscr.clear()

    films = read_files("Films [0-9][0-9][0-9][0-9]", FilmEntry)
    books = read_files("Books [0-9][0-9][0-9][0-9]", BookEntry)

    active_tab = 0
    scroll_offset = 0

    if active_tab == 0:
        max_offset = len(films) - 1
    elif active_tab == 1:
        max_offset = len(books) - 1

    while True:
        win = create_main_win(stdscr)
        max_height, _max_width = win.getmaxyx()

        films_pad = create_pad(win, films)
        books_pad = create_pad(win, books)
        pads = [films_pad, books_pad]

        draw_tabs(stdscr, active_tab)
        draw_help_bar(stdscr)
        pad = pads[active_tab]
        draw_pad(win, pad, scroll_offset)

        key = stdscr.getch()
        if key == ord("q"):
            break
        elif key in (ord("h"), curses.KEY_LEFT):
            active_tab = (active_tab - 1) % len(TABS)
            scroll_offset = 0
        elif key in (ord("l"), curses.KEY_RIGHT):
            active_tab = (active_tab + 1) % len(TABS)
            scroll_offset = 0
        elif key in (ord("j"), curses.KEY_DOWN):
            scroll_offset = min(scroll_offset + 1, max_offset)
        elif key in (ord("k"), curses.KEY_UP):
            scroll_offset = max(scroll_offset - 1, 0)
        elif key in (ord("d"), curses.KEY_DOWN):
            scroll_offset = min(scroll_offset + max_height // 2, max_offset)
        elif key in (ord("u"), curses.KEY_UP):
            scroll_offset = max(scroll_offset - max_height // 2, 0)


if __name__ == "__main__":
    curses.wrapper(main)


def cli():
    curses.wrapper(main)
