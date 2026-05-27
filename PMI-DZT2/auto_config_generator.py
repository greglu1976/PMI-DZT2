import json
import os
import sys
import collections

from CORE.HMIHandler import HMIHandler
from CORE.MainConfigHandler import MainConfigHandler

def load_json_file_ordered(filepath):
    if not os.path.exists(filepath):
        print(f"Ошибка: Файл '{filepath}' не найден.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f, object_pairs_hook=collections.OrderedDict)
    except Exception as e:
        print(f"Ошибка чтения файла '{filepath}': {e}")
        return None

def main():
    print("--- Генератор конфигурации HMI (Auto Mapping with Template) ---")
    
    # 1. MetaHandler
    meta_handler = None
    if os.path.exists("meta.json"):
        try:
            meta_handler = MainConfigHandler.from_json_file("meta.json")
            print("[OK] meta.json загружен.")
        except Exception as e:
            print(f"[WARN] Ошибка meta.json: {e}")
    else:
        print("[WARN] meta.json не найден.")

    # 2. Загрузка шаблона
    template_data = load_json_file_ordered("template.json")
    if template_data is None:
        print("Критическая ошибка: Не удалось загрузить template.json")
        return
    
    print(f"[OK] template.json загружен. DeviceModel: {template_data.get('DeviceModel', 'N/A')}")

    # 3. Загрузка данных
    inputs_data = load_json_file_ordered("inputs.json")
    outputs_data = load_json_file_ordered("outputs.json")

    if inputs_data is None or outputs_data is None:
        print("Критическая ошибка: Отсутствуют inputs.json или outputs.json")
        return

    # 4. Инициализация HMI Handler ИЗ ШАБЛОНА
    hmi_handler = HMIHandler(meta_handler=meta_handler)
    
    # Используем новый метод load_from_dict для переноса всех данных из шаблона
    hmi_handler.load_from_dict(template_data)
    
    # Очищаем маппинги, так как будем генерировать их заново
    hmi_handler.hmi_mappings = []
    
    print(f"     Текущий DeviceModel: {hmi_handler.device_model}")

    print("\n--- Начало автоматического назначения ---")

    # ==========================================================
    # ШАГ 1: Функциональные Кнопки (из inputs.json)
    # ==========================================================
    print("\n--- 1. Настройка ФК (из inputs.json) ---")
    
    fk_index = 2  # Начинаем со 2-й кнопки
    max_fk = 16
    fk_count = 0

    for key in inputs_data.keys():
        target_param = None
        
        if key.startswith("DI_"):
            target_param = key.replace("DI_", "FB_", 1)
        elif key.startswith("FB_"):
            target_param = key
        else:
            continue
            
        if meta_handler:
            if not meta_handler.get_param_info(target_param):
                continue

        if fk_index <= max_fk:
            success = hmi_handler.link_parameter_to_fk(fk_index, target_param)
            if success:
                print(f"  [OK] ФК {fk_index}: {target_param}")
                fk_count += 1
                fk_index += 1

    print(f"Итого назначено ФК: {fk_count}")

    # ==========================================================
    # ШАГ 2: Светодиоды (из outputs.json)
    # ==========================================================
    print("\n--- 2. Настройка СД (из outputs.json) ---")

    sd_index = 1
    max_sd = 16
    sd_count = 0

    for key in outputs_data.keys():
        if meta_handler:
            if not meta_handler.get_param_info(key):
                continue

        if sd_index <= max_sd:
            success = hmi_handler.link_parameter_to_led(sd_index, key)
            if success:
                print(f"  [OK] СД {sd_index}: {key}")
                sd_count += 1
                sd_index += 1

    print(f"Итого назначено СД: {sd_count}")

    # ==========================================================
    # ШАГ 3: Сохранение
    # ==========================================================
    output_filename = "Настройка светодиодов и ФК.json"
    print(f"\n--- Сохранение в {output_filename} ---")
    
    if hmi_handler.save_to_file(output_filename):
        print("[SUCCESS] Конфигурация успешно создана.")
    else:
        print("[ERROR] Не удалось сохранить файл.")

if __name__ == "__main__":
    main()