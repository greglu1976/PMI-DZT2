# RegistrationHandler.py

import json
from typing import Dict, List, Optional, Any


class RegistrationHandler:
    def __init__(self, data: Dict[str, Any]):
        self.version: str = data.get("Version", "")
        self.device_model: str = data.get("DeviceModel", "")
        # Создаём словарь по имени параметра для быстрого доступа
        self._mappings: Dict[str, Dict[str, Any]] = {
            item["ParameterName"]: item for item in data.get("RegistrationMappings", [])
        }

    @classmethod
    def from_json_file(cls, filepath: str) -> "RegistrationHandler":
        """Загружает данные из JSON-файла."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def get_mapping(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Возвращает запись маппинга по имени параметра или None, если не найдено."""
        return self._mappings.get(parameter_name)

    def get_need_write_to_oscillogram(self, parameter_name: str) -> bool:
        """Возвращает флаг NeedWriteToOscillogram для параметра."""
        mapping = self.get_mapping(parameter_name)
        return bool(mapping.get("NeedWriteToOscillogram", False)) if mapping else False

    def get_registration_condition(self, parameter_name: str) -> int:
        """Возвращает RegistrationCondition (целое число)."""
        mapping = self.get_mapping(parameter_name)
        return int(mapping.get("RegistrationCondition", 0)) if mapping else 0

    def get_start_oscillography_condition(self, parameter_name: str) -> int:
        """Возвращает StartOscillographyCondition (целое число)."""
        mapping = self.get_mapping(parameter_name)
        return int(mapping.get("StartOscillographyCondition", 0)) if mapping else 0

    def update_mapping(
        self,
        parameter_name: str,
        need_write: bool,
        reg_condition: int,
        start_condition: int
    ):
        """Обновляет или добавляет запись для параметра."""
        if parameter_name not in self._mappings:
            # Если параметр новый — создаём базовую запись
            self._mappings[parameter_name] = {"ParameterName": parameter_name}
        self._mappings[parameter_name].update({
            "NeedWriteToOscillogram": need_write,
            "RegistrationCondition": reg_condition,
            "StartOscillographyCondition": start_condition
        })

    def save_to_json_file(self, filepath: str):
        """Сохраняет данные обратно в JSON-файл в исходном формате."""
        data = {
            "Version": self.version,
            "DeviceModel": self.device_model,
            "RegistrationMappings": list(self._mappings.values())
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all_parameter_names(self) -> List[str]:
        """Возвращает список всех имён параметров."""
        return list(self._mappings.keys())

    def get_device_info(self) -> Dict[str, str]:
        """Возвращает информацию об устройстве."""
        return {
            "Version": self.version,
            "DeviceModel": self.device_model
        }