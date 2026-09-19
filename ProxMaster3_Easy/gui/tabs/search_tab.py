#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ПОИСК
Поиск и чтение карт LF/HF
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QLineEdit, QCheckBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class SearchTab(QWidget):
    """Вкладка поиска карт"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>🔍 Поиск карт (LF/HF)</h1>")
        layout.addWidget(title)
        
        info = QLabel("Поиск и чтение RFID/NFC карт различных протоколов")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Выбор типа поиска
        search_group = QGroupBox("Тип поиска")
        search_layout = QHBoxLayout()
        
        self.search_type = QComboBox()
        self.search_type.addItems(["LF (Низкая частота)", "HF (Высокая частота)", "Автопоиск"])
        search_layout.addWidget(QLabel("Режим:"))
        search_layout.addWidget(self.search_type)
        
        self.quick_scan = QCheckBox("Быстрое сканирование")
        search_layout.addWidget(self.quick_scan)
        
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Кнопки действий
        btn_group = QGroupBox("Действия")
        btn_layout = QHBoxLayout()
        
        self.btn_search_lf = QPushButton("📡 Поиск LF")
        self.btn_search_hf = QPushButton("📡 Поиск HF")
        self.btn_read_card = QPushButton("💳 Прочитать карту")
        self.btn_detect = QPushButton("🔎 Детектировать тип")
        
        for btn in [self.btn_search_lf, self.btn_search_hf, self.btn_read_card, self.btn_detect]:
            btn.setMinimumHeight(40)
            btn.clicked.connect(self.on_button_click)
            btn_layout.addWidget(btn)
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # Лог вывода
        log_group = QGroupBox("📋 Журнал операций")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: #1a1a1a;
                color: #44ff44;
            }
        """)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, 1)
        
        self.log_message("Вкладка поиска инициализирована")
        
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_search_lf:
            self.execute_command("search_lf")
        elif sender == self.btn_search_hf:
            self.execute_command("search_hf")
        elif sender == self.btn_read_card:
            self.execute_command("read_card")
        elif sender == self.btn_detect:
            self.execute_command("detect_type")
    
    def execute_command(self, cmd_type):
        """Выполнение команды поиска/чтения карт"""
        commands = {
            "search_lf": "lf search",
            "search_hf": "hf search",
            "read_card": "hf read",
            "detect_type": "hf detect"
        }
        
        cmd = commands.get(cmd_type, "")
        if not cmd:
            self.log_message(f"❌ Неизвестная команда: {cmd_type}")
            return
        
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            self.log_message("💡 Подключитесь к Proxmark3 на вкладке 'Главная'")
            return
        
        self.log_message(f"▶️ Выполнение: {cmd}")
        
        # Выполняем команду через command_executor
        try:
            result = self.command_executor.execute(cmd)
            if result:
                self.log_message(f"✅ Успешно: {cmd}")
                # Если есть данные в результате, показываем их
                if hasattr(result, 'output') and result.output:
                    self.log_message("📋 Результат:")
                    for line in result.output.split('\n'):
                        if line.strip():
                            self.log_message(f"   {line}")
            else:
                self.log_message(f"⚠️ Команда выполнена без результата")
        except Exception as e:
            self.log_message(f"❌ Ошибка выполнения: {str(e)}")
            logger.error(f"Ошибка при выполнении команды {cmd}: {e}", exc_info=True)
            
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
