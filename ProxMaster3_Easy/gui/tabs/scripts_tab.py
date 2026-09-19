#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка СКРИПТЫ
Node Editor и управление скриптами
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QSplitter, QFileDialog, QListWidget)
import logging
from ..node_editor import NodeEditorWidget

logger = logging.getLogger(__name__)

class ScriptsTab(QWidget):
    """Вкладка скриптов с Node Editor"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>📜 Скрипты и Node Editor</h1>")
        layout.addWidget(title)
        
        info = QLabel("Создание и выполнение Lua/JavaScript скриптов для автоматизации")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Splitter для редактора и списка
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель - список скриптов
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("📄 Новый")
        self.btn_open = QPushButton("📂 Открыть")
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_run = QPushButton("▶️ Выполнить")
        
        for btn in [self.btn_new, self.btn_open, self.btn_save, self.btn_run]:
            btn.clicked.connect(self.on_button_click)
            btn_layout.addWidget(btn)
        
        left_layout.addLayout(btn_layout)
        
        # Список скриптов
        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(self.load_selected_script)
        left_layout.addWidget(self.scripts_list)
        
        splitter.addWidget(left_panel)
        
        # Правая панель - Node Editor
        self.node_editor = NodeEditorWidget()
        splitter.addWidget(self.node_editor)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter, 1)
        
        # Консоль вывода
        console_group = QGroupBox("📋 Консоль выполнения")
        console_layout = QVBoxLayout()
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                background-color: #1a1a1a;
                color: #44ff44;
            }
        """)
        console_layout.addWidget(self.console_text)
        console_group.setLayout(console_layout)
        layout.addWidget(console_group)
        
        self.log_message("Node Editor инициализирован")
        self.refresh_scripts_list()
        
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_new:
            self.new_script()
        elif sender == self.btn_open:
            self.open_script()
        elif sender == self.btn_save:
            self.save_script()
        elif sender == self.btn_run:
            self.run_script()
    
    def new_script(self):
        self.node_editor.clear()
        self.log_message("Создан новый скрипт")
    
    def open_script(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть скрипт", "", 
            "Lua Files (*.lua);;JavaScript Files (*.js);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.node_editor.set_content(content)
                self.log_message(f"Открыт файл: {file_path}")
            except Exception as e:
                self.log_message(f"Ошибка открытия: {e}")
    
    def save_script(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить скрипт", "", 
            "Lua Files (*.lua);;JavaScript Files (*.js);;All Files (*)"
        )
        if file_path:
            try:
                content = self.node_editor.get_content()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log_message(f"Сохранен файл: {file_path}")
                self.refresh_scripts_list()
            except Exception as e:
                self.log_message(f"Ошибка сохранения: {e}")
    
    def run_script(self):
        content = self.node_editor.get_content()
        if not content.strip():
            self.log_message("❌ Ошибка: Скрипт пуст")
            return
        
        self.log_message("Запуск скрипта...")
        self.console_text.append("=" * 50)
        
        # Здесь будет вызов выполнения скрипта через command_executor
        # В зависимости от типа скрипта (Lua или JS)
        
        self.log_message("Скрипт выполнен")
    
    def load_selected_script(self, item):
        script_name = item.text()
        script_path = f"scripts/{script_name}"
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.node_editor.set_content(content)
            self.log_message(f"Загружен скрипт: {script_name}")
        except Exception as e:
            self.log_message(f"Ошибка загрузки: {e}")
    
    def refresh_scripts_list(self):
        import os
        self.scripts_list.clear()
        scripts_dir = "scripts"
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                if file.endswith(('.lua', '.js')):
                    self.scripts_list.addItem(file)
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.console_text.append(f"[{timestamp}] {message}")
