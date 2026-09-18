"""
ProxMaster Ultimate - Core Module
Основной модуль ядра приложения для управления Proxmark3
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """Уровни риска операций"""
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"
    VARIABLE = "variable"


class ConnectionStatus(Enum):
    """Статусы подключения к устройству"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class CommandParameter:
    """Параметр команды"""
    name: str
    type: str
    description: str
    default: Any = None
    required: bool = False
    min: Optional[float] = None
    max: Optional[float] = None
    options: Optional[List[str]] = None
    pattern: Optional[str] = None


@dataclass
class CommandDefinition:
    """Определение команды из JSON"""
    id: str
    category: str
    name: str
    description: str
    command_template: str
    risk_level: RiskLevel
    timeout: int
    icon: str
    parameters: List[CommandParameter]
    output_format: str
    help_text: str


@dataclass
class DeviceInfo:
    """Информация об устройстве"""
    model: str = ""
    firmware_version: str = ""
    fpga_version: str = ""
    serial_number: str = ""
    build_date: str = ""
    is_connected: bool = False
    connection_type: str = ""


@dataclass
class LogEntry:
    """Запись в логе"""
    timestamp: datetime
    level: str
    message: str
    source: str = ""
    data: Optional[Dict] = None


class CommandManager:
    """Менеджер команд - загрузка и управление командами из JSON"""
    
    def __init__(self, commands_file: Path):
        self.commands_file = commands_file
        self.commands: Dict[str, CommandDefinition] = {}
        self.categories: Dict[str, Dict] = {}
        self.risk_levels: Dict[str, Dict] = {}
        self._load_commands()
    
    def _load_commands(self):
        """Загрузка команд из JSON файла"""
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Загрузка категорий
            for cat_id, cat_data in data.get('categories', {}).items():
                self.categories[cat_id] = cat_data
            
            # Загрузка уровней риска
            for risk_id, risk_data in data.get('risk_levels', {}).items():
                self.risk_levels[risk_id] = risk_data
            
            # Загрузка команд
            for cmd_data in data.get('commands', []):
                params = []
                for p in cmd_data.get('parameters', []):
                    param = CommandParameter(
                        name=p['name'],
                        type=p['type'],
                        description=p['description'],
                        default=p.get('default'),
                        required=p.get('required', False),
                        min=p.get('min'),
                        max=p.get('max'),
                        options=p.get('options'),
                        pattern=p.get('pattern')
                    )
                    params.append(param)
                
                cmd = CommandDefinition(
                    id=cmd_data['id'],
                    category=cmd_data['category'],
                    name=cmd_data['name'],
                    description=cmd_data['description'],
                    command_template=cmd_data['command_template'],
                    risk_level=RiskLevel(cmd_data['risk_level']),
                    timeout=cmd_data['timeout'],
                    icon=cmd_data['icon'],
                    parameters=params,
                    output_format=cmd_data['output_format'],
                    help_text=cmd_data['help_text']
                )
                self.commands[cmd.id] = cmd
            
            logging.info(f"Загружено {len(self.commands)} команд из {self.commands_file}")
        except Exception as e:
            logging.error(f"Ошибка загрузки команд: {e}")
            raise
    
    def get_command(self, cmd_id: str) -> Optional[CommandDefinition]:
        """Получить команду по ID"""
        return self.commands.get(cmd_id)
    
    def get_commands_by_category(self, category: str) -> List[CommandDefinition]:
        """Получить все команды категории"""
        return [cmd for cmd in self.commands.values() if cmd.category == category]
    
    def build_command(self, cmd_id: str, **kwargs) -> Optional[str]:
        """Построить полную команду из шаблона"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            return None
        
        command_str = cmd.command_template
        for key, value in kwargs.items():
            command_str = command_str.replace(f"{{{key}}}", str(value))
        
        return command_str
    
    def validate_parameters(self, cmd_id: str, params: Dict) -> tuple[bool, str]:
        """Валидация параметров команды"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            return False, "Команда не найдена"
        
        for param in cmd.parameters:
            if param.required and param.name not in params:
                return False, f"Обязательный параметр '{param.name}' отсутствует"
            
            if param.name in params:
                value = params[param.name]
                
                # Проверка типа
                if param.type == "integer":
                    try:
                        value = int(value)
                        if param.min is not None and value < param.min:
                            return False, f"Значение меньше минимума ({param.min})"
                        if param.max is not None and value > param.max:
                            return False, f"Значение больше максимума ({param.max})"
                    except ValueError:
                        return False, f"Параметр '{param.name}' должен быть числом"
                
                elif param.type == "hex_string":
                    import re
                    if param.pattern and not re.match(param.pattern, str(value)):
                        return False, f"Параметр '{param.name}' не соответствует формату"
                
                elif param.type == "select":
                    if value not in param.options:
                        return False, f"Недопустимое значение для '{param.name}'"
        
        return True, "OK"


class CommunicationLayer:
    """Слой коммуникации с устройством Proxmark3"""
    
    def __init__(self):
        self.status = ConnectionStatus.DISCONNECTED
        self.device_info = DeviceInfo()
        self.serial_port = None
        self.read_thread = None
        self.write_lock = threading.Lock()
        self.callbacks: List[Callable] = []
        self._stop_reading = False
        self.buffer = ""
        self.timeout = 30
        self.retry_attempts = 3
    
    def connect(self, port: str = None, baudrate: int = 115200) -> bool:
        """Подключение к устройству"""
        try:
            self.status = ConnectionStatus.CONNECTING
            logging.info(f"Попытка подключения к порту {port}...")
            
            # Здесь будет реальная реализация подключения через pyserial
            # Для демонстрации создаем фиктивное подключение
            self.device_info.is_connected = True
            self.device_info.connection_type = "usb"
            self.device_info.model = "Proxmark3 Easy"
            self.device_info.firmware_version = "v4.0+1"
            self.device_info.fpga_version = "FPGA test mode"
            self.device_info.build_date = "2024-01-01"
            
            self.status = ConnectionStatus.CONNECTED
            self._start_read_thread()
            logging.info("Успешное подключение к Proxmark3")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка подключения: {e}")
            self.status = ConnectionStatus.ERROR
            return False
    
    def disconnect(self):
        """Отключение от устройства"""
        try:
            self._stop_reading = True
            if self.read_thread:
                self.read_thread.join(timeout=2)
            
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            
            self.status = ConnectionStatus.DISCONNECTED
            self.device_info.is_connected = False
            logging.info("Отключено от устройства")
        except Exception as e:
            logging.error(f"Ошибка отключения: {e}")
    
    def _start_read_thread(self):
        """Запуск потока чтения"""
        self._stop_reading = False
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def _read_loop(self):
        """Цикл чтения данных из устройства"""
        while not self._stop_reading:
            try:
                if self.serial_port and self.serial_port.is_open:
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                        self.buffer += data
                        
                        # Обработка полных строк
                        while '\n' in self.buffer:
                            line, self.buffer = self.buffer.split('\n', 1)
                            self._notify_callbacks(line.strip())
                    
                    time.sleep(0.01)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Ошибка чтения: {e}")
                time.sleep(0.1)
    
    def send_command(self, command: str, timeout: int = None) -> str:
        """Отправка команды устройству"""
        if self.status != ConnectionStatus.CONNECTED:
            return "Ошибка: Устройство не подключено"
        
        timeout = timeout or self.timeout
        result_lines = []
        
        with self.write_lock:
            try:
                # Отправка команды
                full_command = command + "\n"
                if self.serial_port:
                    self.serial_port.write(full_command.encode('utf-8'))
                
                # Ожидание ответа
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.serial_port and self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                        result_lines.append(line)
                        
                        # Проверка окончания вывода
                        if line.endswith("(pm3) >") or line.startswith("proxmark3>"):
                            break
                    
                    time.sleep(0.05)
                
                return "\n".join(result_lines)
                
            except Exception as e:
                logging.error(f"Ошибка отправки команды: {e}")
                return f"Ошибка: {str(e)}"
    
    def register_callback(self, callback: Callable):
        """Регистрация callback для получения данных"""
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Удаление callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, data: str):
        """Уведомление всех callback"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                logging.error(f"Ошибка в callback: {e}")
    
    def heartbeat(self) -> bool:
        """Проверка живости соединения"""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        
        try:
            response = self.send_command("hw version", timeout=5)
            return len(response) > 0
        except:
            return False


class DataManager:
    """Менеджер данных - работа с дампами, ключами, файлами"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.dumps_dir = data_dir / "dumps"
        self.keys_dir = data_dir / "keys"
        self.logs_dir = data_dir / "logs"
        self.traces_dir = data_dir / "traces"
        
        # Создание директорий
        for dir_path in [self.dumps_dir, self.keys_dir, self.logs_dir, self.traces_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.current_dump: Optional[bytes] = None
        self.current_keys: Dict[int, Dict[str, bytes]] = {}
    
    def save_dump(self, data: bytes, name: str = None) -> Path:
        """Сохранение дампа памяти"""
        if name is None:
            name = f"dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
        
        dump_path = self.dumps_dir / name
        with open(dump_path, 'wb') as f:
            f.write(data)
        
        logging.info(f"Дамп сохранен: {dump_path}")
        return dump_path
    
    def load_dump(self, path: Path) -> Optional[bytes]:
        """Загрузка дампа из файла"""
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.current_dump = data
            logging.info(f"Дамп загружен: {path} ({len(data)} байт)")
            return data
        except Exception as e:
            logging.error(f"Ошибка загрузки дампа: {e}")
            return None
    
    def save_keys(self, keys: Dict, name: str = None) -> Path:
        """Сохранение ключей"""
        if name is None:
            name = f"keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        keys_path = self.keys_dir / name
        
        # Конвертация байтов в hex строки для JSON
        keys_serializable = {}
        for block, key_data in keys.items():
            keys_serializable[str(block)] = {
                'key_a': key_data.get('key_a', b'').hex(),
                'key_b': key_data.get('key_b', b'').hex()
            }
        
        with open(keys_path, 'w', encoding='utf-8') as f:
            json.dump(keys_serializable, f, indent=2)
        
        logging.info(f"Ключи сохранены: {keys_path}")
        return keys_path
    
    def load_keys(self, path: Path) -> Optional[Dict]:
        """Загрузка ключей из файла"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                keys_serializable = json.load(f)
            
            # Конвертация hex строк обратно в байты
            keys = {}
            for block, key_data in keys_serializable.items():
                keys[int(block)] = {
                    'key_a': bytes.fromhex(key_data['key_a']) if key_data.get('key_a') else None,
                    'key_b': bytes.fromhex(key_data['key_b']) if key_data.get('key_b') else None
                }
            
            self.current_keys = keys
            logging.info(f"Ключи загружены: {path}")
            return keys
        except Exception as e:
            logging.error(f"Ошибка загрузки ключей: {e}")
            return None
    
    def add_log_entry(self, entry: LogEntry):
        """Добавление записи в лог"""
        log_file = self.logs_dir / f"log_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [{entry.level}] {entry.source}: {entry.message}\n")
    
    def export_trace(self, trace_data: List[Dict], name: str = None) -> Path:
        """Экспорт трассировки"""
        if name is None:
            name = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        trace_path = self.traces_dir / name
        with open(trace_path, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2)
        
        logging.info(f"Трассировка экспортирована: {trace_path}")
        return trace_path


class UpdateManager:
    """Менеджер обновлений приложения и прошивки"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.current_version = config.get('app_info', {}).get('version', '1.0.0')
        self.update_channel = config.get('update_settings', {}).get('current_channel', 'stable')
        self.available_updates: Dict = {}
        self.download_progress = 0
        self.is_downloading = False
    
    def check_for_updates(self) -> Dict:
        """Проверка доступных обновлений"""
        # Здесь будет реальная проверка на сервере
        updates = {
            'app_update_available': False,
            'firmware_update_available': False,
            'commands_update_available': False,
            'details': {}
        }
        
        # Симуляция проверки
        logging.info("Проверка обновлений...")
        
        return updates
    
    def download_update(self, update_type: str, callback: Callable = None) -> bool:
        """Загрузка обновления"""
        self.is_downloading = True
        self.download_progress = 0
        
        try:
            # Симуляция загрузки
            for i in range(100):
                self.download_progress = i + 1
                if callback:
                    callback(self.download_progress)
                time.sleep(0.05)
            
            self.is_downloading = False
            return True
        except Exception as e:
            logging.error(f"Ошибка загрузки обновления: {e}")
            self.is_downloading = False
            return False
    
    def install_update(self, update_type: str) -> bool:
        """Установка обновления"""
        try:
            logging.info(f"Установка обновления {update_type}...")
            # Здесь будет реальная логика установки
            return True
        except Exception as e:
            logging.error(f"Ошибка установки обновления: {e}")
            return False
    
    def check_firmware_version(self, device_info: DeviceInfo) -> Dict:
        """Проверка версии прошивки устройства"""
        latest_versions = {
            'Proxmark3 Easy': 'v4.0+1',
            'Proxmark3 Iceman': 'v4.0+2',
            'Proxmark3 RDV4': 'v4.0+3'
        }
        
        model = device_info.model
        current = device_info.firmware_version
        latest = latest_versions.get(model, 'unknown')
        
        return {
            'current_version': current,
            'latest_version': latest,
            'update_available': current < latest,
            'model': model
        }


class Logger:
    """Система логирования приложения"""
    
    def __init__(self, max_entries: int = 10000):
        self.entries: List[LogEntry] = []
        self.max_entries = max_entries
        self.listeners: List[Callable] = []
        self._lock = threading.Lock()
    
    def log(self, level: str, message: str, source: str = "", data: Dict = None):
        """Добавление записи в лог"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            source=source,
            data=data
        )
        
        with self._lock:
            self.entries.append(entry)
            
            # Удаление старых записей при превышении лимита
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
        
        # Уведомление слушателей
        for listener in self.listeners:
            try:
                listener(entry)
            except Exception as e:
                pass
    
    def info(self, message: str, source: str = ""):
        self.log("INFO", message, source)
    
    def warning(self, message: str, source: str = ""):
        self.log("WARNING", message, source)
    
    def error(self, message: str, source: str = ""):
        self.log("ERROR", message, source)
    
    def success(self, message: str, source: str = ""):
        self.log("SUCCESS", message, source)
    
    def debug(self, message: str, source: str = ""):
        self.log("DEBUG", message, source)
    
    def clear(self):
        """Очистка лога"""
        with self._lock:
            self.entries.clear()
    
    def get_entries(self, limit: int = None) -> List[LogEntry]:
        """Получение записей лога"""
        with self._lock:
            if limit:
                return self.entries[-limit:]
            return self.entries.copy()
    
    def add_listener(self, listener: Callable):
        """Добавление слушателя логов"""
        self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable):
        """Удаление слушателя"""
        if listener in self.listeners:
            self.listeners.remove(listener)


# Глобальный экземпляр ядра
class ProxMasterCore:
    """Основной класс ядра приложения"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        
        # Определение путей
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.config_file = self.base_dir / "config.json"
        
        # Загрузка конфигурации
        self.config = self._load_config()
        
        # Инициализация компонентов
        self.command_manager = CommandManager(self.data_dir / "commands.json")
        self.comm_layer = CommunicationLayer()
        self.data_manager = DataManager(self.data_dir.parent / "user_data")
        self.update_manager = UpdateManager(self.config)
        self.logger = Logger()
        
        # Состояние приложения
        self.is_running = False
        self.current_operation = None
        
        logging.info("ProxMaster Core инициализирован")
    
    def _load_config(self) -> Dict:
        """Загрузка конфигурации"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Не удалось загрузить конфиг, используем значения по умолчанию: {e}")
            return {
                'app_info': {'name': 'ProxMaster Ultimate', 'version': '1.0.0'},
                'device_settings': {'timeout_seconds': 30, 'baud_rate': 115200},
                'interface_settings': {'language': 'ru', 'theme': 'dark'}
            }
    
    def connect_device(self, port: str = None) -> bool:
        """Подключение к устройству"""
        baudrate = self.config.get('device_settings', {}).get('baud_rate', 115200)
        success = self.comm_layer.connect(port, baudrate)
        
        if success:
            self.logger.info("Устройство подключено", "Core")
        else:
            self.logger.error("Не удалось подключить устройство", "Core")
        
        return success
    
    def disconnect_device(self):
        """Отключение от устройства"""
        self.comm_layer.disconnect()
        self.logger.info("Устройство отключено", "Core")
    
    def execute_command(self, cmd_id: str, **params) -> str:
        """Выполнение команды"""
        cmd = self.command_manager.get_command(cmd_id)
        if not cmd:
            return f"Ошибка: Команда '{cmd_id}' не найдена"
        
        # Валидация параметров
        is_valid, msg = self.command_manager.validate_parameters(cmd_id, params)
        if not is_valid:
            return f"Ошибка валидации: {msg}"
        
        # Построение команды
        command_str = self.command_manager.build_command(cmd_id, **params)
        if not command_str:
            return "Ошибка построения команды"
        
        # Проверка уровня риска
        if cmd.risk_level == RiskLevel.DANGEROUS:
            self.logger.warning(f"Выполняется опасная операция: {cmd.name}", "Core")
        
        # Выполнение
        self.current_operation = cmd_id
        self.logger.info(f"Выполнение команды: {command_str}", "Core")
        
        timeout = cmd.timeout if cmd.timeout > 0 else self.config.get('device_settings', {}).get('timeout_seconds', 30)
        result = self.comm_layer.send_command(command_str, timeout)
        
        self.current_operation = None
        return result
    
    def execute_custom_command(self, command: str, timeout: int = 60) -> str:
        """Выполнение пользовательской команды"""
        self.logger.info(f"Пользовательская команда: {command}", "Core")
        return self.comm_layer.send_command(command, timeout)
    
    def get_device_info(self) -> DeviceInfo:
        """Получение информации об устройстве"""
        return self.comm_layer.device_info
    
    def get_connection_status(self) -> ConnectionStatus:
        """Получение статуса подключения"""
        return self.comm_layer.status
    
    def start(self):
        """Запуск ядра"""
        self.is_running = True
        self.logger.info("Ядро запущено", "Core")
    
    def stop(self):
        """Остановка ядра"""
        self.is_running = False
        self.disconnect_device()
        self.logger.info("Ядро остановлено", "Core")


if __name__ == "__main__":
    # Тестирование ядра
    logging.basicConfig(level=logging.INFO)
    
    core = ProxMasterCore()
    core.start()
    
    print("Команды загружены:", len(core.command_manager.commands))
    print("Категории:", list(core.command_manager.categories.keys()))
    
    core.stop()
