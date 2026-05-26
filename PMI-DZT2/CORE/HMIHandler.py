import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# --- Константы и Маппинги ---

HMI_LED_MODES_MAP = {
    1: "Красный",
    2: "Зеленый"
}
HMI_LED_MODES_REVERSE = {v: k for k, v in HMI_LED_MODES_MAP.items()}

# ИСПРАВЛЕНО согласно вашему комментарию
HMI_LED_SCENARIOS_MAP = {
    1: "Без фиксации", 
    2: "С фиксацией"
}
HMI_LED_SCENARIOS_REVERSE = {v: k for k, v in HMI_LED_SCENARIOS_MAP.items()}

HMI_FK_SCENARIOS_MAP = {
    0: "Установка в 0",
    1: "Установка в 1",
    2: "Состояние кнопки",
    3: "Инвертировать"
}
HMI_FK_SCENARIOS_REVERSE = {v: k for k, v in HMI_FK_SCENARIOS_MAP.items()}


@dataclass
class LedConfig:
    number: int
    scenario_name: str
    mode_name: str
    linked_parameter: Optional[str] = None

@dataclass
class FkConfig:
    number: int
    scenario_name: str
    linked_parameter: Optional[str] = None


class HMIHandler:
    DEFAULT_FILENAME = "Настройка светодиодов и ФК.json"

    def __init__(self, meta_handler: Optional[Any] = None, file_name: Optional[str] = None):
        """
        :param meta_handler: Экземпляр MainConfigHandler для валидации имен параметров.
        :param file_name: Имя файла для загрузки. Если None, используется DEFAULT_FILENAME.
                          Если файл не найден, инициализируется дефолтными значениями.
        """
        self.meta_handler = meta_handler
        
        # Основные поля JSON
        self.version = "1.0.0.0"
        self.device_model = ""
        
        # Словари настроек поведения
        self.hmi_led_scenarios: Dict[str, int] = {}
        self.hmi_led_modes: Dict[str, int] = {}
        self.hmi_fk_scenarios: Dict[str, int] = {}
        self.hmi_button_scenarios: Dict[str, int] = {}
        
        # Список связей Параметр <-> Элементы интерфейса
        self.hmi_mappings: List[Dict[str, Any]] = []
        
        # 1. Сначала инициализируем дефолтными значениями (гарантия, что словари не пусты)
        self._init_defaults()
        
        # 2. Пытаемся загрузить файл, если он указан или существует дефолтный
        target_file = file_name if file_name else self.DEFAULT_FILENAME
        if os.path.exists(target_file):
            self.load_from_file(target_file)
        # Если файла нет, мы остаемся на дефолтных значениях из шага 1

    def _init_defaults(self):
        """Заполняет словари сценариев дефолтными значениями для всех 16 каналов"""
        for i in range(1, 17):
            led_key = f"Светодиод {i}"
            fk_key = f"Функциональная кнопка {i}"
            
            # Дефолтные значения
            # Сценарий LED: 1 - С фиксацией (согласно новому маппингу)
            self.hmi_led_scenarios[led_key] = 1 
            # Режим LED: 1 - Красный
            self.hmi_led_modes[led_key] = 1
            # Сценарий ФК: 3 - Инвертировать
            self.hmi_fk_scenarios[fk_key] = 3
            
        self.hmi_button_scenarios = {}
        self.hmi_mappings = []
        self.version = "1.0.0.0"
        self.device_model = ""

    # --- Загрузка и Сохранение ---

    def load_from_dict(self, data: Dict[str, Any]):
        """
        Загружает конфигурацию из словаря.
        """
        self.version = data.get("Version", self.version)
        self.device_model = data.get("DeviceModel", self.device_model)
        self.hmi_mappings = data.get("HmiMappings", [])
        self.hmi_button_scenarios = data.get("HmiButtonScenarios", {})
        self.hmi_fk_scenarios = data.get("HmiFunctionButtonScenarios", {})
        self.hmi_led_scenarios = data.get("HmiLedScenarios", {})
        self.hmi_led_modes = data.get("HmiLedModes", {})
        
        # Гарантируем наличие всех ключей (даже если в файле чего-то нет)
        self._ensure_all_keys_exist()

    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = self.DEFAULT_FILENAME
            
        try:
            if not os.path.exists(filepath):
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.load_from_dict(data)
            return True
        except Exception as e:
            print(f"Error loading HMI config: {e}")
            return False

    def _ensure_all_keys_exist(self):
        """Гарантирует наличие ключей для всех 16 LED и FK в словарях"""
        for i in range(1, 17):
            led_key = f"Светодиод {i}"
            fk_key = f"Функциональная кнопка {i}"
            
            # Используем setdefault, чтобы не перезаписывать загруженные значения дефолтами
            if led_key not in self.hmi_led_scenarios:
                self.hmi_led_scenarios[led_key] = 1
            if led_key not in self.hmi_led_modes:
                self.hmi_led_modes[led_key] = 1
            if fk_key not in self.hmi_fk_scenarios:
                self.hmi_fk_scenarios[fk_key] = 3

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        if filepath is None:
            filepath = self.DEFAULT_FILENAME

        try:
            self.clean_mappings()

            data = {
                "Version": self.version,
                "DeviceModel": self.device_model,
                "HmiMappings": self.hmi_mappings,
                "HmiButtonScenarios": self.hmi_button_scenarios,
                "HmiFunctionButtonScenarios": self.hmi_fk_scenarios,
                "HmiLedScenarios": self.hmi_led_scenarios,
                "HmiLedModes": self.hmi_led_modes
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving HMI config: {e}")
            return False

    # --- Очистка маппингов ---

    def clean_mappings(self):
        cleaned_mappings = []
        for mapping in self.hmi_mappings:
            leds = mapping.get("Leds", [])
            buttons = mapping.get("Buttons", [])
            func_buttons = mapping.get("FunctionButtons", [])
            
            if leds or buttons or func_buttons:
                cleaned_mappings.append(mapping)
        
        self.hmi_mappings = cleaned_mappings

    # --- Геттеры для GUI ---

    def get_led_modes_list(self) -> List[str]:
        return list(HMI_LED_MODES_MAP.values())

    def get_led_scenarios_list(self) -> List[str]:
        return list(HMI_LED_SCENARIOS_MAP.values())

    def get_fk_scenarios_list(self) -> List[str]:
        return list(HMI_FK_SCENARIOS_MAP.values())

    def get_led_config(self, number: int) -> Optional[LedConfig]:
        if not 1 <= number <= 16:
            return None
            
        key = f"Светодиод {number}"
        raw_scenario = self.hmi_led_scenarios.get(key, 1)
        raw_mode = self.hmi_led_modes.get(key, 1)
        
        scenario_str = HMI_LED_SCENARIOS_MAP.get(raw_scenario, "Неизвестно")
        mode_str = HMI_LED_MODES_MAP.get(raw_mode, "Неизвестно")
        
        linked_param = self._find_parameter_by_led(key)
        
        return LedConfig(
            number=number,
            scenario_name=scenario_str,
            mode_name=mode_str,
            linked_parameter=linked_param
        )

    def get_fk_config(self, number: int) -> Optional[FkConfig]:
        if not 1 <= number <= 16:
            return None
            
        key = f"Функциональная кнопка {number}"
        raw_scenario = self.hmi_fk_scenarios.get(key, 0)
        scenario_str = HMI_FK_SCENARIOS_MAP.get(raw_scenario, "Неизвестно")
        
        linked_param = self._find_parameter_by_fk(key)
        
        return FkConfig(
            number=number,
            scenario_name=scenario_str,
            linked_parameter=linked_param
        )

    def get_available_parameters(self) -> List[str]:
        params = set()
        for mapping in self.hmi_mappings:
            p_name = mapping.get("ParameterName")
            if p_name:
                params.add(p_name)
        return sorted(list(params))

    # --- Сеттеры и Логика Привязки ---

    def update_led_settings(self, number: int, scenario_name: str, mode_name: str) -> int:
        if not 1 <= number <= 16:
            return 1
        if scenario_name not in HMI_LED_SCENARIOS_REVERSE:
            return 1
        if mode_name not in HMI_LED_MODES_REVERSE:
            return 1
            
        key = f"Светодиод {number}"
        self.hmi_led_scenarios[key] = HMI_LED_SCENARIOS_REVERSE[scenario_name]
        self.hmi_led_modes[key] = HMI_LED_MODES_REVERSE[mode_name]
        return 0

    def update_fk_settings(self, number: int, scenario_name: str) -> int:
        if not 1 <= number <= 16:
            return 1
        if scenario_name not in HMI_FK_SCENARIOS_REVERSE:
            return 1
            
        key = f"Функциональная кнопка {number}"
        self.hmi_fk_scenarios[key] = HMI_FK_SCENARIOS_REVERSE[scenario_name]
        return 0

    def link_parameter_to_led(self, number: int, parameter_name: str) -> bool:
        if not 1 <= number <= 16:
            return False
        
        target_led = f"Светодиод {number}"
        
        if self.meta_handler and parameter_name:
            if not self.meta_handler.get_param_info(parameter_name):
                return False

        self._remove_led_from_all_mappings(target_led)

        if not parameter_name:
            self.clean_mappings()
            return True

        existing_mapping = next((m for m in self.hmi_mappings if m["ParameterName"] == parameter_name), None)
        
        if existing_mapping:
            if target_led not in existing_mapping["Leds"]:
                existing_mapping["Leds"].append(target_led)
        else:
            new_mapping = {
                "ParameterName": parameter_name,
                "Buttons": [],
                "FunctionButtons": [],
                "Leds": [target_led]
            }
            self.hmi_mappings.append(new_mapping)
            
        return True

    def link_parameter_to_fk(self, number: int, parameter_name: str) -> bool:
        if not 1 <= number <= 16:
            return False
            
        target_fk = f"Функциональная кнопка {number}"
        
        if self.meta_handler and parameter_name:
            if not self.meta_handler.get_param_info(parameter_name):
                return False

        self._remove_fk_from_all_mappings(target_fk)

        if not parameter_name:
            self.clean_mappings()
            return True

        existing_mapping = next((m for m in self.hmi_mappings if m["ParameterName"] == parameter_name), None)
        
        if existing_mapping:
            if target_fk not in existing_mapping["FunctionButtons"]:
                existing_mapping["FunctionButtons"].append(target_fk)
        else:
            new_mapping = {
                "ParameterName": parameter_name,
                "Buttons": [],
                "FunctionButtons": [target_fk],
                "Leds": []
            }
            self.hmi_mappings.append(new_mapping)
            
        return True

    # --- Внутренние методы очистки связей ---

    def _remove_led_from_all_mappings(self, led_name: str):
        for mapping in self.hmi_mappings:
            if led_name in mapping.get("Leds", []):
                mapping["Leds"].remove(led_name)

    def _remove_fk_from_all_mappings(self, fk_name: str):
        for mapping in self.hmi_mappings:
            if fk_name in mapping.get("FunctionButtons", []):
                mapping["FunctionButtons"].remove(fk_name)

    def _find_parameter_by_led(self, led_name: str) -> Optional[str]:
        for mapping in self.hmi_mappings:
            if led_name in mapping.get("Leds", []):
                return mapping.get("ParameterName")
        return None

    def _find_parameter_by_fk(self, fk_name: str) -> Optional[str]:
        for mapping in self.hmi_mappings:
            if fk_name in mapping.get("FunctionButtons", []):
                return mapping.get("ParameterName")
        return None

    def set_device_model(self, model_string: str):
        self.device_model = model_string
        
    def get_device_model(self) -> str:
        return self.device_model
    


    def _find_leds_by_parameter(self, parameter_name: str) -> Optional[List[str]]:
        """Найти список LED по имени параметра"""
        for mapping in self.hmi_mappings:
            if mapping.get("ParameterName") == parameter_name:
                return mapping.get("Leds", [])
        return None

    def _find_fk_buttons_by_parameter(self, parameter_name: str) -> Optional[List[str]]:
        """Найти список FunctionButtons по имени параметра"""
        #print(self.hmi_mappings)
        for mapping in self.hmi_mappings:
            if mapping.get("ParameterName") == parameter_name:
                return mapping.get("FunctionButtons", [])
        return None

    def _find_fk_buttons_by_parameter2(self, parameter_name: str) -> Optional[List[str]]:
        """Найти список FunctionButtons по имени параметра"""
        print(f"Searching for: {parameter_name}")
        print(self.hmi_mappings)
        
        # Преобразование: убираем DI_ и заменяем GS на GC
        search_parameter = parameter_name.replace("DI_", "").replace("GS", "GC")
        print(f"Search parameter transformed to: {search_parameter}")
        
        for mapping in self.hmi_mappings:
            param_in_mapping = mapping.get("ParameterName", "")
            # Используем startswith для поиска
            if param_in_mapping.startswith(search_parameter):
                result = mapping.get("FunctionButtons", [])
                print(f"Found: {param_in_mapping} -> {result}")
                return result
        
        print(f"No mapping found for {search_parameter}")
        return []  # ВОЗВРАЩАЕМ ПУСТОЙ СПИСОК, А НЕ None!