# Класс обвертка для файлов режимов xlsx
from typing import Dict, Any, List
import os
import pandas as pd
import math
from pathlib import Path

class XLSXHandler:

    def __init__(self):
        pass

    def create_combined_dict_from_xlsx(self, file_path: str) -> Dict[str, Any]:
        """
        Читает xlsx файл с листами SGF_Parameters и Settings,
        создаёт объединённый словарь ключ -> значение.
        
        Args:
            file_path: путь к xlsx файлу
        
        Returns:
            словарь вида {"ключ1": значение1, "ключ2": значение2, ...}
        """
        combined_dict = {}
        
        try:
            # Читаем лист SGF_Parameters
            df_sgf = pd.read_excel(file_path, sheet_name='SGF_Parameters', header=None)
            
            # Первая строка - заголовки (ключи), вторая - значения
            if len(df_sgf) >= 2:
                keys_sgf = df_sgf.iloc[0].astype(str).tolist()  # первая строка - ключи
                values_sgf = df_sgf.iloc[1].tolist()            # вторая строка - значения
                
                for key, value in zip(keys_sgf, values_sgf):
                    if pd.notna(key) and key != 'nan':
                        combined_dict[str(key)] = value if pd.notna(value) else None
            
            # Читаем лист Settings
            df_settings = pd.read_excel(file_path, sheet_name='Settings', header=None)
            
            # Первая строка - заголовки (ключи), вторая - значения
            if len(df_settings) >= 2:
                keys_settings = df_settings.iloc[0].astype(str).tolist()  # первая строка - ключи
                values_settings = df_settings.iloc[1].tolist()            # вторая строка - значения
                
                for key, value in zip(keys_settings, values_settings):
                    if pd.notna(key) and key != 'nan':
                        combined_dict[str(key)] = value if pd.notna(value) else None
                        
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")
            return {}
        
        return combined_dict

    def load_all_modes_from_folder(self, folder_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Загружает все xlsx файлы из папки и создаёт словарь словарей.
        Имя файла должно быть в формате "ИмяУстройства_Режим.xlsx"
        Например: "КЦН1_1.xlsx", "КЦН1_2.xlsx", "КЦН2_1.xlsx"
        
        Args:
            folder_path: путь к папке с xlsx файлами
        
        Returns:
            словарь вида {
                "КЦН1": {
                    "1": {данные из файла КЦН1_1.xlsx},
                    "2": {данные из файла КЦН1_2.xlsx}
                },
                "КЦН2": {
                    "1": {данные из файла КЦН2_1.xlsx}
                }
            }
        """
        result = {}
        
        # Проверяем существование папки
        if not os.path.exists(folder_path):
            print(f"Папка не найдена: {folder_path}")
            return result
        
        # Получаем все xlsx файлы в папке
        xlsx_files = list(Path(folder_path).glob("*.xlsx"))
        
        if not xlsx_files:
            print(f"В папке {folder_path} не найдено xlsx файлов")
            return result
        
        for file_path in xlsx_files:
            filename = file_path.stem  # Получаем имя файла без расширения
            
            # Разделяем имя и режим (по последнему подчёркиванию)
            if '_' in filename:
                parts = filename.rsplit('_', 1)
                device_name = parts[0]
                mode = parts[1]
            else:
                # Если нет подчёркивания, считаем что это режим "default"
                #continue
                device_name = filename
                mode = "default"
            
            # Читаем данные из файла
            file_data = self.create_combined_dict_from_xlsx(str(file_path))
            
            # Добавляем в структуру
            if device_name not in result:
                result[device_name] = {}
            
            result[device_name][mode] = file_data
        
        return result

    def get_device_modes(self, folder_path: str) -> Dict[str, Any]:
        """
        Возвращает все режимы для конкретного устройства.
        
        Args:
            folder_path: путь к папке с xlsx файлами
            device_name: имя устройства (например "КЦН1")
        
        Returns:
            словарь вида {"1": {...}, "2": {...}}
        """
        all_data = self.load_all_modes_from_folder(folder_path)
        return all_data #.get(device_name, {})

    def _normalize_value(self, val):
        """
        Приводит значение к виду, удобному для сравнения.
        Обрабатывает NaN, None и приводит строки к единому виду.
        """
        if val is None:
            return None
        # Проверка на NaN (для float и объектов pandas)
        if isinstance(val, float) and math.isnan(val):
            return None
        if pd.isna(val):
            return None
        
        # Если это строка, убираем лишние пробелы
        if isinstance(val, str):
            return val.strip()
        
        return val

    def optimize_modes(self, modes_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Оптимизирует хранение режимов, оставляя только отличающиеся значения 
        относительно ПРЕДЫДУЩЕГО режима (логика как во втором коде).
        
        Первый режим сохраняется полностью.
        Для каждого последующего режима вычисляются отличия от предыдущего.
        
        Args:
            modes_data: словарь вида {"1": {...}, "2": {...}, "3": {...}}
            
        Returns:
            оптимизированный словарь дифференциальных изменений:
            {
                "1": {...},  # полные данные первого режима
                "2": {"параметр": "новое_значение"}, # только то, что изменилось по сравнению с 1
                "3": {}      # если нет отличий от 2
            }
        """
        if not modes_data:
            return {}
        
        result = {}
        
        # 1. Сортируем ключи для определения порядка режимов
        try:
            modes_list = sorted(modes_data.keys(), key=lambda x: int(x) if str(x).isdigit() else x)
        except Exception:
            modes_list = sorted(modes_data.keys())
        
        if not modes_list:
            return {}

        # Переменная для хранения "полных" данных предыдущего режима
        # Это необходимо, так как в result хранятся только отличия, 
        # а сравнивать нужно полные конфигурации.
        prev_full_data = None

        for i, mode_key in enumerate(modes_list):
            current_raw_data = modes_data[mode_key]
            
            if i == 0:
                # --- ПЕРВЫЙ РЕЖИМ ---
                # Сохраняем полностью, предварительно нормализуя значения
                full_data = {k: self._normalize_value(v) for k, v in current_raw_data.items()}
                result[mode_key] = full_data
                prev_full_data = full_data.copy()
            else:
                # --- ПОСЛЕДУЮЩИЕ РЕЖИМЫ ---
                # Сравниваем с предыдущим полным набором данных (prev_full_data)
                
                # Нормализуем текущие входные данные
                current_normalized = {k: self._normalize_value(v) for k, v in current_raw_data.items()}
                
                diff_data = {}
                
                # Объединяем ключи из текущего и предыдущего, чтобы отловить удаления параметров
                all_keys = set(prev_full_data.keys()) | set(current_normalized.keys())
                
                for key in all_keys:
                    prev_val = prev_full_data.get(key)
                    curr_val = current_normalized.get(key)
                    
                    # Если значения отличаются (с учетом нормализации None/NaN)
                    if prev_val != curr_val:
                        diff_data[key] = curr_val
                
                # Сохраняем только отличия
                result[mode_key] = diff_data
                
                # ВАЖНО: Обновляем prev_full_data для следующей итерации.
                # Мы берем предыдущие полные данные и накладываем на них текущие отличия.
                # Это позволяет следующему режиму сравниваться с актуальным состоянием системы.
                new_full_data = prev_full_data.copy()
                new_full_data.update(diff_data)
                
                # Удаляем ключи, которые стали None (если параметр исчез или сбросился), 
                # если это требуется вашей логикой. Если исчезновение параметра значит 
                # "вернуться к дефолту", то лучше оставить как есть или обрабатывать отдельно.
                # В данном случае просто обновляем значения:
                prev_full_data = new_full_data

        return result
    