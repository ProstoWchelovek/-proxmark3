# ProxMaster3 Easy - GUI Module
"""
Графический интерфейс приложения
Компоненты PyQt6
"""

from .main_window import MainWindow
from .tabs.home_tab import HomeTab
from .tabs.search_tab import SearchTab
from .tabs.data_tab import DataTab
from .tabs.write_tab import WriteTab
from .tabs.emulate_tab import EmulateTab
from .tabs.sniff_tab import SniffTab
from .tabs.scripts_tab import ScriptsTab
from .tabs.tools_tab import ToolsTab
from .tabs.settings_tab import SettingsTab

__all__ = [
    'MainWindow',
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
