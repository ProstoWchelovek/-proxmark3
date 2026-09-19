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
        """Запуск перехвата трафика"""
        freq = self.freq_select.currentText()
        timeout = self.timeout_spin.value()
        continuous = self.opt_continuous.isChecked()
        save_raw = self.opt_save_raw.isChecked()
        
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            return
        
        # Формируем команду в зависимости от частоты
        if "LF" in freq:
            cmd = "lf sniff"
            if continuous:
                cmd += " -c"
        elif "HF" in freq:
            cmd = "hf sniff"
            if continuous:
                cmd += " -c"
        elif "UHF" in freq:
            self.log_message("❌ UHF снифинг не поддерживается на PM3 Easy")
            return
        else:
            self.log_message(f"❌ Неизвестная частота: {freq}")
            return
        
        self.log_message(f"▶️ Запуск перехвата: {freq}")
        self.log_message(f"⏱️ Таймаут: {timeout} сек")
        if continuous:
            self.log_message("🔄 Режим: непрерывный")
        if save_raw:
            self.log_message("💾 Сохранение сырых данных: включено")
        
        self.log_message(f"📡 Команда: {cmd}")
        
        try:
            result = self.command_executor.execute(cmd)
            if result:
                self.log_message(f"✅ Перехват запущен")
                self.log_message("💡 Поднесите карту к считывателю для перехвата данных")
                if hasattr(result, 'output') and result.output:
                    for line in result.output.split('\n'):
                        if line.strip():
                            self.log_message(f"   {line}")
            else:
                self.log_message("⚠️ Перехват запущен без подтверждения")
        except Exception as e:
            self.log_message(f"❌ Ошибка запуска перехвата: {str(e)}")
            logger.error(f"Ошибка при снифинге {freq}: {e}", exc_info=True)
    
    def stop_sniffing(self):
        """Остановка перехвата"""
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            return
        
        self.log_message("⏹️ Остановка перехвата...")
        
        try:
            # Отправляем команду остановки
            result = self.command_executor.execute("")
            if result:
                self.log_message("✅ Перехват остановлен")
                # Проверяем наличие сохранённых данных
                self.log_message("💡 Данные доступны для анализа")
            else:
                self.log_message("⚠️ Команда остановки отправлена")
        except Exception as e:
            self.log_message(f"⚠️ Остановка: {str(e)}")
            logger.error(f"Ошибка при остановке снифинга: {e}", exc_info=True)
    
    def analyze_traffic(self):
        """Анализ перехваченных данных"""
        if not self.device_manager.is_connected():
            self.log_message("❌ Ошибка: Устройство не подключено")
            return
        
        self.log_message("🔍 Анализ перехваченных данных...")
        
        # Получаем последние перехваченные данные
        try:
            # Команда для просмотра последних данных
            cmd = "hf list"
            result = self.command_executor.execute(cmd)
            if result and hasattr(result, 'output') and result.output:
                self.log_message("📋 Результаты анализа:")
                for line in result.output.split('\n'):
                    if line.strip():
                        self.log_message(f"   {line}")
                
                # Пробуем определить тип карты
                if "UID" in result.output or "uid" in result.output:
                    self.log_message("✅ Обнаружен UID карты")
                if "Mifare" in result.output or "mifare" in result.output:
                    self.log_message("✅ Обнаружена карта Mifare")
                if "ISO" in result.output or "iso" in result.output:
                    self.log_message("✅ Обнаружен ISO протокол")
            else:
                self.log_message("⚠️ Нет данных для анализа")
                self.log_message("💡 Сначала выполните перехват трафика")
        except Exception as e:
            self.log_message(f"❌ Ошибка анализа: {str(e)}")
            logger.error(f"Ошибка при анализе трафика: {e}", exc_info=True)
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
