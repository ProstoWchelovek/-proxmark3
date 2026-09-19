"""
ProxMaster3 Easy - Модуль подключения к устройству
Реализация связи с Proxmark3 через COM-порт
"""

import serial
import serial.tools.list_ports
import threading
import queue
import time
from typing import Optional, Callable, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class DeviceConnector(QObject):
    """Класс для подключения и работы с Proxmark3 через COM-порт"""
    
    connected = pyqtSignal(bool, str)  # Успех, сообщение
    data_received = pyqtSignal(str)  # Полученные данные
    command_sent = pyqtSignal(str)  # Отправленная команда
    error_occurred = pyqtSignal(str)  # Ошибка
    
    def __init__(self):
        super().__init__()
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.read_thread: Optional[threading.Thread] = None
        self.stop_flag = False
        self.command_queue = queue.Queue()
        
    def list_ports(self) -> List[Dict[str, str]]:
        """Получение списка доступных COM-портов"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Подключение к устройству"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect()
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            
            self.is_connected = True
            self.stop_flag = False
            
            # Запуск потока чтения
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            self.connected.emit(True, f"Подключено к {port}")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка подключения: {str(e)}"
            self.error_occurred.emit(error_msg)
            self.connected.emit(False, error_msg)
            return False
    
    def disconnect(self):
        """Отключение от устройства"""
        self.stop_flag = True
        self.is_connected = False
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
    
    def send_command(self, command: str) -> bool:
        """Отправка команды устройству"""
        if not self.is_connected or not self.serial_port:
            self.error_occurred.emit("Устройство не подключено")
            return False
        
        try:
            # Добавляем перевод строки если нужно
            if not command.endswith('\n'):
                command += '\n'
            
            self.serial_port.write(command.encode('utf-8'))
            self.serial_port.flush()
            self.command_sent.emit(command.strip())
            return True
            
        except Exception as e:
            error_msg = f"Ошибка отправки: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False
    
    def _read_loop(self):
        """Цикл чтения данных из порта"""
        while not self.stop_flag and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    if data:
                        self.data_received.emit(data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if not self.stop_flag:
                    self.error_occurred.emit(f"Ошибка чтения: {str(e)}")
                break
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса подключения"""
        return {
            'connected': self.is_connected,
            'port': self.serial_port.portstr if self.serial_port else None,
            'baudrate': self.serial_port.baudrate if self.serial_port else None
        }
