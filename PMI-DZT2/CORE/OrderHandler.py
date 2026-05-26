# класс обвертка вокруг файла порядка следования для ИЧМ, файл находится в данных ЮнитСервис
# и называется как func_order.json, GROUPING.json - в ЮНИТ СЕРВИС РЗА пакет поддержки

# В РАЗРАБОТКЕ

import json
from typing import List, Dict, Any

from CORE.MainConfigHandler import MainConfigHandler

class OrderHandler:

    def __init__(self):
        with open("func_order.json", 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.settings_group1 = None
        self._extrude_settings_group1()

        self.config_handler = MainConfigHandler.from_json_file("meta.json")
        self.mapping = {}
        self._create_mapping_from_structure()

    def _extrude_settings_group1(self):
        """Извлекает структуру 'Группа уставок 1' из JSON"""
        for root_node in self.data:
            if root_node.get("Name") == "SettingsTree":
                setting_tree = root_node
                break
        
        for nodes in setting_tree.get("Nodes", []):
            if nodes.get("Name") == "Группа уставок 1":
                settings = nodes
                break
        
        self.settings_group1 = settings.get("Nodes", []) if settings else []

    
    def get_settings_by_fb_name(self, fb_name):
        result = []
        for setting in self.settings_group1:
            if setting["Name"] == fb_name:
                settings = setting["Nodes"]
                for setting in settings:
                    result.append(setting["Name"])
        return result

    def get_data_by_fb_name(self, fb_name):
        for settings in self.settings_group1:
            if settings["Name"]!=fb_name:
                continue
            else:
                return settings
            
    def parse_options(self, options_str):
        """Парсит строку вида '0 - Вывод, 1 - По ЭМО1, ЭМО2' в словарь"""
        import re
        result = {}
        
        # Ищем все вхождения "цифра - значение" (значение может содержать запятые)
        # ?: - несохраняющая группа
        # \s*\d+\s*-\s* - цифра, тире с пробелами
        # (.*?) - значение (любые символы) лениво до...
        # (?=\s*\d+\s*-|$) - ...следующей цифры с тире или конца строки
        pattern = r'(\d+)\s*-\s*(.*?)(?=\s*\d+\s*-|$)'
        
        for match in re.finditer(pattern, options_str):
            key = match.group(1)
            value = match.group(2).strip().rstrip(',')
            result[key] = value
        
        return result


    def prepare_data_for_table(self, fb_name):
        raw = self.config_handler.get_param_info(fb_name)

        s = raw["description"]
        desc = "_".join(s.split("_", 1)[1:])
        col1 = raw["fullDescription"] + " (" + desc + ") "
        col2 = raw["appliedDescription"]
        col0 = fb_name
        
        op_dict = {}
        is_sgf = False
        # Форматирование col3
        if raw["note"] == '':
            # Форматируем min и max с учётом шага
            if raw["step"] and raw["step"] != '':
                step = float(raw["step"])
                # Определяем количество знаков после запятой
                step_str = str(step).rstrip('0').rstrip('.')
                decimals = len(step_str.split('.')[1]) if '.' in step_str else 0
                
                min_val = float(raw["minValue"])
                max_val = float(raw["maxValue"])
                min_formatted = f"{min_val:.{decimals}f}".replace('.', ',')
                max_formatted = f"{max_val:.{decimals}f}".replace('.', ',')
                col3 = f"{min_formatted}...{max_formatted}"
            else:
                # Шага нет - выводим как есть
                col3 = f"{raw['minValue']}...{raw['maxValue']}"
        else:
            col3 = raw["note"]
            op_dict = self.parse_options(col3)

            col3 ="note_"+str(op_dict)
            is_sgf = True

        
        col4 = "-" if raw["units"] == '' else raw["units"]
        
        # col5 - сохраняем старую логику: "-" если note не пустой, иначе step
        if raw["note"] != '':
            col5 = "-"
        else:
            if raw["step"] and raw["step"] != '':
                step = float(raw["step"])
                step_str = str(step).rstrip('0').rstrip('.')
                decimals = len(step_str.split('.')[1]) if '.' in step_str else 0
                col5 = f"{step:.{decimals}f}".replace('.', ',')
            else:
                col5 = "-"
        
        # col6 - форматируем defaultValue
        col6 = "-"
        if raw["defaultValue"] and raw["defaultValue"] != '':
            if is_sgf:
                # SGF параметр - заменяем код на текстовое описание
                col6 = op_dict.get(raw["defaultValue"], raw["defaultValue"])
            elif raw["step"] and raw["step"] != '':
                # Обычный параметр с шагом
                step = float(raw["step"])
                step_str = str(step).rstrip('0').rstrip('.')
                decimals = len(step_str.split('.')[1]) if '.' in step_str else 0
                default_val = float(raw["defaultValue"])
                col6 = f"{default_val:.{decimals}f}".replace('.', ',')
            else:
                # Обычный параметр без шага
                col6 = raw["defaultValue"]
        
        col7=''
        return col0, col1, col2, col3, col4, col5, col6, col7

    def parse_rza_structure(self, data: List[Dict[str, Any]], all_struct: bool = True) -> List[Dict[str, Any]]:
        """
        Преобразует структуру JSON РЗА в список блоков для шаблона Jinja2.
        Каждая уставка (параметр) становится отдельной строкой таблицы.
        all_struct = True если нужно прогнать весь файл с уставками, если отдельный ФБ - то all_struct=False, потом переделать автоматически определение структуры
        """
        
        def is_simple_group(node: Dict) -> bool:
            """
            Группа простая, если не содержит дочерних групп (только параметры).
            """
            if 'Nodes' not in node or not node['Nodes']:
                return True
            
            for child in node['Nodes']:
                if child.get('Type') == 'Group':
                    return False
            return True

        def create_row(param_name: str) -> Dict[str, str]:
            """
            Создает словарь для одной строки таблицы.
            col1 - Имя параметра (для поиска в БД)
            col2-col4 - заглушки для будущих данных (Значение, Ед.изм, Описание)
            """

            col0, col1, col2, col3, col4, col5, col6, col7 = self.prepare_data_for_table(param_name)

            return {
                "col0": col0, # обозначение ключа
                "col1": col1, 
                "col2": col2,  # Место для значения из БД
                "col3": col3,  # Место для ед. измерения
                "col4": col4,   # Место для описания
                "col5": col5,   # Место для описания
                "col6": col6,   # Место для значения по умолчанию
                "col7": col7  # Место для выставленного значения - для режимов
            }

        def process_group(node: Dict) -> List[Dict]:
            """
            Рекурсивная обработка. Возвращает список блоков.
            """
            result_blocks = []
            
            # --- ДОБАВЛЕННАЯ ПРОВЕРКА ---
            # Если имя самой группы (функции) начинается с "GOOSE", 
            # мы просто возвращаем пустой список, игнорируя всё внутри.
            if node.get('Name', '').startswith("GOOSE") or node.get('Name', '').startswith("ВКл:"):
                return [] 

            if is_simple_group(node):
                # --- ПРОСТАЯ ФУНКЦИЯ ---
                # Собираем все параметры в список строк
                rows = []
                if 'Nodes' in node:
                    for child in node['Nodes']:
                        if child.get('Type') == 'Parameter':
                            rows.append(create_row(child.get('Name', '')))
                
                result_blocks.append({
                    "type": "simple",
                    "func_name": node.get('Name', ''),
                    "rows": rows
                })
                
            else:
                # --- СЛОЖНАЯ ФУНКЦИЯ ---
                # Сама группа является контейнером для подфункций
                complex_block = {
                    "type": "complex",
                    "func_name": node.get('Name', ''),
                    "sub_functions": []
                }
                
                for child in node.get('Nodes', []):
                    if child.get('Type') == 'Group':
                        # Обрабатываем подгруппу
                        sub_rows = []
                        if 'Nodes' in child:
                            for param_node in child['Nodes']:
                                if param_node.get('Type') == 'Parameter':
                                    sub_rows.append(create_row(param_node.get('Name', '')))
                        
                        complex_block["sub_functions"].append({
                            "subtitle": child.get('Name', ''),
                            "rows": sub_rows
                        })
                    
                result_blocks.append(complex_block)
                
            return result_blocks

        # --- Основная точка входа ---
        final_output = []
        
        if not data:
            return final_output

        if all_struct:

            # 1. Находим корень SettingsTree
            settings_tree = data[0] 
            
            # 2. Находим первую группу уставок (например, "Группа уставок 1")
            top_nodes = settings_tree.get('Nodes', [])
            if not top_nodes:
                return final_output
                
            first_settings_group = top_nodes[0]
            # Перебираем функциональные группы
            functional_groups = first_settings_group.get('Nodes', [])
            for func_group in functional_groups:
                if func_group.get('Type') == 'Group':
                    blocks = process_group(func_group)
                    final_output.extend(blocks)
        
        else:
            # Режим: data - это уже группа уставок или отдельный блок
            if isinstance(data, list):
                for item in data:
                    if item.get('Type') == 'Group':
                        blocks = process_group(item)
                        final_output.extend(blocks)
            elif isinstance(data, dict) and data.get('Type') == 'Group':
                # Если передан один блок
                blocks = process_group(data)
                final_output.extend(blocks)
                    
        return final_output
    
    def _create_mapping_from_structure(self) -> Dict[str, str]:
        """Создаёт mapping префикс -> имя верхней группы (рекурсивно)"""
        
        mapping = {}
        
        def process_nodes(nodes, root_group_name):
            """Рекурсивно обходит узлы, сохраняя имя корневой группы"""
            if not nodes:
                return
                
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                    
                node_type = node.get('Type')
                
                # Если это Группа - спускаемся внутрь неё рекурсивно
                if node_type == 'Group':
                    # Важно: мы передаем то же самое root_group_name, 
                    # чтобы параметры внутри получили имя верхней группы (например, "ЛО Т_1")
                    process_nodes(node.get('Nodes', []), root_group_name)
                    
                # Если это Параметр
                elif node_type == 'Parameter':
                    param_name = node.get('Name', '')
                    if '_1_' not in param_name:
                        continue
                        
                    prefix = param_name.split('_1_')[0]
                    
                    # Пропускаем служебные
                    if prefix == "Номинальный ток входа":
                        continue
                    
                    # Добавляем в маппинг, если такого префикса еще нет
                    if prefix not in mapping:
                        mapping[prefix] = root_group_name

        # Основной цикл по верхнему уровню
        for group in self.settings_group1:
            if not isinstance(group, dict) or group.get('Type') != 'Group':
                continue
                
            group_name = group.get('Name', '')
            
            # Пропускаем служебные верхние группы
            if group_name.startswith("GOOSE") or group_name.startswith("ВКл:"):
                continue
            
            # Запускаем рекурсию для узлов этой группы
            process_nodes(group.get('Nodes', []), group_name)

        self.mapping = mapping
        return mapping


    def get_setting_group1(self):
        return self.settings_group1
    def get_mapping(self):
        return self.mapping
        
