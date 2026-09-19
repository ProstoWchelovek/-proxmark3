#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка НАСТРОЙКИ
Настройки приложения, ProxSpace, обновления
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QLineEdit, QCheckBox, QFileDialog, QSpinBox)
import logging
import os

logger = logging.getLogger(__name__)

class SettingsTab(QWidget):
    """Вкладка настроек и обновлений"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>⚙️ Настройки и обновления</h1>")
        layout.addWidget(title)
        
        info = QLabel("Настройка подключения, ProxSpace, темы и проверки обновлений")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Настройки ProxSpace
        proxspace_group = QGroupBox("📦 ProxSpace / Iceman")
        proxspace_layout = QVBoxLayout()
        
        self.proxspace_path = QLineEdit()
        self.proxspace_path.setPlaceholderText("Путь к ProxSpace (например: C:/ProxSpace)")
        proxspace_layout.addWidget(QLabel("Путь к ProxSpace:"))
        proxspace_layout.addWidget(self.proxspace_path)
        
        btn_browse_proxspace = QPushButton("📂 Обзор...")
        btn_browse_proxspace.clicked.connect(self.browse_proxspace)
        proxspace_layout.addWidget(btn_browse_proxspace)
        
        self.btn_install_proxspace = QPushButton("📥 Установить ProxSpace")
        self.btn_install_proxspace.setMinimumHeight(40)
        self.btn_install_proxspace.clicked.connect(self.install_proxspace)
        proxspace_layout.addWidget(self.btn_install_proxspace)
        
        proxspace_group.setLayout(proxspace_layout)
        layout.addWidget(proxspace_group)
        
        # Настройки COM-порта
        com_group = QGroupBox("🔌 Подключение к устройству")
        com_layout = QVBoxLayout()
        
        com_row = QHBoxLayout()
        self.com_port = QComboBox()
        self.com_port.setEditable(True)
        self.com_port.addItems(["COM1", "COM2", "COM3", "COM4", "COM5"])
        com_row.addWidget(QLabel("COM-порт:"))
        com_row.addWidget(self.com_port)
        com_row.addStretch()
        com_layout.addLayout(com_row)
        
        baud_row = QHBoxLayout()
        self.baud_rate = QComboBox()
        self.baud_rate.addItems(["9600", "19200", "38400", "57600", "115200", "921600"])
        self.baud_rate.setCurrentText("115200")
        baud_row.addWidget(QLabel("Baudrate:"))
        baud_row.addWidget(self.baud_rate)
        baud_row.addStretch()
        com_layout.addLayout(baud_row)
        
        self.auto_connect = QCheckBox("Автоматическое подключение при запуске")
        com_layout.addWidget(self.auto_connect)
        
        com_group.setLayout(com_layout)
        layout.addWidget(com_group)
        
        # Обновления
        update_group = QGroupBox("🔄 Обновления")
        update_layout = QVBoxLayout()
        
        self.btn_check_updates = QPushButton("🔍 Проверить обновления приложения")
        self.btn_check_updates.setMinimumHeight(40)
        self.btn_check_updates.clicked.connect(self.check_updates)
        update_layout.addWidget(self.btn_check_updates)
        
        self.btn_update_firmware = QPushButton("📲 Обновить прошивку Proxmark3")
        self.btn_update_firmware.setMinimumHeight(40)
        self.btn_update_firmware.clicked.connect(self.update_firmware)
        update_layout.addWidget(self.btn_update_firmware)
        
        self.auto_update = QCheckBox("Автоматически проверять обновления при запуске")
        update_layout.addWidget(self.auto_update)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # Тема оформления
        theme_group = QGroupBox("🎨 Оформление")
        theme_layout = QHBoxLayout()
        
        self.theme_select = QComboBox()
        self.theme_select.addItems(["Тёмная", "Светлая", "Системная"])
        theme_layout.addWidget(QLabel("Тема:"))
        theme_layout.addWidget(self.theme_select)
        theme_layout.addStretch()
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Лог операций
        log_group = QGroupBox("📋 Журнал настроек")
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
        layout.addWidget(log_group)
        
        self.log_message("Вкладка настроек инициализирована")
        self.load_settings()
        
    def browse_proxspace(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выбрать папку ProxSpace", ""
        )
        if folder:
            self.proxspace_path.setText(folder)
            self.save_settings()
            self.log_message(f"ProxSpace путь установлен: {folder}")
    
    def install_proxspace(self):
        self.log_message("Запуск установщика ProxSpace...")
        # Здесь будет вызов installer/proxspace_installer.py
        self.log_message("Установщик будет запущен в отдельном окне")
    
    def check_updates(self):
        self.log_message("Проверка обновлений приложения...")
        # Здесь будет логика проверки обновлений
        self.log_message("Проверка завершена")
    
    def update_firmware(self):
        self.log_message("Обновление прошивки Proxmark3...")
        # Здесь будет логика обновления прошивки
        self.log_message("Используйте команду: hf mf fkeys или аналогичную")
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        settings_file = "settings.json"
        if os.path.exists(settings_file):
            try:
                import json
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                if 'proxspace_path' in settings:
                    self.proxspace_path.setText(settings['proxspace_path'])
                if 'com_port' in settings:
                    self.com_port.setCurrentText(settings['com_port'])
                if 'baud_rate' in settings:
                    self.baud_rate.setCurrentText(settings['baud_rate'])
                if 'theme' in settings:
                    self.theme_select.setCurrentText(settings['theme'])
                
                self.log_message("Настройки загружены")
            except Exception as e:
                self.log_message(f"Ошибка загрузки настроек: {e}")
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        settings = {
            'proxspace_path': self.proxspace_path.text(),
            'com_port': self.com_port.currentText(),
            'baud_rate': self.baud_rate.currentText(),
            'theme': self.theme_select.currentText(),
            'auto_connect': self.auto_connect.isChecked(),
            'auto_update': self.auto_update.isChecked()
        }
        
        try:
            import json
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            self.log_message("Настройки сохранены")
        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек: {e}")
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
