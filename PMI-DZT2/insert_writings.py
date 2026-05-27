# Для ИЧМ

import pymupdf

def wrap_text_simple(text, max_chars):
    """Переносит текст по символам"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= max_chars:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

# Параметры столбцов
col1_x = 385      # X координата первого столбца
col2_x = 455      # X координата второго столбца
start_y = 168   # начальная Y координата
step_y = 32.6     # шаг между строками (расстояние между позициями)

# Ширина столбцов в символах
col1_width_chars = 13   # ширина первого столбца в символах
col2_width_chars = 17   # ширина второго столбца в символах

# Данные для первого столбца
#text_list_1 = ["М/Д", "МТЗ 3 ст на сигн", "Вывод терминала"]
# Данные для второго столбца
#text_list_2 = ["МТЗ 3 ст: Пуск ф.А", "МТЗ 3 ст: Пуск ф.В", "МТЗ 3 ст: Пуск ф.С", "МТЗ 3 ст: Пуск", "МТЗ 3 ст: Срабатывание сигн", "МТЗ 3 ст: Срабатывание", "МТЗ 3 ст: ИО IА", "МТЗ 3 ст: ИО IВ", "МТЗ 3 ст: ИО IС", "ЛО Т / ЛО: Срабатывание", "ЛО Т / ЗАПВ: Запрет АПВ",  "ЛО Т / ЗАВР: Запрет АВР", "БЛЗШ: Блокировка", "ПС: Пуск", "КПОН2: Пуск", "КЦН2: Неисправность ЦН"]

# Данные для первого столбца
text_list_1 = ["М/Д", "МТЗ 1 ст на сигн", "Вывод терминала"]
# Данные для второго столбца
text_list_2 = ["МТЗ 1 ст: Пуск ф.А", "МТЗ 1 ст: Пуск ф.В", "МТЗ 1 ст: Пуск ф.С", "МТЗ 1 ст: Пуск", "МТЗ 1 ст: Срабатывание сигн", "МТЗ 1 ст: Срабатывание", "МТЗ 1 ст: ИО IА", "МТЗ 1 ст: ИО IВ", "МТЗ 1 ст: ИО IС", "ЛО Т / ЛО: Срабатывание", "ЛО Т / ЗАПВ: Запрет АПВ",  "ЛО Т / ЗАВР: Запрет АВР", "БЛЗШ: Блокировка", "ПС: Пуск", "КПОН1: Пуск", "КЦН1: Неисправность ЦН"]


# Открываем PDF
doc = pymupdf.open("input.pdf")
page = doc[0]

# Вывод первого столбца
current_y = start_y
for item in text_list_1:
    # Разбиваем длинный текст на строки
    lines = wrap_text_simple(item, col1_width_chars)
    for line in lines:
        page.insert_text(
            (col1_x, current_y),
            line,
            fontsize=9,
            fontname="Montserrat",
            fontfile="Montserrat-Regular.ttf",
            color=(0, 0, 0)
        )
        current_y += 11  # отступ между строками внутри одного пункта
    current_y = start_y + step_y * (text_list_1.index(item) + 1)

# Вывод второго столбца (выравнивание по строкам первого столбца)
for i, item in enumerate(text_list_2):
    # Разбиваем длинный текст на строки
    lines = wrap_text_simple(item, col2_width_chars)
    # Y координата соответствует строке из первого столбца
    item_y = start_y + step_y * i
    for line in lines:
        page.insert_text(
            (col2_x, item_y),
            line,
            fontsize=9,
            fontname="Montserrat",
            fontfile="Montserrat-Regular.ttf",
            color=(0, 0, 0)
        )
        item_y += 11  # отступ между строками


doc.save("output.pdf")
doc.close()
print("Готово! Текст выведен в два столбца")