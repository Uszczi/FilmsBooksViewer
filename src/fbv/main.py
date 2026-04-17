import curses
import datetime
import glob
import os
import re
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial

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


_store: dict = {}


class TabsEnum(Enum):
    films = "Films"
    books = "Books"


TABS = (TabsEnum.films, TabsEnum.books)


class ValuesEnum(Enum):
    scroll_offset = auto()
    max_offset = auto()
    current_line = auto()


def set(
    name: ValuesEnum,
    value,
    active_tab: int,
):
    _store[(name, active_tab)] = value


def get(
    name: ValuesEnum,
    active_tab: int,
):
    return _store.get((name, active_tab), 0)


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


TYPES = type[FilmEntry] | type[BookEntry]
TYPES_INS = FilmEntry | BookEntry


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


def draw_edit_entry(
    win: curses.window,
    entry: TYPES_INS,
) -> TYPES_INS:
    pass


def _get_fields(entry_type: TYPES):
    if entry_type == FilmEntry:
        fields = [
            ("Title", ""),
            ("Director", ""),
            ("Production Year", ""),
        ]
        title_text = "Add Film Entry"
    else:  # BookEntry
        fields = [
            ("Title", ""),
            ("Author", ""),
        ]
        title_text = "Add Book Entry"

    return fields, title_text


def draw_add_entry(
    win: curses.window, entry_type: TYPES
) -> FilmEntry | BookEntry | None:
    """
    Draw a dialog for adding a new entry (Film or Book).
    Returns the created entry or None if cancelled.
    """

    current_year = datetime.datetime.now().year

    fields, title_text = _get_fields(entry_type)

    # Create centered dialog
    max_h, max_w = win.getmaxyx()
    dialog_h = len(fields) * 2 + 8  # fields + title + buttons + padding
    dialog_w = 60
    start_y = max(0, (max_h - dialog_h) // 2)
    start_x = max(0, (max_w - dialog_w) // 2)

    # Create dialog window
    dialog = curses.newwin(dialog_h, dialog_w, start_y, start_x)
    dialog.keypad(True)

    current_field = 0
    field_values = [""] * len(fields)

    while True:
        dialog.clear()
        dialog.border()

        # Draw title
        dialog.addstr(
            1,
            (dialog_w - len(title_text)) // 2,
            title_text,
            curses.A_BOLD | curses.color_pair(4),
        )

        # Draw fields
        for idx, (label, _) in enumerate(fields):
            y = 3 + idx * 2
            dialog.addstr(y, 2, f"{label}:")

            # Draw input box
            input_x = 2
            input_y = y + 1
            input_w = dialog_w - 4

            if idx == current_field:
                dialog.attron(curses.color_pair(5))

            dialog.addstr(input_y, input_x, " " * (input_w - 1))
            display_value = field_values[idx][: input_w - 2]
            dialog.addstr(input_y, input_x, display_value)

            if idx == current_field:
                dialog.attroff(curses.color_pair(5))

        # Draw buttons
        button_y = dialog_h - 3
        cancel_x = dialog_w // 2 - 15
        accept_x = dialog_w // 2 + 5

        # Cancel button
        if current_field == len(fields):
            dialog.addstr(button_y, cancel_x, "[ Cancel ]", curses.A_REVERSE)
        else:
            dialog.addstr(button_y, cancel_x, "[ Cancel ]")

        # Accept button
        if current_field == len(fields) + 1:
            dialog.addstr(button_y, accept_x, "[ Accept ]", curses.A_REVERSE)
        else:
            dialog.addstr(button_y, accept_x, "[ Accept ]")

        # Draw help text
        help_text = "Tab/↑↓: Navigate | Enter: Select | Esc: Cancel"
        try:
            dialog.addstr(
                dialog_h - 1,
                max(1, (dialog_w - len(help_text)) // 2),
                help_text[: dialog_w - 2],
                curses.A_DIM,
            )
        except curses.error:
            pass

        dialog.refresh()

        key = dialog.getch()

        if key == 27:  # ESC
            return None
        elif key in (curses.KEY_DOWN, 9):  # Down arrow or Tab
            current_field = (current_field + 1) % (len(fields) + 2)
        elif key in (curses.KEY_UP, curses.KEY_BTAB):  # Up arrow or Shift+Tab
            current_field = (current_field - 1) % (len(fields) + 2)
        elif key == 10:  # Enter
            if current_field == len(fields):  # Cancel button
                return None
            elif current_field == len(fields) + 1:  # Accept button
                # Validate and create entry
                if entry_type == FilmEntry:
                    title = field_values[0].strip()
                    director = field_values[1].strip()
                    try:
                        production_year = (
                            int(field_values[2].strip())
                            if field_values[2].strip()
                            else 0
                        )
                    except ValueError:
                        production_year = 0

                    if not title:
                        continue

                    return FilmEntry(
                        title=title,
                        director=director,
                        watch_year=current_year,
                        production_year=production_year,
                        is_valid=bool(title and director and production_year),
                    )
                else:  # BookEntry
                    title = field_values[0].strip()
                    author = field_values[1].strip()

                    if not title:
                        continue

                    return BookEntry(
                        title=title,
                        author=author,
                        read_year=current_year,
                        is_valid=bool(title and author),
                    )
        elif current_field < len(fields):
            # Handle text input for current field
            if key == curses.KEY_BACKSPACE or key == 127:
                field_values[current_field] = field_values[current_field][:-1]
            elif 32 <= key <= 126:  # Printable characters
                field_values[current_field] += chr(key)


def draw_scroll(win: curses.window, scroll_offset: int, max_lines: int) -> None:
    win_h, win_w = win.getmaxyx()

    # Available height for scrollbar (excluding borders and tab area)
    available_h = win_h - 6  # Account for tabs (3) + borders + help bar

    if max_lines <= available_h:
        # Content fits, no scrollbar needed
        return

    # Calculate thumb size (proportional to visible area vs total content)
    thumb_size = max(1, int(available_h * available_h / max_lines))

    # Calculate thumb position based on scroll offset
    max_scroll = max_lines - available_h
    if max_scroll > 0:
        thumb_pos = int((scroll_offset / max_scroll) * (available_h - thumb_size))
    else:
        thumb_pos = 0

    # Draw scrollbar track and thumb on right side
    x = win_w - 4  # Position inside right border
    for y in range(available_h):
        actual_y = y + 3  # Offset for tab area (3 rows)
        try:
            if y >= thumb_pos and y < thumb_pos + thumb_size:
                win.addch(actual_y, x, "█", curses.color_pair(2))  # Thumb
            else:
                win.addch(actual_y, x, "│")  # Track
        except curses.error:
            pass  # Ignore errors at edge of screen

    win.refresh()


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


def create_pad(
    win: curses.window,
    entries: list[FilmEntry | BookEntry],
    current_line: int,
):
    win_h, win_w = win.getmaxyx()

    pad_height = max(len(entries), win_h - 4)
    pad = curses.newpad(pad_height + 1, win_w - 3)

    for idx, entry in enumerate(entries):
        text = entry.display()

        decorate = 0
        if idx == current_line:
            decorate = decorate | curses.color_pair(4)

        if entry.is_valid:
            pad.addstr(idx, 0, text, decorate)
        else:
            pad.addstr(idx, 0, text, decorate | curses.color_pair(1))

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

    file_pattern = os.path.join(BASE_PATH, f"{pattern}.md")
    files = sorted(glob.glob(file_pattern))

    entries = []
    for file_path in files:
        with open(file_path, "r") as f:
            try:
                year = int(f.name.split(" ")[1].removesuffix(".md"))
            except ValueError:
                year = 0

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
    data = [films, books]

    active_tab = 0

    _s = partial(set, active_tab=active_tab)
    _g = partial(get, active_tab=active_tab)

    while True:

        win = create_main_win(stdscr)
        max_height, _max_width = win.getmaxyx()

        films_pad = create_pad(win, films, _g(ValuesEnum.current_line))
        books_pad = create_pad(win, books, _g(ValuesEnum.current_line))
        pads = [films_pad, books_pad]

        if active_tab == 0:
            _s(ValuesEnum.max_offset, len(films) - 1)
        elif active_tab == 1:
            _s(ValuesEnum.max_offset, len(books) - 1)

        draw_tabs(stdscr, active_tab)
        win.refresh()
        draw_help_bar(stdscr)

        pad = pads[active_tab]
        draw_pad(win, pad, _g(ValuesEnum.scroll_offset))
        draw_scroll(stdscr, _g(ValuesEnum.scroll_offset), len(data[active_tab]))

        curses.curs_set(0)

        key = stdscr.getch()
        if key == ord("q"):
            break
        elif key in (ord("h"), curses.KEY_LEFT):
            active_tab = (active_tab - 1) % len(TABS)
        elif key in (ord("l"), curses.KEY_RIGHT):
            active_tab = (active_tab + 1) % len(TABS)
        elif key in (ord("j"), curses.KEY_DOWN):
            current_line = min(
                _g(ValuesEnum.current_line) + 1, len(data[active_tab]) - 1
            )
            _s(ValuesEnum.current_line, current_line)

            scroll_offset = min(
                _g(ValuesEnum.scroll_offset) + 1,
                _g(ValuesEnum.max_offset),
            )
            _s(ValuesEnum.scroll_offset, scroll_offset)
        elif key in (ord("k"), curses.KEY_UP):
            current_line = max(_g(ValuesEnum.current_line) - 1, 0)
            _s(ValuesEnum.current_line, current_line)

            scroll_offset = max(_g(ValuesEnum.scroll_offset) - 1, 0)
            _s(ValuesEnum.scroll_offset, scroll_offset)
        elif key in (ord("d"),):
            offset = max_height // 2
            scroll_offset = min(
                _g(ValuesEnum.scroll_offset) + offset,
                _g(ValuesEnum.max_offset),
            )
            _s(
                ValuesEnum.current_line,
                min(
                    _g(ValuesEnum.current_line) + offset,
                    _g(ValuesEnum.max_offset),
                ),
            )
            _s(ValuesEnum.scroll_offset, scroll_offset)
        elif key in (ord("u"),):
            offset = max_height // 2
            scroll_offset = max(_g(ValuesEnum.scroll_offset) - offset, 0)
            _s(ValuesEnum.scroll_offset, scroll_offset)
            _s(
                ValuesEnum.current_line,
                max(_g(ValuesEnum.current_line) - offset, 0),
            )
        elif key in (ord("g"),):
            _s(ValuesEnum.scroll_offset, 0)
            _s(ValuesEnum.current_line, 0)
        elif key in (ord("G"),):
            _s(ValuesEnum.scroll_offset, len(data[active_tab]) - 1)
            _s(ValuesEnum.current_line, len(data[active_tab]) - 1)

        elif key in (ord("a"),):
            entry_type = (FilmEntry, BookEntry)[active_tab]

            new_entry = draw_add_entry(stdscr, entry_type)

            if new_entry is not None:
                data[active_tab].append(new_entry)


def cli():
    curses.wrapper(main)


if __name__ == "__main__":
    cli()
