#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster Pro - Точка входа в приложение
Запуск GUI приложения
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_app import main

if __name__ == '__main__':
    print("=" * 60)
    print("  ProxMaster Pro v1.0.0")
    print("  Профессиональный инструмент для управления Proxmark3")
    print("=" * 60)
    print()
    print("Запуск приложения...")
    print()
    
    main()
