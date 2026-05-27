# РАЗРАБОТКА ГЕНЕРАТОРА ОТЧЕТОВ ПМИ ИЧМ
# Версия 2 - БЕЗ обращений к базе SQL, только из пакета поддержки meta.json и GROUPING.json

from pathlib import Path
import json
from docxtpl import DocxTemplate


from CORE.HMIHandler import HMIHandler
from CORE.PMI2 import PMI
from CORE.PMIRenderer import PMIRenderer
from CORE.BlancGen import BlancGen
from CORE.MainConfigHandler import MainConfigHandler

meta = "meta.json"
config_handler = MainConfigHandler.from_json_file(meta)

pmi = PMI(config_handler)

################################################################################
# 1 Поиск папок с режимами

path_to_modes_xlsx = "C:/Users/g.lubov.UNI-ENG/Desktop/М300-Т2/PMI-T2/ПМИ ИЧМ"
# 1. Находим все папки
modes_folders = [
    folder for folder in Path(path_to_modes_xlsx).iterdir()
    if folder.is_dir() and folder.name.endswith('_modes')
]
if not modes_folders:
    print("❌ Папки с режимами не найдены!")

#print(modes_folders)
#################################################################################


# II. Создаем документ с описанием ПМИ
# II.1 Создаем таблицу матрицы входов выходов   C:\Users\g.lubov.UNI-ENG\Desktop\М300-Т\PMI-T\CORE\pmi-t\pmi_ka\ka_modes


root_path = "core/"

for folder in modes_folders:

    # Проверяем есть ли файл Настройка светодиодов и ФК.json в этом каталоге и если есть то загружаем
    # Для таблицы СД и ФК
    # --- ПРОВЕРКА И ЗАГРУЗКА ИЧМ.json ---
    ichm_file_path = folder / "Настройка светодиодов и ФК.json"
    if ichm_file_path.exists():
        #print(f"✅ Найден файл ИЧМ.json для папки: {folder.name}")
        hmi = HMIHandler(file_name=ichm_file_path)
    else:
        #print(f"⚠️ Файл ИЧМ.json не найден в папке: {folder.name}")
        hmi = None                



    # Открываем файл и загружаем данные общих описаний режимов
    mode_desc_path =  folder / "descriptions.json"
    with open(mode_desc_path, 'r', encoding='utf-8') as f:
        mode_desc_dict = json.load(f)

    tpl = DocxTemplate(root_path+"/origin.docx")
    tpl.render(mode_desc_dict)
    tpl.save("Output/tmpl.docx")


    pmi_doc = PMIRenderer("Output/tmpl.docx")


    # Пошли заполнять по разделам 

    # 1 раздел - матрица входов и выходов
    pmi_doc.doc_add_heading_one("Назначение дискретных входов и выходных реле для проверки режимов")
    matrix_path = folder / "ПМИ Матрица.json"
    matrix = pmi.get_matrix(matrix_path)

    # Добавляем СД ФК в матрицу, если есть файл с ФК СД
    if hmi:
        matrix.insert(0, ('ФК1', 'ФК М/Д', '-'))

        for i, matri in enumerate(matrix):
            u = matri[1]
            m = config_handler.get_first_parameter_name_by_applied_description(u)
            if m and 'DI_' in m:
                #print(m)
                m = m.replace('DI_', 'FB_')
                r = config_handler.get_param_info(m)

                fk = hmi._find_fk_buttons_by_parameter(m)
                if fk==[] or not fk: 
                    print(fk)
                    number = -1000
                else:    
                    number = fk[0].split()[-1]  # берем последнее слово (цифру)
                # Заменяем весь кортеж:
                matrix[i] = (f'ФК{number}', r["appliedDescription"], matri[2])  # ✅ Работает

        for i, matri in enumerate(matrix):
            if 'K' in matri[2]:
                y = matri[2].split('K')[1]
                x = int(matri[2].split('K')[0])
                q = (x-3)*8+int(y)

                # Заменяем весь кортеж:
                matrix[i] = (matri[0], matri[1] , f"СД{q} / {matri[2]}")  # ✅ Работает

           
    #print(matrix)
    pmi_doc.add_table_matrix(matrix, 2)


    # 2,3 раздел - Подаваемые значения при проверке

    mode_inputs_path =  folder
    ins_df, outs_df = pmi.get_inputs_raw_data(mode_inputs_path)


    if hmi:
        # Находим все столбцы, начинающиеся с 'ФК:'
        ins_df.insert(0, 'ФК: М/Д', 1)
        fk_columns = [col for col in ins_df.columns if col.startswith('ФК:')]
        # Вариант 1: Используем replace для каждого столбца
        for col in fk_columns:
            ins_df[col] = ins_df[col].replace({0: '⭘', 1: '⬤'})

        new_columns = []
        for i, old_name in enumerate(outs_df.columns):
            new_columns.append(f'СД{i+1} / {old_name}')
        outs_df.columns = new_columns

    pmi_doc.doc_add_heading_one("Подаваемые воздействия для проверки режимов")
    pmi_doc.add_inout_table(ins_df, type = 'inputs')
    pmi_doc.doc_add_heading_one("Результаты проверки")
    pmi_doc.add_inout_table(outs_df, type = 'outputs')  


    # 4 раздел - бланки уставок по режимам (с разделителями)

    pmi_doc.doc_add_heading_one("Заданные уставки для проверки режимов")

    blanc = BlancGen(mode_inputs_path, mode_desc_dict["modes_prefix"])
    #print(blanc.final_output)

    pmi_doc.insert_settings_blancs(blanc)

    # Сохранение документа по режимам
    pmi_doc.save_docx(f'Output/{mode_desc_dict["file_name"]}')  






