# registration_gui.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog  # ← добавлен simpledialog
from CORE.RegistrationHandler import RegistrationHandler
from CORE.MainConfigHandler import MainConfigHandler


class RegistrationEditorApp:
    def __init__(self, root: tk.Tk, reg_handler: RegistrationHandler, config_handler: MainConfigHandler, json_path: str):
        self.root = root
        self.reg_handler = reg_handler
        self.config_handler = config_handler
        self.json_path = json_path

        self.root.title("Редактор регистрационных настроек")
        self.root.geometry("1100x600")

        # === Кнопки: Обновить и Сохранить ===
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        refresh_btn = tk.Button(button_frame, text="🔄 Обновить", command=self.refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        save_btn = tk.Button(button_frame, text="💾 Сохранить в JSON", command=self.save_changes)
        save_btn.pack(side=tk.LEFT, padx=5)

        # В методе __init__, в блоке кнопок:
        group_btn = tk.Button(button_frame, text="🔄 Изменить группу", command=self.bulk_update_reg_condition)
        group_btn.pack(side=tk.LEFT, padx=5)


        # === Таблица ===
        columns = ("param_name", "description", "need_write", "reg_cond", "start_cond")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=25)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        headings = {
            "param_name": "Имя параметра",
            "description": "Описание",
            "need_write": "Запись в осциллограмму",
            "reg_cond": "Условие регистрации",
            "start_cond": "Условие запуска осциллографии"
        }
        widths = {
            "param_name": 200,
            "description": 300,
            "need_write": 150,
            "reg_cond": 150,
            "start_cond": 150
        }

        for col in columns:
            self.tree.heading(col, text=headings[col], anchor="w")
            self.tree.column(col, width=widths[col], anchor="w")

        # Настройка тега для активных строк
        self.tree.tag_configure("active", background="#e6f7e6")

        self.tree.bind("<Double-1>", self.on_double_click)

        vsb = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.item_param_map = {}
        self.load_data()

    def refresh_data(self):
        """Перезагружает данные из JSON-файлов и обновляет таблицу."""
        try:
            # Предполагаем, что metadata.json лежит рядом или путь известен
            # Лучше передавать его отдельно, но для совместимости — попытка угадать
            import os
            meta_path = os.path.join(os.path.dirname(self.json_path), "meta.json")
            if not os.path.exists(meta_path):
                # Альтернатива: если вы используете фиксированное имя
                meta_path = "meta.json"

            self.config_handler = MainConfigHandler.from_json_file(meta_path)
            self.reg_handler = RegistrationHandler.from_json_file(self.json_path)
            self.load_data()
            messagebox.showinfo("Успех", "Данные успешно обновлены из файлов.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить данные:\n{e}")

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        self.item_param_map.clear()

        for param_name in self.reg_handler.get_all_parameter_names():
            param_info = self.config_handler.get_param_info(param_name)
            description = param_info.get("description", "") if param_info else ""

            need_write = self.reg_handler.get_need_write_to_oscillogram(param_name)
            reg_cond = self.reg_handler.get_registration_condition(param_name)
            start_cond = self.reg_handler.get_start_oscillography_condition(param_name)

            values = (
                param_name,
                description,
                "Да" if need_write else "Нет",
                str(reg_cond),
                str(start_cond)
            )

            is_active = need_write or (reg_cond != 0) or (start_cond != 0)
            iid = self.tree.insert(
                "", "end",
                values=values,
                tags=("active",) if is_active else ()
            )
            self.item_param_map[iid] = param_name

    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)

        # Первые два столбца — только для чтения (имя и описание)
        if column in ("#1", "#2"):
            return

        col_index = int(column.replace("#", "")) - 1
        if col_index not in (2, 3, 4):  # индексы: need_write=2, reg_cond=3, start_cond=4
            return

        current_value = self.tree.item(row, "values")[col_index]
        entry = ttk.Entry(self.tree)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.focus()

        x, y, width, height = self.tree.bbox(row, column)
        entry.place(x=x, y=y, width=width, height=height)

        def apply_edit(_):
            new_val = entry.get().strip()
            values = list(self.tree.item(row, "values"))
            values[col_index] = new_val
            self.tree.item(row, values=values)
            entry.destroy()

            param_name = self.item_param_map[row]
            try:
                # Извлекаем актуальные значения из строки
                need_write = values[2].lower() in ("да", "yes", "true", "1")
                reg_cond = int(values[3])
                start_cond = int(values[4])

                self.reg_handler.update_mapping(param_name, need_write, reg_cond, start_cond)

                # Обновляем цвет строки
                is_active = need_write or (reg_cond != 0) or (start_cond != 0)
                self.tree.item(row, tags=("active",) if is_active else ())
            except ValueError:
                messagebox.showwarning("Ошибка ввода", "Условия должны быть целыми числами.\nNeedWrite: Да/Нет или True/False.")
                self.load_data()

        entry.bind("<Return>", apply_edit)
        entry.bind("<FocusOut>", apply_edit)
        entry.bind("<Escape>", lambda _: entry.destroy())

    def save_changes(self):
        try:
            self.reg_handler.save_to_json_file(self.json_path)
            messagebox.showinfo("Успех", f"Данные успешно сохранены в:\n{self.json_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")


    def bulk_update_reg_condition(self):
        """Групповое изменение 'Условие регистрации' для выделенных строк."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Внимание", "Сначала выделите строки для изменения.")
            return

        # Запрашиваем новое значение
        new_value_str = tk.simpledialog.askstring(
            "Групповое изменение",
            "Введите новое значение для 'Условие регистрации' (целое число):"
        )
        if new_value_str is None:
            return  # отмена

        try:
            new_value = int(new_value_str.strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Значение должно быть целым числом.")
            return

        # Обновляем каждую выделенную строку
        for item in selected_items:
            param_name = self.item_param_map.get(item)
            if not param_name:
                continue

            # Обновляем модель
            need_write = self.reg_handler.get_need_write_to_oscillogram(param_name)
            start_cond = self.reg_handler.get_start_oscillography_condition(param_name)
            self.reg_handler.update_mapping(param_name, need_write, new_value, start_cond)

            # Обновляем строку в таблице
            current_values = list(self.tree.item(item, "values"))
            current_values[3] = str(new_value)  # reg_cond — 4-й столбец (индекс 3)
            self.tree.item(item, values=current_values)

            # Обновляем цвет строки
            is_active = need_write or (new_value != 0) or (start_cond != 0)
            self.tree.item(item, tags=("active",) if is_active else ())



def create_registration_editor(
    registration_json: str,
    metadata_json: str
):
    try:
        config_handler = MainConfigHandler.from_json_file(metadata_json)
        reg_handler = RegistrationHandler.from_json_file(registration_json)
        root = tk.Tk()
        app = RegistrationEditorApp(root, reg_handler, config_handler, registration_json)
        root.mainloop()
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    # Укажите свои пути
    REGISTRATION_FILE = "Настройка регистрации.json"
    METADATA_FILE = "meta.json"

    create_registration_editor(REGISTRATION_FILE, METADATA_FILE)