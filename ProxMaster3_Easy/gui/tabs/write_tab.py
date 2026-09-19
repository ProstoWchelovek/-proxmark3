#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ЗАПИСЬ
Запись данных на карты
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QLineEdit, QCheckBox)
import logging

logger = logging.getLogger(__name__)

class WriteTab(QWidget):
    """Вкладка записи на карты"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>✏️ Запись на карты</h1>")
        layout.addWidget(title)
        
        info = QLabel("Запись данных на различные типы карт (T55xx, Mifare, EM410x)")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Выбор типа карты
        card_group = QGroupBox("Тип карты")
        card_layout = QHBoxLayout()
        
        self.card_type = QComboBox()
        self.card_type.addItems(["T55xx", "Mifare Classic", "EM410x", "iClass"])
        card_layout.addWidget(QLabel("Карта:"))
        card_layout.addWidget(self.card_type)
        card_layout.addStretch()
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)
        
        # Параметры записи
        params_group = QGroupBox("Параметры записи")
        params_layout = QVBoxLayout()
        
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("Данные в HEX (например: 0102030405060708)")
        params_layout.addWidget(QLabel("Данные:"))
        params_layout.addWidget(self.data_input)
        
        self.block_num = QLineEdit()
        self.block_num.setPlaceholderText("Номер блока (например: 0)")
        params_layout.addWidget(QLabel("Номер блока:"))
        params_layout.addWidget(self.block_num)
        
        self.use_key = QCheckBox("Использовать ключ доступа")
        params_layout.addWidget(self.use_key)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Ключ в HEX (6 байт)")
        self.key_input.setEnabled(False)
        self.use_key.stateChanged.connect(lambda x: self.key_input.setEnabled(x))
        params_layout.addWidget(QLabel("Ключ:"))
        params_layout.addWidget(self.key_input)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Кнопки действий
        btn_group = QGroupBox("Действия")
        btn_layout = QHBoxLayout()
        
        self.btn_write = QPushButton("✏️ Записать данные")
        self.btn_write_block = QPushButton("📝 Записать блок")
        self.btn_clone = QPushButton("🔄 Клонировать карту")
        
        for btn in [self.btn_write, self.btn_write_block, self.btn_clone]:
            btn.setMinimumHeight(40)
            btn.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; font-weight: bold; }")
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
        
        self.log_message("Вкладка записи инициализирована")
        self.log_message("⚠️ Внимание: Запись может повредить карту!")
        
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_write:
            self.execute_write()
        elif sender == self.btn_write_block:
            self.execute_write_block()
        elif sender == self.btn_clone:
            self.execute_clone()
    
    def execute_write(self):
        data = self.data_input.text().strip()
        card_type = self.card_type.currentText()
        
        if not data:
            self.log_message("❌ Ошибка: Введите данные для записи")
            return
        
        self.log_message(f"Запись на {card_type}: {data}")
        # Здесь будет вызов команды записи
    
    def execute_write_block(self):
        block = self.block_num.text().strip()
        data = self.data_input.text().strip()
        
        if not block or not data:
            self.log_message("❌ Ошибка: Введите номер блока и данные")
            return
        
        self.log_message(f"Запись блока {block}: {data}")
        # Здесь будет вызов команды записи блока
    
    def execute_clone(self):
        self.log_message("Клонирование карты... (требуется исходный дамп)")
        # Здесь будет логика клонирования
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
