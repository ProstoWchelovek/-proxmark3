#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ГЛАВНАЯ
Быстрый доступ к основным функциям устройства с раскрывающимися меню и подсказками
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGroupBox, QTextEdit,
                             QGridLayout, QFrame, QProgressBar, QToolButton,
                             QMenu, QSizePolicy, QToolTip)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QIcon, QCursor
import logging
import sys
import os

logger = logging.getLogger(__name__)

class HomeTab(QWidget):
    """Вкладка Главная - основные функции устройства"""

    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        # Словарь с подсказками для команд
        self.command_hints = {
            "hw status": "📊 Показать статус устройства: напряжение, антенны, кнопки",
            "hw version": "ℹ️ Версия железа и прошивки Proxmark3",
            "hw tune": "📡 Измерить настройку антенн LF/HF",
            "lf search": "🔍 Поиск LF карт (125 kHz)",
            "hf search": "🔍 Поиск HF карт (13.56 MHz)",
            "hf read": "📖 Прочитать данные карты",
            "data samples": "📈 Получить сырые данные с антенны"
        }
        
        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Верхняя панель с подключением
        connection_group = self._create_connection_panel()
        layout.addWidget(connection_group)

        # Центральная часть с быстрыми кнопками
        quick_actions_group = self._create_quick_actions_panel()
        layout.addWidget(quick_actions_group)

        # Панель статуса устройства
        status_group = self._create_device_status_panel()
        layout.addWidget(status_group)

        # Лог операций
        log_group = self._create_log_panel()
        layout.addWidget(log_group, 1)

    def _create_connection_panel(self) -> QGroupBox:
        """Панель подключения к устройству"""
        group = QGroupBox("🔌 Подключение к устройству")
        layout = QHBoxLayout()
        
        # Выбор COM-порта
        layout.addWidget(QLabel("COM-порт:"))
        self.combo_ports = QComboBox()
        self.combo_ports.setMinimumWidth(150)
        self.combo_ports.setToolTip("📡 Выберите COM-порт для подключения к Proxmark3")
        layout.addWidget(self.combo_ports)
        
        # Кнопка обновления портов
        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedWidth(40)
        btn_refresh.setToolTip("🔄 Обновить список COM-портов")
        btn_refresh.clicked.connect(self.refresh_ports)
        layout.addWidget(btn_refresh)
        
        # Выбор скорости
        layout.addWidget(QLabel("Скорость:"))
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["115200", "921600", "57600", "38400"])
        self.combo_baud.setCurrentText("115200")
        self.combo_baud.setToolTip("⚡ Скорость соединения (бит/сек)")
        layout.addWidget(self.combo_baud)
        
        layout.addStretch()
        
        # Кнопка подключения
        self.btn_connect = QPushButton("Подключиться")
        self.btn_connect.setCheckable(True)
        self.btn_connect.setMinimumWidth(120)
        self.btn_connect.setToolTip("🔗 Подключиться/отключиться от устройства")
        self.btn_connect.clicked.connect(self.toggle_connection)
        layout.addWidget(self.btn_connect)
        
        # Индикатор подключения
        self.connection_indicator = QFrame()
        self.connection_indicator.setFixedSize(20, 20)
        self.connection_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
        self.connection_indicator.setToolTip("🔴 Отключено / 🟢 Подключено")
        layout.addWidget(self.connection_indicator)
        
        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_quick_actions_panel(self) -> QGroupBox:
        """Панель быстрых действий с раскрывающимися меню"""
        group = QGroupBox("⚡ Быстрые действия")
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # Кнопка 1: Диагностика устройства (с меню)
        btn_diagnostics = self._create_dropdown_button(
            "🔍 Диагностика",
            ["hw status", "hw version", "hw tune"],
            ["Статус устройства", "Версия прошивки", "Настройка антенн"],
            "📊 Полная диагностика устройства"
        )
        layout.addWidget(btn_diagnostics, 0, 0)
        
        # Кнопка 2: Поиск карт (с меню)
        btn_search = self._create_dropdown_button(
            "🔎 Поиск карт",
            ["lf search", "hf search", "hf read"],
            ["Поиск LF (125 kHz)", "Поиск HF (13.56 MHz)", "Прочитать карту"],
            "🔍 Поиск и чтение RFID карт"
        )
        layout.addWidget(btn_search, 0, 1)
        
        # Кнопка 3: Работа с данными (с меню)
        btn_data = self._create_dropdown_button(
            "💾 Данные",
            ["data samples", "data load", "data save"],
            ["Получить сэмплы", "Загрузить дамп", "Сохранить дамп"],
            "💾 Управление данными и дампами"
        )
        layout.addWidget(btn_data, 0, 2)
        
        # Кнопка 4: Быстрые команды (с меню)
        btn_quick = self._create_dropdown_button(
            "⚡ Команды",
            ["hf 14a reader", "lf em410x read", "hf mf fkeys"],
            ["Режим читателя 14A", "Читать EM410x", "Проверка ключей Mifare"],
            "⚡ Быстрый запуск частых команд"
        )
        layout.addWidget(btn_quick, 0, 3)
        
        # Кнопка 5: Очистить лог
        btn_clear = QPushButton("🗑️ Очистить лог")
        btn_clear.setToolTip("🗑️ Очистить окно логов")
        btn_clear.clicked.connect(lambda: self.log_output.clear())
        layout.addWidget(btn_clear, 1, 0, 1, 4)
        
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
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QToolButton:hover {
                background-color: #45a049;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        # Создаем меню
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
                background-color: #4CAF50;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #ddd;
                margin: 5px;
            }
        """)
        
        # Добавляем пункты меню
        for cmd, desc in zip(commands, descriptions):
            action = menu.addAction(f"{desc}")
            action.setToolTip(self.command_hints.get(cmd, f"Команда: {cmd}"))
            action.triggered.connect(lambda checked, c=cmd: self.execute_command(c))
        
        btn.setMenu(menu)
        return btn

    def _create_device_status_panel(self) -> QGroupBox:
        """Панель статуса устройства"""
        group = QGroupBox("📊 Статус устройства")
        layout = QGridLayout()
        
        # Статус подключения
        layout.addWidget(QLabel("Статус:"), 0, 0)
        self.lbl_status = QLabel("❌ Отключено")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.lbl_status, 0, 1)
        
        # Версия прошивки
        layout.addWidget(QLabel("Прошивка:"), 0, 2)
        self.lbl_firmware = QLabel("Неизвестно")
        layout.addWidget(self.lbl_firmware, 0, 3)
        
        # Антенна LF
        layout.addWidget(QLabel("LF антенна:"), 1, 0)
        self.lbl_lf = QLabel("—")
        layout.addWidget(self.lbl_lf, 1, 1)
        
        # Антенна HF
        layout.addWidget(QLabel("HF антенна:"), 1, 2)
        self.lbl_hf = QLabel("—")
        layout.addWidget(self.lbl_hf, 1, 3)
        
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        group.setLayout(layout)
        return group

    def _create_log_panel(self) -> QGroupBox:
        """Панель лога операций"""
        group = QGroupBox("📝 Лог операций")
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

    def refresh_ports(self):
        """Обновить список COM-портов"""
        self.log_message("🔄 Обновление списка портов...")
        ports = self.device_manager.scan_ports()
        self.combo_ports.clear()
        for port in ports:
            self.combo_ports.addItem(port)
        if ports:
            self.log_message(f"✅ Найдено портов: {len(ports)}")
        else:
            self.log_message("⚠️ Порты не найдены. Подключите устройство.")

    def toggle_connection(self):
        """Подключить/отключить устройство"""
        if self.btn_connect.isChecked():
            self.connect_device()
        else:
            self.disconnect_device()

    def connect_device(self):
        """Подключение к устройству"""
        port = self.combo_ports.currentText()
        baud = int(self.combo_baud.currentText())
        
        if not port:
            self.log_message("❌ Выберите COM-порт")
            self.btn_connect.setChecked(False)
            return
        
        self.log_message(f"🔌 Подключение к {port} ({baud} бод)...")
        success = self.device_manager.connect(port, baud)
        
        if success:
            self.btn_connect.setText("Отключиться")
            self.btn_connect.setStyleSheet("background-color: #f44336; color: white;")
            self.connection_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 10px;")
            self.lbl_status.setText("🟢 Подключено")
            self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            self.log_message("✅ Успешное подключение!")
            
            # Автоматически получить статус устройства
            QTimer.singleShot(500, lambda: self.execute_command("hw status"))
        else:
            self.btn_connect.setChecked(False)
            self.log_message("❌ Ошибка подключения")

    def disconnect_device(self):
        """Отключение от устройства"""
        self.device_manager.disconnect()
        self.btn_connect.setText("Подключиться")
        self.btn_connect.setStyleSheet("")
        self.connection_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
        self.lbl_status.setText("❌ Отключено")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        self.log_message("🔌 Устройство отключено")

    def execute_command(self, command):
        """Выполнить команду"""
        if not self.device_manager.is_connected():
            self.log_message("❌ Сначала подключитесь к устройству!")
            return
        
        hint = self.command_hints.get(command, "")
        if hint:
            self.log_message(f"ℹ️ {hint}")
        
        self.log_message(f"▶️ Выполнение: {command}")
        
        # Используем command_executor если доступен
        if hasattr(self, 'command_executor') and self.command_executor:
            result = self.command_executor.execute(command)
            if result:
                self.log_message(f"✅ Результат: {result[:200]}..." if len(result) > 200 else f"✅ Результат: {result}")
        else:
            # Fallback к прямому вызову
            result = self.device_manager.send_command(command)
            if result:
                self.log_message(f"✅ Получен ответ: {result[:200]}..." if len(result) > 200 else f"✅ Получен ответ: {result}")

    def log_message(self, message):
        """Добавить сообщение в лог"""
        timestamp = self.device_manager.get_timestamp() if hasattr(self.device_manager, 'get_timestamp') else ""
        if timestamp:
            self.log_output.append(f"[{timestamp}] {message}")
        else:
            self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
