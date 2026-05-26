from CORE.MainConfigHandler import MainConfigHandler
from CORE.InOutsMatrixHandler import InOutsMatrixHandler   
import pandas as pd
from CORE.sql_handler import SQL_handler
import json
from collections import defaultdict
from typing import List, Dict, Any, Optional

from pathlib import Path
import re
from natsort import natsorted, natsort_key

class PMI:
    def __init__(self, db_handler: SQL_handler, db_cursor, root_path: str, xlsx_path: str):
        """
        Args:
            db_handler: экземпляр SQL_handler (нужен для методов get_block_description и т.д.)
            db_cursor: курсор для прямых SQL запросов (если нужен)
        """
        self.root_path = root_path
        #meta = root_path + "meta.json"
        meta = "meta.json"
        self.config_handler = MainConfigHandler.from_json_file(meta)

        #self.inouts_handler = InOutsMatrixHandler.from_json_file(matrix)

        self.path_to_modes_xlsx = xlsx_path #root_path+"pmi_ka/"
        self._fbs_set = set()
        self._current_df = None
        self.description_dict = self._load_description_dict()
        
        # Сохраняем оба объекта
        self.db = db_handler  # Сохраняем сам обработчик БД
        self.cursor = db_cursor  # Сохраняем курсор (на случай, если нужен для прямых запросов)
        
        self.fbs_list_sorted = []

    def _load_description_dict(self, json_file: str = 'CORE/description.json') -> Dict[str, str]:
        """Загружает словарь описаний из JSON файла"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки описаний: {e}")
            return {}

    def _get_current_setting_from_xlsx_mode(self, short_name: str, full_name: str) -> str:
        """Получает текущее значение настройки из Excel файла режима"""
        if self._current_df is None:
            return ""
        
        mode = "1"
        suffix = '_' + short_name
        
        if full_name.endswith(suffix):
            block_prefix = full_name[:-len(suffix)]
        else:
            block_prefix = full_name
        
        searched_name = f"{block_prefix}_{mode}_{short_name}"
        
        try:
            if searched_name in self._current_df.columns:
                # Данные в первой строке (индекс 0)
                return str(self._current_df.iloc[0][searched_name]), searched_name
            return "", searched_name
        except Exception as e:
            print(f"Ошибка получения значения для {searched_name}: {e}")
            return "", searched_name

    def _group_and_enrich_data(self, data_list: List[Dict]) -> Dict[str, Dict]:
        """
        Группирует данные по NodeNameRu и выносит FullNodeNameRu на уровень группы.
        """
        grouped_data = {}
        
        # Сортируем исходные данные по ExcelRowIndex
        sorted_data = sorted(data_list, key=lambda x: x.get('ExcelRowIndex', 0))
        
        for item in sorted_data:
            node_key = item.get('NodeNameRu')
            if not node_key:
                continue
            
            # Если группа ещё не создана, инициализируем её
            if node_key not in grouped_data:
                grouped_data[node_key] = {
                    'NodeNameRu': node_key,
                    'FullNodeNameRu': self.description_dict.get(node_key, node_key),  # Полное имя для заголовка
                    'parameters': []  # Список параметров без дублирования FullNodeNameRu
                }
            
            # Создаем копию элемента БЕЗ поля FullNodeNameRu
            new_item = item.copy()
            
            # Добавляем параметр в список группы
            grouped_data[node_key]['parameters'].append(new_item)
            
        return grouped_data

    def _get_fbs_list(self):
        """Получает список ФБ из примера Excel файла"""
        example_name = "example.xlsx"
        settings_list, self._current_df = self.get_xlsx_data(example_name)
        for setting in settings_list:
            if '_1_' in setting:
                b = setting.split('_1_')
                self._fbs_set.add(b[0])

    def collect_mode_settings(self, mode_file: str = "example.xlsx") -> Dict:
        """
        Собирает настройки режима и формирует структуру для отчета
        
        Args:
            mode_file: имя файла режима в папке core/modes/
            
        Returns:
            Словарь с полной структурой настроек по блокам и функциям
        """
        # Получаем список ФБ и загружаем данные из Excel
        settings_list, self._current_df = self.get_xlsx_data(mode_file)
        self._fbs_set.clear()
        
        for setting in settings_list:
            if '_1_' in setting:
                b = setting.split('_1_')
                self._fbs_set.add(b[0])

        # Собираем список ФБ с информацией из БД
        fbs_list = []
        for fb in self._fbs_set:
            # ИСПРАВЛЕНО: используем self.db (экземпляр SQL_handler), а не self.cursor
            block_desc = self.db.get_block_description(fb)
            if block_desc:
                # Преобразуем sqlite3.Row в словарь для удобства
                block_desc_dict = dict(block_desc)
                fbs_list.append({
                    'BlockName': block_desc_dict['BlockName'],
                    'RussianName': block_desc_dict['RussianName'],
                    'FullRusName': self.description_dict.get(block_desc_dict['RussianName'], block_desc_dict['RussianName']),
                    'WeightCoefficient': block_desc_dict['WeightCoefficient']
                })

        self.fbs_list_sorted = sorted(fbs_list, key=lambda x: x['WeightCoefficient'])
        #(f"Найдено ФБ: {len(self.fbs_list_sorted)}")

        if not self.fbs_list_sorted:
            print("Список ФБ пуст")
            return {}

        # Словарь для хранения итоговой структуры: { BlockName: { ... } }
        final_report_structure = {}

        for fb in self.fbs_list_sorted:
            block_name = fb["BlockName"]
            block_full_rus = fb["FullRusName"]
            
            #print(f"Обработка блока: {block_name} ({block_full_rus})")
            
            # ИСПРАВЛЕНО: используем self.db (экземпляр SQL_handler)
            rows = self.db.get_all_settings(block_name)
            block_settings_list = []
            
            for row in rows:
                # Преобразуем sqlite3.Row в словарь
                row_dict = dict(row)
                curr_set, full_sett = self._get_current_setting_from_xlsx_mode(row_dict['Name'], row_dict['FullName'])
                block_settings_list.append({
                    'ShortIECName': row_dict['Name'],
                    'FullIECName': row_dict['FullName'],
                    'GebType': row_dict['GebType'],
                    'NativeType': row_dict['NativeType'],
                    'NodeNameRu': row_dict['NodeNameRu'],
                    'Description': row_dict['Description'],
                    'FullDescription': row_dict['FullDescription'],
                    'AppliedDescription': row_dict['AppliedDescription'],
                    'Units': row_dict['Units'],
                    'Min': row_dict['Min'],
                    'Max': row_dict['Max'],
                    'Step': row_dict['Step'],
                    'DefaultValue': row_dict['DefaultValue'],
                    'Note': row_dict['Note'],
                    'CurrentSetting': curr_set,
                    'ExcelRowIndex': row_dict['ExcelRowIndex'],
                    'Color':'0',
                    'SpecificSettingName': full_sett
                })
            
            # Группируем настройки текущего блока по функциям (NodeNameRu)
            grouped_functions = self._group_and_enrich_data(block_settings_list)
            
            # Добавляем блок в общую структуру
            final_report_structure[block_name] = {
                "BlockName": block_name,
                "BlockFullRusName": block_full_rus,
                "functions": grouped_functions
            }

        return final_report_structure

    def save_report_to_json(self, report_data: Dict, filename: str = 'report_structure.json'):
        """Сохраняет структуру отчета в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"Отчет сохранен в {filename}")

    def generate_report(self, mode_file: str = "example.xlsx") -> Dict:
        """
        Основной метод для генерации отчета
        
        Returns:
            Словарь со структурой отчета
        """
        report_data = self.collect_mode_settings(mode_file)
        #self.save_report_to_json(report_data)
        return report_data

    def get_matrix(self, matrix):
        """ method to prepare matrix of inputs and outputs for PMI from json files """

        inouts_handler = InOutsMatrixHandler.from_json_file(matrix)
        matrix_param_list = inouts_handler.get_all_parameter_names()

        matrix_data = {
            "parameters": {},
            "discrete_inputs": {},
            "output_relays": {},  
        }

        for param in matrix_param_list:
            discrete_inputs = inouts_handler.get_discrete_inputs(param)
            output_relays = inouts_handler.get_output_relays(param)
            if discrete_inputs or output_relays:
                matrix_data["parameters"][param] = self.config_handler.get_param_info(param)
                matrix_data["discrete_inputs"][param] = discrete_inputs
                matrix_data["output_relays"][param] = output_relays

        # Пересобираем данные из matrix_data в объект для заполнения таблица вида (вход, параметр, выход)
        inputs_matrix = []
        outputs_matrix = []

        for param, inputs in matrix_data["discrete_inputs"].items():
            if inputs:
                param_info = matrix_data["parameters"].get(param, {})
                appliedDescription = param_info.get('appliedDescription', 'Нет описания')
                inputs_matrix.append((inputs[0], appliedDescription, '-'))

        for param, outputs in matrix_data["output_relays"].items():
            if outputs:
                param_info = matrix_data["parameters"].get(param, {})
                appliedDescription = param_info.get('appliedDescription', 'Нет описания')
                outputs_matrix.append(('-', appliedDescription, outputs[0]))

        inputs_sorted = natsorted(inputs_matrix, key=lambda x: x[0])
        outputs_sorted = natsorted(outputs_matrix, key=lambda x: x[2])

        table_matrix = inputs_sorted + outputs_sorted

        return table_matrix

    def get_xlsx_data(self, file_path):
        """Читает данные из Excel файла режима
        
        Args:
            file_path: полный путь к файлу ИЛИ имя файла (str или Path)
                    Если передано имя файла, будет использован self.path_to_modes_xlsx
        """
        
        path_obj = Path(file_path)
        
        # Если передано только имя файла (без пути), добавляем базовую директорию
        if not path_obj.is_absolute() and len(path_obj.parts) == 1:
            # Это просто имя файла, добавляем путь к папке modes
            path_to_example = Path(self.path_to_modes_xlsx) / path_obj
        else:
            # Это полный или относительный путь, используем как есть
            path_to_example = path_obj
        
        if not path_to_example.exists():
            raise FileNotFoundError(f"Файл не найден: {path_to_example}")
        
        df_settings = pd.read_excel(path_to_example, sheet_name='Settings', header=None)
        df_sgf = pd.read_excel(path_to_example, sheet_name='SGF_Parameters', header=None)
        
        # Назначаем заголовки из первой строки
        df_settings.columns = df_settings.iloc[0]
        df_sgf.columns = df_sgf.iloc[0]
        
        # Удаляем первую строку (она стала заголовками)
        df_settings = df_settings.iloc[1:].reset_index(drop=True)
        df_sgf = df_sgf.iloc[1:].reset_index(drop=True)
        
        # Объединяем
        df_combined = pd.concat([df_settings, df_sgf], axis=1)
        
        # Возвращаем список имен для поиска ФБ
        headers_list = df_combined.columns.tolist()
        
        return headers_list, df_combined
    

    def create_df_for_analyse_modes(self, first_folder):
        """Анализирует все файлы режимов из первой папки *_modes"""
        
        #print(f"Обрабатываем папку: {first_folder.name}")
        
        # Находим файлы
        mode_files = []
        for file_path in first_folder.iterdir():
            if file_path.suffix.lower() == '.xlsx':
                if 'Журнал событий' in file_path.name:
                    continue
                if re.search(r'_\d+\.xlsx$', file_path.name, re.IGNORECASE):
                    mode_files.append(file_path)
        
        if not mode_files:
            return None, None
        
        # ✅ Natural sort файлов
        mode_files = natsorted(mode_files, key=lambda x: x.name)
        
        # Собираем DataFrame
        all_dataframes = []
        
        for file_path in mode_files:
            try:
                headers_list, df_combined = self.get_xlsx_data(file_path)
                #print(headers_list)
                df_combined['source_file'] = file_path.name
                df_combined['source_folder'] = first_folder.name
                all_dataframes.append(df_combined)
            except Exception as e:
                print(f"Ошибка {file_path.name}: {e}")
                continue
        
        if all_dataframes:
            #print(all_dataframes)
            final_df = pd.concat(all_dataframes, axis=0, ignore_index=True)
            
            # ✅ Natural sort строк в DataFrame
            final_df = final_df.sort_values(
                by='source_file', 
                key=lambda x: x.map(natsort_key),
                ignore_index=True
            )
            
            #print(f"✅ Итоговый DataFrame: {final_df.shape[0]} строк, {final_df.shape[1]} колонок")
            #print(f"Файлы в порядке: {final_df['source_file'].unique().tolist()}")
            
            return mode_files, final_df
        
        return None, None
    

    def analyse_df(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Анализирует DataFrame с режимами и находит различия в уставках 
        между соседними режимами.
        
        Args:
            df: DataFrame, полученный из analyse_modes (с колонкой source_file)
            
        Returns:
            Словарь: { 'ИмяФайлаРежима': ['Список_колонок_с_различиями'], ... }
            Ключи — это имена файлов режимов, начиная со второго.
        """
        if df is None or df.empty:
            print("❌ DataFrame пуст или не передан.")
            return {}

        # Исключаем служебные колонки из сравнения уставок
        exclude_cols = {'source_file', 'source_folder'}
        compare_cols = [col for col in df.columns if col not in exclude_cols]
        
        if not compare_cols:
            print("❌ Нет колонок для сравнения.")
            return {}

        # Получаем упорядоченный список уникальных файлов режимов
        # (они уже отсортированы natural sort на этапе создания df)
        modes_list = df['source_file'].unique().tolist()
        
        if len(modes_list) < 2:
            print("⚠️ Найдено менее 2 режимов. Сравнение невозможно.")
            return {}

        differences_dict = {}
        
        #print(f"\n🔍 Анализ различий ({len(modes_list)} режимов)...")
        
        # Проходим по парам: (Режим 1, Режим 2), (Режим 2, Режим 3) и т.д.
        for i in range(1, len(modes_list)):
            prev_mode = modes_list[i-1]
            curr_mode = modes_list[i]
            
            # Извлекаем данные для текущего и предыдущего режима
            # Предполагаем, что структура строк внутри одного файла одинакова (1 строка на файл или одинаковый индекс)
            # Если в файле несколько строк, нужно агрегировать или сравнивать по индексу.
            # В данном случае берем все строки соответствующего файла.
            
            df_prev = df[df['source_file'] == prev_mode].reset_index(drop=True)
            df_curr = df[df['source_file'] == curr_mode].reset_index(drop=True)
            
            # Проверка на совпадение количества строк (структуры)
            if len(df_prev) != len(df_curr):
                print(f"  ⚠️ Предупреждение: Количество строк в {prev_mode} ({len(df_prev)}) "
                    f"и {curr_mode} ({len(df_curr)}) отличается. Сравнение построчно может быть некорректным.")
                # Приводим к минимальному количеству строк для сравнения
                min_len = min(len(df_prev), len(df_curr))
                df_prev = df_prev.iloc[:min_len]
                df_curr = df_curr.iloc[:min_len]

            diff_columns_set = set()
            
            # Сравниваем построчно
            # Если в каждом файле всего 1 строка с настройками, цикл выполнится 1 раз
            for idx in range(len(df_prev)):
                row_prev = df_prev.iloc[idx][compare_cols]
                row_curr = df_curr.iloc[idx][compare_cols]
                
                # Находим различия в этой строке
                # compare != работает поэлементно, возвращает Boolean серию
                diff_mask = row_prev != row_curr
                
                # Добавляем имена колонок, где есть различия (учитывая NaN)
                # fillna используется, чтобы NaN != NaN не считалось различием (или считалось, в зависимости от задачи)
                # Обычно NaN == NaN считаем равными (уставка не задана в обоих случаях)
                diff_mask = diff_mask.fillna(False) 
                
                changed_cols = diff_mask[diff_mask].index.tolist()
                diff_columns_set.update(changed_cols)
            
            if diff_columns_set:
                # Сортируем список колонок для удобства чтения
                differences_dict[curr_mode] = sorted(list(diff_columns_set))
                #print(f"  📊 {prev_mode} ➔ {curr_mode}: найдено {len(diff_columns_set)} измененных параметров")
            else:
                pass
                #print(f"  ✅ {prev_mode} ➔ {curr_mode}: изменений нет")

        return differences_dict
    
    def generate_pair_one_mode(self, target_folder):
        rep = self.generate_reports(target_folder)
        mode_files, final_df = self.create_df_for_analyse_modes(target_folder)
        analysed = self.analyse_df(final_df)
        marked = self.mark_different_settings(rep, analysed)
        # ✅ Добавляем распространение флагов изменений
        marked = self.propagate_change_flags(marked)
        return rep, marked

    def generate_pair_all_modes(self):

        # 1. Находим все папки
        modes_folders = [
            folder for folder in Path(self.path_to_modes_xlsx).iterdir()
            if folder.is_dir() and folder.name.endswith('_modes')
        ]
        if not modes_folders:
            print("❌ Папки с режимами не найдены!")
            return []
        all_modes = []
        for modes_folder in modes_folders:
            rep, norm = self.generate_pair_one_mode(modes_folder)
            all_modes.append(norm)
        return all_modes


    def generate_reports(self, target_folder) -> List[Dict]:
        """
        Собирает отчеты по всем режимам из одной папки *_modes,
        используя готовый метод generate_report.
        """
        
        reports_list = []
        
        #print(f"📁 Обрабатываем папку: {target_folder.name}")
        
        # 3. Находим файлы
        mode_files = []
        for file_path in target_folder.iterdir():
            if file_path.suffix.lower() == '.xlsx':
                if 'Журнал событий' in file_path.name:
                    continue
                if re.search(r'_\d+\.xlsx$', file_path.name, re.IGNORECASE):
                    mode_files.append(file_path)
        
        if not mode_files:
            print(f"   ⚠️ Файлы не найдены")
            return []
        
        # Сортируем
        mode_files = natsorted(mode_files, key=lambda x: x.name)
        #print(f"   📄 Найдено файлов: {len(mode_files)}")
        
        # --- ВАЖНОЕ ИЗМЕНЕНИЕ НАЧАЛО ---
        # Сохраняем старый путь, чтобы потом восстановить
        original_path = self.path_to_modes_xlsx
        
        # Временно меняем путь поиска на текущую подпапку (например, core/modes/kpon_modes/)
        # Добавляем слэш в конце, если его нет, для корректного соединения путей
        self.path_to_modes_xlsx = str(target_folder) + "/" 
        # --------------------------------
        
        try:
            # 4. Вызываем готовый generate_report для каждого файла
            for file_path in mode_files:
                try:
                    #print(f"      🔄 {file_path.name}...", end=" ")
                    
                    # Теперь generate_report будет искать файл по пути self.path_to_modes_xlsx + file_path.name
                    # То есть: core/modes/kpon_modes/ + КПОН_1.xlsx
                    report_data = self.generate_report(file_path.name)
                    
                    if report_data:
                        full_report = {
                            'mode_file': file_path.name,
                            'mode_folder': target_folder.name,
                            'mode_path': str(file_path),
                            'settings': report_data
                        }
                        reports_list.append(full_report)
                        #("✅")
                    else:
                        print("⚠️ Пустой отчет")
                        
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
                    continue
        finally:
            # --- ВАЖНОЕ ИЗМЕНЕНИЕ КОНЕЦ ---
            # Обязательно возвращаем исходный путь, даже если произошла ошибка
            self.path_to_modes_xlsx = original_path
            # ------------------------------
        
        #print(f"\n✅ Всего собрано отчетов: {len(reports_list)}")
        return reports_list
    


    def mark_different_settings(self, reports: List[Dict], differences: Dict[str, List[str]]) -> List[Dict]:
        """
        Помечает уставки, которые отличаются в разных режимах, установкой Color='1'
        
        Args:
            reports: Список отчетов (результат generate_reports)
            differences: Словарь {имя_файла: [список_отличающихся_SpecificSettingName]}
        
        Returns:
            Обновленный список отчетов с помеченными уставками
        """
        for report in reports:
            mode_file = report['mode_file']
            
            # Если для этого файла есть отличающиеся уставки
            if mode_file in differences:
                diff_settings = set(differences[mode_file])  # set для быстрого поиска
                
                # Проходим по всем блокам настроек
                settings = report['settings']
                for block_name, block_data in settings.items():
                    functions = block_data.get('functions', {})
                    
                    # Проходим по всем функциям в блоке
                    for func_name, func_data in functions.items():
                        parameters = func_data.get('parameters', [])
                        
                        # Проходим по всем параметрам
                        for param in parameters:
                            specific_name = param.get('SpecificSettingName')
                            
                            # Если SpecificSettingName есть в списке отличий — помечаем
                            if specific_name and specific_name in diff_settings:
                                param['Color'] = '1'
        
        return reports
    

    def propagate_change_flags(self, reports: List[Dict]) -> List[Dict]:
        """
        Распространяет флаги изменений от параметров к функциям, блокам и режимам.
        Устанавливает is_changed=1 если есть хотя бы один измененный параметр.
        
        Args:
            reports: Список отчетов с помеченными параметрами (Color='1')
            
        Returns:
            Обновленный список отчетов с флагами is_changed на всех уровнях
        """
        for report in reports:
            mode_changed = False
            settings = report['settings']
            
            # Проходим по всем блокам
            for block_name, block_data in settings.items():
                block_changed = False
                functions = block_data.get('functions', {})
                
                # Проходим по всем функциям в блоке
                for func_name, func_data in functions.items():
                    func_changed = False
                    parameters = func_data.get('parameters', [])
                    
                    # Проверяем параметры
                    for param in parameters:
                        if param.get('Color') == '1':
                            func_changed = True
                            break
                    
                    # Устанавливаем флаг на функции
                    func_data['is_changed'] = 1 if func_changed else 0
                    
                    if func_changed:
                        block_changed = True
                
                # Устанавливаем флаг на блоке
                block_data['is_changed'] = 1 if block_changed else 0
                
                if block_changed:
                    mode_changed = True
            
            # Устанавливаем флаг на режиме
            report['is_changed'] = 1 if mode_changed else 0
        
        return reports
    



    ############################################
    ######## Методы сбора входов и выходов #####
    ############################################

    def get_inputs_raw_data(self, path_to):

        # === 1. Загружаем ключи из JSON файлов ===
        mode_inputs_path = path_to / "inputs.json"
        mode_outputs_path = path_to / "outputs.json"

        with open(mode_inputs_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)  # Теперь это словарь: {'key': value, ...}

        with open(mode_outputs_path, 'r', encoding='utf-8') as f:
            output_data = json.load(f) # Теперь это словарь: {'key': value, ...}

        merged_config = {**input_data, **output_data}

        # Если вам все еще нужен список только ключей для фильтрации колонок:
        input_columns = list(input_data.keys())
        output_columns = list(output_data.keys())

        _, ins_df, outs_df = self.create_df_for_render_modes(path_to)

        # === 2. Функция для фильтрации, упорядочивания и переименования ===
        def filter_and_rename_df(df, json_cols, config_handler):
            # Оставляем только те колонки, которые есть в JSON и в DataFrame
            valid_cols = [col for col in json_cols if col in df.columns]
            
            # Если ни одной общей колонки не найдено, возвращаем пустой DataFrame
            if not valid_cols:
                return pd.DataFrame()
            
            # Фильтруем и упорядочиваем столбцы по списку из JSON
            df = df[valid_cols].copy()
            
            # Заменяем заголовки на описания из config_handler
            new_cols = []
            for col in df.columns:
                info = config_handler.get_param_info(col)


                if info:
                    # Если есть мета-информация (описание), берем её
                    new_name = info.get('appliedDescription', col)
                elif col in merged_config:
                    # ИЗМЕНЕНИЕ: Если описания нет, но ключ есть в нашем общем словаре значений,
                    # берем ЗНАЧЕНИЕ из JSON вместо имени колонки.
                    # Преобразуем в строку на случай, если значение числовое или булево.
                    new_name = str(merged_config[col])
                else:
                    # Если ничего не найдено, оставляем имя колонки как запасной вариант
                    new_name = col


                new_cols.append(new_name)
            
            df.columns = new_cols
            return df

        # === 3. Применяем к обоим DataFrame (разные списки колонок) ===
        ins_df = filter_and_rename_df(ins_df, input_columns, self.config_handler)
        outs_df = filter_and_rename_df(outs_df, output_columns, self.config_handler)

        # === 4. Проверка результата ===
        #print(f"ins_df колонки ({len(ins_df.columns)}): {list(ins_df.columns)}")
        #print(f"outs_df колонки ({len(outs_df.columns)}): {list(outs_df.columns)}")
        return ins_df, outs_df

    def get_xlsx_data_inout(self, file_path):
        
        path_obj = Path(file_path)
        
        # Если передано только имя файла (без пути), добавляем базовую директорию
        if not path_obj.is_absolute() and len(path_obj.parts) == 1:
            # Это просто имя файла, добавляем путь к папке modes
            path_to_example = Path(self.path_to_modes_xlsx) / path_obj
        else:
            # Это полный или относительный путь, используем как есть
            path_to_example = path_obj
        
        if not path_to_example.exists():
            raise FileNotFoundError(f"Файл не найден: {path_to_example}")
        
        df_ins = pd.read_excel(path_to_example, sheet_name='Inputs', header=None)
        df_outs = pd.read_excel(path_to_example, sheet_name='Outputs', header=None)
        
        # Назначаем заголовки из первой строки
        df_ins.columns = df_ins.iloc[0]
        df_outs.columns = df_outs.iloc[0]
        
        # Удаляем первую строку (она стала заголовками)
        df_ins = df_ins.iloc[1:].reset_index(drop=True)
        df_outs = df_outs.iloc[1:].reset_index(drop=True)
        
        # Возвращаем список имен для поиска ФБ
        headers_list_ins = df_ins.columns.tolist()
        headers_list_outs = df_outs.columns.tolist()
        return headers_list_ins, headers_list_outs, df_ins, df_outs
    

    def create_df_for_render_modes(self, first_folder):
        """Анализирует все файлы режимов из первой папки *_modes"""
        
        #print(f"Обрабатываем папку: {first_folder.name}")
        
        # Находим файлы
        mode_files = []
        for file_path in first_folder.iterdir():
            if file_path.suffix.lower() == '.xlsx':
                if 'Журнал событий' in file_path.name:
                    continue
                if re.search(r'_\d+\.xlsx$', file_path.name, re.IGNORECASE):
                    mode_files.append(file_path)
        
        if not mode_files:
            return None, None
        
        # ✅ Natural sort файлов
        mode_files = natsorted(mode_files, key=lambda x: x.name)
        
        # Собираем DataFrame
        all_dataframes_ins = []
        all_dataframes_outs = []

        for file_path in mode_files:
            try:
                headers_list_ins, headers_list_outs, df_ins, df_outs = self.get_xlsx_data_inout(file_path)
                df_ins['source_file'] = file_path.name
                df_ins['source_folder'] = first_folder.name
                df_outs['source_file'] = file_path.name
                df_outs['source_folder'] = first_folder.name
                all_dataframes_ins.append(df_ins)
                all_dataframes_outs.append(df_outs)
            except Exception as e:
                print(f"Ошибка {file_path.name}: {e}")
                continue
        
        if all_dataframes_ins:
            final_df_ins = pd.concat(all_dataframes_ins, axis=0, ignore_index=True)

        if all_dataframes_outs:
            final_df_outs = pd.concat(all_dataframes_outs, axis=0, ignore_index=True)


            # ✅ Natural sort строк в DataFrame
            final_df_ins = final_df_ins.sort_values(
                by='source_file', 
                key=lambda x: x.map(natsort_key),
                ignore_index=True
            )

            # ✅ Natural sort строк в DataFrame
            final_df_outs = final_df_outs.sort_values(
                by='source_file', 
                key=lambda x: x.map(natsort_key),
                ignore_index=True
            )

            #print(f"✅ Итоговый DataFrame: {final_df.shape[0]} строк, {final_df.shape[1]} колонок")
            #print(f"Файлы в порядке: {final_df['source_file'].unique().tolist()}")
            
            return mode_files, final_df_ins, final_df_outs
        
        return None, None, None