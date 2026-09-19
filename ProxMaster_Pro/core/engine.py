# ProxMaster Pro - Ядро приложения
"""
Ядро приложения ProxMaster Pro
Управление командами, связь с устройством, обработка данных
"""

import json
import serial
import serial.tools.list_ports
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Уровни риска операций"""
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"


@dataclass
class CommandResult:
    """Результат выполнения команды"""
    success: bool
    output: str
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class LogEntry:
    """Запись лога"""
    level: str
    message: str
    timestamp: datetime
    category: str = ""
    
    def to_string(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] [{self.level}] {self.message}"


class CommunicationLayer:
    """Слой связи с устройством Proxmark3"""
    
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.port_name: str = ""
        self.baudrate: int = 115200
        self.timeout: int = 5
        self._read_thread: Optional[threading.Thread] = None
        self._stop_read = False
        self._buffer = bytearray()
        self.on_data_received: Optional[Callable[[str], None]] = None
        
    def list_ports(self) -> List[Dict[str, str]]:
        """Получить список доступных COM портов"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Подключиться к устройству"""
        try:
            if self.is_connected:
                self.disconnect()
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.port_name = port
            self.baudrate = baudrate
            self.is_connected = True
            self._buffer.clear()
            
            # Запуск потока чтения
            self._stop_read = False
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Отключиться от устройства"""
        self._stop_read = True
        if self._read_thread:
            self._read_thread.join(timeout=2)
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.serial_port = None
        self.is_connected = False
        self.port_name = ""
    
    def _read_loop(self):
        """Цикл чтения данных из порта"""
        while not self._stop_read and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    self._buffer.extend(data)
                    
                    # Обработка полных строк
                    while b'\n' in self._buffer:
                        line_end = self._buffer.index(b'\n')
                        line = self._buffer[:line_end].decode('utf-8', errors='ignore').strip()
                        self._buffer = self._buffer[line_end + 1:]
                        
                        if line and self.on_data_received:
                            self.on_data_received(line)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if not self._stop_read:
                    print(f"Ошибка чтения: {e}")
                break
    
    def write(self, data: str) -> bool:
        """Отправить данные в порт"""
        if not self.is_connected or not self.serial_port:
            return False
        
        try:
            command = data + '\n'
            self.serial_port.write(command.encode('utf-8'))
            self.serial_port.flush()
            return True
        except Exception as e:
            print(f"Ошибка записи: {e}")
            return False
    
    def write_and_read(self, command: str, timeout: int = 5000) -> str:
        """Отправить команду и получить ответ"""
        if not self.is_connected or not self.serial_port:
            return ""
        
        try:
            # Очистка буфера
            self._buffer.clear()
            
            # Отправка команды
            self.write(command)
            
            # Ожидание ответа
            start_time = time.time()
            output_lines = []
            timeout_sec = timeout / 1000.0
            
            while time.time() - start_time < timeout_sec:
                if self._buffer:
                    try:
                        text = self._buffer.decode('utf-8', errors='ignore')
                        lines = text.split('\n')
                        
                        # Обрабатываем все кроме последнего (может быть неполным)
                        for line in lines[:-1]:
                            if line.strip():
                                output_lines.append(line.strip())
                        
                        # Проверяем конец вывода
                        full_text = '\n'.join(output_lines)
                        if 'dbug' in full_text.lower() or len(lines) > 1 and lines[-1] == '':
                            break
                    except:
                        pass
                
                time.sleep(0.05)
            
            # Добавляем оставшееся
            if self._buffer:
                try:
                    remaining = self._buffer.decode('utf-8', errors='ignore').strip()
                    if remaining:
                        output_lines.append(remaining)
                except:
                    pass
            
            return '\n'.join(output_lines)
            
        except Exception as e:
            return f"Ошибка: {e}"


class CommandManager:
    """Менеджер команд Proxmark3"""
    
    def __init__(self, comm: CommunicationLayer):
        self.comm = comm
        self.commands_db: Dict[str, Any] = {}
        self.categories: List[Dict] = []
        self.current_log: List[LogEntry] = []
        self.max_log_size = 1000
        
    def load_commands(self, filepath: str) -> bool:
        """Загрузить базу команд из JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.commands_db = data
            self.categories = data.get('categories', [])
            
            # Индексация команд по ID
            self._command_index = {}
            for cat in self.categories:
                for cmd in cat.get('commands', []):
                    self._command_index[cmd['id']] = cmd
            
            return True
        except Exception as e:
            print(f"Ошибка загрузки команд: {e}")
            return False
    
    def get_command(self, cmd_id: str) -> Optional[Dict]:
        """Получить команду по ID"""
        return self._command_index.get(cmd_id)
    
    def get_commands_by_tab(self, tab_name: str) -> List[Dict]:
        """Получить все команды для вкладки"""
        result = []
        for cat in self.categories:
            if cat.get('tab') == tab_name:
                result.extend(cat.get('commands', []))
        return result
    
    def get_categories_for_tab(self, tab_name: str) -> List[Dict]:
        """Получить категории для вкладки"""
        return [cat for cat in self.categories if cat.get('tab') == tab_name]
    
    def build_command(self, cmd_id: str, params: Dict[str, Any] = None) -> Optional[str]:
        """Построить команду для отправки"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            return None
        
        template = cmd.get('template', '')
        
        if not params:
            return template
        
        # Замена параметров в шаблоне
        result = template
        for param_name, param_value in params.items():
            placeholder = '{' + param_name + '}'
            result = result.replace(placeholder, str(param_value))
        
        return result
    
    def execute_command(self, cmd_id: str, params: Dict[str, Any] = None, 
                       timeout: int = None) -> CommandResult:
        """Выполнить команду"""
        start_time = time.time()
        
        # Построение команды
        command = self.build_command(cmd_id, params)
        if not command:
            return CommandResult(
                success=False,
                output="",
                error=f"Команда {cmd_id} не найдена"
            )
        
        # Получение таймаута
        cmd = self.get_command(cmd_id)
        if cmd and timeout is None:
            timeout = cmd.get('timeout', 5000)
        elif timeout is None:
            timeout = 5000
        
        # Выполнение
        output = self.comm.write_and_read(command, timeout)
        
        duration = time.time() - start_time
        
        # Анализ результата
        success = len(output) > 0 and 'error' not in output.lower()
        
        return CommandResult(
            success=success,
            output=output,
            error=None if success else "Не получен корректный ответ",
            duration=duration
        )
    
    def add_log(self, level: str, message: str, category: str = ""):
        """Добавить запись в лог"""
        entry = LogEntry(
            level=level,
            message=message,
            timestamp=datetime.now(),
            category=category
        )
        self.current_log.append(entry)
        
        # Ограничение размера лога
        if len(self.current_log) > self.max_log_size:
            self.current_log = self.current_log[-self.max_log_size:]
    
    def get_log(self) -> List[LogEntry]:
        """Получить текущий лог"""
        return self.current_log
    
    def clear_log(self):
        """Очистить лог"""
        self.current_log = []


class DataManager:
    """Менеджер данных (дампы, ключи, логи)"""
    
    def __init__(self, base_path: str = "data/user_data"):
        self.base_path = base_path
        self.cards: List[Dict] = []
        self.keys: List[Dict] = []
        
    def save_card(self, uid: str, data: Dict) -> bool:
        """Сохранить информацию о карте"""
        card = {
            'uid': uid,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.cards.append(card)
        return True
    
    def save_key(self, uid: str, key_type: str, key: str, block: int = 0) -> bool:
        """Сохранить ключ"""
        key_entry = {
            'uid': uid,
            'key_type': key_type,
            'key': key,
            'block': block,
            'timestamp': datetime.now().isoformat()
        }
        self.keys.append(key_entry)
        return True
    
    def find_keys_for_uid(self, uid: str) -> List[Dict]:
        """Найти ключи для UID"""
        return [k for k in self.keys if k['uid'] == uid]
    
    def export_to_file(self, filename: str, data_type: str) -> bool:
        """Экспорт данных в файл"""
        import os
        filepath = os.path.join(self.base_path, filename)
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                if data_type == 'cards':
                    json.dump(self.cards, f, indent=2, ensure_ascii=False)
                elif data_type == 'keys':
                    json.dump(self.keys, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False
    
    def import_from_file(self, filename: str, data_type: str) -> bool:
        """Импорт данных из файла"""
        import os
        filepath = os.path.join(self.base_path, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data_type == 'cards':
                self.cards.extend(data)
            elif data_type == 'keys':
                self.keys.extend(data)
            
            return True
        except Exception as e:
            print(f"Ошибка импорта: {e}")
            return False


class ProxMasterEngine:
    """Основной движок приложения"""
    
    def __init__(self, commands_file: str = "data/commands.json"):
        self.comm = CommunicationLayer()
        self.cmd_manager = CommandManager(self.comm)
        self.data_manager = DataManager()
        
        # Загрузка команд
        if not self.cmd_manager.load_commands(commands_file):
            print("Предупреждение: Не удалось загрузить базу команд")
        
        # Подключение обработчика данных
        self.comm.on_data_received = self._on_data_received
    
    def _on_data_received(self, data: str):
        """Обработчик полученных данных"""
        self.cmd_manager.add_log("INFO", data, "DEVICE")
    
    def connect(self, port: str) -> bool:
        """Подключиться к устройству"""
        return self.comm.connect(port)
    
    def disconnect(self):
        """Отключиться от устройства"""
        self.comm.disconnect()
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.comm.is_connected
    
    def get_ports(self) -> List[Dict[str, str]]:
        """Получить список портов"""
        return self.comm.list_ports()
    
    def execute(self, cmd_id: str, params: Dict = None, timeout: int = None) -> CommandResult:
        """Выполнить команду"""
        result = self.cmd_manager.execute_command(cmd_id, params, timeout)
        
        # Логирование
        level = "SUCCESS" if result.success else "ERROR"
        self.cmd_manager.add_log(level, f"{cmd_id}: {result.output[:100]}")
        
        return result
    
    def get_commands_for_tab(self, tab: str) -> List[Dict]:
        """Получить команды для вкладки"""
        return self.cmd_manager.get_commands_by_tab(tab)
    
    def get_categories_for_tab(self, tab: str) -> List[Dict]:
        """Получить категории для вкладки"""
        return self.cmd_manager.get_categories_for_tab(tab)
    
    def get_log(self) -> List[LogEntry]:
        """Получить лог"""
        return self.cmd_manager.get_log()
    
    def clear_log(self):
        """Очистить лог"""
        self.cmd_manager.clear_log()
