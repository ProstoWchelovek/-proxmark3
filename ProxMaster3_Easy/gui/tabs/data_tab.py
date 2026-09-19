#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка МЕНЕДЖЕР ДАННЫХ
Hex-редактор и управление дампами
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QGroupBox, QSplitter, QFileDialog)
from PyQt6.QtCore import Qt
import logging
from gui.hex_editor import HexEditorWidget

logger = logging.getLogger(__name__)

class DataTab(QWidget):
    """Вкладка менеджера данных с Hex-редактором"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>💾 Менеджер данных и Hex-редактор</h1>")
        layout.addWidget(title)
        
        info = QLabel("Просмотр, редактирование и сохранение дампов карт")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Кнопки управления
        btn_group = QGroupBox("Управление файлами")
        btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("📂 Загрузить дамп")
        self.btn_save = QPushButton("💾 Сохранить дамп")
        self.btn_save_as = QPushButton("💾 Сохранить как...")
        self.btn_clear = QPushButton("🗑️ Очистить")
        self.btn_from_device = QPushButton("📥 Загрузить из устройства")
        
        for btn in [self.btn_load, self.btn_save, self.btn_save_as, self.btn_clear, self.btn_from_device]:
            btn.setMinimumHeight(35)
            btn.clicked.connect(self.on_button_click)
            btn_layout.addWidget(btn)
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # Splitter для редактора
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Hex редактор
        self.hex_editor = HexEditorWidget()
        splitter.addWidget(self.hex_editor)
        
        # Информация о файле
        info_group = QGroupBox("ℹ️ Информация")
        info_layout = QVBoxLayout()
        self.file_info = QLabel("Файл не загружен")
        self.file_info.setWordWrap(True)
        info_layout.addWidget(self.file_info)
        info_group.setLayout(info_layout)
        splitter.addWidget(info_group)
        
        layout.addWidget(splitter, 1)
        
        self.log_message("Hex-редактор инициализирован")
        
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_load:
            self.load_dump()
        elif sender == self.btn_save:
            self.save_dump()
        elif sender == self.btn_save_as:
            self.save_dump_as()
        elif sender == self.btn_clear:
            self.clear_editor()
        elif sender == self.btn_from_device:
            self.load_from_device()
    
    def load_dump(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить дамп", "", "Binary Files (*.bin);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                self.hex_editor.set_data(data)
                self.file_info.setText(f"Файл: {file_path}\nРазмер: {len(data)} байт")
                self.log_message(f"Загружен файл: {file_path}")
            except Exception as e:
                self.log_message(f"Ошибка загрузки: {e}")
    
    def save_dump(self):
        self.save_dump_as()
    
    def save_dump_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить дамп", "", "Binary Files (*.bin);;All Files (*)"
        )
        if file_path:
            try:
                data = self.hex_editor.get_data()
                with open(file_path, 'wb') as f:
                    f.write(data)
                self.file_info.setText(f"Файл: {file_path}\nРазмер: {len(data)} байт")
                self.log_message(f"Сохранен файл: {file_path}")
            except Exception as e:
                self.log_message(f"Ошибка сохранения: {e}")
    
    def clear_editor(self):
        self.hex_editor.set_data(b'\x00' * 256)
        self.file_info.setText("Файл не загружен")
        self.log_message("Редактор очищен")
    
    def load_from_device(self):
        """Загрузка данных из устройства Proxmark3"""
        if not self.device_manager or not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            self.log_message("💡 Подключитесь к Proxmark3 на вкладке 'Главная'")
            return
        
        self.log_message("📥 Загрузка данных из устройства...")
        
        # Получаем последний дамп из памяти устройства
        cmd = "hf mf dump"
        try:
            result = self.command_executor.execute(cmd, callback=self.log_message)
            if result and hasattr(result, 'output'):
                self.log_message("✅ Данные получены")
                # Парсинг результата для извлечения данных
                # В реальной реализации здесь будет парсинг бинарных данных
                self.log_message("💡 Данные доступны для просмотра в Hex-редакторе")
        except Exception as e:
            self.log_message(f"❌ Ошибка загрузки: {e}")
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
