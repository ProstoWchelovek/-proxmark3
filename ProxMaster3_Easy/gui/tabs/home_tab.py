#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ГЛАВНАЯ
Быстрый доступ к основным функциям устройства
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QGroupBox, QTextEdit,
                             QGridLayout, QFrame, QProgressBar)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class HomeTab(QWidget):
    """Вкладка Главная - основные функции устройства"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
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
        layout.addWidget(log_group, 1)  # Растягиваем на оставшееся место
    
    def _create_connection_panel(self) -> QGroupBox:
        """Панель подключения к устройству"""
        group = QGroupBox("🔌 Подключение к устройству")
        layout = QHBoxLayout()
        
        # Выбор COM-порта
        layout.addWidget(QLabel("COM-порт:"))
        self.com_port_combo = QComboBox()
        self.com_port_combo.setMinimumWidth(200)
        layout.addWidget(self.com_port_combo)
        
        # Кнопка обновления списка портов
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_btn)
        
        # Кнопки подключения/отключения
        self.connect_btn = QPushButton("🔌 Подключиться")
        self.connect_btn.clicked.connect(self.connect_device)
        layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("❌ Отключиться")
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        self.disconnect_btn.setEnabled(False)
        layout.addWidget(self.disconnect_btn)
        
        # Индикатор подключения
        self.connection_indicator = QLabel("🔴 Не подключено")
        self.connection_indicator.setStyleSheet("font-weight: bold; color: #ff4444;")
        layout.addStretch()
        layout.addWidget(self.connection_indicator)
        
        group.setLayout(layout)
        return group
    
    def _create_quick_actions_panel(self) -> QGroupBox:
        """Панель быстрых действий"""
        group = QGroupBox("⚡ Быстрые действия")
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # Кнопки действий (3x3 сетка)
        actions = [
            ("📊 Статус", "hw status", "Получить статус устройства"),
            ("🔍 Версия", "hw version", "Показать версии прошивки"),
            ("📡 Антенна", "hw tune", "Настройка антенны"),
            ("🔎 Поиск LF", "lf search", "Поиск LF карт"),
            ("🔎 Поиск HF", "hf search", "Поиск HF карт"),
            ("💾 Дамп", "hf mf dump", "Дамп Mifare карты"),
            ("📋 Чтение UID", "hf mf ruid", "Чтение UID карты"),
            ("🎭 Эмуляция", "hf mf sim", "Эмуляция карты"),
            ("⚙️ Настройки", "hw prefs", "Настройки устройства"),
        ]
        
        row = 0
        col = 0
        for name, command, tooltip in actions:
            btn = QPushButton(name)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda checked, cmd=command: self.execute_quick_command(cmd))
            layout.addWidget(btn, row, col)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_device_status_panel(self) -> QGroupBox:
        """Панель статуса устройства"""
        group = QGroupBox("📈 Статус устройства")
        layout = QGridLayout()
        
        # Информация об устройстве
        self.device_info_labels = {
            'type': QLabel("Тип: Неизвестно"),
            'firmware': QLabel("Прошивка: Неизвестно"),
            'port': QLabel("Порт: -"),
            'baudrate': QLabel("Скорость: -"),
        }
        
        row = 0
        for key, label in self.device_info_labels.items():
            layout.addWidget(label, row, 0)
            row += 1
        
        # Индикаторы состояния
        self.status_indicators = {
            'power': QLabel("⚡ Питание: ---"),
            'antenna': QLabel("📡 Антенна: ---"),
            'button': QLabel("🔘 Кнопка: ---"),
            'led': QLabel("💡 LED: ---"),
        }
        
        row = 0
        for key, label in self.status_indicators.items():
            layout.addWidget(label, row, 1)
            row += 1
        
        group.setLayout(layout)
        return group
    
    def _create_log_panel(self) -> QGroupBox:
        """Панель лога операций"""
        group = QGroupBox("📋 Журнал операций")
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #1a1a1a;
                color: #44ff44;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Кнопки управления логом
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Очистить лог")
        clear_btn.clicked.connect(self.log_text.clear)
        btn_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("💾 Сохранить лог")
        save_btn.clicked.connect(self.save_log)
        btn_layout.addWidget(save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def execute_quick_command(self, command: str):
        """Выполнить быструю команду"""
        if not self.device_manager.is_connected:
            self.log_message(f"❌ Ошибка: Устройство не подключено", "error")
            return
        
        self.log_message(f"▶️ Выполнение: {command}", "info")
        
        success, response = self.device_manager.send_command(command)
        
        if success:
            self.log_message(f"✅ Успех: {command}", "success")
            if response:
                self.log_message(response[:500], "response")  # Ограничиваем длину
        else:
            self.log_message(f"❌ Ошибка: {response}", "error")
    
    def connect_device(self):
        """Подключиться к устройству"""
        port = self.com_port_combo.currentText()
        
        if not port:
            self.log_message("❌ Выберите COM-порт", "error")
            return
        
        self.log_message(f"🔌 Подключение к {port}...", "info")
        
        success, message = self.device_manager.connect(port)
        
        if success:
            self.log_message(f"✅ {message}", "success")
            self.connection_indicator.setText("🟢 Подключено")
            self.connection_indicator.setStyleSheet("font-weight: bold; color: #44ff44;")
            
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.com_port_combo.setEnabled(False)
            
            # Обновление информации об устройстве
            self.update_device_info()
        else:
            self.log_message(f"❌ {message}", "error")
            self.connection_indicator.setText("🔴 Ошибка подключения")
            self.connection_indicator.setStyleSheet("font-weight: bold; color: #ff4444;")
    
    def disconnect_device(self):
        """Отключиться от устройства"""
        self.device_manager.disconnect()
        
        self.log_message("❌ Отключено от устройства", "info")
        self.connection_indicator.setText("🔴 Не подключено")
        self.connection_indicator.setStyleSheet("font-weight: bold; color: #ff4444;")
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.com_port_combo.setEnabled(True)
        
        # Сброс информации
        for label in self.device_info_labels.values():
            label.setText(label.text().split(":")[0] + ": Неизвестно")
    
    def refresh_ports(self):
        """Обновить список COM-портов"""
        self.com_port_combo.clear()
        
        ports = self.device_manager.list_com_ports()
        
        for port in ports:
            display_text = f"{port['device']} - {port['description']}"
            if port.get('is_proxmark'):
                display_text += " (Proxmark)"
            self.com_port_combo.addItem(display_text, port['device'])
        
        if ports:
            self.log_message(f"📋 Найдено портов: {len(ports)}", "info")
        else:
            self.log_message("⚠️ COM-порты не найдены", "warning")
    
    def update_device_info(self):
        """Обновить информацию об устройстве"""
        if self.device_manager.is_connected:
            status = self.device_manager.get_status()
            
            self.device_info_labels['port'].setText(f"Порт: {status.get('port', '-')}")
            self.device_info_labels['baudrate'].setText(f"Скорость: {status.get('baudrate', '-')} бод")
            self.device_info_labels['type'].setText(f"Тип: {status.get('device_info', {}).get('type', 'Proxmark3 Easy')}")
            self.device_info_labels['firmware'].setText(f"Прошивка: {status.get('device_info', {}).get('firmware', 'Iceman')}")
    
    def log_message(self, message: str, level: str = "info"):
        """Добавить сообщение в лог"""
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        
        colors = {
            'info': '#44aaff',
            'success': '#44ff44',
            'warning': '#ffaa00',
            'error': '#ff4444',
            'response': '#aaaaaa'
        }
        
        color = colors.get(level, '#ffffff')
        icon = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'response': '📝'
        }.get(level, '•')
        
        html_message = f'<span style="color: {color};">[{timestamp}] {icon} {message}</span><br>'
        self.log_text.append(html_message)
        
        # Прокрутка вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def save_log(self):
        """Сохранить лог в файл"""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить лог", 
            self.data_manager.logs_dir / f"log_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log_message(f"💾 Лог сохранен: {filename}", "success")
            except Exception as e:
                self.log_message(f"❌ Ошибка сохранения: {e}", "error")
