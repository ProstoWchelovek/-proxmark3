#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster Pro - Точка запуска приложения
"""

import sys
import os

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_app import main

if __name__ == "__main__":
    main()
