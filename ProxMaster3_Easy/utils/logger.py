"""
ProxMaster3 Easy - Модуль логирования
Профессиональная система логирования с цветами и уровнями
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProxMasterLogger:
    """Кастомный логгер для приложения с цветным выводом"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("ProxMaster3")
        self.logger.setLevel(logging.DEBUG)
        
        # Очистка существующих обработчиков
        self.logger.handlers.clear()
        
        # Консольный обработчик с цветами
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Файловый обработчик
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(module)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Информационное сообщение"""
        self.logger.info(message)
    
    def success(self, message: str):
        """Сообщение об успехе (зеленый)"""
        self.logger.log(SUCCESS_LEVEL, message)
    
    def warning(self, message: str):
        """Предупреждение (желтый)"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Ошибка (красный)"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Отладочное сообщение"""
        self.logger.debug(message)


# Пользовательский уровень для успешных операций
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для разных уровней"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'SUCCESS': '\033[92m',    # Bright Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[95m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_level = record.levelname
        color = self.COLORS.get(log_level, self.RESET)
        record.levelname = f"{color}{log_level}{self.RESET}"
        return super().format(record)


# Глобальный экземпляр логгера
proxmaster_logger: Optional[ProxMasterLogger] = None


def get_logger(log_file: Optional[str] = None) -> ProxMasterLogger:
    """Получение экземпляра логгера"""
    global proxmaster_logger
    if proxmaster_logger is None:
        proxmaster_logger = ProxMasterLogger(log_file)
    return proxmaster_logger
