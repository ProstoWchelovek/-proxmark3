#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ПОИСК
Поиск и чтение RFID карт с раскрывающимися меню и подсказками
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QTextEdit, QGridLayout,
                             QToolButton, QMenu, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

class SearchTab(QWidget):
    """Вкладка Поиск - поиск и чтение карт"""

    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        # Подсказки для команд поиска
        self.search_hints = {
            "lf search": "🔍 Поиск LF карт (125 kHz) - EM410x, T55xx, HID и др.",
            "hf search": "🔍 Поиск HF карт (13.56 MHz) - Mifare, ISO14443A/B",
            "hf read": "📖 Прочитать данные HF карты",
            "hf detect": "🎯 Автоматическое определение типа карты",
            "lf em410x read": "📖 Читать EM410x (стандартные 125 kHz карты)",
            "lf hid read": "📖 Читать HID Prox (корпоративные карты)",
            "lf indala read": "📖 Читать Indala (карты контроля доступа)",
            "hf 14a reader": "📡 Режим читателя ISO14443-A",
            "hf 14b reader": "📡 Режим читателя ISO14443-B"
        }
        
        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Панель быстрого поиска
        quick_search_group = self._create_quick_search_panel()
        layout.addWidget(quick_search_group)
        
        # Панель протоколов LF
        lf_group = self._create_lf_protocols_panel()
        layout.addWidget(lf_group)
        
        # Панель протоколов HF
        hf_group = self._create_hf_protocols_panel()
        layout.addWidget(hf_group)
        
        # Лог
        log_group = self._create_log_panel()
        layout.addWidget(log_group, 1)

    def _create_quick_search_panel(self) -> QGroupBox:
        """Панель быстрого поиска с раскрывающимися кнопками"""
        group = QGroupBox("⚡ Быстрый поиск")
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # Кнопка LF поиск
        btn_lf = self._create_dropdown_button(
            "📡 LF Поиск",
            ["lf search", "lf em410x read", "lf hid read", "lf indala read"],
            ["Поиск всех LF карт", "Читать EM410x", "Читать HID", "Читать Indala"],
            "🔍 Поиск LF карт на частоте 125 kHz"
        )
        layout.addWidget(btn_lf, 0, 0)
        
        # Кнопка HF поиск
        btn_hf = self._create_dropdown_button(
            "📡 HF Поиск",
            ["hf search", "hf read", "hf detect", "hf 14a reader"],
            ["Поиск всех HF карт", "Прочитать карту", "Определить тип", "Режим 14A"],
            "🔍 Поиск HF карт на частоте 13.56 MHz"
        )
        layout.addWidget(btn_hf, 0, 1)
        
        # Кнопка Полный скан
        btn_full = self._create_dropdown_button(
            "🔍 Полный скан",
            ["lf search u", "hf search", "hf 14a s"],
            ["LF с UID", "HF полный", "14A с серийником"],
            "🔍 Полное сканирование всех частот"
        )
        layout.addWidget(btn_full, 0, 2)
        
        group.setLayout(layout)
        return group

    def _create_lf_protocols_panel(self) -> QGroupBox:
        """Панель LF протоколов"""
        group = QGroupBox("📻 LF Протоколы (125 kHz)")
        layout = QGridLayout()
        layout.setSpacing(8)
        
        protocols = [
            ("EM410x", "lf em410x read", "Стандартные карты 125 kHz"),
            ("T55xx", "lf t55xx read", "Перезаписываемые карты"),
            ("HID Prox", "lf hid read", "Корпоративные карты HID"),
            ("Indala", "lf indala read", "Карты Motorola Indala"),
            ("AWID", "lf awid read", "Системы контроля AWID"),
            ("Viking", "lf viking read", "Карты Viking"),
            ("Cerberus", "lf cerberus read", "Системы Cerberus"),
            ("Fudan", "lf fudan read", "Китайские карты Fudan"),
            ("Hitag2", "lf hitag2 read", "Автомобильные ключи"),
            ("PCF7930", "lf pcf7930 read", "Чипы NXP PCF7930"),
            ("EM4200", "lf em4200 read", "Карты EM4200"),
            ("Keri", "lf keri read", "Системы Keri"),
            ("PAC/Stanley", "lf pac read", "Карты Stanley"),
            ("NexWatch", "lf nexwatch read", "Браслеты NexWatch"),
            ("IOProx", "lf ioprox read", "Карты IOProx"),
            ("Visa2000", "lf visa2000 read", "Карты Visa2000"),
            ("Cotag", "lf cotag read", "Системы Cotag"),
            ("Linear", "lf linear read", "Системы Linear"),
            ("GProx", "lf gprox read", "Карты GProx"),
            ("Farpointe", "lf farpointe read", "Карты Farpointe")
        ]
        
        row = 0
        col = 0
        for name, cmd, hint in protocols:
            btn = QPushButton(name)
            btn.setToolTip(f"{hint}\nКоманда: {cmd}")
            btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
            layout.addWidget(btn, row, col)
            col += 1
            if col > 4:
                col = 0
                row += 1
        
        group.setLayout(layout)
        return group

    def _create_hf_protocols_panel(self) -> QGroupBox:
        """Панель HF протоколов"""
        group = QGroupBox("📶 HF Протоколы (13.56 MHz)")
        layout = QGridLayout()
        layout.setSpacing(8)
        
        protocols = [
            ("ISO14443A", "hf 14a reader", "Стандарт ISO14443-A"),
            ("ISO14443B", "hf 14b reader", "Стандарт ISO14443-B"),
            ("Mifare Classic", "hf mf reader", "Карты Mifare Classic 1K/4K"),
            ("Mifare Ultralight", "hf mfu reader", "Карты Ultralight"),
            ("Mifare DESFire", "hf df reader", "Карты DESFire"),
            ("iClass", "hf iclass reader", "Карты HID iClass"),
            ("LEGIC", "hf legic reader", "Карты LEGIC"),
            ("FeliCa", "hf felica reader", "Японские карты FeliCa"),
            ("ISO15693", "hf 15 reader", "Стандарт ISO15693"),
            ("Tag-it", "hf tagit reader", "Карты Tag-it"),
            ("My-d", "hf myd reader", "Карты My-d"),
            ("SR", "hf sr reader", "Карты ST SR"),
            ("SRI", "hf sri reader", "Карты SRI"),
            ("EMV", "hf emv scan", "Банковские карты EMV"),
            ("NFC", "hf nfc scan", "NFC устройства")
        ]
        
        row = 0
        col = 0
        for name, cmd, hint in protocols:
            btn = QPushButton(name)
            btn.setToolTip(f"{hint}\nКоманда: {cmd}")
            btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
            layout.addWidget(btn, row, col)
            col += 1
            if col > 4:
                col = 0
                row += 1
        
        group.setLayout(layout)
        return group

    def _create_log_panel(self) -> QGroupBox:
        """Панель лога"""
        group = QGroupBox("📝 Результаты поиска")
        layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 10))
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_output)
        
        group.setLayout(layout)
        return group

    def _create_dropdown_button(self, text, commands, descriptions, tooltip) -> QToolButton:
        """Создать кнопку с раскрывающимся меню"""
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setStyleSheet("""
            QToolButton {
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QToolButton:hover {
                background-color: #1976D2;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        menu = QMenu(btn)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                margin: 2px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #ddd;
                margin: 5px;
            }
        """)
        
        for cmd, desc in zip(commands, descriptions):
            action = menu.addAction(desc)
            action.setToolTip(self.search_hints.get(cmd, f"Команда: {cmd}"))
            action.triggered.connect(lambda checked, c=cmd: self.execute_command(c))
        
        btn.setMenu(menu)
        return btn

    def execute_command(self, command):
        """Выполнить команду поиска"""
        if not self.device_manager.is_connected():
            self.log_message("❌ Сначала подключитесь к устройству!")
            return
        
        hint = self.search_hints.get(command, "")
        if hint:
            self.log_message(f"ℹ️ {hint}")
        
        self.log_message(f"▶️ Выполнение: {command}")
        
        if hasattr(self, 'command_executor') and self.command_executor:
            result = self.command_executor.execute(command)
            if result:
                self.log_message(f"✅ Результат:\n{result}")
        else:
            result = self.device_manager.send_command(command)
            if result:
                self.log_message(f"✅ Получен ответ:\n{result}")

    def log_message(self, message):
        """Добавить сообщение в лог"""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
