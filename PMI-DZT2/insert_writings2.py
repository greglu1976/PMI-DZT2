# Для ИЧМ

import os
import sys
import pymupdf


def app_dir():
    """
    Возвращает папку, где лежат:
      - сам .exe, если скрипт собран в EXE
      - сам .py-скрипт, если запущен как скрипт
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = app_dir()

INPUT_PDF  = os.path.join(APP_DIR, "input.pdf")
OUTPUT_PDF = os.path.join(APP_DIR, "output.pdf")
DATA_TXT   = os.path.join(APP_DIR, "data.txt")


def find_font():
    """
    Ищет шрифт Arial Narrow:
      1) рядом с EXE/скриптом
      2) в системной папке Windows
    Возвращает (путь_к_файлу, имя_шрифта).
    """
    local_variants = [
        "ArialNarrow.ttf",
        "arialn.ttf",
        "ARIALN.TTF",
    ]
    for name in local_variants:
        p = os.path.join(APP_DIR, name)
        if os.path.isfile(p):
            return p, "ArialNarrow"

    system_variants = [
        r"C:\Windows\Fonts\arialn.ttf",
        r"C:\Windows\Fonts\ARIALN.TTF",
        r"C:\Windows\Fonts\ArialNarrow.ttf",
    ]
    for p in system_variants:
        if os.path.isfile(p):
            return p, "ArialNarrow"

    raise FileNotFoundError(
        "Не найден шрифт Arial Narrow ни рядом с программой, "
        "ни в C:\\Windows\\Fonts (arialn.ttf)."
    )


FONT_PATH, FONT_NAME = find_font()


def wrap_text_simple(text, max_chars):
    """Переносит текст по словам, ограничивая длину строки в символах."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_chars:
            current_line = (current_line + " " + word) if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def read_pairs(path, sep="-"):
    """
    Читает txt-файл, где каждая строка — пара 'первое - второе'.
    """
    col1, col2 = [], []

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue

            if sep in line:
                left, right = line.split(sep, 1)
            else:
                left, right = line, ""

            col1.append(left.strip())
            col2.append(right.strip())

    return col1, col2


# ---------- Параметры ----------
col1_x = 385
col2_x = 455
start_y = 168
step_y = 32.6

col1_width_chars = 13
col2_width_chars = 17

# ---------- Чтение данных ----------
text_list_1, text_list_2 = read_pairs(DATA_TXT, sep="-")

# ---------- Открываем PDF ----------
doc = pymupdf.open(INPUT_PDF)
page = doc[0]

# ---------- Первый столбец ----------
for i, item in enumerate(text_list_1):
    if not item:
        continue
    current_y = start_y + step_y * i
    for line in wrap_text_simple(item, col1_width_chars):
        page.insert_text(
            (col1_x, current_y),
            line,
            fontsize=9,
            fontname=FONT_NAME,
            fontfile=FONT_PATH,
            color=(0, 0, 0),
        )
        current_y += 9

# ---------- Второй столбец ----------
for i, item in enumerate(text_list_2):
    if not item:
        continue
    item_y = start_y + step_y * i
    for line in wrap_text_simple(item, col2_width_chars):
        page.insert_text(
            (col2_x, item_y),
            line,
            fontsize=9,
            fontname=FONT_NAME,
            fontfile=FONT_PATH,
            color=(0, 0, 0),
        )
        item_y += 9

doc.save(OUTPUT_PDF)
doc.close()
print(f"Готово! Данные взяты из {DATA_TXT}, результат: {OUTPUT_PDF}")
print(f"Использован шрифт: {FONT_PATH}")