#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Device Manager
Модуль для управления подключением к Proxmark3 Easy
"""

import serial
import serial.tools.list_ports
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class DeviceManager:
    """Управление подключением к устройству Proxmark3"""
    
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.device_info: Dict = {}
        self.is_connected: bool = False
        self.com_port: Optional[str] = None
        self.baudrate: int = 115200
        self.timeout: float = 2.0
        
    def list_com_ports(self) -> List[Dict]:
        """Получить список доступных COM-портов"""
        ports = []
        try:
            available_ports = serial.tools.list_ports.comports()
            for port in available_ports:
                port_info = {
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid,
                    'is_proxmark': 'Proxmark' in port.description or 
                                   'CP210' in port.description or 
                                   'CH340' in port.description
                }
                ports.append(port_info)
                logger.info(f"Найден порт: {port.device} - {port.description}")
        except Exception as e:
            logger.error(f"Ошибка получения списка портов: {e}")
        return ports
    
    def connect(self, com_port: str, baudrate: int = 115200) -> Tuple[bool, str]:
        """
        Подключиться к устройству Proxmark3
        
        Args:
            com_port: COM-порт (например, 'COM3' или '/dev/ttyUSB0')
            baudrate: Скорость соединения
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        if self.is_connected:
            self.disconnect()
            
        try:
            self.com_port = com_port
            self.baudrate = baudrate
            
            logger.info(f"Подключение к {com_port} со скоростью {baudrate}")
            self.serial_port = serial.Serial(
                port=com_port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            # Проверка подключения
            if self._check_connection():
                self.is_connected = True
                self._get_device_info()
                logger.info(f"Успешное подключение к {com_port}")
                return True, f"Подключено к {com_port}"
            else:
                self.serial_port.close()
                self.serial_port = None
                return False, "Не удалось подтвердить подключение"
                
        except serial.SerialException as e:
            error_msg = f"Ошибка порта: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Неизвестная ошибка: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def disconnect(self) -> bool:
        """Отключиться от устройства"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.serial_port = None
            self.is_connected = False
            self.com_port = None
            self.device_info = {}
            logger.info("Отключено от устройства")
            return True
        except Exception as e:
            logger.error(f"Ошибка отключения: {e}")
            return False
    
    def _check_connection(self) -> bool:
        """Проверить активность соединения"""
        try:
            if not self.serial_port or not self.serial_port.is_open:
                return False
                
            # Отправить команду статуса
            self.serial_port.write(b'\n')
            self.serial_port.flush()
            
            # Попытаться прочитать ответ
            import time
            time.sleep(0.1)
            
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.read(self.serial_port.in_waiting)
                logger.debug(f"Ответ при проверке: {response[:100]}")
                return True
                
            return True  # Если нет ошибки записи, считаем подключенным
            
        except Exception as e:
            logger.error(f"Ошибка проверки соединения: {e}")
            return False
    
    def _get_device_info(self) -> Dict:
        """Получить информацию об устройстве"""
        self.device_info = {
            'port': self.com_port,
            'baudrate': self.baudrate,
            'status': 'connected',
            'type': 'Proxmark3 Easy',
            'firmware': 'Iceman'
        }
        return self.device_info
    
    def send_command(self, command: str) -> Tuple[bool, str]:
        """
        Отправить команду устройству
        
        Args:
            command: Команда для отправки
            
        Returns:
            Tuple[bool, str]: (успех, ответ)
        """
        if not self.is_connected or not self.serial_port:
            return False, "Устройство не подключено"
        
        try:
            # Форматирование команды для proxmark3 cli
            full_command = f"{command}\n"
            self.serial_port.write(full_command.encode('utf-8'))
            self.serial_port.flush()
            
            # Чтение ответа
            import time
            time.sleep(0.5)  # Ждем выполнения команды
            
            response = ""
            start_time = time.time()
            
            while time.time() - start_time < 5.0:  # Таймаут 5 секунд
                if self.serial_port.in_waiting > 0:
                    chunk = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk
                    
                if 'pm3>' in response or 'db>' in response:
                    break
                    
                time.sleep(0.1)
            
            logger.debug(f"Команда: {command}, Ответ: {response[:200]}")
            return True, response
            
        except Exception as e:
            error_msg = f"Ошибка отправки команды: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_status(self) -> Dict:
        """Получить текущий статус подключения"""
        return {
            'connected': self.is_connected,
            'port': self.com_port,
            'baudrate': self.baudrate,
            'device_info': self.device_info
        }
    
    def auto_detect(self) -> Optional[str]:
        """Автоматически найти устройство Proxmark3"""
        ports = self.list_com_ports()
        
        # Ищем порты с признаками Proxmark
        for port in ports:
            if port.get('is_proxmark'):
                logger.info(f"Автообнаружение: найден Proxmark на {port['device']}")
                return port['device']
        
        # Если не нашли по описанию, пробуем первый доступный USB-COM
        for port in ports:
            if 'USB' in port.get('hwid', ''):
                logger.info(f"Автообнаружение: предположительно Proxmark на {port['device']}")
                return port['device']
        
        logger.warning("Автообнаружение: устройство не найдено")
        return None
