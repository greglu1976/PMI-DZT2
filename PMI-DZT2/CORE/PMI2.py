# Версия 2 - БЕЗ обращений к базе SQL, только из пакета поддержки meta.json и GROUPING.json

from CORE.MainConfigHandler import MainConfigHandler
from CORE.InOutsMatrixHandler import InOutsMatrixHandler   
import pandas as pd

import json
from collections import defaultdict
from typing import List, Dict, Any, Optional

from pathlib import Path
import re
from natsort import natsorted, natsort_key



class PMI:


    def __init__(self, config_handler=None):

        if not config_handler:
            meta = "meta.json"
            self.config_handler = MainConfigHandler.from_json_file(meta)
        else:
            self.config_handler = config_handler



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