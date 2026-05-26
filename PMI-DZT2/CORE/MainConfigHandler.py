import json
from typing import List, Dict, Optional, Any


class MainConfigHandler:
    def __init__(self, metadata_data: Dict[str, Any]):
        self.config_version = metadata_data.get("ConfigurationVersion")
        self.model_version = metadata_data.get("ModelPackageVersion")
        self.model_regex = metadata_data.get("ModelRegex")
        # Создаем словарь параметров для быстрого доступа по имени
        self._params = {p["name"]: p for p in metadata_data.get("Parameters", [])}

    @classmethod
    def from_json_file(cls, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def get_param_info(self, name: str) -> Optional[Dict[str, Any]]:
        return self._params.get(name)

    def is_readonly(self, name: str) -> bool:
        info = self.get_param_info(name)
        return info.get("readonly", True) if info else True

    def is_command(self, name: str) -> bool:
        info = self.get_param_info(name)
        return info.get("command", False) if info else False

    def get_group(self, name: str) -> Optional[str]:
        info = self.get_param_info(name)
        return info.get("group") if info else None

    def validate_value(self, name: str, value: str) -> bool:
        info = self.get_param_info(name)
        if not info:
            return False
        try:
            val = int(value)
        except (ValueError, TypeError):
            return False
        min_val = info.get("minValue")
        max_val = info.get("maxValue")
        if min_val is not None and val < int(min_val):
            return False
        if max_val is not None and val > int(max_val):
            return False
        return True

    def get_first_parameter_name_by_description(self, description: str, use_full: bool = False) -> Optional[str]:
        target_key = "fullDescription" if use_full else "description"
        for name, param in self._params.items():
            if param.get(target_key) == description:
                return name
        return None

    def get_first_parameter_name_by_applied_description(self, description: str) -> Optional[str]:
        target_key = "appliedDescription"
        for name, param in self._params.items():
            if param.get(target_key) == description:
                return name
        return None


    def find_parameter_names_by_description_substring(self, substring: str, use_full: bool = False) -> List[str]:
        target_key = "fullDescription" if use_full else "description"
        matches = []
        for name, param in self._params.items():
            desc = param.get(target_key, "")
            if substring in desc:
                matches.append(name)
        return matches

    def find_parameter_names_by_description(self, description: str, use_full: bool = False) -> List[str]:
        target_key = "fullDescription" if use_full else "description"
        matches = []
        for name, param in self._params.items():
            if param.get(target_key) == description:
                matches.append(name)
        return matches

    def find_parameters_by_rus_name(self, partial_description: str) -> List[str]:
        matches = []
        for name, param in self._params.items():
            desc = param.get("description", "")
            base_desc = desc.split('_', 1)[0]
            if base_desc == partial_description:
                matches.append(name)
        return matches

    def find_parameter_name_by_rus_name_and_full_desc_in_settings(
        self,
        rus_name: str = "",
        full_desc: str = "",
        setting_group: int = 0
    ) -> List[str]:
        matches = []
        target_suffix = f"_SG{setting_group}" if setting_group in (1, 2, 3, 4) else None
        for name, param in self._params.items():
            if target_suffix and not name.endswith(target_suffix):
                continue
            desc_ok = True
            if rus_name:
                base_desc = param.get("description", "").split('_', 1)[0]
                desc_ok = (base_desc == rus_name)
            full_ok = True
            if full_desc:
                base_full = param.get("fullDescription", "").split('_', 1)[0]
                full_ok = (base_full == full_desc)
            if desc_ok and full_ok:
                matches.append(name)
        return matches

    def get_description_by_base_name(self, base_name: str) -> Optional[str]:
        for i in range(1, 6):
            full_name = f"{base_name}_SG{i}"
            param = self._params.get(full_name)
            if param and "description" in param:
                return param["description"]
        param = self._params.get(base_name)
        if param and "description" in param:
            return param["description"]
        return None
    
    def find_measurement_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает параметр с указанным именем, только если он принадлежит группе 'measurement'.
        Если параметр не найден или его группа не 'measurement' — возвращает None.
        """
        param = self._params.get(name)
        if param and param.get("group") == "measurement":
            return param
        return None
    
    def get_applied_description(self, name: str) -> str:
        """
        Возвращает значение поля 'appliedDescription' для параметра.
        Если поле отсутствует или пустое — возвращает description.
        Если и description нет — возвращает имя параметра.
        """
        info = self.get_param_info(name)
        if not info:
            return name
        
        applied = info.get("appliedDescription")
        if applied:
            return applied
        
        description = info.get("description")
        if description:
            return description
        
        return name
    
    def find_parameters_starting_with(self, prefix: str) -> List[Dict[str, Any]]:
        """Находит параметры, имя которых начинается с заданного префикса"""
        matches = []
        for name, param in self._params.items():
            if name.startswith(prefix):
                matches.append(param)
        return matches
    
    def find_parameters_ending_with(self, suffix: str) -> List[Dict[str, Any]]:
        """Находит параметры, имя которых заканчивается заданным суффиксом"""
        matches = []
        for name, param in self._params.items():
            if name.endswith(suffix):
                matches.append(param)
        return matches

    def get_valid_led_parameters(self) -> List[str]:
        """
        Возвращает список имен параметров, подходящих для привязки к светодиодам.
        Правила фильтрации:
        1. group == 'measurement' (исключаем уставки/settings)
        2. size == 1 (только булевы/двоичные сигналы)
        3. appliedDescription содержит символ '/' (исключаем простые входные сигналы)
        """
        valid_names = []
        
        for name, param in self._params.items():
            # 1. Проверка группы
            if param.get("group") != "measurement":
                continue
            
            # 2. Проверка размера (должен быть 1 для бинарного сигнала)
            try:
                size = int(param.get("size", 0))
            except (ValueError, TypeError):
                continue
                
            if size != 1:
                continue
            
            # 3. Проверка наличия '/' в appliedDescription
            applied_desc = self.get_applied_description(name)
            
            if "/" not in applied_desc:
                continue
            if "_" in applied_desc:
                continue
            if "ДВ:" in applied_desc or "ФК:" in applied_desc or "GOOSE" in applied_desc or "ИЧМ:" in applied_desc:
                continue

            valid_names.append(name)
            
        return valid_names