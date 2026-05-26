# InOutsMatrixHandler.py

import json
from typing import List, Dict, Optional, Any


class InOutsMatrixHandler:
    def __init__(self, data: Dict[str, Any]):
        self.version: str = data.get("Version", "")
        self.device_model: str = data.get("DeviceModel", "")
        # Создаём словарь для быстрого поиска по имени параметра
        self._mappings: Dict[str, Dict[str, Any]] = {
            item["ParameterName"]: item for item in data.get("SignalMappings", [])
        }

    @classmethod
    def from_json_file(cls, filepath: str) -> "InOutsMatrixHandler":
        """Загружает данные из JSON-файла."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def get_mapping(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Возвращает полную запись маппинга по имени параметра или None, если не найдено."""
        return self._mappings.get(parameter_name)

    def get_discrete_inputs(self, parameter_name: str) -> List[str]:
        """Возвращает список DiscreteInputs для заданного параметра."""
        mapping = self.get_mapping(parameter_name)
        if mapping:
            return mapping.get("DiscreteInputs", [])
        return []

    def get_digital_inputs(self, parameter_name: str) -> List[str]:
        """Возвращает список DigitalInputs для заданного параметра."""
        mapping = self.get_mapping(parameter_name)
        if mapping:
            return mapping.get("DigitalInputs", [])
        return []

    def get_output_relays(self, parameter_name: str) -> List[str]:
        """Возвращает список OutputRelays для заданного параметра."""
        mapping = self.get_mapping(parameter_name)
        if mapping:
            return mapping.get("OutputRelays", [])
        return []

    def has_discrete_input(self, parameter_name: str) -> bool:
        """Проверяет, есть ли у параметра хотя бы один DiscreteInput."""
        return len(self.get_discrete_inputs(parameter_name)) > 0

    def has_output_relay(self, parameter_name: str) -> bool:
        """Проверяет, есть ли у параметра хотя бы один OutputRelay."""
        return len(self.get_output_relays(parameter_name)) > 0

    def find_parameters_by_discrete_input(self, address: str) -> List[str]:
        """Находит все параметры, использующие указанный DiscreteInput (например, '8B2')."""
        result = []
        for name, mapping in self._mappings.items():
            if address in mapping.get("DiscreteInputs", []):
                result.append(name)
        return result

    def find_parameters_by_output_relay(self, relay: str) -> List[str]:
        """Находит все параметры, использующие указанный OutputRelay (например, '3K1')."""
        result = []
        for name, mapping in self._mappings.items():
            if relay in mapping.get("OutputRelays", []):
                result.append(name)
        return result

    def get_all_parameter_names(self) -> List[str]:
        """Возвращает список всех имён параметров."""
        return list(self._mappings.keys())

    def get_device_info(self) -> Dict[str, str]:
        """Возвращает информацию об устройстве: версию и модель."""
        return {
            "Version": self.version,
            "DeviceModel": self.device_model
        }
    
    # InOutsMatrixHandler.py — дополнение

    def update_signal_mapping(
        self,
        parameter_name: str,
        discrete_inputs: List[str],
        digital_inputs: List[str],
        output_relays: List[str]
    ):
        """Обновляет маппинг сигнала для указанного параметра."""
        if parameter_name not in self._mappings:
            raise KeyError(f"Parameter '{parameter_name}' not found in mappings.")
        
        self._mappings[parameter_name]["DiscreteInputs"] = discrete_inputs
        self._mappings[parameter_name]["DigitalInputs"] = digital_inputs
        self._mappings[parameter_name]["OutputRelays"] = output_relays


    def save_to_json_file(self, filepath: str):
        """Сохраняет текущие данные обратно в JSON-файл в исходном формате."""
        data = {
            "Version": self.version,
            "DeviceModel": self.device_model,
            "SignalMappings": list(self._mappings.values())
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)