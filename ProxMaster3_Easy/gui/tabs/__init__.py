#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Модуль вкладок
Импорт всех классов вкладок из отдельных файлов
"""

from .home_tab import HomeTab
from .search_tab import SearchTab
from .data_tab import DataTab
from .write_tab import WriteTab
from .emulate_tab import EmulateTab
from .sniff_tab import SniffTab
from .scripts_tab import ScriptsTab
from .tools_tab import ToolsTab
from .settings_tab import SettingsTab

__all__ = [
    'HomeTab',
    'SearchTab',
    'DataTab',
    'WriteTab',
    'EmulateTab',
    'SniffTab',
    'ScriptsTab',
    'ToolsTab',
    'SettingsTab'
]
