# ГЕНЕРАЦИЯ COMTRADE 2013 ИЗ ФАЙЛА СОБЫТИЙ XLSX (Журнал событий.xlsx)


import pandas as pd
from datetime import datetime
import os
import sys
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ================= НАСТРОЙКИ =================
INPUT_FILE = 'Журнал событий.xlsx'            # Имя входного файла Excel
OUTPUT_PREFIX = 'comtrade_2013'  # Префикс выходных файлов (.cfg, .dat)
SAMPLING_RATE = 1000             # Частота дискретизации в Гц (1000 Гц = 1 мс)

# Индексы колонок в Excel (нумерация с 0)
COL_TIME = 2       # Колонка "Время"
COL_NAME = 3       # Колонка "Наименование события"
COL_VALUE = 8      # Колонка "Значение" (где 0 или 1)
# =============================================

def parse_timestamp(t_value):
    """Универсальный парсер времени."""
    if pd.isna(t_value):
        return None
    
    if isinstance(t_value, datetime):
        return t_value
    
    t_str = str(t_value).strip().replace(',', '.')
    try:
        return datetime.strptime(t_str, '%d.%m.%Y %H:%M:%S.%f')
    except ValueError:
        try:
            return datetime.strptime(t_str, '%d.%m.%Y %H:%M:%S')
        except ValueError:
            return None

def sanitize_channel_name(name, for_xml=False):
    """
    Очищает имя канала для COMTRADE 2013.
    В версии 2013 можно использовать Unicode, но нужно экранировать для XML.
    """
    if pd.isna(name):
        return "Unknown"
    
    # Заменяем проблемные символы
    name_str = str(name).strip()
    
    if for_xml:
        # Для XML нужно экранировать специальные символы
        name_str = (name_str.replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;')
                           .replace("'", '&apos;'))
    
    return name_str

def create_xml_header(start_time, end_time, signal_names, station_name="Substation"):
    """
    Создает XML заголовок для COMTRADE 2013.
    """
    # Создаем корневой элемент
    root = ET.Element("device", attrib={
        "xmlns": "http://iec.ch/TC57/2013/ComtradeSchema",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
    })
    
    # Информация о записи
    recording = ET.SubElement(root, "recording")
    ET.SubElement(recording, "stationName").text = station_name
    ET.SubElement(recording, "deviceID").text = OUTPUT_PREFIX
    ET.SubElement(recording, "startTime").text = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    ET.SubElement(recording, "duration").text = f"{(end_time - start_time).total_seconds():.6f}"
    
    # Информация о каналах
    channels = ET.SubElement(root, "channels")
    
    # Добавляем аналоговые каналы (все наши сигналы)
    for i, name in enumerate(signal_names):
        analog = ET.SubElement(channels, "analog")
        ET.SubElement(analog, "index").text = str(i + 1)
        ET.SubElement(analog, "name").text = sanitize_channel_name(name, for_xml=True)
        ET.SubElement(analog, "phase").text = ""
        ET.SubElement(analog, "unit").text = "V"
        ET.SubElement(analog, "multiplier").text = "1"
        ET.SubElement(analog, "offset").text = "0"
        ET.SubElement(analog, "min").text = "0"
        ET.SubElement(analog, "max").text = "1"
        ET.SubElement(analog, "primary").text = "1"
        ET.SubElement(analog, "secondary").text = "1"
        ET.SubElement(analog, "circuitType").text = "0"
    
    # Частота дискретизации
    sampling = ET.SubElement(root, "sampling")
    rates = ET.SubElement(sampling, "rates")
    rate = ET.SubElement(rates, "rate")
    ET.SubElement(rate, "nominalFrequency").text = "50"
    ET.SubElement(rate, "samplesPerSecond").text = str(SAMPLING_RATE)
    ET.SubElement(rate, "numberOfSamples").text = "0"  # Будет заполнено позже
    
    # Конвертируем в красивый XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ", encoding='utf-8')
    return xml_str.decode('utf-8')

def main():
    print(f"=== COMTRADE Generator (IEEE C37.111-2013) ===")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_PREFIX}.cfg / {OUTPUT_PREFIX}.dat")
    print("-" * 50)

    # 1. Проверка наличия файла
    if not os.path.exists(INPUT_FILE):
        print(f"ОШИБКА: Файл {INPUT_FILE} не найден!")
        sys.exit(1)

    # 2. Чтение Excel
    print("Чтение Excel файла...")
    try:
        df_raw = pd.read_excel(INPUT_FILE, header=None, skiprows=1)
    except Exception as e:
        print(f"ОШИБКА чтения Excel: {e}")
        sys.exit(1)

    print(f"  Размер таблицы: {df_raw.shape[0]} строк, {df_raw.shape[1]} колонок")
    
    if df_raw.shape[0] == 0:
        print("ОШИБКА: Файл пуст или все строки пропущены!")
        sys.exit(1)

    if df_raw.shape[1] <= max(COL_TIME, COL_NAME, COL_VALUE):
        print(f"ОШИБКА: Недостаточно колонок в файле.")
        sys.exit(1)

    # 3. Предобработка данных
    print("Обработка данных...")
    df_raw.columns = [f'col_{i}' for i in range(df_raw.shape[1])]
    
    df = pd.DataFrame({
        'time_raw': df_raw.iloc[:, COL_TIME],
        'name': df_raw.iloc[:, COL_NAME],
        'value': df_raw.iloc[:, COL_VALUE]
    })
    
    # Парсим время
    print("  Парсинг времени...")
    df['timestamp'] = df['time_raw'].apply(parse_timestamp)
    valid_count = df['timestamp'].notna().sum()
    
    if valid_count == 0:
        print("ОШИБКА: Не найдено валидных записей с временем!")
        sys.exit(1)
    
    df = df.dropna(subset=['timestamp'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0).astype(int)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"  Всего событий: {len(df)}")
    print(f"  Уникальных сигналов: {df['name'].nunique()}")
    print(f"  Период: {df['timestamp'].min()} - {df['timestamp'].max()}")

    # 4. Формирование широкой таблицы (Pivot)
    print("  Создание сводной таблицы...")
    wide_df = df.pivot_table(
        index='timestamp', 
        columns='name', 
        values='value', 
        aggfunc='last'
    )
    wide_df = wide_df.ffill().fillna(0).astype(int)
    
    print(f"  Уникальных меток времени: {len(wide_df)}")

    # 5. Ресемплинг к равномерной сетке
    print(f"Ресемплинг к сетке {SAMPLING_RATE} Гц...")
    start_time = wide_df.index[0]
    end_time = wide_df.index[-1]
    
    # Округляем микросекунды до миллисекунд
    start_time = start_time.replace(microsecond=(start_time.microsecond // 1000) * 1000)
    end_time = end_time.replace(microsecond=(end_time.microsecond // 1000) * 1000)
    
    new_index = pd.date_range(start=start_time, end=end_time, freq='1ms')
    resampled_df = wide_df.reindex(new_index, method='ffill').fillna(0).astype(int)
    resampled_df.index.name = 'time'
    
    print(f"  Отсчётов после ресемплинга: {len(resampled_df)}")
    duration = (end_time - start_time).total_seconds()
    print(f"  Длительность: {duration:.3f} сек")

    # 6. Генерация файлов COMTRADE 2013
    print("Генерация файлов COMTRADE 2013...")
    
    # Сохраняем оригинальные имена
    signal_names = [sanitize_channel_name(name, for_xml=False) for name in resampled_df.columns]
    num_channels = len(signal_names)
    num_samples = len(resampled_df)
    print(f"  Каналов (дискретных): {num_channels}")

    # === CFG ФАЙЛ (Строгий стандарт 2013) ===
    cfg_file = f"{OUTPUT_PREFIX}.cfg"
    #with open(cfg_file, 'w', encoding='utf-8') as f:
    with open(cfg_file, 'w', encoding='cp1251') as f:    
        # 1. station_name, recording_device_id, rev_year
        f.write(f"Substation,{OUTPUT_PREFIX},2013\n")
        
        # 2. TT,##A,##D (Всего каналов, Аналоговых, Дискретных)
        # Обязательно указываются буквы 'A' и 'D'
        f.write(f"{num_channels},0A,{num_channels}D\n")
        
        # 3. Описание дискретных каналов (т.к. у нас сигналы 0/1)
        # Формат: Dn,ch_id,ph,ccbm,y (y - нормальное состояние, обычно 0)
        for i, name in enumerate(signal_names):
            f.write(f"{i+1},{name},,,0\n")
            
        # 4. Частота сети (Гц)
        f.write(f"50.0\n")
        
        # 5. nrates (количество частот дискретизации)
        f.write(f"1\n")
        
        # 6. samp,endsamp (частота, кол-во отсчетов)
        f.write(f"{SAMPLING_RATE},{num_samples}\n")
        
        # 7. Время начала (строго DD/MM/YYYY,HH:MM:SS.ffffff)
        start_str = start_time.strftime('%d/%m/%Y,%H:%M:%S.%f')
        f.write(f"{start_str}\n")
        
        # 8. Время окончания (оно же время триггера)
        end_str = end_time.strftime('%d/%m/%Y,%H:%M:%S.%f')
        f.write(f"{end_str}\n")
        
        # 9. Формат файла данных
        f.write(f"ASCII\n")
        
        # 10. Множитель времени (timemult). 1.0 значит время в DAT идет в микросекундах.
        f.write(f"1.0\n")
        
        # 11. time_code,local_code (Параметр 2013 года: смещение времени)
        f.write(f"0,0\n")
        
        # 12. tmq_code,leapsec (Параметр 2013 года: качество времени)
        f.write(f"0,0\n")

    # === DAT ФАЙЛ (ASCII) ===
    dat_file = f"{OUTPUT_PREFIX}.dat"
    print("  Запись файла данных...")
    #with open(dat_file, 'w', encoding='utf-8') as f:
    with open(dat_file, 'w', encoding='cp1251') as f:        
        for i, (idx, row) in enumerate(resampled_df.iterrows()):
            if i % 50000 == 0 and i > 0:
                print(f"    Обработано {i}/{num_samples} отсчётов ({i/num_samples*100:.1f}%)...")
            
            sample_num = i + 1
            
            # Время в МИКРОСЕКУНДАХ от начала записи (требование стандарта при timemult=1.0)
            time_us = int((i * 1000000) / SAMPLING_RATE)
            
            # Значения (0 или 1)
            values = [int(row[col]) for col in resampled_df.columns]
            
            # Формат: номер_образца,время_в_мкс,дискретный1,дискретный2...
            line = f"{sample_num},{time_us}," + ",".join(map(str, values))
            f.write(line + "\n")

    print("-" * 50)
    print(f"ГОТОВО! (Формат IEEE C37.111-2013)")
    print(f"  CFG файл: {os.path.abspath(cfg_file)}")
    print(f"  DAT файл: {os.path.abspath(dat_file)}")
    print(f"  Каналов: {num_channels} (дискретных)")
    print(f"  Отсчётов: {num_samples}")
    print(f"  Длительность: {duration:.3f} сек")

if __name__ == '__main__':
    main()
    print("-" * 50)
    print("Готово!")
    input("Нажмите Enter, чтобы выйти...")