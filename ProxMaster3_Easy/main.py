#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Главный файл запуска приложения
Точка входа в приложение
"""

import sys
import os
from pathlib import Path

# Добавление корневой директории в путь импорта
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Настройка логирования
from utils.logger_setup import setup_logging
setup_logging(log_dir=root_dir / 'logs')

import logging
logger = logging.getLogger(__name__)

def check_dependencies():
    """Проверить наличие всех зависимостей"""
    missing = []
    
    try:
        import PyQt6
    except ImportError:
        missing.append('PyQt6')
    
    try:
        import serial
    except ImportError:
        missing.append('pyserial')
    
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    if missing:
        logger.error(f"Отсутствуют зависимости: {', '.join(missing)}")
        print(f"❌ Отсутствуют необходимые библиотеки: {', '.join(missing)}")
        print("\nУстановите их командой:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    logger.info("Все зависимости найдены")
    return True

def main():
    """Основная функция запуска приложения"""
    logger.info("=" * 50)
    logger.info("ProxMaster3 Easy v2.0 - Запуск приложения")
    logger.info("=" * 50)
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Импорт PyQt6 после проверки зависимостей
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    
    # Настройка приложения
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("ProxMaster3 Easy")
    app.setOrganizationName("ProxMaster Team")
    app.setStyle("Fusion")
    
    # Установка шрифта по умолчанию
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Импорт главного окна
    from gui.main_window import MainWindow
    
    # Создание и показ главного окна
    window = MainWindow()
    window.show()
    
    logger.info("Главное окно показано")
    
    # Запуск цикла событий
    exit_code = app.exec()
    
    logger.info(f"Приложение завершено с кодом: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
