import pandas as pd
import os
from pathlib import Path

def process_excel_files(folder_path):
    """
    Обрабатывает все xlsx файлы в папке:
    - читает лист 'Inputs'
    - заменяет DI_ на FB_ в названиях столбцов
    - сохраняет изменения в тот же файл
    """
    
    # Получаем все xlsx файлы в папке
    excel_files = list(Path(folder_path).glob("*.xlsx"))
    
    if not excel_files:
        print(f"В папке '{folder_path}' не найдено xlsx файлов")
        return
    
    print(f"Найдено файлов: {len(excel_files)}")
    
    for file_path in excel_files:
        print(f"\nОбработка: {file_path.name}")
        
        try:
            # Читаем только лист 'Inputs'
            df = pd.read_excel(file_path, sheet_name='Inputs')
            
            # Проверяем, есть ли столбцы, начинающиеся с 'DI_'
            original_columns = df.columns.tolist()
            new_columns = []
            changes_made = False
            
            for col in original_columns:
                if col.startswith('DI_'):
                    new_col = col.replace('DI_', 'FB_', 1)  # заменяем только первое вхождение
                    new_columns.append(new_col)
                    changes_made = True
                    print(f"  Переименован столбец: '{col}' -> '{new_col}'")
                else:
                    new_columns.append(col)
            
            if changes_made:
                # Применяем новые имена столбцов
                df.columns = new_columns
                
                # Сохраняем изменения обратно в файл (только лист Inputs)
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', 
                                   if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name='Inputs', index=False)
                print(f"  ✓ Изменения сохранены")
            else:
                print(f"  Столбцов с префиксом 'DI_' не найдено")
                
        except ValueError as e:
            print(f"  ✗ Ошибка: лист 'Inputs' не найден в файле {file_path.name}")
        except Exception as e:
            print(f"  ✗ Ошибка при обработке файла {file_path.name}: {str(e)}")
    
    print(f"\nОбработка завершена")

# Использование:
folder_path = "."  # текущая папка, или укажите свой путь, например: "C:/Мои документы/Excel файлы"
process_excel_files(folder_path)