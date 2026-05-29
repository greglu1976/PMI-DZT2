import pandas as pd
from pathlib import Path
from collections import defaultdict

def read_parameter_table(file_path, sheet_name):
    """Читает таблицу с двумя строками (заголовки и значения)"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        if len(df) >= 2:
            headers = df.iloc[0].astype(str).str.strip().tolist()
            values = df.iloc[1].tolist()
            result = {}
            for h, v in zip(headers, values):
                if h and str(h) != 'nan':
                    result[h] = v
            return result
    except Exception as e:
        print(f"  Ошибка чтения листа '{sheet_name}': {e}")
        return {}
    return {}

def compare_with_previous():
    """Сравнивает каждый режим с предыдущим в текущей папке"""
    
    current_folder = Path.cwd()
    print(f"Рабочая папка: {current_folder}\n")
    
    # Группируем файлы по префиксу
    groups = defaultdict(list)
    
    for file_path in current_folder.glob("*.xlsx"):
        stem = file_path.stem
        parts = stem.rsplit('_', 1)
        
        if len(parts) == 2 and parts[1].isdigit():
            prefix, number = parts[0], int(parts[1])
            groups[prefix].append((number, file_path))
    
    if not groups:
        print("Не найдено файлов вида xxx_N.xlsx в текущей папке")
        input("\nНажмите Enter для выхода...")
        return
    
    # Анализируем каждую группу
    for prefix, files in groups.items():
        files.sort(key=lambda x: x[0])  # Сортируем по номеру
        
        if len(files) < 2:
            print(f"\nПрефикс '{prefix}': только один файл (режим {files[0][0]}), сравнение невозможно")
            continue
        
        print(f"\n{'='*70}")
        print(f"Группа файлов: {prefix}")
        print(f"{'='*70}")
        
        # Загружаем данные всех файлов
        all_data = []
        for num, file_path in files:
            print(f"\nЧтение режима {num}: {file_path.name}")
            data = {
                'num': num,
                'path': file_path,
                'SGF_Parameters': read_parameter_table(file_path, "SGF_Parameters"),
                'Settings': read_parameter_table(file_path, "Settings")
            }
            all_data.append(data)
        
        # Сравниваем каждый режим с предыдущим
        for i in range(1, len(all_data)):
            prev = all_data[i-1]
            curr = all_data[i]
            
            mode_name = f"Режим {curr['num']}"
            differences = []
            
            # Сравниваем SGF_Parameters
            all_params = set(prev['SGF_Parameters'].keys()) | set(curr['SGF_Parameters'].keys())
            for param in sorted(all_params):
                prev_val = prev['SGF_Parameters'].get(param)
                curr_val = curr['SGF_Parameters'].get(param)
                
                if pd.isna(prev_val) and pd.isna(curr_val):
                    continue
                if pd.isna(prev_val):
                    prev_val = None
                if pd.isna(curr_val):
                    curr_val = None
                    
                if prev_val != curr_val:
                    differences.append(f"  [SGF_Parameters] {param}: '{prev_val}' → '{curr_val}'")
            
            # Сравниваем Settings
            all_settings = set(prev['Settings'].keys()) | set(curr['Settings'].keys())
            for setting in sorted(all_settings):
                prev_val = prev['Settings'].get(setting)
                curr_val = curr['Settings'].get(setting)
                
                if pd.isna(prev_val) and pd.isna(curr_val):
                    continue
                if pd.isna(prev_val):
                    prev_val = None
                if pd.isna(curr_val):
                    curr_val = None
                    
                if prev_val != curr_val:
                    differences.append(f"  [Settings] {setting}: '{prev_val}' → '{curr_val}'")
            
            # Вывод результата
            if differences:
                print(f"\n🔴 {mode_name} ИЗМЕНЕН относительно режима {prev['num']}:")
                for diff in differences:
                    print(diff)
            else:
                print(f"\n🟢 {mode_name} не имеет отличий от режима {prev['num']}")
    
    input("\n\nНажмите Enter для выхода...")

if __name__ == "__main__":
    compare_with_previous()