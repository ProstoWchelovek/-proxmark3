#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ЭМУЛЯЦИЯ
Эмуляция различных типов карт
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QLineEdit)
import logging

logger = logging.getLogger(__name__)

class EmulateTab(QWidget):
    """Вкладка эмуляции карт"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>🎭 Эмуляция карт</h1>")
        layout.addWidget(title)
        
        info = QLabel("Эмуляция RFID/NFC карт для тестирования систем доступа")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Выбор типа эмуляции
        emul_group = QGroupBox("Тип эмуляции")
        emul_layout = QHBoxLayout()
        
        self.emul_type = QComboBox()
        self.emul_type.addItems([
            "Mifare Classic", "Mifare Ultralight", "EM410x (LF)",
            "T55xx (LF)", "iClass", "LEGIC", "FeliCa"
        ])
        emul_layout.addWidget(QLabel("Протокол:"))
        emul_layout.addWidget(self.emul_type)
        emul_layout.addStretch()
        emul_group.setLayout(emul_layout)
        layout.addWidget(emul_group)
        
        # Параметры эмуляции
        params_group = QGroupBox("Параметры")
        params_layout = QVBoxLayout()
        
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("UID в HEX (например: 04A1B2C3)")
        params_layout.addWidget(QLabel("UID карты:"))
        params_layout.addWidget(self.uid_input)
        
        self.dump_file = QLineEdit()
        self.dump_file.setPlaceholderText("Путь к файлу дампа (опционально)")
        params_layout.addWidget(QLabel("Файл дампа:"))
        params_layout.addWidget(self.dump_file)
        
        btn_browse = QPushButton("📂 Обзор...")
        btn_browse.setMaximumWidth(100)
        btn_browse.clicked.connect(self.browse_dump)
        params_layout.addWidget(btn_browse)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Кнопки действий
        btn_group = QGroupBox("Действия")
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("▶️ Начать эмуляцию")
        self.btn_stop = QPushButton("⏹️ Остановить")
        
        for btn in [self.btn_start, self.btn_stop]:
            btn.setMinimumHeight(40)
            btn.clicked.connect(self.on_button_click)
            btn_layout.addWidget(btn)
        
        self.btn_start.setStyleSheet("QPushButton { background-color: #388e3c; color: white; font-weight: bold; }")
        self.btn_stop.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; font-weight: bold; }")
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # Лог вывода
        log_group = QGroupBox("📋 Журнал эмуляции")
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
        
        self.log_message("Вкладка эмуляции инициализирована")
        
    def browse_dump(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать дамп", "", "Binary Files (*.bin);;All Files (*)"
        )
        if file_path:
            self.dump_file.setText(file_path)
            self.log_message(f"Выбран файл: {file_path}")
    
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_start:
            self.start_emulation()
        elif sender == self.btn_stop:
            self.stop_emulation()
    
    def start_emulation(self):
        """Запуск эмуляции карты"""
        emul_type = self.emul_type.currentText()
        uid = self.uid_input.text().strip()
        dump = self.dump_file.text().strip()
        
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            return
        
        # Формируем команду в зависимости от типа эмуляции
        if emul_type == "Mifare Classic":
            if dump:
                cmd = f"hf mf eload -f {dump}"
            elif uid:
                cmd = f"hf mf sim -u {uid}"
            else:
                cmd = "hf mf sim"
        elif emul_type == "Mifare Ultralight":
            if dump:
                cmd = f"hf mfu eload -f {dump}"
            else:
                cmd = "hf mfu sim"
        elif emul_type == "EM410x (LF)":
            if uid:
                cmd = f"lf em410x sim -u {uid}"
            else:
                cmd = "lf em410x sim"
        elif emul_type == "T55xx (LF)":
            if dump:
                cmd = f"lf t55xx sim -f {dump}"
            else:
                cmd = "lf t55xx sim"
        elif emul_type == "iClass":
            if dump:
                cmd = f"hf iclass sim -f {dump}"
            else:
                cmd = "hf iclass sim"
        elif emul_type == "LEGIC":
            cmd = "hf legic sim"
        elif emul_type == "FeliCa":
            cmd = "hf felica sim"
        else:
            self.log_message(f"❌ Неизвестный тип эмуляции: {emul_type}")
            return
        
        self.log_message(f"▶️ Запуск эмуляции: {emul_type}")
        if uid:
            self.log_message(f"📋 UID: {uid}")
        if dump:
            self.log_message(f"📂 Дамп: {dump}")
        self.log_message(f"📡 Команда: {cmd}")
        
        try:
            result = self.command_executor.execute(cmd)
            if result:
                self.log_message(f"✅ Эмуляция запущена")
                self.log_message("💡 Поднесите карту к считывателю")
                if hasattr(result, 'output') and result.output:
                    for line in result.output.split('\n'):
                        if line.strip():
                            self.log_message(f"   {line}")
            else:
                self.log_message("⚠️ Эмуляция запущена без подтверждения")
        except Exception as e:
            self.log_message(f"❌ Ошибка запуска эмуляции: {str(e)}")
            logger.error(f"Ошибка при эмуляции {emul_type}: {e}", exc_info=True)
    
    def stop_emulation(self):
        """Остановка эмуляции"""
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            return
        
        # Отправляем команду остановки (Ctrl+C или hf tune)
        self.log_message("⏹️ Остановка эмуляции...")
        
        try:
            # Пробуем отправить команду остановки
            result = self.command_executor.execute("hf tune")
            if result:
                self.log_message("✅ Эмуляция остановлена")
            else:
                self.log_message("⚠️ Команда остановки отправлена")
        except Exception as e:
            self.log_message(f"⚠️ Остановка: {str(e)}")
            logger.error(f"Ошибка при остановке эмуляции: {e}", exc_info=True)
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
