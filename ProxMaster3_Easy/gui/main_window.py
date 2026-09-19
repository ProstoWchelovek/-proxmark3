#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Главное окно приложения
Основной интерфейс с 9 вкладками
"""

import sys
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QLabel, QPushButton, QStatusBar,
                             QMenuBar, QMenu, QAction, QMessageBox, QToolBar,
                             QSystemTrayIcon, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QActionGroup

from ..core.device_manager import DeviceManager
from ..core.command_executor import CommandExecutor
from ..core.data_manager import DataManager

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Главное окно приложения ProxMaster3 Easy"""
    
    # Сигналы для обновления статуса
    status_changed = pyqtSignal(str)
    device_connected = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        
        # Инициализация компонентов
        self.device_manager = DeviceManager()
        self.command_executor = CommandExecutor(self.device_manager)
        self.data_manager = DataManager()
        
        # Настройка окна
        self.setWindowTitle("ProxMaster3 Easy v2.0 - Proxmark3 Iceman GUI")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(self._get_dark_style())
        
        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создание вкладок
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        main_layout.addWidget(self.tab_widget)
        
        # Создание вкладок
        self._create_tabs()
        
        # Создание меню
        self._create_menu_bar()
        
        # Создание статусной строки
        self._create_status_bar()
        
        # Таймер автообновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_device_status)
        self.status_timer.start(5000)  # Обновление каждые 5 секунд
        
        # Загрузка состояния
        self._load_saved_state()
        
        logger.info("Главное окно инициализировано")
    
    def _create_tabs(self):
        """Создать все вкладки интерфейса"""
        
        # Вкладка 1: ГЛАВНАЯ
        from .tabs.home_tab import HomeTab
        self.home_tab = HomeTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.home_tab, "🏠 Главная")
        
        # Вкладка 2: ПОИСК
        from .tabs.search_tab import SearchTab
        self.search_tab = SearchTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.search_tab, "🔍 Поиск")
        
        # Вкладка 3: МЕНЕДЖЕР ДАННЫХ
        from .tabs.data_tab import DataTab
        self.data_tab = DataTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.data_tab, "💾 Менеджер данных")
        
        # Вкладка 4: ЗАПИСЬ
        from .tabs.write_tab import WriteTab
        self.write_tab = WriteTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.write_tab, "✏️ Запись")
        
        # Вкладка 5: ЭМУЛЯЦИЯ
        from .tabs.emulate_tab import EmulateTab
        self.emulate_tab = EmulateTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.emulate_tab, "🎭 Эмуляция")
        
        # Вкладка 6: СНИФИНГ
        from .tabs.sniff_tab import SniffTab
        self.sniff_tab = SniffTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.sniff_tab, "📡 Снифинг")
        
        # Вкладка 7: СКРИПТЫ
        from .tabs.scripts_tab import ScriptsTab
        self.scripts_tab = ScriptsTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.scripts_tab, "📜 Скрипты")
        
        # Вкладка 8: ИНСТРУМЕНТЫ
        from .tabs.tools_tab import ToolsTab
        self.tools_tab = ToolsTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.tools_tab, "🛠️ Инструменты")
        
        # Вкладка 9: НАСТРОЙКИ
        from .tabs.settings_tab import SettingsTab
        self.settings_tab = SettingsTab(self.device_manager, self.command_executor, self.data_manager)
        self.tab_widget.addTab(self.settings_tab, "⚙️ Настройки")
        
        logger.info("Создано 9 вкладок интерфейса")
    
    def _create_menu_bar(self):
        """Создать главное меню"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("📁 Файл")
        
        open_action = QAction("📂 Открыть дамп", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(lambda: self.data_tab.load_dump_file())
        file_menu.addAction(open_action)
        
        save_action = QAction("💾 Сохранить дамп", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.data_tab.save_current_dump())
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Устройство
        device_menu = menubar.addMenu("🔌 Устройство")
        
        connect_action = QAction("🔌 Подключиться", self)
        connect_action.triggered.connect(lambda: self.home_tab.connect_device())
        device_menu.addAction(connect_action)
        
        disconnect_action = QAction("❌ Отключиться", self)
        disconnect_action.triggered.connect(lambda: self.home_tab.disconnect_device())
        device_menu.addAction(disconnect_action)
        
        device_menu.addSeparator()
        
        refresh_action = QAction("🔄 Обновить порты", self)
        refresh_action.triggered.connect(lambda: self.home_tab.refresh_ports())
        device_menu.addAction(refresh_action)
        
        # Меню Помощь
        help_menu = menubar.addMenu("❓ Помощь")
        
        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction("📖 Документация", self)
        docs_action.triggered.connect(self._open_docs)
        help_menu.addAction(docs_action)
        
        check_updates_action = QAction("🔄 Проверить обновления", self)
        check_updates_action.triggered.connect(lambda: self.settings_tab.check_for_updates())
        help_menu.addAction(check_updates_action)
    
    def _create_status_bar(self):
        """Создать статусную строку"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Левая часть - статус устройства
        self.device_status_label = QLabel("🔴 Устройство не подключено")
        self.device_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        self.statusbar.addPermanentWidget(self.device_status_label)
        
        # Центральная часть - текущая операция
        self.operation_label = QLabel("Готов к работе")
        self.statusbar.addWidget(self.operation_label, 1)
        
        # Правая часть - версия
        version_label = QLabel("v2.0.0")
        version_label.setStyleSheet("color: #888888;")
        self.statusbar.addPermanentWidget(version_label)
        
        # Подключение сигналов
        self.device_connected.connect(self._on_device_connected)
    
    def _on_device_connected(self, connected: bool):
        """Обработчик изменения статуса подключения"""
        if connected:
            self.device_status_label.setText("🟢 Устройство подключено")
            self.device_status_label.setStyleSheet("color: #44ff44; font-weight: bold;")
            port = self.device_manager.com_port
            self.operation_label.setText(f"Подключено к {port}")
        else:
            self.device_status_label.setText("🔴 Устройство не подключено")
            self.device_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
            self.operation_label.setText("Ожидание подключения")
    
    def _update_device_status(self):
        """Периодическое обновление статуса устройства"""
        if self.device_manager.is_connected:
            if not self.device_manager.serial_port or not self.device_manager.serial_port.is_open:
                self.device_manager.is_connected = False
                self.device_connected.emit(False)
                logger.warning("Соединение с устройством потеряно")
    
    def _load_saved_state(self):
        """Загрузить сохраненное состояние"""
        # Здесь можно загрузить последние настройки из конфига
        logger.debug("Загрузка сохраненного состояния")
    
    def _show_about(self):
        """Показать диалог о программе"""
        QMessageBox.about(
            self,
            "О программе ProxMaster3 Easy",
            """<h2>ProxMaster3 Easy v2.0</h2>
            <p>Профессиональное приложение для работы с Proxmark3 Easy</p>
            <p><b>Прошивка:</b> Iceman Fork</p>
            <p><b>Команд:</b> 857+</p>
            <p><b>Вкладок:</b> 9</p>
            <br>
            <p>© 2024 ProxMaster Team</p>
            <p>Лицензия: MIT</p>
            """
        )
    
    def _open_docs(self):
        """Открыть документацию"""
        import webbrowser
        webbrowser.open("https://github.com/RfidResearchGroup/proxmark3")
    
    def _get_dark_style(self) -> str:
        """Темная тема оформления"""
        return """
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QTabWidget::pane {
            border: 1px solid #333333;
            background-color: #252525;
            border-radius: 5px;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #cccccc;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        QTabBar::tab:selected {
            background-color: #1e88e5;
            color: white;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #3d3d3d;
        }
        
        QPushButton {
            background-color: #1e88e5;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #42a5f5;
        }
        
        QPushButton:pressed {
            background-color: #1565c0;
        }
        
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 5px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #1e88e5;
        }
        
        QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 5px;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444444;
        }
        
        QGroupBox {
            background-color: #252525;
            border: 1px solid #333333;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: #1e88e5;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        
        QTableWidget, QTreeWidget, QListWidget {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444444;
            border-radius: 4px;
        }
        
        QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
            background-color: #1e88e5;
        }
        
        QHeaderView::section {
            background-color: #333333;
            color: #ffffff;
            padding: 5px;
            border: none;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QProgressBar {
            background-color: #2d2d2d;
            border: none;
            border-radius: 4px;
            height: 20px;
        }
        
        QProgressBar::chunk {
            background-color: #1e88e5;
            border-radius: 4px;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QStatusBar {
            background-color: #252525;
            color: #cccccc;
        }
        
        QMenuBar {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QMenuBar::item:selected {
            background-color: #333333;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444444;
        }
        
        QMenu::item:selected {
            background-color: #1e88e5;
        }
        """
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        # Сохранение состояния перед закрытием
        logger.info("Закрытие приложения")
        
        # Отключение от устройства
        if self.device_manager.is_connected:
            self.device_manager.disconnect()
        
        event.accept()
