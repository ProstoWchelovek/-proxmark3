#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка СНИФИНГ
Перехват и анализ трафика
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QCheckBox, QSpinBox)
import logging

logger = logging.getLogger(__name__)

class SniffTab(QWidget):
    """Вкладка снифинга трафика"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>📡 Снифинг трафика</h1>")
        layout.addWidget(title)
        
        info = QLabel("Перехват и анализ RFID/NFC трафика между картой и считывателем")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Настройки снифинга
        settings_group = QGroupBox("Настройки перехвата")
        settings_layout = QVBoxLayout()
        
        # Частота
        freq_layout = QHBoxLayout()
        self.freq_select = QComboBox()
        self.freq_select.addItems(["LF (125 kHz)", "HF (13.56 MHz)", "UHF"])
        freq_layout.addWidget(QLabel("Частота:"))
        freq_layout.addWidget(self.freq_select)
        freq_layout.addStretch()
        settings_layout.addLayout(freq_layout)
        
        # Опции
        self.opt_continuous = QCheckBox("Непрерывный перехват")
        settings_layout.addWidget(self.opt_continuous)
        
        self.opt_save_raw = QCheckBox("Сохранять сырые данные")
        settings_layout.addWidget(self.opt_save_raw)
        
        # Таймаут
        timeout_layout = QHBoxLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        timeout_layout.addWidget(QLabel("Таймаут (сек):"))
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        settings_layout.addLayout(timeout_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Кнопки действий
        btn_group = QGroupBox("Действия")
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("▶️ Начать перехват")
        self.btn_stop = QPushButton("⏹️ Остановить")
        self.btn_analyze = QPushButton("🔍 Анализировать")
        
        for btn in [self.btn_start, self.btn_stop, self.btn_analyze]:
            btn.setMinimumHeight(40)
            btn.clicked.connect(self.on_button_click)
            btn_layout.addWidget(btn)
        
        self.btn_start.setStyleSheet("QPushButton { background-color: #388e3c; color: white; font-weight: bold; }")
        self.btn_stop.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; font-weight: bold; }")
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        # Лог вывода
        log_group = QGroupBox("📋 Журнал перехвата")
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
        
        self.log_message("Вкладка снифинга инициализирована")
        
    def on_button_click(self):
        sender = self.sender()
        if sender == self.btn_start:
            self.start_sniffing()
        elif sender == self.btn_stop:
            self.stop_sniffing()
        elif sender == self.btn_analyze:
            self.analyze_traffic()
    
    def start_sniffing(self):
        freq = self.freq_select.currentText()
        timeout = self.timeout_spin.value()
        continuous = self.opt_continuous.isChecked()
        save_raw = self.opt_save_raw.isChecked()
        
        self.log_message(f"Запуск перехвата: {freq}")
        self.log_message(f"Таймаут: {timeout} сек")
        if continuous:
            self.log_message("Режим: непрерывный")
        if save_raw:
            self.log_message("Сохранение сырых данных: включено")
        
        # Здесь будет вызов команды снифинга
    
    def stop_sniffing(self):
        self.log_message("Остановка перехвата...")
        # Здесь будет вызов команды остановки
    
    def analyze_traffic(self):
        self.log_message("Анализ перехваченных данных...")
        # Здесь будет логика анализа
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
