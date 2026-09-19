#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Настройка логирования
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """
    Настроить систему логирования
    
    Args:
        log_dir: Директория для логов
        level: Уровень логирования
    """
    # Создание директории для логов
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Имя файла лога с датой
    log_file = log_path / f"proxmaster_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Настройка формата сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Логирование запуска
    logging.info(f"Логирование настроено. Файл: {log_file}")
