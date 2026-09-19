"""
ProxMaster Ultimate - Ядро приложения
Полноценное GUI приложение для управления Proxmark3 Easy/Iceman
Версия: 1.0.0
"""

import json
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RiskLevel(Enum):
    """Уровни риска операций"""
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"


class LogLevel(Enum):
    """Уровни логирования"""
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CommandParameter:
    """Параметр команды"""
    name: str
    param_type: str  # string, integer, hex, choice, boolean, float
    required: bool = True
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    choices: Optional[List[str]] = None
    default: Optional[Any] = None
    description: str = ""
    length: Optional[int] = None  # Для hex строк


@dataclass
class Command:
    """Команда Proxmark3"""
    id: str
    category: str
    name: str
    description: str
    template: str
    risk_level: RiskLevel
    timeout: int
    parameters: List[CommandParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)
    output_format: str = ""
    deprecated: bool = False
    aliases: List[str] = field(default_factory=list)


@dataclass
class LogEntry:
    """Запись лога"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = ""
    data: Optional[Any] = None


class CommandManager:
    """Менеджер команд Proxmark3"""
    
    def __init__(self, commands_file: str):
        self.commands: Dict[str, Command] = {}
        self.categories: Dict[str, dict] = {}
        self.metadata: dict = {}
        self.load_commands(commands_file)
    
    def load_commands(self, filepath: str) -> bool:
        """Загрузка команд из JSON файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('metadata', {})
            
            # Загрузка категорий
            for cat in data.get('categories', []):
                self.categories[cat['id']] = cat
            
            # Загрузка команд
            for cmd_data in data.get('commands', []):
                cmd = self._parse_command(cmd_data)
                if cmd:
                    self.commands[cmd.id] = cmd
                    # Добавляем алиасы
                    for alias in cmd.aliases:
                        self.commands[alias] = cmd
            
            logging.info(f"Загружено {len(self.commands)} команд из {len(self.categories)} категорий")
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки команд: {e}")
            return False
    
    def _parse_command(self, data: dict) -> Optional[Command]:
        """Парсинг данных команды"""
        try:
            params = []
            for p in data.get('parameters', []):
                param = CommandParameter(
                    name=p.get('name', ''),
                    param_type=p.get('type', 'string'),
                    required=p.get('required', True),
                    min_value=p.get('min'),
                    max_value=p.get('max'),
                    choices=p.get('choices'),
                    default=p.get('default'),
                    description=p.get('description', ''),
                    length=p.get('length')
                )
                params.append(param)
            
            risk = RiskLevel(data.get('risk_level', 'safe'))
            
            return Command(
                id=data.get('id', ''),
                category=data.get('category', ''),
                name=data.get('name', ''),
                description=data.get('description', ''),
                template=data.get('template', ''),
                risk_level=risk,
                timeout=data.get('timeout', 5000),
                parameters=params,
                examples=data.get('examples', []),
                tips=data.get('tips', []),
                output_format=data.get('output_format', ''),
                deprecated=data.get('deprecated', False),
                aliases=data.get('aliases', [])
            )
        except Exception as e:
            logging.error(f"Ошибка парсинга команды: {e}")
            return None
    
    def get_command(self, cmd_id: str) -> Optional[Command]:
        """Получение команды по ID"""
        return self.commands.get(cmd_id)
    
    def get_commands_by_category(self, category: str) -> List[Command]:
        """Получение всех команд категории"""
        return [cmd for cmd in self.commands.values() 
                if cmd.category == category and not cmd.deprecated]
    
    def search_commands(self, query: str) -> List[Command]:
        """Поиск команд по запросу"""
        query = query.lower()
        results = []
        for cmd in self.commands.values():
            if (query in cmd.id.lower() or 
                query in cmd.name.lower() or 
                query in cmd.description.lower()):
                results.append(cmd)
        return results
    
    def build_command(self, cmd_id: str, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """Построение команды для выполнения
        
        Returns:
            Tuple[команда, ошибка]
        """
        cmd = self.get_command(cmd_id)
        if not cmd:
            return None, f"Команда {cmd_id} не найдена"
        
        command_str = cmd.template
        
        # Проверка и подстановка параметров
        for param in cmd.parameters:
            value = kwargs.get(param.name)
            
            # Проверка обязательности
            if value is None:
                if param.required:
                    return None, f"Обязательный параметр '{param.name}' не указан"
                value = param.default
            
            # Валидация типа
            if not self._validate_param(value, param):
                return None, f"Неверное значение параметра '{param.name}'"
            
            # Подстановка в шаблон
            command_str = command_str.replace(f"<{param.name}>", str(value))
        
        return command_str, None
    
    def _validate_param(self, value: Any, param: CommandParameter) -> bool:
        """Валидация параметра"""
        if value is None:
            return not param.required
        
        try:
            if param.param_type == 'integer':
                val = int(value)
                if param.min_value is not None and val < param.min_value:
                    return False
                if param.max_value is not None and val > param.max_value:
                    return False
            elif param.param_type == 'float':
                float(value)
            elif param.param_type == 'hex':
                # Удаление пробелов и 0x префикса
                hex_str = str(value).replace(' ', '').lower()
                if hex_str.startswith('0x'):
                    hex_str = hex_str[2:]
                # Проверка на valid hex
                int(hex_str, 16)
                # Проверка длины
                if param.length and len(hex_str) != param.length:
                    return False
            elif param.param_type == 'choice':
                if param.choices and str(value) not in param.choices:
                    return False
            elif param.param_type == 'boolean':
                if str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    def get_all_categories(self) -> List[dict]:
        """Получение всех категорий"""
        return list(self.categories.values())
    
    def get_statistics(self) -> dict:
        """Статистика по командам"""
        stats = {
            'total': len(self.commands),
            'by_category': {},
            'by_risk': {level.value: 0 for level in RiskLevel}
        }
        
        for cmd in self.commands.values():
            # По категориям
            cat_count = stats['by_category'].get(cmd.category, 0)
            stats['by_category'][cmd.category] = cat_count + 1
            
            # По риску
            stats['by_risk'][cmd.risk_level.value] += 1
        
        return stats


class CommunicationLayer:
    """Слой связи с устройством Proxmark3"""
    
    def __init__(self):
        self.connected = False
        self.device_info = {}
        self.serial_port = None
        self.timeout = 5000
        self._buffer = bytearray()
    
    def connect(self, port: str = None) -> Tuple[bool, str]:
        """Подключение к устройству"""
        try:
            # Попытка автоопределения порта
            if not port:
                port = self._auto_detect_port()
            
            if not port:
                return False, "Устройство Proxmark3 не найдено"
            
            # Здесь будет реальная реализация через pyserial
            # Для демонстрации просто эмулируем подключение
            self.connected = True
            self.serial_port = port
            self.device_info = {
                'port': port,
                'firmware': 'Proxmark3 Easy v1.0',
                'hardware': 'RDV4.0',
                'bootloader': 'v1.5'
            }
            
            return True, f"Подключено к {port}"
        except Exception as e:
            return False, f"Ошибка подключения: {e}"
    
    def disconnect(self) -> bool:
        """Отключение от устройства"""
        try:
            self.connected = False
            self.serial_port = None
            self.device_info = {}
            return True
        except Exception:
            return False
    
    def _auto_detect_port(self) -> Optional[str]:
        """Автоопределение порта Proxmark3"""
        # В реальной реализации сканируем COM порты
        # Для Windows: COM3, COM4, etc.
        # Для Linux: /dev/ttyACM0, /dev/ttyUSB0, etc.
        return "COM3"  # Заглушка для демонстрации
    
    def send_command(self, command: str, timeout: int = None) -> Tuple[bool, str]:
        """Отправка команды устройству"""
        if not self.connected:
            return False, "Устройство не подключено"
        
        try:
            if timeout is None:
                timeout = self.timeout
            
            # Эмуляция отправки команды
            # В реальности: self.serial.write((command + '\n').encode())
            
            start_time = time.time()
            
            # Эмуляция ответа (в реальности читаем из serial)
            response = self._simulate_response(command)
            
            elapsed = (time.time() - start_time) * 1000
            
            if elapsed > timeout:
                return False, "Превышен таймаут ожидания ответа"
            
            return True, response
        except Exception as e:
            return False, f"Ошибка отправки команды: {e}"
    
    def _simulate_response(self, command: str) -> str:
        """Эмуляция ответа устройства (для демонстрации)"""
        # В реальной реализации читаем ответ из serial порта
        cmd_lower = command.lower()
        
        if 'search' in cmd_lower or 'scan' in cmd_lower:
            return """
[+] Searching for ISO14443-A cards...
[+] Found card:
    UID: 12:34:56:78
   ATQA: 0044
    SAK: 08
    Type: Mifare Classic 1K
[+] Done in 1.2s
"""
        elif 'version' in cmd_lower or 'hw version' in cmd_lower:
            return """
[+] Proxmark3 Easy
    Firmware: Iceman v4.12345
    Hardware: RDV4.0
    Bootloader: v1.5
    FPGA: bitstream loaded
    Chip: AT91SAM7S512
"""
        elif 'read' in cmd_lower or 'dump' in cmd_lower:
            return """
[+] Reading sector 0...
[+] Key A: ffffffffffff
[+] Key B: ffffffffffff
[+] Block 0:  12 34 56 78 00 00 00 00 00 00 00 00 00 00 00 00
[+] Block 1:  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
[+] Block 2:  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
[+] Block 3:  ff ff ff ff ff ff ff 07 80 69 ff ff ff ff ff ff
[+] Done
"""
        elif 'ping' in cmd_lower:
            return "[+] Pong! Device is alive"
        elif 'status' in cmd_lower:
            return """
[+] Device Status:
    USB: connected
    Button: not pressed
    LED: green
    Antenna: HF on
    Temperature: 35C
"""
        else:
            return f"[+] Executed: {command}\n[+] Done"
    
    def read_data(self, timeout: int = None) -> str:
        """Чтение данных из устройства"""
        if not self.connected:
            return ""
        
        try:
            # В реальности читаем из serial
            # data = self.serial.read_all()
            return ""
        except Exception:
            return ""
    
    def write_data(self, data: bytes) -> bool:
        """Запись данных в устройство"""
        if not self.connected:
            return False
        
        try:
            # В реальности пишем в serial
            # self.serial.write(data)
            return True
        except Exception:
            return False
    
    def get_device_info(self) -> dict:
        """Получение информации об устройстве"""
        return self.device_info.copy()
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.connected


class DataManager:
    """Менеджер данных приложения"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.base_path = Path(base_path)
        self.data_path = self.base_path / 'data'
        self.user_data_path = self.data_path / 'user_data'
        self.dumps_path = self.user_data_path / 'dumps'
        self.keys_path = self.user_data_path / 'keys'
        self.logs_path = self.user_data_path / 'logs'
        self.nodes_path = self.base_path / 'nodes'
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        for path in [self.data_path, self.user_data_path, 
                     self.dumps_path, self.keys_path, 
                     self.logs_path, self.nodes_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def save_dump(self, filename: str, data: bytes) -> bool:
        """Сохранение дампа карты"""
        try:
            filepath = self.dumps_path / filename
            with open(filepath, 'wb') as f:
                f.write(data)
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения дампа: {e}")
            return False
    
    def load_dump(self, filename: str) -> Optional[bytes]:
        """Загрузка дампа карты"""
        try:
            filepath = self.dumps_path / filename
            if filepath.exists():
                with open(filepath, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            logging.error(f"Ошибка загрузки дампа: {e}")
            return None
    
    def list_dumps(self) -> List[str]:
        """Список сохраненных дампов"""
        return [f.name for f in self.dumps_path.iterdir() if f.is_file()]
    
    def save_keys(self, filename: str, keys: List[bytes]) -> bool:
        """Сохранение ключей"""
        try:
            filepath = self.keys_path / filename
            with open(filepath, 'wb') as f:
                for key in keys:
                    f.write(key)
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения ключей: {e}")
            return False
    
    def load_keys(self, filename: str) -> Optional[List[bytes]]:
        """Загрузка ключей"""
        try:
            filepath = self.keys_path / filename
            if filepath.exists():
                with open(filepath, 'rb') as f:
                    data = f.read()
                # Разбиваем на ключи по 6 байт
                return [data[i:i+6] for i in range(0, len(data), 6)]
            return None
        except Exception as e:
            logging.error(f"Ошибка загрузки ключей: {e}")
            return None
    
    def save_log(self, log_entries: List[LogEntry], filename: str = None) -> str:
        """Сохранение лога в файл"""
        if filename is None:
            filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            filepath = self.logs_path / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in log_entries:
                    f.write(f"[{entry.timestamp.strftime('%H:%M:%S')}] ")
                    f.write(f"[{entry.level.value.upper()}] ")
                    f.write(f"{entry.message}\n")
            return str(filepath)
        except Exception as e:
            logging.error(f"Ошибка сохранения лога: {e}")
            return ""
    
    def save_node_graph(self, name: str, graph_data: dict) -> bool:
        """Сохранение графа нод"""
        try:
            filepath = self.nodes_path / f"{name}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения графа: {e}")
            return False
    
    def load_node_graph(self, name: str) -> Optional[dict]:
        """Загрузка графа нод"""
        try:
            filepath = self.nodes_path / f"{name}.json"
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logging.error(f"Ошибка загрузки графа: {e}")
            return None
    
    def list_node_graphs(self) -> List[str]:
        """Список сохраненных графов"""
        return [f.stem for f in self.nodes_path.iterdir() 
                if f.is_file() and f.suffix == '.json']
    
    def get_config_path(self) -> Path:
        """Путь к файлу конфигурации"""
        return self.base_path / 'config.json'
    
    def save_config(self, config: dict) -> bool:
        """Сохранение конфигурации"""
        try:
            with open(self.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения конфига: {e}")
            return False
    
    def load_config(self) -> dict:
        """Загрузка конфигурации"""
        try:
            if self.get_config_path().exists():
                with open(self.get_config_path(), 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки конфига: {e}")
        return {}


class Logger:
    """Система логирования приложения"""
    
    def __init__(self):
        self.entries: List[LogEntry] = []
        self.callbacks: List[callable] = []
        self.max_entries = 10000
    
    def add_callback(self, callback: callable):
        """Добавление колбэка для новых записей лога"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: callable):
        """Удаление колбэка"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def log(self, level: LogLevel, message: str, source: str = "", data: Any = None):
        """Добавление записи лога"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            source=source,
            data=data
        )
        
        self.entries.append(entry)
        
        # Ограничение размера лога
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        
        # Уведомление колбэков
        for callback in self.callbacks:
            try:
                callback(entry)
            except Exception:
                pass
    
    def debug(self, message: str, source: str = ""):
        self.log(LogLevel.DEBUG, message, source)
    
    def info(self, message: str, source: str = ""):
        self.log(LogLevel.INFO, message, source)
    
    def success(self, message: str, source: str = ""):
        self.log(LogLevel.SUCCESS, message, source)
    
    def warning(self, message: str, source: str = ""):
        self.log(LogLevel.WARNING, message, source)
    
    def error(self, message: str, source: str = ""):
        self.log(LogLevel.ERROR, message, source)
    
    def clear(self):
        """Очистка лога"""
        self.entries.clear()
    
    def get_entries(self, level: LogLevel = None, limit: int = None) -> List[LogEntry]:
        """Получение записей лога"""
        entries = self.entries
        
        if level:
            entries = [e for e in entries if e.level == level]
        
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def export_to_file(self, filepath: str) -> bool:
        """Экспорт лога в файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self.entries:
                    f.write(f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ")
                    f.write(f"[{entry.level.value.upper():7}] ")
                    if entry.source:
                        f.write(f"[{entry.source}] ")
                    f.write(f"{entry.message}\n")
            return True
        except Exception as e:
            logging.error(f"Ошибка экспорта лога: {e}")
            return False


# Глобальные экземпляры
_command_manager: Optional[CommandManager] = None
_communication: Optional[CommunicationLayer] = None
_data_manager: Optional[DataManager] = None
_logger: Optional[Logger] = None


def initialize_app(base_path: str = None) -> bool:
    """Инициализация приложения"""
    global _command_manager, _communication, _data_manager, _logger
    
    try:
        # Инициализация менеджера данных
        _data_manager = DataManager(base_path)
        
        # Инициализация логгера
        _logger = Logger()
        _logger.info("Приложение запущено", "System")
        
        # Инициализация менеджера команд
        commands_file = _data_manager.data_path / 'commands.json'
        _command_manager = CommandManager(str(commands_file))
        
        # Инициализация слоя связи
        _communication = CommunicationLayer()
        
        _logger.success("Все компоненты инициализированы", "System")
        return True
    except Exception as e:
        if _logger:
            _logger.error(f"Ошибка инициализации: {e}", "System")
        return False


def get_command_manager() -> CommandManager:
    """Получение менеджера команд"""
    return _command_manager


def get_communication() -> CommunicationLayer:
    """Получение слоя связи"""
    return _communication


def get_data_manager() -> DataManager:
    """Получение менеджера данных"""
    return _data_manager


def get_logger() -> Logger:
    """Получение логгера"""
    return _logger
