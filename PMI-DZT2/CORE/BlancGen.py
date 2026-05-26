from CORE.OrderHandler import OrderHandler
from CORE.XLSXHandler import XLSXHandler
import json
import copy
import re


class BlancGen:

    def __init__(self, folder_to_modes, modes_prefix):
        # I часть. Создаем объект РЕЖИМОВ
        self.handler = XLSXHandler()
        all_data = self.handler.load_all_modes_from_folder(folder_to_modes)
        #modes = self.handler.get_device_modes("./.")
        optimized = self.handler.optimize_modes(all_data[modes_prefix]) 

        # II часть. Создаем объект GROUPING и собираем БАЗОВУЮ структуру (шаблон)
        self.order_handler = OrderHandler()
        self.maps = self.order_handler.get_mapping() # Исправлено: self.order_handler
        
        ordered_fbs = list(self.maps.keys())

        base_structure = []
        # Итерируемся в правильном порядке
        for fb in ordered_fbs:
            fb_map = self.maps.get(fb) # Исправлено: self.maps
            if not fb_map:
                continue
                
            json_data = self.order_handler.get_data_by_fb_name(fb_map) # Исправлено: self.order_handler
            parsed_blocks = self.order_handler.parse_rza_structure(json_data, all_struct=0) # Исправлено: self.order_handler
            
            base_structure.extend(parsed_blocks)

        # Сохраняем базовую структуру как атрибут класса, чтобы она была доступна другим методам
        self.base_structure = base_structure

        # --- III часть. Логика заполнения и сохранения ---
        # Проходим по всем режимам и формируем итоговый словарь
        self.final_output = {}

        for mode_id, params in optimized.items():
            if not params:
                continue 
            
            # Генерируем структуру конкретно для этого режима
            mode_specific_data = self.filter_and_fill_structure(self.base_structure, params)
            self.final_output[mode_id] = mode_specific_data

    def get_optimized_value(self, col0_name, mode_params):
        """
        Ищет значение уставки. 
        Если col0 = 'Name_SG1', а в params есть 'Name', вернет значение 'Name'.
        """
        if col0_name in mode_params:
            return mode_params[col0_name]
        
        # Убираем суффикс группы сигналов (_SG1, _SG2...) для поиска в optimized
        clean_name = re.sub(r'_SG\d+$', '', col0_name)
        if clean_name in mode_params:
            return mode_params[clean_name]
            
        return None

    def filter_and_fill_structure(self, base_struct, current_mode_params):
        """
        Возвращает новую структуру, где:
        1. col7 заполнен значением из режима.
        2. Оставлены ТОЛЬКО строки, присутствующие в режиме.
        3. Порядок блоков сохраняется таким же, как в base_struct.
        """
        result_structure = []
        
        for block in base_struct:
            new_block = copy.deepcopy(block)
            has_data = False
            
            if new_block['type'] == 'simple':
                filtered_rows = []
                for row in new_block['rows']:
                    val = self.get_optimized_value(row['col0'], current_mode_params)
                    if val is not None:
                        row['col7'] = str(val)
                        filtered_rows.append(row)
                        has_data = True
                new_block['rows'] = filtered_rows
                
            elif new_block['type'] == 'complex':
                filtered_subs = []
                for sub in new_block['sub_functions']:
                    filtered_rows = []
                    for row in sub['rows']:
                        val = self.get_optimized_value(row['col0'], current_mode_params)
                        if val is not None:
                            row['col7'] = str(val)
                            filtered_rows.append(row)
                            has_data = True
                    sub['rows'] = filtered_rows
                    if filtered_rows:
                        filtered_subs.append(sub)
                new_block['sub_functions'] = filtered_subs
                
            if has_data:
                result_structure.append(new_block)
                
        return result_structure

    def save_to_json(self, filename="optimized_modes_result.json"):
        """Сохраняет результат в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.final_output, f, ensure_ascii=False, indent=2)
        print(f"Результат сохранен в файл: {filename}")
        print(f"Обработано режимов: {len(self.final_output)}")

