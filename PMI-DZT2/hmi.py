import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

# Импорты классов
from CORE.HMIHandler import HMIHandler
from CORE.MainConfigHandler import MainConfigHandler 


class HMIGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Настройка HMI: Полный список")
        self.root.geometry("1000x1100")
        
        # --- Инициализация обработчиков ---
        self.meta_handler = None
        if os.path.exists("meta.json"):
            try:
                self.meta_handler = MainConfigHandler.from_json_file("meta.json")
            except Exception as e:
                print(f"Warning: Could not load meta.json: {e}")

        self.hmi_handler = HMIHandler(meta_handler=self.meta_handler)
        
        if os.path.exists(HMIHandler.DEFAULT_FILENAME):
            self.hmi_handler.load_from_file()

        # --- Статические списки ---
        self.led_modes_list = self.hmi_handler.get_led_modes_list()
        self.led_scenarios_list = self.hmi_handler.get_led_scenarios_list()
        self.fk_scenarios_list = self.hmi_handler.get_fk_scenarios_list()
        
        # --- Динамические списки параметров ---
        self.led_params_display_list, self.led_params_map = self._build_param_lists(filter_type="led")
        self.fb_params_display_list, self.fb_params_map = self._build_param_lists(filter_type="fb")

        # --- Словари для хранения виджетов (чтобы обновлять их значения) ---
        # Ключ: номер (1-16), Значение: dict с виджетами
        self.led_widgets = {}
        self.fk_widgets = {}

        # --- Построение интерфейса ---
        self._create_menu()
        self._create_main_layout()

    def _build_param_lists(self, filter_type: str = "all") -> tuple:
        display_list = ["<Нет привязки>"]
        mapping = {} 
        raw_names = []
        
        if self.meta_handler:
            if filter_type == "fb":
                all_names = list(self.meta_handler._params.keys())
                raw_names = [n for n in all_names if n.startswith("FB_")]
            elif filter_type == "led":
                raw_names = self.meta_handler.get_valid_led_parameters()
            else:
                raw_names = list(self.meta_handler._params.keys())
        else:
            raw_names = self.hmi_handler.get_available_parameters()
            if filter_type == "fb":
                raw_names = [n for n in raw_names if n.startswith("FB_")]

        raw_names.sort()

        for tech_name in raw_names:
            if self.meta_handler:
                desc = self.meta_handler.get_applied_description(tech_name)
            else:
                desc = tech_name
            display_list.append(desc)
            mapping[desc] = tech_name
            
        return display_list, mapping

    def _get_tech_name_by_description(self, description: str, filter_type: str) -> str:
        if description == "<Нет привязки>":
            return ""
        mapping_dict = self.fb_params_map if filter_type == "fb" else self.led_params_map
        return mapping_dict.get(description, description) 

    def _get_description_by_tech_name(self, tech_name: str, filter_type: str) -> str:
        if not tech_name:
            return "<Нет привязки>"
        mapping_dict = self.fb_params_map if filter_type == "fb" else self.led_params_map
        for desc, name in mapping_dict.items():
            if name == tech_name:
                return desc
        return tech_name

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Загрузить конфигурацию...", command=self.load_config)
        file_menu.add_command(label="Сохранить конфигурацию...", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

    def _create_main_layout(self):
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- Левая панель: Список Светодиодов ---
        led_container = ttk.LabelFrame(paned, text="Светодиоды (1-16)", padding="5")
        paned.add(led_container, weight=1)
        self._build_scrollable_led_list(led_container)

        # --- Правая панель: Список ФК ---
        fk_container = ttk.LabelFrame(paned, text="Функциональные Кнопки (1-16)", padding="5")
        paned.add(fk_container, weight=1)
        self._build_scrollable_fk_list(fk_container)

    def _build_scrollable_led_list(self, parent):
        """Создает прокручиваемый список карточек для светодиодов"""
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Генерация карточек для 16 светодиодов
        for i in range(1, 17):
            card = self._create_led_card(scrollable_frame, i)
            card.pack(fill=tk.X, padx=5, pady=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_scrollable_fk_list(self, parent):
        """Создает прокручиваемый список карточек для ФК"""
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Генерация карточек для 16 ФК
        for i in range(1, 17):
            card = self._create_fk_card(scrollable_frame, i)
            card.pack(fill=tk.X, padx=5, pady=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_led_card(self, parent, number):
        """Создает визуальную карточку настроек для одного светодиода"""
        frame = ttk.LabelFrame(parent, text=f"Светодиод {number}", padding="5")
        
        # Сетка внутри карточки
        # Row 0: Режим и Сценарий
        ttk.Label(frame, text="Цвет:").grid(row=0, column=0, sticky=tk.W)
        mode_combo = ttk.Combobox(frame, values=self.led_modes_list, width=12, state="readonly")
        mode_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        mode_combo.bind('<<ComboboxSelected>>', lambda e, n=number: self.on_led_setting_change(n))

        ttk.Label(frame, text="Сценарий:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        scen_combo = ttk.Combobox(frame, values=self.led_scenarios_list, width=15, state="readonly")
        scen_combo.grid(row=0, column=3, padx=5, sticky=tk.W)
        scen_combo.bind('<<ComboboxSelected>>', lambda e, n=number: self.on_led_setting_change(n))

        # Row 1: Параметр
        ttk.Label(frame, text="Параметр:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        param_combo = ttk.Combobox(frame, values=self.led_params_display_list, width=30, state="readonly")
        param_combo.grid(row=1, column=1, columnspan=3, padx=5, sticky=tk.EW, pady=(5,0))
        param_combo.bind('<<ComboboxSelected>>', lambda e, n=number: self.on_led_param_change(n))

        # Info Label
        info_label = ttk.Label(frame, text="", foreground="gray", font=("Segoe UI", 8))
        info_label.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(2,0))

        frame.columnconfigure(3, weight=1) # Растягиваем комбобокс параметра

        # Сохраняем ссылки на виджеты для обновления при загрузке
        self.led_widgets[number] = {
            "mode": mode_combo,
            "scenario": scen_combo,
            "param": param_combo,
            "info": info_label
        }
        
        return frame

    def _create_fk_card(self, parent, number):
        """Создает визуальную карточку настроек для одной ФК"""
        frame = ttk.LabelFrame(parent, text=f"ФК {number}", padding="5")
        
        # Row 0: Сценарий
        ttk.Label(frame, text="Действие:").grid(row=0, column=0, sticky=tk.W)
        scen_combo = ttk.Combobox(frame, values=self.fk_scenarios_list, width=20, state="readonly")
        scen_combo.grid(row=0, column=1, padx=5, sticky=tk.W)
        scen_combo.bind('<<ComboboxSelected>>', lambda e, n=number: self.on_fk_setting_change(n))

        # Row 1: Параметр
        ttk.Label(frame, text="Параметр (ФБ):").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        param_combo = ttk.Combobox(frame, values=self.fb_params_display_list, width=30, state="readonly")
        param_combo.grid(row=1, column=1, columnspan=3, padx=5, sticky=tk.EW, pady=(5,0))
        param_combo.bind('<<ComboboxSelected>>', lambda e, n=number: self.on_fk_param_change(n))

        # Info Label
        info_label = ttk.Label(frame, text="", foreground="gray", font=("Segoe UI", 8))
        info_label.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(2,0))

        frame.columnconfigure(3, weight=1)

        self.fk_widgets[number] = {
            "scenario": scen_combo,
            "param": param_combo,
            "info": info_label
        }
        
        return frame

    # --- Обработчики событий LED ---

    def on_led_setting_change(self, number):
        """Вызывается при изменении режима или сценария"""
        widgets = self.led_widgets[number]
        mode = widgets["mode"].get()
        scenario = widgets["scenario"].get()
        
        self.hmi_handler.update_led_settings(number, scenario, mode)

    def on_led_param_change(self, number):
        """Вызывается при изменении привязанного параметра"""
        widgets = self.led_widgets[number]
        display_name = widgets["param"].get()
        
        tech_name = self._get_tech_name_by_description(display_name, filter_type="led")
            
        success = self.hmi_handler.link_parameter_to_led(number, tech_name)
        if success:
            self._update_led_info(number, tech_name)
        else:
            # Откат UI если ошибка
            self.refresh_led_ui(number)
            messagebox.showwarning("Ошибка", f"Не удалось привязать параметр к LED {number}")

    def _update_led_info(self, number, tech_name):
        if self.meta_handler and tech_name:
            desc = self.meta_handler.get_applied_description(tech_name)
            group = self.meta_handler.get_group(tech_name)
            text = f"{desc}"
            if group: text += f" ({group})"
            self.led_widgets[number]["info"].config(text=text)
        else:
            self.led_widgets[number]["info"].config(text="")

    def refresh_led_ui(self, number):
        """Обновляет UI конкретного светодиода из данных HMIHandler"""
        config = self.hmi_handler.get_led_config(number)
        if config and number in self.led_widgets:
            w = self.led_widgets[number]
            w["mode"].set(config.mode_name)
            w["scenario"].set(config.scenario_name)
            
            desc = self._get_description_by_tech_name(config.linked_parameter, filter_type="led")
            w["param"].set(desc)
            
            self._update_led_info(number, config.linked_parameter)

    # --- Обработчики событий FK ---

    def on_fk_setting_change(self, number):
        widgets = self.fk_widgets[number]
        scenario = widgets["scenario"].get()
        self.hmi_handler.update_fk_settings(number, scenario)

    def on_fk_param_change(self, number):
        widgets = self.fk_widgets[number]
        display_name = widgets["param"].get()
        
        tech_name = self._get_tech_name_by_description(display_name, filter_type="fb")
            
        success = self.hmi_handler.link_parameter_to_fk(number, tech_name)
        if success:
            self._update_fk_info(number, tech_name)
        else:
            self.refresh_fk_ui(number)
            messagebox.showwarning("Ошибка", f"Не удалось привязать параметр к ФК {number}")

    def _update_fk_info(self, number, tech_name):
        if self.meta_handler and tech_name:
            desc = self.meta_handler.get_applied_description(tech_name)
            self.fk_widgets[number]["info"].config(text=f"{desc}")
        else:
            self.fk_widgets[number]["info"].config(text="")

    def refresh_fk_ui(self, number):
        config = self.hmi_handler.get_fk_config(number)
        if config and number in self.fk_widgets:
            w = self.fk_widgets[number]
            w["scenario"].set(config.scenario_name)
            
            desc = self._get_description_by_tech_name(config.linked_parameter, filter_type="fb")
            w["param"].set(desc)
            
            self._update_fk_info(number, config.linked_parameter)

    # --- Глобальное обновление UI (при загрузке файла) ---
    
    def refresh_all_ui(self):
        for i in range(1, 17):
            self.refresh_led_ui(i)
            self.refresh_fk_ui(i)

    # --- Файловые операции ---

    def load_config(self):
        filepath = filedialog.askopenfilename(
            title="Загрузка конфигурации HMI",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            if self.hmi_handler.load_from_file(filepath):
                self.refresh_all_ui()
                messagebox.showinfo("Успех", "Конфигурация загружена")
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить файл")

    def save_config(self):
        filepath = filedialog.asksaveasfilename(
            title="Сохранение конфигурации HMI",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=HMIHandler.DEFAULT_FILENAME
        )
        if filepath:
            if self.hmi_handler.save_to_file(filepath):
                messagebox.showinfo("Успех", "Конфигурация сохранена")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить файл")

if __name__ == "__main__":
    root = tk.Tk()
    default_font = ("Segoe UI", 9)
    root.option_add("*Font", default_font)
    
    app = HMIGUIApp(root)
    # Принудительное обновление UI после запуска, чтобы отобразить загруженные данные
    app.refresh_all_ui()
    root.mainloop()