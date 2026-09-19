# -*- coding: utf-8 -*-
"""
ProxMaster Pro - Профессиональный инструмент управления Proxmark3
Модуль ядра приложения: управление командами, связь, данные, логирование
"""

import json
import os
import re
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
import serial
import serial.tools.list_ports


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
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CommandParameter:
    """Параметр команды"""
    name: str
    type: str  # str, int, float, bool, hex, file, select
    required: bool = False
    default: Any = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    options: List[str] = field(default_factory=list)
    description: str = ""
    validation_pattern: Optional[str] = None


@dataclass
class CommandDefinition:
    """Определение команды"""
    id: str
    category: str
    name: str
    description: str
    template: str
    risk_level: RiskLevel
    timeout: int
    parameters: List[CommandParameter]
    examples: List[str]
    tips: List[str]
    returns_data: bool = False
    plot_required: bool = False
    hf_required: bool = False
    lf_required: bool = False


@dataclass
class LogEntry:
    """Запись лога"""
    timestamp: str
    level: LogLevel
    message: str
    source: str = ""
    data: Optional[Dict] = None


@dataclass
class DeviceInfo:
    """Информация об устройстве"""
    connected: bool = False
    port: str = ""
    firmware_version: str = ""
    hardware_version: str = ""
    serial_number: str = ""
    chip_info: str = ""
    capabilities: List[str] = field(default_factory=list)


class CommunicationLayer:
    """Слой связи с устройством Proxmark3"""
    
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.device_info = DeviceInfo()
        self.is_connected = False
        self.read_timeout = 5.0
        self.write_timeout = 5.0
        self._read_thread: Optional[threading.Thread] = None
        self._stop_read = False
        self._data_queue = queue.Queue()
        self._callbacks: List[Callable] = []
        
    def list_ports(self) -> List[Dict[str, str]]:
        """Получить список доступных COM портов"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'vid': hex(port.vid) if port.vid else '',
                'pid': hex(port.pid) if port.pid else ''
            })
        return ports
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Подключиться к устройству"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect()
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.read_timeout,
                write_timeout=self.write_timeout
            )
            
            time.sleep(2)  # Ждем инициализации устройства
            
            # Очищаем буферы
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            self.device_info.port = port
            self.device_info.connected = True
            self.is_connected = True
            
            # Запускаем поток чтения
            self._stop_read = False
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            
            return True
        except Exception as e:
            self.device_info.connected = False
            self.is_connected = False
            print(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключиться от устройства"""
        self._stop_read = True
        if self._read_thread:
            self._read_thread.join(timeout=2)
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.serial_port = None
        self.device_info.connected = False
        self.is_connected = False
    
    def _read_loop(self):
        """Цикл чтения данных из порта"""
        buffer = ""
        while not self._stop_read:
            try:
                if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # Обрабатываем полные строки
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._data_queue.put(line)
                            for callback in self._callbacks:
                                try:
                                    callback(line)
                                except Exception as e:
                                    print(f"Ошибка в callback: {e}")
                else:
                    time.sleep(0.01)
            except Exception as e:
                if not self._stop_read:
                    print(f"Ошибка чтения: {e}")
                time.sleep(0.1)
    
    def add_data_callback(self, callback: Callable):
        """Добавить callback для получения данных"""
        self._callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """Удалить callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def write(self, data: str) -> bool:
        """Отправить данные в устройство"""
        if not self.serial_port or not self.serial_port.is_open:
            return False
        
        try:
            command = data + '\n'
            self.serial_port.write(command.encode('utf-8'))
            self.serial_port.flush()
            return True
        except Exception as e:
            print(f"Ошибка записи: {e}")
            return False
    
    def write_and_read(self, command: str, timeout: float = None) -> List[str]:
        """Отправить команду и получить ответ"""
        if not self.serial_port or not self.serial_port.is_open:
            return []
        
        if timeout is None:
            timeout = self.read_timeout
        
        try:
            # Очищаем входной буфер
            self.serial_port.reset_input_buffer()
            
            # Отправляем команду
            self.write(command)
            
            # Читаем ответ
            response_lines = []
            start_time = time.time()
            empty_lines_count = 0
            
            while time.time() - start_time < timeout:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        empty_lines_count = 0
                    else:
                        empty_lines_count += 1
                        if empty_lines_count > 3:  # Несколько пустых строк подряд - конец ответа
                            break
                else:
                    time.sleep(0.05)
            
            return response_lines
        except Exception as e:
            print(f"Ошибка чтения ответа: {e}")
            return []
    
    def get_queued_data(self) -> List[str]:
        """Получить накопленные данные из очереди"""
        lines = []
        while not self._data_queue.empty():
            try:
                lines.append(self._data_queue.get_nowait())
            except queue.Empty:
                break
        return lines


class CommandManager:
    """Менеджер команд Proxmark3"""
    
    def __init__(self, commands_file: str):
        self.commands_file = commands_file
        self.commands: Dict[str, CommandDefinition] = {}
        self.categories: Dict[str, List[str]] = {}
        self.load_commands()
    
    def load_commands(self):
        """Загрузить команды из JSON файла"""
        if not os.path.exists(self.commands_file):
            raise FileNotFoundError(f"Файл команд не найден: {self.commands_file}")
        
        with open(self.commands_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.commands = {}
        self.categories = {}
        
        for cmd_data in data.get('commands', []):
            try:
                params = []
                for p in cmd_data.get('parameters', []):
                    param = CommandParameter(
                        name=p['name'],
                        type=p['type'],
                        required=p.get('required', False),
                        default=p.get('default'),
                        min_value=p.get('min_value'),
                        max_value=p.get('max_value'),
                        options=p.get('options', []),
                        description=p.get('description', ''),
                        validation_pattern=p.get('validation_pattern')
                    )
                    params.append(param)
                
                cmd = CommandDefinition(
                    id=cmd_data['id'],
                    category=cmd_data['category'],
                    name=cmd_data['name'],
                    description=cmd_data['description'],
                    template=cmd_data['template'],
                    risk_level=RiskLevel(cmd_data['risk_level']),
                    timeout=cmd_data.get('timeout', 30),
                    parameters=params,
                    examples=cmd_data.get('examples', []),
                    tips=cmd_data.get('tips', []),
                    returns_data=cmd_data.get('returns_data', False),
                    plot_required=cmd_data.get('plot_required', False),
                    hf_required=cmd_data.get('hf_required', False),
                    lf_required=cmd_data.get('lf_required', False)
                )
                
                self.commands[cmd.id] = cmd
                
                # Группируем по категориям
                if cmd.category not in self.categories:
                    self.categories[cmd.category] = []
                self.categories[cmd.category].append(cmd.id)
                
            except Exception as e:
                print(f"Ошибка загрузки команды {cmd_data.get('id', 'unknown')}: {e}")
    
    def get_command(self, cmd_id: str) -> Optional[CommandDefinition]:
        """Получить определение команды по ID"""
        return self.commands.get(cmd_id)
    
    def get_category_commands(self, category: str) -> List[CommandDefinition]:
        """Получить все команды категории"""
        cmd_ids = self.categories.get(category, [])
        return [self.commands[cmd_id] for cmd_id in cmd_ids if cmd_id in self.commands]
    
    def get_all_categories(self) -> List[str]:
        """Получить все категории"""
        return list(self.categories.keys())
    
    def build_command(self, cmd_id: str, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        """
        Построить команду для отправки
        Возвращает (команда, ошибка)
        """
        cmd = self.get_command(cmd_id)
        if not cmd:
            return None, f"Команда {cmd_id} не найдена"
        
        command_str = cmd.template
        
        # Проверяем обязательные параметры
        for param in cmd.parameters:
            if param.required and param.name not in kwargs:
                if param.default is None:
                    return None, f"Обязательный параметр '{param.name}' отсутствует"
        
        # Подставляем параметры
        for param in cmd.parameters:
            value = kwargs.get(param.name, param.default)
            if value is not None:
                # Валидация
                if not self._validate_parameter(param, value):
                    return None, f"Неверное значение параметра '{param.name}': {value}"
                
                # Форматирование значения
                formatted_value = self._format_value(param, value)
                command_str = command_str.replace(f'{{{param.name}}}', str(formatted_value))
        
        # Удаляем неподставленные параметры (необязательные без значения)
        for param in cmd.parameters:
            if param.name not in kwargs or kwargs.get(param.name) is None:
                command_str = command_str.replace(f'{{{param.name}}}', '')
        
        # Очищаем лишние пробелы
        command_str = re.sub(r'\s+', ' ', command_str).strip()
        
        return command_str, None
    
    def _validate_parameter(self, param: CommandParameter, value: Any) -> bool:
        """Валидация параметра"""
        if value is None:
            return not param.required
        
        # Проверка типа
        if param.type == 'int':
            if not isinstance(value, int):
                try:
                    value = int(value)
                except:
                    return False
            if param.min_value is not None and value < param.min_value:
                return False
            if param.max_value is not None and value > param.max_value:
                return False
        
        elif param.type == 'float':
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except:
                    return False
            if param.min_value is not None and value < param.min_value:
                return False
            if param.max_value is not None and value > param.max_value:
                return False
        
        elif param.type == 'bool':
            if not isinstance(value, bool):
                return False
        
        elif param.type == 'select':
            if value not in param.options:
                return False
        
        elif param.type == 'hex':
            if not re.match(r'^[0-9A-Fa-f]+$', str(value)):
                return False
        
        elif param.type == 'file':
            if not os.path.exists(str(value)):
                return False
        
        # Проверка паттерна
        if param.validation_pattern:
            if not re.match(param.validation_pattern, str(value)):
                return False
        
        return True
    
    def _format_value(self, param: CommandParameter, value: Any) -> Any:
        """Форматирование значения параметра"""
        if param.type == 'hex':
            return str(value).upper()
        elif param.type == 'bool':
            return '1' if value else '0'
        return value


class DataManager:
    """Менеджер данных приложения"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.dumps_dir = os.path.join(base_dir, 'dumps')
        self.keys_dir = os.path.join(base_dir, 'keys')
        self.traces_dir = os.path.join(base_dir, 'traces')
        self.logs_dir = os.path.join(base_dir, 'logs')
        self.nodes_dir = os.path.join(base_dir, 'nodes')
        
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Создать необходимые директории"""
        for dir_path in [self.dumps_dir, self.keys_dir, self.traces_dir, 
                         self.logs_dir, self.nodes_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def save_dump(self, filename: str, data: bytes) -> str:
        """Сохранить дамп карты"""
        filepath = os.path.join(self.dumps_dir, filename)
        if not filepath.endswith('.bin'):
            filepath += '.bin'
        
        with open(filepath, 'wb') as f:
            f.write(data)
        
        return filepath
    
    def load_dump(self, filename: str) -> Optional[bytes]:
        """Загрузить дамп карты"""
        filepath = os.path.join(self.dumps_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'rb') as f:
            return f.read()
    
    def save_keys(self, filename: str, keys: Dict[int, str]) -> str:
        """Сохранить ключи"""
        filepath = os.path.join(self.keys_dir, filename)
        if not filepath.endswith('.json'):
            filepath += '.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(keys, f, indent=2)
        
        return filepath
    
    def load_keys(self, filename: str) -> Optional[Dict[int, str]]:
        """Загрузить ключи"""
        filepath = os.path.join(self.keys_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_trace(self, filename: str, trace_data: List[Dict]) -> str:
        """Сохранить трассировку"""
        filepath = os.path.join(self.traces_dir, filename)
        if not filepath.endswith('.json'):
            filepath += '.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2)
        
        return filepath
    
    def load_trace(self, filename: str) -> Optional[List[Dict]]:
        """Загрузить трассировку"""
        filepath = os.path.join(self.traces_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_node_graph(self, filename: str, graph_data: Dict) -> str:
        """Сохранить граф нод"""
        filepath = os.path.join(self.nodes_dir, filename)
        if not filepath.endswith('.json'):
            filepath += '.json'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_node_graph(self, filename: str) -> Optional[Dict]:
        """Загрузить граф нод"""
        filepath = os.path.join(self.nodes_dir, filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_files(self, directory: str, extension: str = '') -> List[str]:
        """Получить список файлов в директории"""
        dir_path = getattr(self, f"{directory}_dir", self.base_dir)
        if not os.path.exists(dir_path):
            return []
        
        files = []
        for f in os.listdir(dir_path):
            if not extension or f.endswith(extension):
                files.append(f)
        
        return sorted(files)
    
    def delete_file(self, directory: str, filename: str) -> bool:
        """Удалить файл"""
        dir_path = getattr(self, f"{directory}_dir", self.base_dir)
        filepath = os.path.join(dir_path, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False


class Logger:
    """Система логирования"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.entries: List[LogEntry] = []
        self.callbacks: List[Callable[[LogEntry], None]] = []
        self.max_entries = 10000
    
    def add_callback(self, callback: Callable[[LogEntry], None]):
        """Добавить callback для новых записей лога"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[LogEntry], None]):
        """Удалить callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def log(self, level: LogLevel, message: str, source: str = "", data: Optional[Dict] = None):
        """Добавить запись в лог"""
        entry = LogEntry(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            level=level,
            message=message,
            source=source,
            data=data
        )
        
        self.entries.append(entry)
        
        # Ограничиваем размер
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        
        # Уведомляем callbacks
        for callback in self.callbacks:
            try:
                callback(entry)
            except Exception as e:
                print(f"Ошибка в callback лога: {e}")
        
        # Пишем в файл
        if self.log_file:
            self._write_to_file(entry)
    
    def _write_to_file(self, entry: LogEntry):
        """Записать запись в файл"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{entry.timestamp}] [{entry.level.value.upper()}] {entry.source}: {entry.message}\n")
        except Exception as e:
            print(f"Ошибка записи в файл лога: {e}")
    
    def debug(self, message: str, source: str = "", data: Optional[Dict] = None):
        self.log(LogLevel.DEBUG, message, source, data)
    
    def info(self, message: str, source: str = "", data: Optional[Dict] = None):
        self.log(LogLevel.INFO, message, source, data)
    
    def warning(self, message: str, source: str = "", data: Optional[Dict] = None):
        self.log(LogLevel.WARNING, message, source, data)
    
    def error(self, message: str, source: str = "", data: Optional[Dict] = None):
        self.log(LogLevel.ERROR, message, source, data)
    
    def critical(self, message: str, source: str = "", data: Optional[Dict] = None):
        self.log(LogLevel.CRITICAL, message, source, data)
    
    def get_entries(self, level: Optional[LogLevel] = None, 
                    source: Optional[str] = None,
                    limit: int = 100) -> List[LogEntry]:
        """Получить записи лога с фильтрацией"""
        entries = self.entries
        
        if level:
            entries = [e for e in entries if e.level == level]
        
        if source:
            entries = [e for e in entries if e.source == source]
        
        return entries[-limit:]
    
    def clear(self):
        """Очистить лог"""
        self.entries = []


class SignalProcessor:
    """Обработчик сигналов для визуализации"""
    
    @staticmethod
    def parse_trace_line(line: str) -> Optional[Dict]:
        """Распарсить строку трассировки"""
        # Пример формата: "db: 1234567890abcdef | uid: 04a2b3c4"
        result = {}
        
        # Ищем hex данные
        hex_match = re.search(r'[0-9A-Fa-f]{8,}', line)
        if hex_match:
            result['hex'] = hex_match.group()
            result['bytes'] = bytes.fromhex(hex_match.group())
        
        # Ищем uid
        uid_match = re.search(r'uid:\s*([0-9A-Fa-f]+)', line, re.IGNORECASE)
        if uid_match:
            result['uid'] = uid_match.group(1)
        
        # Ищем db значения для графика
        db_match = re.search(r'db:\s*(-?\d+)', line, re.IGNORECASE)
        if db_match:
            result['db'] = int(db_match.group(1))
        
        # Ищем тип модуляции
        mod_match = re.search(r'mod:(\w+)', line, re.IGNORECASE)
        if mod_match:
            result['modulation'] = mod_match.group(1)
        
        return result if result else None
    
    @staticmethod
    def bytes_to_plot_data(data: bytes) -> Tuple[List[int], List[int]]:
        """Преобразовать байты в данные для графика"""
        x_values = list(range(len(data)))
        y_values = list(data)
        return x_values, y_values
    
    @staticmethod
    def demodulate_ask(data: bytes) -> List[int]:
        """Демодулировать ASK сигнал"""
        result = []
        threshold = 128
        
        for byte in data:
            if byte > threshold:
                result.append(1)
            else:
                result.append(0)
        
        return result
    
    @staticmethod
    def demodulate_fsk(data: bytes, sample_rate: int = 125000) -> List[int]:
        """Демодулировать FSK сигнал (упрощенно)"""
        # Простая реализация для демонстрации
        result = []
        window_size = sample_rate // 10000  # Окно для анализа частоты
        
        for i in range(0, len(data) - window_size, window_size):
            window = data[i:i + window_size]
            avg = sum(window) / len(window)
            result.append(1 if avg > 128 else 0)
        
        return result
    
    @staticmethod
    def calculate_fft(data: bytes) -> Tuple[List[float], List[float]]:
        """Вычислить FFT для спектрального анализа"""
        import math
        
        n = len(data)
        if n == 0:
            return [], []
        
        # Простое FFT (для реальных приложений использовать numpy)
        frequencies = []
        magnitudes = []
        
        for k in range(n // 2):
            real = 0
            imag = 0
            for t in range(n):
                angle = 2 * math.pi * k * t / n
                real += data[t] * math.cos(angle)
                imag -= data[t] * math.sin(angle)
            
            magnitude = math.sqrt(real**2 + imag**2) / n
            frequency = k * 125000 / n  # Предполагаемая частота дискретизации 125 kHz
            
            frequencies.append(frequency)
            magnitudes.append(magnitude)
        
        return frequencies, magnitudes


class ApplicationCore:
    """Основное ядро приложения"""
    
    def __init__(self, base_dir: str, commands_file: str):
        self.base_dir = base_dir
        self.data_manager = DataManager(base_dir)
        self.command_manager = CommandManager(commands_file)
        self.communication = CommunicationLayer()
        self.logger = Logger(os.path.join(base_dir, 'logs', 'app.log'))
        self.signal_processor = SignalProcessor()
        
        # Состояние приложения
        self.is_busy = False
        self.current_operation = None
        self.progress_callbacks: List[Callable[[int, str], None]] = []
        
        # Подключаем получение данных от устройства
        self.communication.add_data_callback(self._on_device_data)
    
    def _on_device_data(self, line: str):
        """Обработка данных от устройства"""
        self.logger.debug(f"RX: {line}", source="Device")
    
    def add_progress_callback(self, callback: Callable[[int, str], None]):
        """Добавить callback прогресса"""
        self.progress_callbacks.append(callback)
    
    def _update_progress(self, percent: int, message: str):
        """Обновить прогресс"""
        for callback in self.progress_callbacks:
            try:
                callback(percent, message)
            except Exception as e:
                self.logger.error(f"Ошибка в progress callback: {e}")
    
    def execute_command(self, cmd_id: str, **kwargs) -> Tuple[bool, List[str]]:
        """
        Выполнить команду
        Возвращает (успех, результат)
        """
        cmd = self.command_manager.get_command(cmd_id)
        if not cmd:
            self.logger.error(f"Команда {cmd_id} не найдена", source="Core")
            return False, []
        
        # Проверка подключения для команд требующих устройство
        if not self.communication.is_connected and cmd_id != 'help':
            self.logger.error("Устройство не подключено", source="Core")
            return False, ["Устройство не подключено"]
        
        # Построение команды
        command_str, error = self.command_manager.build_command(cmd_id, **kwargs)
        if error:
            self.logger.error(f"Ошибка построения команды: {error}", source="Core")
            return False, [error]
        
        self.logger.info(f"TX: {command_str}", source="Core")
        
        # Отправка команды
        self.is_busy = True
        self.current_operation = cmd.name
        self._update_progress(10, "Отправка команды...")
        
        try:
            response = self.communication.write_and_read(command_str, timeout=cmd.timeout)
            
            self._update_progress(100, "Готово")
            self.logger.info(f"Получен ответ ({len(response)} строк)", source="Core")
            
            return True, response
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды: {e}", source="Core")
            return False, [str(e)]
        finally:
            self.is_busy = False
            self.current_operation = None
    
    def connect_device(self, port: str) -> bool:
        """Подключить устройство"""
        self.logger.info(f"Подключение к порту {port}", source="Core")
        
        if self.communication.connect(port):
            self.logger.info("Устройство подключено", source="Core")
            
            # Получаем информацию об устройстве
            success, response = self.execute_command('system_version')
            if success:
                self.communication.device_info.firmware_version = '\n'.join(response)
            
            return True
        
        self.logger.error("Не удалось подключить устройство", source="Core")
        return False
    
    def disconnect_device(self):
        """Отключить устройство"""
        self.logger.info("Отключение устройства", source="Core")
        self.communication.disconnect()
    
    def scan_ports(self) -> List[Dict[str, str]]:
        """Сканировать доступные порты"""
        ports = self.communication.list_ports()
        self.logger.info(f"Найдено портов: {len(ports)}", source="Core")
        return ports
    
    def save_trace_from_response(self, filename: str, response: List[str]) -> str:
        """Сохранить трассировку из ответа"""
        trace_data = []
        
        for line in response:
            parsed = self.signal_processor.parse_trace_line(line)
            if parsed:
                parsed['raw'] = line
                trace_data.append(parsed)
        
        filepath = self.data_manager.save_trace(filename, trace_data)
        self.logger.info(f"Трассировка сохранена: {filepath}", source="Core")
        return filepath
    
    def load_trace_for_plot(self, filename: str) -> Optional[Tuple[List[int], List[int]]]:
        """Загрузить трассировку для построения графика"""
        trace = self.data_manager.load_trace(filename)
        if not trace:
            return None
        
        # Собираем данные для графика
        y_values = []
        for entry in trace:
            if 'bytes' in entry:
                y_values.extend(entry['bytes'])
            elif 'db' in entry:
                y_values.append(entry['db'])
        
        if not y_values:
            return None
        
        x_values = list(range(len(y_values)))
        return x_values, y_values


# Экспорт основных классов
__all__ = [
    'RiskLevel',
    'LogLevel',
    'CommandParameter',
    'CommandDefinition',
    'LogEntry',
    'DeviceInfo',
    'CommunicationLayer',
    'CommandManager',
    'DataManager',
    'Logger',
    'SignalProcessor',
    'ApplicationCore'
]
