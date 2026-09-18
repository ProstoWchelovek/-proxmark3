"""
ProxMaster Professional - Ядро приложения
Профессиональный инструмент для управления Proxmark3 Easy/Iceman

Модуль содержит основные классы для:
- Управления командами (CommandManager)
- Коммуникации с устройством (CommunicationLayer)
- Работы с данными (DataManager)
- Логирования (Logger)
- Валидации и парсинга команд
"""

import json
import os
import re
import time
import threading
import serial
import serial.tools.list_ports
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import logging


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
    type: str  # str, int, hex, bool, file, uid, key
    required: bool = True
    default: Any = None
    min_value: Any = None
    max_value: Any = None
    pattern: Optional[str] = None
    description: str = ""
    examples: List[str] = field(default_factory=list)
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Валидация параметра"""
        if value is None:
            if self.required:
                return False, f"Параметр '{self.name}' обязателен"
            return True, ""
        
        try:
            if self.type == "int":
                int_val = int(value)
                if self.min_value is not None and int_val < self.min_value:
                    return False, f"Значение должно быть >= {self.min_value}"
                if self.max_value is not None and int_val > self.max_value:
                    return False, f"Значение должно быть <= {self.max_value}"
            elif self.type == "hex":
                hex_str = str(value).replace(" ", "").replace(":", "")
                if not re.match(r'^[0-9a-fA-F]+$', hex_str):
                    return False, "Неверный формат HEX"
                if self.min_value is not None and len(hex_str) < self.min_value * 2:
                    return False, f"Минимальная длина: {self.min_value} байт"
            elif self.type == "uid":
                uid_str = str(value).replace(" ", "").replace(":", "")
                if not re.match(r'^[0-9a-fA-F]{8}$', uid_str):
                    return False, "UID должен быть 4 байта (8 hex символов)"
            elif self.type == "key":
                key_str = str(value).replace(" ", "").replace(":", "")
                if not re.match(r'^[0-9a-fA-F]{12}$', key_str):
                    return False, "Ключ должен быть 6 байт (12 hex символов)"
            elif self.type == "file":
                if not os.path.exists(str(value)):
                    return False, f"Файл не найден: {value}"
            
            if self.pattern and not re.match(self.pattern, str(value)):
                return False, f"Значение не соответствует шаблону: {self.pattern}"
                
            return True, ""
        except Exception as e:
            return False, f"Ошибка валидации: {str(e)}"


@dataclass
class Command:
    """Команда для Proxmark3"""
    id: str
    category: str
    name: str
    description: str
    template: str
    risk_level: RiskLevel
    timeout: int = 30
    parameters: List[CommandParameter] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    returns: str = ""
    examples: List[str] = field(default_factory=list)
    related_commands: List[str] = field(default_factory=list)
    
    def build(self, **kwargs) -> Tuple[Optional[str], str]:
        """Построение команды из шаблона"""
        try:
            cmd = self.template
            
            # Проверка обязательных параметров
            for param in self.parameters:
                if param.required and param.name not in kwargs:
                    if param.default is None:
                        return None, f"Отсутствует обязательный параметр: {param.name}"
                    kwargs[param.name] = param.default
            
            # Подстановка параметров
            for key, value in kwargs.items():
                placeholder = f"{{{key}}}"
                if placeholder in cmd:
                    if value is not None:
                        cmd = cmd.replace(placeholder, str(value))
                    elif self.parameters:
                        for p in self.parameters:
                            if p.name == key and p.default is not None:
                                cmd = cmd.replace(placeholder, str(p.default))
                                break
            
            # Удаление необязательных параметров без значений
            for param in self.parameters:
                if not param.required:
                    placeholder = f"{{{param.name}}}"
                    if placeholder in cmd:
                        cmd = cmd.replace(placeholder, "").strip()
            
            # Очистка от лишних пробелов
            cmd = re.sub(r'\s+', ' ', cmd).strip()
            
            return cmd, ""
        except Exception as e:
            return None, f"Ошибка построения команды: {str(e)}"


@dataclass
class CommandResult:
    """Результат выполнения команды"""
    success: bool
    command: str
    output: str
    error: str = ""
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "command": self.command,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class ProxmarkLogger:
    """Система логирования с цветным выводом"""
    
    COLORS = {
        LogLevel.DEBUG: "\033[90m",      # Серый
        LogLevel.INFO: "\033[94m",       # Синий
        LogLevel.SUCCESS: "\033[92m",    # Зеленый
        LogLevel.WARNING: "\033[93m",    # Желтый
        LogLevel.ERROR: "\033[91m",      # Красный
    }
    RESET = "\033[0m"
    
    def __init__(self, log_file: Optional[str] = None, max_lines: int = 10000):
        self.log_file = log_file
        self.max_lines = max_lines
        self.logs: List[Dict] = []
        self.callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def add_callback(self, callback: Callable):
        """Добавить колбэк для новых логов"""
        self.callbacks.append(callback)
    
    def _add_log(self, level: LogLevel, message: str, source: str = ""):
        """Добавление записи лога"""
        with self._lock:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level.value,
                "message": message,
                "source": source
            }
            self.logs.append(entry)
            
            # Ограничение размера
            if len(self.logs) > self.max_lines:
                self.logs = self.logs[-self.max_lines:]
            
            # Консольный вывод
            color = self.COLORS.get(level, "")
            timestamp = entry["timestamp"].split("T")[1].split(".")[0]
            source_str = f"[{source}] " if source else ""
            print(f"{color}[{timestamp}] {source_str}{message}{self.RESET}")
            
            # Запись в файл
            if self.log_file:
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(f"[{entry['timestamp']}] [{level.value.upper()}] {source_str}{message}\n")
                except Exception:
                    pass
            
            # Вызов колбэков
            for callback in self.callbacks:
                try:
                    callback(entry)
                except Exception:
                    pass
    
    def debug(self, message: str, source: str = ""):
        self._add_log(LogLevel.DEBUG, message, source)
    
    def info(self, message: str, source: str = ""):
        self._add_log(LogLevel.INFO, message, source)
    
    def success(self, message: str, source: str = ""):
        self._add_log(LogLevel.SUCCESS, message, source)
    
    def warning(self, message: str, source: str = ""):
        self._add_log(LogLevel.WARNING, message, source)
    
    def error(self, message: str, source: str = ""):
        self._add_log(LogLevel.ERROR, message, source)
    
    def get_logs(self, level: Optional[LogLevel] = None, 
                 limit: int = 100) -> List[Dict]:
        """Получение логов"""
        with self._lock:
            logs = self.logs[-limit:]
            if level:
                logs = [l for l in logs if l["level"] == level.value]
            return logs
    
    def clear(self):
        """Очистка логов"""
        with self._lock:
            self.logs.clear()


class CommunicationLayer:
    """Слой коммуникации с Proxmark3"""
    
    def __init__(self, logger: ProxmarkLogger):
        self.logger = logger
        self.port: Optional[serial.Serial] = None
        self.is_connected = False
        self.device_info: Dict = {}
        self._lock = threading.Lock()
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._buffer = ""
        self._response_callbacks: List[Callable] = []
    
    def list_ports(self) -> List[Dict]:
        """Список доступных COM портов"""
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "device": p.device,
                "name": p.name,
                "description": p.description,
                "hwid": p.hwid,
                "vid": p.vid,
                "pid": p.pid
            })
        return ports
    
    def connect(self, port: str, baudrate: int = 115200, 
                timeout: float = 1.0) -> Tuple[bool, str]:
        """Подключение к устройству"""
        try:
            with self._lock:
                if self.is_connected:
                    self.disconnect()
                
                self.port = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=timeout,
                    write_timeout=timeout
                )
                
                time.sleep(0.5)  # Ждем инициализации
                self.port.reset_input_buffer()
                self.port.reset_output_buffer()
                
                self.is_connected = True
                self._running = True
                self._buffer = ""
                
                # Запуск потока чтения
                self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
                self._read_thread.start()
                
                # Получение информации об устройстве
                self._get_device_info()
                
                self.logger.success(f"Подключено к {port}", "COM")
                return True, ""
                
        except serial.SerialException as e:
            error_msg = f"Ошибка подключения: {str(e)}"
            self.logger.error(error_msg, "COM")
            return False, error_msg
        except Exception as e:
            error_msg = f"Неизвестная ошибка: {str(e)}"
            self.logger.error(error_msg, "COM")
            return False, error_msg
    
    def disconnect(self):
        """Отключение от устройства"""
        with self._lock:
            self._running = False
            
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.join(timeout=2.0)
            
            if self.port:
                try:
                    self.port.close()
                except Exception:
                    pass
                self.port = None
            
            self.is_connected = False
            self.device_info = {}
            self.logger.info("Отключено от устройства", "COM")
    
    def _read_loop(self):
        """Цикл чтения данных"""
        while self._running and self.port:
            try:
                if self.port.in_waiting > 0:
                    data = self.port.read(self.port.in_waiting).decode('utf-8', errors='ignore')
                    self._buffer += data
                    
                    # Обработка полных строк
                    while '\n' in self._buffer:
                        line, self._buffer = self._buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self._process_line(line)
                            
                time.sleep(0.01)
            except Exception as e:
                if self._running:
                    self.logger.error(f"Ошибка чтения: {str(e)}", "COM")
                break
    
    def _process_line(self, line: str):
        """Обработка полученной строки"""
        # Удаление промпта pm3 >
        if line.startswith("pm3 >"):
            line = line[5:].strip()
        
        # Фильтрация служебных сообщений
        if line.startswith("[=]") or line.startswith("[+]") or line.startswith("[-]"):
            self.logger.info(line, "PM3")
        elif line.startswith("#"):
            self.logger.debug(line, "PM3")
        
        # Вызов колбэков
        for callback in self._response_callbacks:
            try:
                callback(line)
            except Exception:
                pass
    
    def _get_device_info(self):
        """Получение информации об устройстве"""
        try:
            # Команда версии
            result = self.send_command("version", timeout=5.0, wait_response=True)
            if result and result.output:
                self.device_info["version"] = result.output[:500]
                self.logger.success(f"Устройство: {result.output[:100]}", "PM3")
        except Exception as e:
            self.logger.warning(f"Не удалось получить версию: {str(e)}", "PM3")
    
    def send_command(self, command: str, timeout: float = 30.0,
                     wait_response: bool = True) -> Optional[CommandResult]:
        """Отправка команды"""
        if not self.is_connected or not self.port:
            self.logger.error("Нет подключения к устройству", "COM")
            return None
        
        try:
            with self._lock:
                start_time = time.time()
                
                # Отправка команды
                full_command = f"{command}\n"
                self.port.write(full_command.encode('utf-8'))
                self.port.flush()
                
                self.logger.debug(f">>> {command}", "TX")
                
                if not wait_response:
                    return CommandResult(
                        success=True,
                        command=command,
                        output="",
                        execution_time=time.time() - start_time
                    )
                
                # Ожидание ответа
                output_lines = []
                elapsed = 0
                
                while elapsed < timeout:
                    time.sleep(0.1)
                    elapsed = time.time() - start_time
                    
                    # Проверка наличия ответа
                    if self.port.in_waiting > 0:
                        while self.port.in_waiting > 0:
                            line = self.port.readline().decode('utf-8', errors='ignore').strip()
                            if line:
                                output_lines.append(line)
                                self._process_line(line)
                    
                    # Проверка завершения (промпт или пустая строка после данных)
                    if output_lines and any("pm3 >" in l for l in output_lines):
                        break
                    
                    # Таймаут для длительных операций
                    if elapsed > timeout * 0.8 and not output_lines:
                        self.logger.warning("Ожидание ответа...", "COM")
                
                output = "\n".join(output_lines)
                execution_time = time.time() - start_time
                
                # Определение успеха/ошибки
                success = True
                error = ""
                
                if "ERROR" in output.upper() or "FAIL" in output.upper():
                    success = False
                    error = "Команда выполнена с ошибкой"
                
                return CommandResult(
                    success=success,
                    command=command,
                    output=output,
                    error=error,
                    execution_time=execution_time
                )
                
        except serial.SerialException as e:
            error_msg = f"Ошибка связи: {str(e)}"
            self.logger.error(error_msg, "COM")
            return CommandResult(
                success=False,
                command=command,
                output="",
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Неизвестная ошибка: {str(e)}"
            self.logger.error(error_msg, "COM")
            return CommandResult(
                success=False,
                command=command,
                output="",
                error=error_msg
            )
    
    def add_response_callback(self, callback: Callable):
        """Добавить колбэк на ответы устройства"""
        self._response_callbacks.append(callback)
    
    def reset_device(self):
        """Перезагрузка устройства"""
        if self.is_connected:
            self.send_command("reset", timeout=5.0, wait_response=False)
            time.sleep(2.0)
            self._get_device_info()


class DataManager:
    """Управление данными (дампы, ключи, конфигурации)"""
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.dumps_path = self.base_path / "dumps"
        self.keys_path = self.base_path / "keys"
        self.nodes_path = self.base_path / "nodes"
        
        # Создание директорий
        for path in [self.dumps_path, self.keys_path, self.nodes_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def save_dump(self, data: bytes, filename: str, 
                  card_type: str = "unknown") -> Tuple[bool, str]:
        """Сохранение дампа карты"""
        try:
            filepath = self.dumps_path / f"{filename}_{card_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
            with open(filepath, 'wb') as f:
                f.write(data)
            return True, str(filepath)
        except Exception as e:
            return False, str(e)
    
    def load_dump(self, filename: str) -> Tuple[Optional[bytes], str]:
        """Загрузка дампа"""
        try:
            filepath = self.dumps_path / filename
            if not filepath.exists():
                return None, f"Файл не найден: {filename}"
            with open(filepath, 'rb') as f:
                return f.read(), ""
        except Exception as e:
            return None, str(e)
    
    def save_keys(self, keys: Dict, filename: str) -> Tuple[bool, str]:
        """Сохранение ключей"""
        try:
            filepath = self.keys_path / f"{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2, ensure_ascii=False)
            return True, str(filepath)
        except Exception as e:
            return False, str(e)
    
    def load_keys(self, filename: str) -> Tuple[Optional[Dict], str]:
        """Загрузка ключей"""
        try:
            filepath = self.keys_path / filename
            if not filepath.exists():
                return None, f"Файл не найден: {filename}"
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f), ""
        except Exception as e:
            return None, str(e)
    
    def list_dumps(self) -> List[Dict]:
        """Список сохраненных дампов"""
        dumps = []
        for f in self.dumps_path.glob("*"):
            if f.is_file():
                stat = f.stat()
                dumps.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": f.suffix
                })
        return sorted(dumps, key=lambda x: x["modified"], reverse=True)
    
    def list_keys(self) -> List[Dict]:
        """Список сохраненных ключей"""
        keys = []
        for f in self.keys_path.glob("*.json"):
            if f.is_file():
                stat = f.stat()
                keys.append({
                    "name": f.stem,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return sorted(keys, key=lambda x: x["modified"], reverse=True)
    
    def delete_file(self, filepath: str) -> Tuple[bool, str]:
        """Удаление файла"""
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                return True, ""
            return False, "Файл не найден"
        except Exception as e:
            return False, str(e)


class CommandManager:
    """Менеджер команд Proxmark3"""
    
    def __init__(self, commands_file: str = "data/commands.json"):
        self.commands_file = commands_file
        self.commands: Dict[str, Command] = {}
        self.categories: Dict[str, List[str]] = {}
        self.logger = ProxmarkLogger()
        self._load_commands()
    
    def _load_commands(self):
        """Загрузка команд из JSON"""
        if not os.path.exists(self.commands_file):
            self.logger.warning(f"Файл команд не найден: {self.commands_file}")
            return
        
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for cmd_data in data.get("commands", []):
                try:
                    # Парсинг параметров
                    params = []
                    for p in cmd_data.get("parameters", []):
                        param = CommandParameter(
                            name=p["name"],
                            type=p.get("type", "str"),
                            required=p.get("required", True),
                            default=p.get("default"),
                            min_value=p.get("min_value"),
                            max_value=p.get("max_value"),
                            pattern=p.get("pattern"),
                            description=p.get("description", ""),
                            examples=p.get("examples", [])
                        )
                        params.append(param)
                    
                    # Создание команды
                    cmd = Command(
                        id=cmd_data["id"],
                        category=cmd_data.get("category", "general"),
                        name=cmd_data["name"],
                        description=cmd_data.get("description", ""),
                        template=cmd_data["template"],
                        risk_level=RiskLevel(cmd_data.get("risk_level", "safe")),
                        timeout=cmd_data.get("timeout", 30),
                        parameters=params,
                        hints=cmd_data.get("hints", []),
                        returns=cmd_data.get("returns", ""),
                        examples=cmd_data.get("examples", []),
                        related_commands=cmd_data.get("related_commands", [])
                    )
                    
                    self.commands[cmd.id] = cmd
                    
                    # Группировка по категориям
                    if cmd.category not in self.categories:
                        self.categories[cmd.category] = []
                    self.categories[cmd.category].append(cmd.id)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка загрузки команды {cmd_data.get('id', 'unknown')}: {str(e)}")
            
            self.logger.success(f"Загружено команд: {len(self.commands)}", "CMD")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки файла команд: {str(e)}")
    
    def get_command(self, cmd_id: str) -> Optional[Command]:
        """Получение команды по ID"""
        return self.commands.get(cmd_id)
    
    def get_commands_by_category(self, category: str) -> List[Command]:
        """Получение команд по категории"""
        cmd_ids = self.categories.get(category, [])
        return [self.commands[cid] for cid in cmd_ids if cid in self.commands]
    
    def get_categories(self) -> List[str]:
        """Список категорий"""
        return list(self.categories.keys())
    
    def search_commands(self, query: str) -> List[Command]:
        """Поиск команд"""
        query = query.lower()
        results = []
        
        for cmd in self.commands.values():
            if (query in cmd.id.lower() or 
                query in cmd.name.lower() or 
                query in cmd.description.lower()):
                results.append(cmd)
        
        return results
    
    def build_command(self, cmd_id: str, **kwargs) -> Tuple[Optional[str], str]:
        """Построение команды"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            return None, f"Команда не найдена: {cmd_id}"
        
        return cmd.build(**kwargs)
    
    def validate_parameters(self, cmd_id: str, params: Dict) -> Tuple[bool, str]:
        """Валидация параметров команды"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            return False, f"Команда не найдена: {cmd_id}"
        
        for param in cmd.parameters:
            if param.name in params:
                valid, error = param.validate(params[param.name])
                if not valid:
                    return False, error
        
        return True, ""
    
    def add_command(self, cmd: Command) -> bool:
        """Добавление команды"""
        if cmd.id in self.commands:
            return False
        
        self.commands[cmd.id] = cmd
        
        if cmd.category not in self.categories:
            self.categories[cmd.category] = []
        self.categories[cmd.category].append(cmd.id)
        
        return True
    
    def remove_command(self, cmd_id: str) -> bool:
        """Удаление команды"""
        if cmd_id not in self.commands:
            return False
        
        cmd = self.commands[cmd_id]
        if cmd.category in self.categories:
            self.categories[cmd.category].remove(cmd_id)
        
        del self.commands[cmd_id]
        return True
    
    def export_commands(self, filepath: str) -> Tuple[bool, str]:
        """Экспорт команд в JSON"""
        try:
            data = {
                "commands": []
            }
            
            for cmd in self.commands.values():
                cmd_data = {
                    "id": cmd.id,
                    "category": cmd.category,
                    "name": cmd.name,
                    "description": cmd.description,
                    "template": cmd.template,
                    "risk_level": cmd.risk_level.value,
                    "timeout": cmd.timeout,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required,
                            "default": p.default,
                            "min_value": p.min_value,
                            "max_value": p.max_value,
                            "pattern": p.pattern,
                            "description": p.description,
                            "examples": p.examples
                        }
                        for p in cmd.parameters
                    ],
                    "hints": cmd.hints,
                    "returns": cmd.returns,
                    "examples": cmd.examples,
                    "related_commands": cmd.related_commands
                }
                data["commands"].append(cmd_data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True, filepath
        except Exception as e:
            return False, str(e)


class ProxmarkCore:
    """Основной класс ядра ProxMaster"""
    
    def __init__(self, config_path: str = "config.json"):
        # Загрузка конфигурации
        self.config = self._load_config(config_path)
        
        # Инициализация компонентов
        self.logger = ProxmarkLogger(
            log_file="logs/proxmaster.log",
            max_lines=self.config.get("settings", {}).get("max_log_lines", 10000)
        )
        
        self.command_manager = CommandManager("data/commands.json")
        self.communication = CommunicationLayer(self.logger)
        self.data_manager = DataManager("data")
        
        # Состояние
        self.is_initialized = False
        self.current_operation: Optional[str] = None
        self.operation_lock = threading.Lock()
        
        self.logger.success("ProxMaster Professional инициализирован", "CORE")
    
    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурации"""
        default_config = {
            "settings": {
                "default_port": "COM3",
                "default_baudrate": 115200,
                "timeout_seconds": 30
            }
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки конфига: {e}")
        
        return default_config
    
    def connect(self, port: Optional[str] = None, 
                baudrate: Optional[int] = None) -> Tuple[bool, str]:
        """Подключение к Proxmark3"""
        port = port or self.config.get("settings", {}).get("default_port", "COM3")
        baudrate = baudrate or self.config.get("settings", {}).get("default_baudrate", 115200)
        
        success, error = self.communication.connect(port, baudrate)
        
        if success:
            self.is_initialized = True
            self.logger.success(f"Подключено к {port}", "CORE")
        else:
            self.logger.error(f"Ошибка подключения: {error}", "CORE")
        
        return success, error
    
    def disconnect(self):
        """Отключение от устройства"""
        self.communication.disconnect()
        self.is_initialized = False
        self.logger.info("Отключено от устройства", "CORE")
    
    def execute_command(self, cmd_id: str, **params) -> CommandResult:
        """Выполнение команды"""
        if not self.is_initialized:
            return CommandResult(
                success=False,
                command=cmd_id,
                output="",
                error="Нет подключения к устройству"
            )
        
        # Построение команды
        cmd_str, error = self.command_manager.build_command(cmd_id, **params)
        if not cmd_str:
            return CommandResult(
                success=False,
                command=cmd_id,
                output="",
                error=error
            )
        
        # Получение таймаута
        cmd = self.command_manager.get_command(cmd_id)
        timeout = cmd.timeout if cmd else 30
        
        # Выполнение
        self.logger.info(f"Выполнение: {cmd_str}", "EXEC")
        result = self.communication.send_command(cmd_str, timeout=timeout)
        
        if result and result.success:
            self.logger.success(f"Успешно: {cmd_id}", "EXEC")
        elif result:
            self.logger.error(f"Ошибка: {result.error}", "EXEC")
        
        return result or CommandResult(
            success=False,
            command=cmd_str,
            output="",
            error="Неизвестная ошибка"
        )
    
    def execute_raw(self, command: str, timeout: float = 30.0) -> CommandResult:
        """Выполнение сырой команды"""
        if not self.is_initialized:
            return CommandResult(
                success=False,
                command=command,
                output="",
                error="Нет подключения к устройству"
            )
        
        self.logger.info(f"RAW: {command}", "EXEC")
        result = self.communication.send_command(command, timeout=timeout)
        
        return result or CommandResult(
            success=False,
            command=command,
            output="",
            error="Неизвестная ошибка"
        )
    
    def get_device_info(self) -> Dict:
        """Информация об устройстве"""
        return self.communication.device_info.copy()
    
    def is_connected(self) -> bool:
        """Статус подключения"""
        return self.communication.is_connected
    
    def list_ports(self) -> List[Dict]:
        """Список портов"""
        return self.communication.list_ports()
    
    def shutdown(self):
        """Корректное завершение работы"""
        self.logger.info("Завершение работы...", "CORE")
        self.disconnect()
        self.logger.info("ProxMaster остановлен", "CORE")


# Экспорт основных классов
__all__ = [
    'ProxmarkCore',
    'CommandManager', 
    'CommunicationLayer',
    'DataManager',
    'ProxmarkLogger',
    'Command',
    'CommandParameter',
    'CommandResult',
    'RiskLevel',
    'LogLevel'
]
