#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Вкладка ИНСТРУМЕНТЫ
Анализ, графики, GPIO, UART и другие утилиты
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QGroupBox, QHBoxLayout, QComboBox,
                             QTabWidget, QSpinBox, QLineEdit)
import logging

logger = logging.getLogger(__name__)

class ToolsTab(QWidget):
    """Вкладка инструментов и анализа"""
    
    def __init__(self, device_manager, command_executor, data_manager):
        super().__init__()
        self.device_manager = device_manager
        self.command_executor = command_executor
        self.data_manager = data_manager
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("<h1>🛠️ Инструменты и анализ</h1>")
        layout.addWidget(title)
        
        info = QLabel("Дополнительные утилиты: анализ данных, GPIO, UART, MQTT")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Вкладки инструментов
        tools_tabs = QTabWidget()
        
        # Вкладка 1: Анализ
        analyze_tab = self.create_analyze_tab()
        tools_tabs.addTab(analyze_tab, "📊 Анализ")
        
        # Вкладка 2: GPIO
        gpio_tab = self.create_gpio_tab()
        tools_tabs.addTab(gpio_tab, "🔌 GPIO")
        
        # Вкладка 3: UART
        uart_tab = self.create_uart_tab()
        tools_tabs.addTab(uart_tab, "📡 UART")
        
        # Вкладка 4: MQTT
        mqtt_tab = self.create_mqtt_tab()
        tools_tabs.addTab(mqtt_tab, "☁️ MQTT")
        
        layout.addWidget(tools_tabs, 1)
        
        # Общий лог
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
        layout.addWidget(log_group)
        
        self.log_message("Вкладка инструментов инициализирована")
        
    def create_analyze_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Кнопки анализа
        btn_layout = QHBoxLayout()
        self.btn_analyze_dump = QPushButton("📊 Анализ дампа")
        self.btn_wiegand = QPushButton("Wiegand декодер")
        self.btn_crc = QPushButton("CRC калькулятор")
        
        self.btn_analyze_dump.clicked.connect(self.analyze_dump)
        self.btn_wiegand.clicked.connect(self.decode_wiegand)
        self.btn_crc.clicked.connect(self.calculate_crc)
        
        for btn in [self.btn_analyze_dump, self.btn_wiegand, self.btn_crc]:
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        # Результат анализа
        self.analyze_result = QTextEdit()
        self.analyze_result.setReadOnly(True)
        self.analyze_result.setPlaceholderText("Результат анализа появится здесь...")
        layout.addWidget(self.analyze_result, 1)
        
        return tab
    
    def analyze_dump(self):
        """Анализ текущего дампа"""
        if not self.data_manager:
            self.log_message("❌ DataManager не инициализирован")
            return
        
        dumps = self.data_manager.list_dumps()
        if not dumps:
            self.log_message("⚠️ Нет доступных дампов для анализа")
            return
        
        latest_dump = dumps[0]
        self.log_message(f"📊 Анализ дампа: {latest_dump}")
        
        try:
            data = self.data_manager.load_dump(latest_dump)
            if data:
                self.log_message(f"✅ Размер дампа: {len(data)} байт")
                self.log_message(f"📋 Первые 16 байт: {data[:16].hex()}")
                
                # Попытка определить тип карты
                if len(data) >= 4:
                    uid = data[:4].hex().upper()
                    self.log_message(f"🔍 UID: {uid}")
                    
                    if uid.startswith("04"):
                        self.log_message("💡 Обнаружена карта Mifare")
                    elif uid.startswith("A2"):
                        self.log_message("💡 Обнаружена карта FeliCa")
        except Exception as e:
            self.log_message(f"❌ Ошибка анализа: {e}")
    
    def decode_wiegand(self):
        """Декодирование Wiegand"""
        self.log_message("🔓 Wiegand декодер")
        cmd = "wiegand decode"
        if self.command_executor:
            result = self.command_executor.execute(cmd, callback=self.log_message)
            if result and hasattr(result, 'output'):
                self.log_message(f"📋 Результат:\n{result.output}")
        else:
            self.log_message("⚠️ CommandExecutor недоступен")
    
    def calculate_crc(self):
        """CRC калькулятор"""
        self.log_message("🔢 CRC калькулятор готов к работе")
        self.log_message("💡 Введите данные в формате HEX для расчёта CRC16/CRC32")
    
    def create_gpio_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Выбор пина
        pin_layout = QHBoxLayout()
        pin_layout.addWidget(QLabel("GPIO пин:"))
        self.gpio_pin = QSpinBox()
        self.gpio_pin.setRange(0, 7)
        pin_layout.addWidget(self.gpio_pin)
        pin_layout.addStretch()
        layout.addLayout(pin_layout)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_gpio_read = QPushButton("📖 Читать")
        self.btn_gpio_write = QPushButton("✏️ Записать")
        self.btn_gpio_high = QPushButton("⬆️ HIGH")
        self.btn_gpio_low = QPushButton("⬇️ LOW")
        
        self.btn_gpio_read.clicked.connect(self.gpio_read)
        self.btn_gpio_write.clicked.connect(self.gpio_write)
        self.btn_gpio_high.clicked.connect(self.gpio_set_high)
        self.btn_gpio_low.clicked.connect(self.gpio_set_low)
        
        for btn in [self.btn_gpio_read, self.btn_gpio_write, self.btn_gpio_high, self.btn_gpio_low]:
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        # Статус
        self.gpio_status = QTextEdit()
        self.gpio_status.setReadOnly(True)
        self.gpio_status.setPlaceholderText("Статус GPIO...")
        layout.addWidget(self.gpio_status, 1)
        
        return tab
    
    def gpio_read(self):
        """Чтение состояния GPIO"""
        pin = self.gpio_pin.value()
        self.log_message(f"📖 Чтение GPIO{pin}...")
        cmd = f"hw gpioread {pin}"
        if self.command_executor:
            result = self.command_executor.execute(cmd, callback=self.log_message)
            if result and hasattr(result, 'output'):
                self.gpio_status.append(f"GPIO{pin}: {result.output.strip()}")
        else:
            self.log_message("⚠️ CommandExecutor недоступен")
    
    def gpio_write(self):
        """Запись значения GPIO"""
        pin = self.gpio_pin.value()
        self.log_message(f"✏️ Запись в GPIO{pin}...")
        self.log_message("💡 Используйте кнопки HIGH/LOW для установки значения")
    
    def gpio_set_high(self):
        """Установка GPIO в HIGH"""
        pin = self.gpio_pin.value()
        self.log_message(f"⬆️ Установка GPIO{pin} в HIGH")
        cmd = f"hw gpioset {pin} 1"
        if self.command_executor:
            self.command_executor.execute(cmd, callback=self.log_message)
    
    def gpio_set_low(self):
        """Установка GPIO в LOW"""
        pin = self.gpio_pin.value()
        self.log_message(f"⬇️ Установка GPIO{pin} в LOW")
        cmd = f"hw gpioset {pin} 0"
        if self.command_executor:
            self.command_executor.execute(cmd, callback=self.log_message)
    
    def create_uart_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Настройки UART
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Baudrate:"))
        self.uart_baud = QComboBox()
        self.uart_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        settings_layout.addWidget(self.uart_baud)
        settings_layout.addStretch()
        layout.addLayout(settings_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_uart_open = QPushButton("🔓 Открыть")
        self.btn_uart_close = QPushButton("🔒 Закрыть")
        self.btn_uart_send = QPushButton("📤 Отправить")
        
        self.btn_uart_open.clicked.connect(self.uart_open)
        self.btn_uart_close.clicked.connect(self.uart_close)
        self.btn_uart_send.clicked.connect(self.uart_send)
        
        for btn in [self.btn_uart_open, self.btn_uart_close, self.btn_uart_send]:
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        # Терминал
        self.uart_terminal = QTextEdit()
        self.uart_terminal.setReadOnly(True)
        self.uart_terminal.setPlaceholderText("UART терминал...")
        layout.addWidget(self.uart_terminal, 1)
        
        return tab
    
    def uart_open(self):
        """Открытие UART порта"""
        baudrate = int(self.uart_baud.currentText())
        self.log_message(f"🔓 Открытие UART порта ({baudrate} бод)...")
        cmd = f"uart open -b {baudrate}"
        if self.command_executor:
            result = self.command_executor.execute(cmd, callback=self.log_message)
            if result:
                self.uart_terminal.append(f"✅ UART открыт на скорости {baudrate}")
    
    def uart_close(self):
        """Закрытие UART порта"""
        self.log_message("🔒 Закрытие UART порта...")
        cmd = "uart close"
        if self.command_executor:
            self.command_executor.execute(cmd, callback=self.log_message)
            self.uart_terminal.append("✅ UART закрыт")
    
    def uart_send(self):
        """Отправка данных через UART"""
        self.log_message("📤 Отправка данных через UART...")
        self.log_message("💡 Введите данные в поле ввода (будет добавлено)")
    
    def create_mqtt_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Настройки MQTT
        self.mqtt_server = QLineEdit()
        self.mqtt_server.setPlaceholderText("MQTT сервер (например: broker.mqttdashboard.com)")
        layout.addWidget(QLabel("Сервер:"))
        layout.addWidget(self.mqtt_server)
        
        port_layout = QHBoxLayout()
        self.mqtt_port = QSpinBox()
        self.mqtt_port.setRange(1, 65535)
        self.mqtt_port.setValue(1883)
        port_layout.addWidget(QLabel("Порт:"))
        port_layout.addWidget(self.mqtt_port)
        port_layout.addStretch()
        layout.addLayout(port_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_mqtt_connect = QPushButton("🔗 Подключиться")
        self.btn_mqtt_publish = QPushButton("📤 Опубликовать")
        self.btn_mqtt_subscribe = QPushButton("📥 Подписаться")
        
        self.btn_mqtt_connect.clicked.connect(self.mqtt_connect)
        self.btn_mqtt_publish.clicked.connect(self.mqtt_publish)
        self.btn_mqtt_subscribe.clicked.connect(self.mqtt_subscribe)
        
        for btn in [self.btn_mqtt_connect, self.btn_mqtt_publish, self.btn_mqtt_subscribe]:
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        # Лог MQTT
        self.mqtt_log = QTextEdit()
        self.mqtt_log.setReadOnly(True)
        self.mqtt_log.setPlaceholderText("MQTT события...")
        layout.addWidget(self.mqtt_log, 1)
        
        return tab
    
    def mqtt_connect(self):
        """Подключение к MQTT брокеру"""
        server = self.mqtt_server.text().strip()
        port = self.mqtt_port.value()
        
        if not server:
            self.log_message("❌ Введите адрес MQTT сервера")
            return
        
        self.log_message(f"🔗 Подключение к {server}:{port}...")
        self.mqtt_log.append(f"Попытка подключения к {server}:{port}")
        
        # Проверка наличия библиотеки paho-mqtt
        try:
            import paho.mqtt.client as mqtt
            self.mqtt_log.append("✅ Библиотека paho-mqtt найдена")
            self.log_message("✅ MQTT клиент готов к работе")
            self.mqtt_log.append("💡 Реализация подключения будет добавлена в следующей версии")
        except ImportError:
            self.mqtt_log.append("⚠️ Библиотека paho-mqtt не найдена")
            self.log_message("💡 Установите: pip install paho-mqtt")
    
    def mqtt_publish(self):
        """Публикация сообщения MQTT"""
        server = self.mqtt_server.text().strip()
        if not server:
            self.log_message("❌ Сначала подключитесь к MQTT серверу")
            return
        
        self.log_message("📤 Публикация сообщения MQTT...")
        self.mqtt_log.append("💡 Введите топик и сообщение для публикации")
    
    def mqtt_subscribe(self):
        """Подписка на MQTT топик"""
        server = self.mqtt_server.text().strip()
        if not server:
            self.log_message("❌ Сначала подключитесь к MQTT серверу")
            return
        
        self.log_message("📥 Подписка на MQTT топик...")
        self.mqtt_log.append("💡 Введите топик для подписки")
    
    def log_message(self, message: str):
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
