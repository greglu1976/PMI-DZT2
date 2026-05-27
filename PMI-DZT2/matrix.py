# РАБОТА С ФАЙЛОМ КОНФИГУРАЦИИ МАТРИЦЫ ВХОДОВ ВЫХОДОВ

# combined_gui.py — полная версия с редактированием, выпадающими списками и валидацией

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
import re
from CORE.InOutsMatrixHandler import InOutsMatrixHandler
from CORE.MainConfigHandler import MainConfigHandler


class MatrixEditorApp:
    def __init__(self, root: tk.Tk, inouts_handler: InOutsMatrixHandler, config_handler: MainConfigHandler, matrix_file_path: str):
        self.root = root
        self.inouts_handler = inouts_handler
        self.config_handler = config_handler
        self.matrix_file_path = matrix_file_path

        # === Настройка диапазонов (можно менять) ===
        self.ins = ["8-14", "9-2"]   # формат: "слот-количество"
        self.outs = ["3-8", "4-8"]

        # Генерация допустимых значений
        self.discrete_options = ["-"] + self._generate_from_ranges(self.ins, letter="B")
        self.relay_options = ["-"] + self._generate_from_ranges(self.outs, letter="K")

        self.root.title("Редактор матрицы входов/выходов")
        self.root.geometry("950x600")

        # === Кнопки ===
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        reset_btn = tk.Button(button_frame, text="🧹 Сбросить входы и выходы", command=self.reset_all_io)
        reset_btn.pack(side=tk.LEFT, padx=5)

        save_btn = tk.Button(button_frame, text="💾 Сохранить в JSON", command=self.save_changes)
        save_btn.pack(side=tk.LEFT, padx=5)

        # Таблица
        # В __init__ замените:
        columns = ("param_desc", "applied_desc", "discrete", "digital", "relay")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=25)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        headings = {
            "param_desc": "Имя параметра",
            "applied_desc": "Применяемое описание",
            "discrete": "Дискр.Вход",
            "digital": "Двоич.Вход",
            "relay": "Вых. Реле"
        }
        self.sort_states = {col: False for col in columns}

        for col, text in headings.items():
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by_column(c))
            if col == "param_desc":
                width = 200
            elif col == "applied_desc":
                width = 300
            else:
                width = 120
            self.tree.column(col, width=width)

        self.tree.bind("<Double-1>", self.on_double_click)

        vsb = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.item_param_map = {}
        self.load_data_into_tree()

    def _generate_from_ranges(self, ranges: List[str], letter: str) -> List[str]:
        """Генерирует список адресов по шаблонам вида ['8-8', '9-14'] с указанной буквой (B или K)."""
        result = []
        for r in ranges:
            if '-' not in r:
                continue
            try:
                bank_str, count_str = r.split('-', 1)
                bank = int(bank_str)
                count = int(count_str)
                for i in range(1, count + 1):
                    result.append(f"{bank}{letter}{i}")
            except ValueError:
                continue  # игнорируем некорректные записи
        return result

    def load_data_into_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.item_param_map.clear()

        for param_name in self.inouts_handler.get_all_parameter_names():
            # Имя параметра
            param_label = param_name

            # Применяемое описание
            applied_desc = self.config_handler.get_applied_description(param_name)

            # Сигналы
            disc = ", ".join(self.inouts_handler.get_discrete_inputs(param_name)) or "-"
            digi = ", ".join(self.inouts_handler.get_digital_inputs(param_name)) or "-"
            rel  = ", ".join(self.inouts_handler.get_output_relays(param_name)) or "-"

            iid = self.tree.insert("", "end", values=(param_label, applied_desc, disc, digi, rel))
            self.item_param_map[iid] = param_name

    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)

        if column == "#1":  # описание — только для чтения
            return

        col_index = int(column.replace("#", "")) - 1
        if col_index not in (2, 3, 4):  # discrete=2, digital=3, relay=4
            return

        current_value = self.tree.item(row, "values")[col_index]
        if current_value == "-":
            current_value = ""

        # === Новое: модальное окно для столбцов 1 и 3 ===
        if col_index == 2:  # Дискр.Вход
            new_val = self.open_checkbox_editor(
                row, col_index, current_value,
                self.discrete_options,
                "Выберите дискретные входы"
            )
        elif col_index == 4:  # Вых. Реле
            new_val = self.open_checkbox_editor(
                row, col_index, current_value,
                self.relay_options,
                "Выберите выходные реле"
            )
        else:  # Двоич.Вход — остаётся Entry
            x, y, width, height = self.tree.bbox(row, column)
            widget = ttk.Entry(self.tree)
            widget.insert(0, current_value)
            widget.select_range(0, tk.END)
            widget.place(x=x, y=y, width=width, height=height)
            widget.focus()

            def save_edit(_):
                new_val_inner = widget.get().strip()
                values = list(self.tree.item(row, "values"))
                values[col_index] = new_val_inner if new_val_inner else "-"
                self.tree.item(row, values=values)
                widget.destroy()
                param_name = self.item_param_map[row]
                self.update_inouts_data(param_name, values[2], values[3], values[4])

            widget.bind("<Return>", save_edit)
            widget.bind("<FocusOut>", save_edit)
            widget.bind("<Escape>", lambda _: widget.destroy())
            return

        # Применяем результат из модального окна
        if new_val is not None:
            values = list(self.tree.item(row, "values"))
            values[col_index] = new_val
            self.tree.item(row, values=values)
            param_name = self.item_param_map[row]
            self.update_inouts_data(param_name, values[2], values[3], values[4])

    def parse_input_list(self, s: str) -> List[str]:
        if not s or s == "-":
            return []
        return [part.strip() for part in s.split(",") if part.strip()]

    def update_inouts_data(self, param_name: str, disc_str: str, digi_str: str, relay_str: str):
        disc = self.parse_input_list(disc_str)
        digi = self.parse_input_list(digi_str)
        relay = self.parse_input_list(relay_str)
        self.inouts_handler.update_signal_mapping(param_name, disc, digi, relay)

    def sort_by_column(self, col: str):
        items = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        def sort_key(item):
            val = item[0]
            if val == "-":
                return (0, "")
            try:
                return (1, int(val))
            except ValueError:
                return (1, val.lower())
        items.sort(key=sort_key, reverse=self.sort_states[col])
        for index, (_, child) in enumerate(items):
            self.tree.move(child, '', index)
        self.sort_states[col] = not self.sort_states[col]

    def save_changes(self):
        try:
            discrete_addresses = []
            seen_discrete = set()
            duplicate_found = False
            cyrillic_errors = []

            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                param_name = self.item_param_map[item]

                # Дискр.Вход
                disc_str = values[2]
                if disc_str != "-":
                    parts = [p.strip() for p in disc_str.split(",") if p.strip()]
                    for addr in parts:
                        if re.search(r'[А-Яа-яЁё]', addr):
                            cyrillic_errors.append(f"Дискр.Вход: {addr} (параметр: {param_name})")
                        if addr in seen_discrete:
                            duplicate_found = True
                        else:
                            seen_discrete.add(addr)
                        discrete_addresses.append(addr)

                # Вых. Реле
                relay_str = values[4]
                if relay_str != "-":
                    parts = [p.strip() for p in relay_str.split(",") if p.strip()]
                    for addr in parts:
                        if re.search(r'[А-Яа-яЁё]', addr):
                            cyrillic_errors.append(f"Вых. Реле: {addr} (параметр: {param_name})")

            error_messages = []
            if cyrillic_errors:
                error_messages.append(
                    "Обнаружены кириллические символы в адресах:\n" +
                    "\n".join(cyrillic_errors) +
                    "\n\nИспользуйте только латинские буквы (например, 'B', а не 'В')."
                )
            if duplicate_found:
                error_messages.append(
                    "Обнаружены повторяющиеся адреса в столбце 'Дискр.Вход'.\n"
                    "Каждый дискретный вход должен использоваться только один раз."
                )

            if error_messages:
                messagebox.showerror("Ошибка при сохранении", "\n\n".join(error_messages))
                return

            self.inouts_handler.save_to_json_file(self.matrix_file_path)
            messagebox.showinfo("Успех", f"Изменения успешно сохранены в:\n{self.matrix_file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")


    def open_checkbox_editor(self, parent_item, col_index, current_value, options, title):
        """Открывает модальное окно с чекбоксами рядом с главным окном."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()  # модальное
        
        # === Текущие выбранные значения ===
        current_set = set(current_value.split(", ")) if current_value != "-" else set()
        
        # === Контейнер для чекбоксов (с прокруткой если много опций) ===
        canvas = tk.Canvas(dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # === Переменные для чекбоксов ===
        var_dict = {}
        for opt in options:
            if opt == "-":
                continue
            var = tk.BooleanVar(value=(opt in current_set))
            cb = tk.Checkbutton(scrollable_frame, text=opt, variable=var, font=("Arial", 10))
            cb.pack(anchor="w", padx=10, pady=3)
            var_dict[opt] = var
        
        # === Расположение canvas и scrollbar ===
        canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if len(var_dict) > 8:  # показываем scrollbar если много опций
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === Кнопки ===
        result = [None]
        
        def on_ok():
            selected = [opt for opt, var in var_dict.items() if var.get()]
            result[0] = ", ".join(selected) if selected else "-"
            dialog.destroy()
        
        def on_cancel():
            result[0] = None
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # === Вычисляем размер окна ===
        dialog.update_idletasks()
        
        # Высота: количество опций × ~25 пикселей + место для кнопок
        option_count = len(var_dict)
        calculated_height = min(option_count * 25 + 80, 500)  # макс. 500 пикселей
        dialog.geometry(f"320x{calculated_height}")
        
        # === Позиционируем окно рядом с главным ===
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        # Открываем справа от главного окна
        dialog_x = main_x + main_width + 10
        dialog_y = main_y + 50
        
        # Проверяем, не выходит ли за экран
        screen_width = self.root.winfo_screenwidth()
        if dialog_x + 320 > screen_width:
            dialog_x = main_x - 330  # открываем слева
        
        dialog.geometry(f"+{dialog_x}+{dialog_y}")
        
        self.root.wait_window(dialog)
        return result[0]


    def reset_all_io(self):
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сбросить все входы и выходы?"):
            return

        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[2] = "-"  # discrete
            values[4] = "-"  # relay
            self.tree.item(item, values=values)

            param_name = self.item_param_map[item]
            self.update_inouts_data(param_name, "-", values[3], "-")
        
        #messagebox.showinfo("Готово", "Все входы и выходы сброшены.")


def create_editor_window(inouts_handler: InOutsMatrixHandler, config_handler: MainConfigHandler, matrix_file_path: str):
    root = tk.Tk()
    app = MatrixEditorApp(root, inouts_handler, config_handler, matrix_file_path)
    root.mainloop()


if __name__ == "__main__":
    METADATA_FILE = "meta.json"
    MATRIX_FILE = "ПМИ Матрица.json"

    try:
        config_handler = MainConfigHandler.from_json_file(METADATA_FILE)
        inouts_handler = InOutsMatrixHandler.from_json_file(MATRIX_FILE)
        create_editor_window(inouts_handler, config_handler, MATRIX_FILE)
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        input("Нажмите Enter для выхода...")