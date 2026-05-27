import json
import os
import glob
from pathlib import Path

def update_virtual_keys_in_all_json(folder_path="."):
    """
    Обрабатывает все JSON файлы в указанной папке:
    - Находит все параметры VirtualKey_X_Condition_SG1
    - Заменяет их значение с False на True
    - Создает резервные копии
    """
    
    # Показываем текущую рабочую папку
    current_dir = os.path.abspath(folder_path)
    print(f"Текущая рабочая папка: {current_dir}")
    print(f"Поиск файлов в: {current_dir}")
    print("-" * 60)
    
    # Получаем все JSON файлы
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    # Показываем найденные файлы
    if json_files:
        print(f"\nНайденные JSON файлы:")
        for f in json_files:
            print(f"  - {os.path.basename(f)}")
    else:
        print(f"\nВ папке '{current_dir}' не найдено JSON файлов")
        return
    
    print(f"\nВсего найдено JSON файлов: {len(json_files)}")
    print("="*60)
    
    total_changes = 0
    
    for file_path in json_files:
        file_name = os.path.basename(file_path)
        print(f"\nОбработка: {file_name}")
        
        try:
            # Читаем JSON файл
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Счетчик изменений для этого файла
            file_changes = 0
            changed_params = []
            
            # Обновляем параметры
            for item in data:
                param_name = item.get('Parameter', '')
                
                # Проверяем условие
                if param_name.startswith('VirtualKey_') and param_name.endswith('_SG1'):
                    if item.get('Value') == 'True':
                        item['Value'] = 'False'
                        file_changes += 1
                        changed_params.append(param_name)
            
            if file_changes > 0:
                # Создаем резервную копию
                backup_path = file_path.replace('.json', '_backup.json')
                with open(backup_path, 'w', encoding='utf-8') as backup:
                    json.dump(data, backup, indent=2, ensure_ascii=False)
                
                # Сохраняем изменения в исходный файл
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=2, ensure_ascii=False)
                
                print(f"  ✓ Изменено: {file_changes} параметров")
                if len(changed_params) <= 10:  # Показываем только первые 10
                    for param in changed_params[:10]:
                        print(f"    - {param}")
                else:
                    print(f"    - {changed_params[0]} ... и еще {len(changed_params)-10}")
            else:
                print(f"  Параметров VirtualKey_X_Condition_SG1 со значением False не найдено")
            
            total_changes += file_changes
            
        except json.JSONDecodeError as e:
            print(f"  ✗ Ошибка: Неверный JSON формат - {e}")
        except Exception as e:
            print(f"  ✗ Ошибка: {str(e)}")
    
    print("\n" + "="*60)
    print(f"ОБЩИЙ РЕЗУЛЬТАТ:")
    print(f"Обработано файлов: {len(json_files)}")
    print(f"Всего изменений: {total_changes}")
    print("="*60)

# Запуск обработки текущей папки
if __name__ == "__main__":
    # Для текущей папки:
    update_virtual_keys_in_all_json(".")
    
    # Задержка перед закрытием
    print("\n" + "="*60)
    input("Нажмите Enter для выхода...")