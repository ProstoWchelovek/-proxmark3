#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Professional GUI for Proxmark3 Easy with Iceman Firmware
Версия: 1.0.0
Автор: ProxMaster Team
"""

import sys
import os
import json
import serial
import serial.tools.list_ports
import subprocess
import threading
import queue
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# Проверка наличия PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QPushButton, QLabel, QTextEdit, QComboBox, QLineEdit,
        QProgressBar, QGroupBox, QGridLayout, QSplitter, QFrame, QScrollArea,
        QFileDialog, QMessageBox, QMenu, QAction, QStatusBar, QToolBar,
        QSpinBox, QCheckBox, QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
        QTableWidget, QTableWidgetItem, QHeaderView, QSyntaxHighlighter, QFontDialog,
        QColorDialog, QSystemTrayIcon, QMenu as QTrayMenu, QSplashScreen
    )
    from PyQt6.QtCore import (
        Qt, QThread, pyqtSignal, QObject, QTimer, QSettings, QUrl, QMimeData,
        QPropertyAnimation, QEasingCurve, QVariantAnimation, QParallelAnimationGroup,
        QSequentialAnimationGroup, QStateMachine, QState, QSize, QPoint, QRect
    )
    from PyQt6.QtGui import (
        QIcon, QPixmap, QPainter, QColor, QFont, QPalette, QBrush, QPen,
        QLinearGradient, QRadialGradient, QConicalGradient, QKeySequence,
        QActionGroup, QStandardItemModel, QStandardItem, QTextCursor, QTextCharFormat,
        QSyntaxHighlighter as BaseSyntaxHighlighter, QIntValidator, QDoubleValidator,
        QRegExpValidator, QRegularExpressionValidator, QDesktopServices, QImage,
        QMovie, QBitmap, QMaskGenerator
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("PyQt6 не найден. Установите: pip install PyQt6")

# Импорт локальных модулей
from gui.hex_editor import HexEditorWidget
from gui.node_editor import ProxmasterNodeEditor
from core.device_connector import DeviceConnector
from core.ai_assistant import AIAssistant
from gui.ai_widget import AIAssistantWidget
from utils.logger import ProxMasterLogger
from utils.file_manager import FileManager

# Импорт локальных модулей
from installer.proxspace_installer import ProxSpaceInstaller, IcemanFirmwareManager
from core.ai_assistant import AIAssistant, AIProvider, ai_assistant
from gui.ai_widget import AIFloatingPanel


class CommandLoader:
    """Загрузчик команд из JSON файла"""
    
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.commands = {}
        self.tabs = {}
        self.total_commands = 0
        
    def load(self) -> bool:
        """Загрузка команд из JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.tabs = data.get('tabs', {})
            self.total_commands = data.get('total_commands', 0)
            
            # Преобразование структуры tab->commands в плоский словарь
            for tab_name, tab_data in self.tabs.items():
                if 'commands' in tab_data:
                    for cmd in tab_data['commands']:
                        cmd['tab'] = tab_name
                        self.commands[cmd.get('id', '')] = cmd
                if 'categories' in tab_data:
                    for cat_name, cat_data in tab_data['categories'].items():
                        if 'commands' in cat_data:
                            for cmd in cat_data['commands']:
                                cmd['tab'] = tab_name
                                cmd['category'] = cat_name
                                self.commands[cmd.get('id', '')] = cmd
            
            return True
        except Exception as e:
            print(f"Ошибка загрузки команд: {e}")
            return False
    
    def get_commands_by_category(self, category: str) -> List[Dict]:
        """Получение команд по категории"""
        return [cmd for cmd in self.commands.values() if cmd.get('category') == category or category.upper() in cmd.get('category', '').upper()]
    
    def get_commands_by_tab(self, tab_name: str) -> List[Dict]:
        """Получение команд по вкладке"""
        return [cmd for cmd in self.commands.values() if cmd.get('tab') == tab_name]
    
    def get_command(self, cmd_id: str) -> Optional[Dict]:
        """Получение команды по ID"""
        return self.commands.get(cmd_id)
    
    def search_commands(self, query: str) -> List[Dict]:
        """Поиск команд по запросу"""
        query = query.lower()
        results = []
        for cmd in self.commands.values():
            if (query in cmd.get('name', '').lower() or 
                query in cmd.get('description', '').lower() or
                query in cmd.get('command', '').lower()):
                results.append(cmd)
        return results


class ProxmarkDevice(QObject):
    """Класс для работы с устройством Proxmark3"""
    
    log_signal = pyqtSignal(str, str)  # message, level
    status_signal = pyqtSignal(dict)   # status info
    command_complete_signal = pyqtSignal(str, str)  # command, output
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_connected = False
        self.device_info = {}
        self.command_queue = queue.Queue()
        self.running = False
        
    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """Подключение к устройству"""
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            self.is_connected = True
            self.log_signal.emit(f"Подключено к порту {port}", "SUCCESS")
            
            # Получение информации об устройстве
            self.get_device_info()
            
            return True
        except Exception as e:
            self.log_signal.emit(f"Ошибка подключения: {str(e)}", "ERROR")
            return False
    
    def disconnect(self):
        """Отключение от устройства"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
                self.is_connected = False
                self.log_signal.emit("Отключено от устройства", "INFO")
            except Exception as e:
                self.log_signal.emit(f"Ошибка отключения: {str(e)}", "ERROR")
    
    def send_command(self, command: str, wait_response: bool = True) -> str:
        """Отправка команды устройству"""
        if not self.is_connected or not self.serial_port:
            error_msg = "Устройство не подключено"
            self.log_signal.emit(error_msg, "ERROR")
            return error_msg
        
        try:
            # Добавление новой строки к команде
            full_command = command + "\n"
            self.serial_port.write(full_command.encode('utf-8'))
            self.serial_port.flush()
            
            self.log_signal.emit(f">>> {command}", "COMMAND")
            
            if wait_response:
                response = self.read_response()
                self.command_complete_signal.emit(command, response)
                return response
            
            return "Команда отправлена"
            
        except Exception as e:
            error_msg = f"Ошибка отправки команды: {str(e)}"
            self.log_signal.emit(error_msg, "ERROR")
            return error_msg
    
    def read_response(self, timeout: float = 5.0) -> str:
        """Чтение ответа от устройства"""
        if not self.serial_port:
            return ""
        
        response = ""
        start_time = datetime.now()
        
        try:
            while (datetime.now() - start_time).total_seconds() < timeout:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore')
                    response += line
                    if line.strip() and not line.startswith('#'):
                        break
            
            # Чтение дополнительных строк
            self.serial_port.timeout = 0.5
            while True:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore')
                    response += line
                    if "pm3 -->" in line or len(line.strip()) == 0:
                        break
                else:
                    break
                    
        except Exception as e:
            self.log_signal.emit(f"Ошибка чтения ответа: {str(e)}", "ERROR")
        
        return response.strip()
    
    def get_device_info(self) -> Dict:
        """Получение информации об устройстве"""
        if not self.is_connected:
            return {}
        
        try:
            # Запрос версии устройства
            response = self.send_command("hw version")
            
            # Парсинг информации
            info = {
                "connected": True,
                "raw_response": response
            }
            
            # Извлечение версий
            version_patterns = {
                "hardware": r"Hardware:\s*(.+)",
                "firmware": r"Firmware:\s*(.+)",
                "bootrom": r"Bootrom:\s*(.+)"
            }
            
            for key, pattern in version_patterns.items():
                match = re.search(pattern, response)
                if match:
                    info[key] = match.group(1).strip()
            
            self.device_info = info
            self.status_signal.emit(info)
            
            return info
            
        except Exception as e:
            self.log_signal.emit(f"Ошибка получения информации: {str(e)}", "ERROR")
            return {}
    
    def auto_detect_port(self) -> Optional[str]:
        """Автоматическое определение COM-порта"""
        ports = serial.tools.list_ports.comports()
        proxmark_ports = []
        
        for port in ports:
            # Поиск по VID/PID Proxmark
            if "09ac" in port.hwid.lower() or "proxmark" in port.description.lower():
                proxmark_ports.append(port.device)
            # Также проверяем стандартные COM порты
            elif "COM" in port.device or "tty" in port.device:
                proxmark_ports.append(port.device)
        
        if proxmark_ports:
            return proxmark_ports[0]
        
        return None
    
    def get_available_ports(self) -> List[Dict]:
        """Получение списка доступных портов"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid
            })
        return ports


class LogHighlighter(QTextCursor):
    """Подсветка логов"""
    
    STYLES = {
        'INFO': {'color': '#ffffff', 'weight': 'normal'},
        'SUCCESS': {'color': '#4caf50', 'weight': 'bold'},
        'WARNING': {'color': '#ff9800', 'weight': 'bold'},
        'ERROR': {'color': '#f44336', 'weight': 'bold'},
        'COMMAND': {'color': '#2196f3', 'weight': 'normal'},
        'RESPONSE': {'color': '#9e9e9e', 'weight': 'normal'}
    }
    
    @staticmethod
    def get_style(level: str) -> Dict:
        return LogHighlighter.STYLES.get(level.upper(), LogHighlighter.STYLES['INFO'])


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Загрузка настроек
        self.settings = QSettings("ProxMaster", "ProxMaster3Easy")
        
        # Инициализация компонентов
        self.device = ProxmarkDevice()
        self.command_loader = CommandLoader("commands.json")
        self.installer = ProxSpaceInstaller()
        self.ai_assistant = ai_assistant  # Глобальный экземпляр ИИ
        self.ai_panel = None  # Плавающая панель ИИ
        
        # Загрузка команд
        if not self.command_loader.load():
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить команды из commands.json")
            sys.exit(1)
        
        # Настройка интерфейса
        self.init_ui()
        self.apply_theme()
        
        # Подключение сигналов
        self.connect_signals()
        
        # Автоопределение устройства
        self.auto_detect_device()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("ProxMaster3 Easy - Professional RFID Tool")
        self.setMinimumSize(1400, 900)
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральная виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель
        self.create_top_panel(main_layout)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Создание вкладок
        self.create_tabs()
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        # Меню
        self.create_menu_bar()
        
        # Панель инструментов
        self.create_tool_bar()
        
    def create_top_panel(self, layout: QVBoxLayout):
        """Создание верхней панели"""
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        top_layout = QHBoxLayout(top_frame)
        
        # Информация об устройстве
        device_group = QGroupBox("🔌 Устройство")
        device_layout = QHBoxLayout(device_group)
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.port_combo.setEditable(True)
        
        self.connect_btn = QPushButton("🔗 Подключить")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        self.device_status_label = QLabel("❌ Не подключено")
        self.device_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        
        device_layout.addWidget(QLabel("Порт:"))
        device_layout.addWidget(self.port_combo)
        device_layout.addWidget(self.connect_btn)
        device_layout.addWidget(self.device_status_label)
        device_layout.addStretch()
        
        # Кнопка обновления портов
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(40)
        refresh_btn.clicked.connect(self.refresh_ports)
        device_layout.addWidget(refresh_btn)
        
        top_layout.addWidget(device_group)
        
        # Быстрые действия
        actions_group = QGroupBox("⚡ Быстрые действия")
        actions_layout = QHBoxLayout(actions_group)
        
        self.auto_search_btn = QPushButton("🔍 Автопоиск")
        self.auto_search_btn.clicked.connect(lambda: self.execute_command("auto search"))
        
        self.hw_status_btn = QPushButton("📊 Статус")
        self.hw_status_btn.clicked.connect(lambda: self.execute_command("hw status"))
        
        self.hw_tune_btn = QPushButton("📡 Tune")
        self.hw_tune_btn.clicked.connect(lambda: self.execute_command("hw tune"))
        
        actions_layout.addWidget(self.auto_search_btn)
        actions_layout.addWidget(self.hw_status_btn)
        actions_layout.addWidget(self.hw_tune_btn)
        
        top_layout.addWidget(actions_group)
        
        layout.addWidget(top_frame)
        
    def create_tabs(self):
        """Создание вкладок"""
        tabs_config = [
            ("🏠 Главная", self.create_home_tab),
            ("🔍 Поиск", self.create_search_tab),
            ("💾 Менеджер данных", self.create_data_manager_tab),
            ("✏️ Запись", self.create_write_tab),
            ("🎭 Эмуляция", self.create_emulation_tab),
            ("📡 Снифинг", self.create_sniffing_tab),
            ("📜 Скрипты", self.create_scripts_tab),
            ("🛠️ Инструменты", self.create_tools_tab),
            ("⚙️ Настройки", self.create_settings_tab)
        ]
        
        for tab_name, create_func in tabs_config:
            tab_widget = create_func()
            self.tab_widget.addTab(tab_widget, tab_name)
        
    def create_home_tab(self) -> QWidget:
        """Создание вкладки Главная"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Статус устройства
        status_frame = QFrame()
        status_frame.setStyleSheet("QFrame { background-color: #34495e; border-radius: 10px; padding: 15px; }")
        status_layout = QGridLayout(status_frame)
        
        # Информация об устройстве
        info_labels = [
            ("Статус:", self.device_status_label),
            ("Порт:", QLabel("N/A")),
            ("Версия HW:", QLabel("N/A")),
            ("Версия FW:", QLabel("N/A")),
            ("Bootrom:", QLabel("N/A"))
        ]
        
        for i, (label_text, label_widget) in enumerate(info_labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; color: #ecf0f1;")
            status_layout.addWidget(label, i, 0)
            status_layout.addWidget(label_widget, i, 1)
        
        layout.addWidget(status_frame)
        
        # Быстрые команды
        quick_cmds_frame = QGroupBox("⚡ Быстрые команды")
        quick_cmds_layout = QGridLayout(quick_cmds_frame)
        
        quick_commands = [
            ("hw status", "📊 Статус устройства"),
            ("hw version", "ℹ️ Версия"),
            ("hw tune", "📡 Настройка антенны"),
            ("auto search", "🔍 Автопоиск карт"),
            ("data list", "📋 Список данных"),
            ("help", "❓ Помощь")
        ]
        
        for i, (cmd, name) in enumerate(quick_commands):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
            row = i // 3
            col = i % 3
            quick_cmds_layout.addWidget(btn, row, col)
        
        layout.addWidget(quick_cmds_frame)
        layout.addStretch()
        
        return widget
        
    def create_search_tab(self) -> QWidget:
        """Создание вкладки Поиск"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # LF Поиск
        lf_group = QGroupBox("📡 LF Поиск (125 kHz)")
        lf_layout = QVBoxLayout(lf_group)
        
        lf_commands = self.command_loader.get_commands_by_tab("ПОИСК")[:20]  # Первые 20 команд из вкладки ПОИСК
        for cmd_info in lf_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command(c.get('command', '')))
            lf_layout.addWidget(btn)
        
        # HF Поиск
        hf_group = QGroupBox("📶 HF Поиск (13.56 MHz)")
        hf_layout = QVBoxLayout(hf_group)
        
        hf_commands = self.command_loader.get_commands_by_tab("ПОИСК")[20:40]  # Следующие 20 команд
        for cmd_info in hf_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command(c.get('command', '')))
            hf_layout.addWidget(btn)
        
        # Размещение
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(lf_group)
        splitter.addWidget(hf_group)
        layout.addWidget(splitter)
        
        return widget
        
    def create_data_manager_tab(self) -> QWidget:
        """Создание вкладки Менеджер данных с профессиональным Hex редактором"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        self.btn_load_dump = QPushButton("📂 Открыть файл")
        self.btn_save_dump = QPushButton("💾 Сохранить в файл")
        self.btn_copy_hex = QPushButton("📋 Копировать HEX")
        self.btn_paste_hex = QPushButton("📥 Вставить HEX")
        self.btn_fill = QPushButton("🎨 Заполнить")
        self.btn_undo = QPushButton("↩️ Отменить")
        
        for btn in [self.btn_load_dump, self.btn_save_dump, self.btn_copy_hex, self.btn_paste_hex, self.btn_fill, self.btn_undo]:
            btn.setFixedHeight(35)
            toolbar.addWidget(btn)
        
        toolbar.addStretch()
        
        self.lbl_file_info = QLabel("Файл: нет | Размер: 0 байт")
        self.lbl_file_info.setStyleSheet("color: #aaa; padding: 5px;")
        toolbar.addWidget(self.lbl_file_info)
        
        layout.addLayout(toolbar)
        
        # Профессиональный Hex редактор
        self.hex_editor = HexEditorWidget()
        self.hex_editor.data_changed.connect(self.on_hex_data_changed)
        layout.addWidget(self.hex_editor)
        
        # Подключение кнопок
        self.btn_load_dump.clicked.connect(self.load_dump_file)
        self.btn_save_dump.clicked.connect(self.save_dump_file)
        self.btn_copy_hex.clicked.connect(self.hex_editor.copy_hex)
        self.btn_paste_hex.clicked.connect(self.hex_editor.paste_hex)
        self.btn_undo.clicked.connect(self.hex_editor.undo_last_change)
        self.btn_fill.clicked.connect(self.show_fill_dialog)
        
        return widget
    
    def load_dump_file(self):
        """Загрузка дампа из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть дамп", "dumps/", 
            "Все файлы (*);;Hex файлы (*.hex);;Bin файлы (*.bin)"
        )
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                self.hex_editor.set_data(data)
                self.lbl_file_info.setText(f"Файл: {os.path.basename(file_path)} | Размер: {len(data)} байт")
                self.log_success(f"Загружен дамп: {file_path} ({len(data)} байт)")
            except Exception as e:
                self.log_error(f"Ошибка загрузки: {e}")
    
    def save_dump_file(self):
        """Сохранение дампа в файл"""
        data = self.hex_editor.get_data()
        if not data:
            self.log_warning("Нет данных для сохранения")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить дамп", "dumps/dump_", 
            "Bin файлы (*.bin);;Hex файлы (*.hex);;Все файлы (*)"
        )
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(data)
                self.log_success(f"Сохранен дамп: {file_path} ({len(data)} байт)")
            except Exception as e:
                self.log_error(f"Ошибка сохранения: {e}")
    
    def on_hex_data_changed(self, data: bytes):
        """Обработка изменения данных в hex редакторе"""
        self.lbl_file_info.setText(f"Размер: {len(data)} байт | Изменено")
    
    def show_fill_dialog(self):
        """Показ диалога заполнения"""
        from gui.hex_editor import FillDialog
        dialog = FillDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            start = dialog.spin_start.value()
            end = dialog.spin_end.value()
            value = dialog.spin_value.value()
            if start <= end and end < len(self.hex_editor.get_data()):
                self.hex_editor.fill_bytes(start, end, value)
                self.log_success(f"Заполнено {end - start + 1} байт значением 0x{value:02X}")
            else:
                self.log_error("Неверный диапазон")
        
    def create_write_tab(self) -> QWidget:
        """Создание вкладки Запись"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Скролл для команд
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        write_commands = self.command_loader.get_commands_by_tab("ЗАПИСЬ")
        if not write_commands:
            write_commands = self.command_loader.get_commands_by_category("WRITE")
        
        for cmd_info in write_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            
            if cmd_info.get('warning'):
                btn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
            
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command_with_confirm(c))
            scroll_layout.addWidget(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def create_emulation_tab(self) -> QWidget:
        """Создание вкладки Эмуляция"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        emul_commands = self.command_loader.get_commands_by_tab("ЭМУЛЯЦИЯ")
        if not emul_commands:
            emul_commands = self.command_loader.get_commands_by_category("EMULATION")
        
        for cmd_info in emul_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command(c.get('command', '')))
            scroll_layout.addWidget(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
    
    def create_sniffing_tab(self) -> QWidget:
        """Создание вкладки Снифинг"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        sniff_commands = self.command_loader.get_commands_by_tab("СНИФИНГ")
        if not sniff_commands:
            sniff_commands = self.command_loader.get_commands_by_category("SNIFFING")
        
        for cmd_info in sniff_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command(c.get('command', '')))
            scroll_layout.addWidget(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
        
    def create_scripts_tab(self) -> QWidget:
        """Создание вкладки Скрипты"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Node Editor - профессиональный редактор с подсветкой и консолью
        node_group = QGroupBox("🔧 Node Editor (JavaScript/Lua)")
        node_layout = QVBoxLayout(node_group)
        
        # Используем профессиональный компонент NodeEditor
        self.node_editor = ProxmasterNodeEditor(ai_assistant=self.ai_assistant)
        node_layout.addWidget(self.node_editor)

        layout.addWidget(node_group)

        return widget
        
    def create_tools_tab(self) -> QWidget:
        """Создание вкладки Инструменты"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        tools_commands = self.command_loader.get_commands_by_tab("ИНСТРУМЕНТЫ")
        if not tools_commands:
            tools_commands = self.command_loader.get_commands_by_category("TOOLS")
        
        for cmd_info in tools_commands:
            btn = QPushButton(f"{cmd_info.get('icon', '')} {cmd_info.get('name', '')}")
            btn.setToolTip(f"{cmd_info.get('description', '')}\n\nКоманда: {cmd_info.get('command', '')}")
            btn.clicked.connect(lambda checked, c=cmd_info: self.execute_command(c.get('command', '')))
            scroll_layout.addWidget(btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return widget
        
    def create_settings_tab(self) -> QWidget:
        """Создание вкладки Настройки"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Настройки ProxSpace
        proxspace_group = QGroupBox("📦 ProxSpace Установка")
        proxspace_layout = QVBoxLayout(proxspace_group)
        
        install_btn = QPushButton("📥 Установить ProxSpace и Iceman")
        install_btn.clicked.connect(self.run_installer)
        
        update_btn = QPushButton("🔄 Обновить ProxSpace")
        update_btn.clicked.connect(self.update_proxspace)
        
        verify_btn = QPushButton("✅ Проверить установку")
        verify_btn.clicked.connect(self.verify_installation)
        
        proxspace_layout.addWidget(install_btn)
        proxspace_layout.addWidget(update_btn)
        proxspace_layout.addWidget(verify_btn)
        
        layout.addWidget(proxspace_group)
        
        # Настройки темы
        theme_group = QGroupBox("🎨 Тема")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["Тёмная", "Светлая", "Синяя"])
        theme_combo.currentTextChanged.connect(self.change_theme)
        
        theme_layout.addWidget(QLabel("Выберите тему:"))
        theme_layout.addWidget(theme_combo)
        
        layout.addWidget(theme_group)
        layout.addStretch()
        
        return widget
        
    def create_menu_bar(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("📁 Файл")
        
        open_action = QAction("📂 Открыть дамп", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_dump)
        file_menu.addAction(open_action)
        
        save_action = QAction("💾 Сохранить дамп", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_dump)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 Выход", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Инструменты
        tools_menu = menubar.addMenu("🛠️ Инструменты")
        
        ai_action = QAction("🤖 AI Помощник", self)
        ai_action.triggered.connect(self.show_ai_assistant)
        tools_menu.addAction(ai_action)
        
        dev_mode_action = QAction("👨‍💻 Режим разработчика", self)
        dev_mode_action.triggered.connect(self.toggle_dev_mode)
        tools_menu.addAction(dev_mode_action)
        
        # Справка
        help_menu = menubar.addMenu("❓ Справка")
        
        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_tool_bar(self):
        """Создание панели инструментов"""
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction("🔗", self.toggle_connection, "Подключить/Отключить")
        toolbar.addAction("🔍", lambda: self.execute_command("auto search"), "Автопоиск")
        toolbar.addAction("📊", lambda: self.execute_command("hw status"), "Статус")
        toolbar.addSeparator()
        toolbar.addAction("🤖", self.show_ai_assistant, "AI Помощник")
        
    def connect_signals(self):
        """Подключение сигналов"""
        self.device.log_signal.connect(self.append_log)
        self.device.status_signal.connect(self.update_device_status)
        
    def append_log(self, message: str, level: str = "INFO"):
        """Добавление сообщения в лог"""
        # Здесь будет реализация добавления в лог окно
        self.status_bar.showMessage(f"{level}: {message}", 5000)
        
    def update_device_status(self, status: dict):
        """Обновление статуса устройства"""
        if status.get('connected'):
            self.device_status_label.setText("✅ Подключено")
            self.device_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self.device_status_label.setText("❌ Не подключено")
            self.device_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        
    def toggle_connection(self):
        """Переключение подключения"""
        if self.device.is_connected:
            self.device.disconnect()
        else:
            port = self.port_combo.currentText()
            if port:
                self.device.connect(port)
                
    def refresh_ports(self):
        """Обновление списка портов"""
        self.port_combo.clear()
        ports = self.device.get_available_ports()
        for port in ports:
            self.port_combo.addItem(f"{port['device']} - {port['description']}")
            
    def auto_detect_device(self):
        """Автоопределение устройства"""
        port = self.device.auto_detect_port()
        if port:
            self.port_combo.setCurrentText(port)
            
    def execute_command(self, command: str):
        """Выполнение команды"""
        if not self.device.is_connected:
            QMessageBox.warning(self, "Внимание", "Сначала подключитесь к устройству!")
            return
        
        threading.Thread(target=self.device.send_command, args=(command,), daemon=True).start()
        
    def execute_command_with_confirm(self, cmd_info: dict):
        """Выполнение команды с подтверждением"""
        if cmd_info.get('warning'):
            reply = QMessageBox.warning(
                self,
                "⚠️ Предупреждение",
                cmd_info.get('warning'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.execute_command(cmd_info.get('command', ''))
        
    def load_dump(self):
        """Загрузка дампа"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить дамп", "dumps/", "Все файлы (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                self.hex_editor.setText(content)
                self.append_log(f"Загружен дамп: {file_path}", "SUCCESS")
            except Exception as e:
                self.append_log(f"Ошибка загрузки: {str(e)}", "ERROR")
                
    def save_dump(self):
        """Сохранение дампа"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить дамп", "dumps/dump_", "Все файлы (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.hex_editor.toPlainText())
                self.append_log(f"Сохранён дамп: {file_path}", "SUCCESS")
            except Exception as e:
                self.append_log(f"Ошибка сохранения: {str(e)}", "ERROR")
                
    def run_installer(self):
        """Запуск установщика"""
        self.append_log("Запуск установщика ProxSpace...", "INFO")
        # Здесь будет интеграция с GUI установщика
        
    def update_proxspace(self):
        """Обновление ProxSpace"""
        self.append_log("Обновление ProxSpace...", "INFO")
        success = self.installer.update_proxspace()
        if success:
            self.append_log("ProxSpace обновлён успешно", "SUCCESS")
        else:
            self.append_log("Ошибка обновления ProxSpace", "ERROR")
            
    def verify_installation(self):
        """Проверка установки"""
        results = self.installer.verify_installation()
        for check, status in results.items():
            status_str = "✅" if status else "❌"
            self.append_log(f"{status_str} {check}", "INFO" if status else "WARNING")
            
    def show_ai_assistant(self):
        """Показ AI помощника"""
        QMessageBox.information(self, "AI Помощник", "AI помощник будет реализован в следующей версии\n\nПоддержка:\n- LM Studio\n- Cherry Studio\n- Ollama\n\nРежим разработчика позволит редактировать код в реальном времени.")
        
    def toggle_dev_mode(self):
        """Переключение режима разработчика"""
        QMessageBox.information(self, "Режим разработчика", "Режим разработчика позволяет:\n- Редактировать код в реальном времени\n- Создавать новые команды\n- Модифицировать JSON конфигурацию\n- Интегрировать AI для автодополнения")
        
    def change_theme(self, theme: str):
        """Смена темы"""
        self.apply_theme(theme)
        
    def apply_theme(self, theme: str = "Тёмная"):
        """Применение темы"""
        if theme == "Тёмная":
            self.setStyleSheet("""
                QMainWindow { background-color: #1a1a2e; }
                QWidget { color: #ffffff; background-color: #16213e; }
                QPushButton { 
                    background-color: #0f3460; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 8px;
                }
                QPushButton:hover { background-color: #e94560; }
                QTabWidget::pane { border: 1px solid #0f3460; }
                QTabBar::tab { 
                    background-color: #0f3460; 
                    color: white; 
                    padding: 10px;
                }
                QTabBar::tab:selected { background-color: #e94560; }
            """)
        elif theme == "Светлая":
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f5f5; }
                QWidget { color: #333333; background-color: #ffffff; }
                QPushButton { 
                    background-color: #2196f3; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 8px;
                }
                QPushButton:hover { background-color: #1976d2; }
            """)
        
    def show_about(self):
        """Показ окна О программе"""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>ProxMaster3 Easy v1.0.0</h2>"
            "<p>Профессиональный инструмент для работы с Proxmark3 Easy</p>"
            "<p>Поддержка прошивки Iceman через ProxSpace</p>"
            "<p>© 2024 ProxMaster Team</p>"
        )

    def show_ai_assistant(self):
        """Показать ИИ помощника"""
        if not self.ai_panel:
            self.ai_panel = AIFloatingPanel(self.ai_assistant, self)
        
        self.ai_panel.show()
        self.ai_panel.raise_()
        self.ai_panel.activateWindow()
    
    def toggle_dev_mode(self):
        """Переключить режим разработчика"""
        is_enabled = not self.ai_assistant.config.dev_mode
        self.ai_assistant.enable_dev_mode(is_enabled)
        
        if is_enabled:
            QMessageBox.information(
                self,
                "Режим разработчика",
                "✅ Режим разработчика активирован!\n\n"
                "Теперь ИИ имеет доступ к:\n"
                "- Исходному коду приложения\n"
                "- Модулям GUI\n"
                "- Ядру работы с устройством\n"
                "- Конфигурационным файлам\n"
                "- Системе обновлений\n\n"
                "Выберите режим 'developer' в панели ИИ для начала работы."
            )
        else:
            QMessageBox.information(
                self,
                "Режим разработчика",
                "Режим разработчика деактивирован"
            )
    
    def load_ai_config(self):
        """Загрузить конфигурацию ИИ"""
        try:
            config_path = "models/ai_config.json"
            if os.path.exists(config_path):
                self.ai_assistant.load_config(config_path)
                print(f"[Main] Конфигурация ИИ загружена из {config_path}")
        except Exception as e:
            print(f"[Main] Ошибка загрузки конфигурации ИИ: {e}")


def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)
    app.setApplicationName("ProxMaster3 Easy")
    app.setOrganizationName("ProxMaster")
    
    # Показ splash screen
    splash_pix = QPixmap(400, 300)
    splash_pix.fill(QColor("#1a1a2e"))
    splash = QSplashScreen(splash_pix)
    splash.showMessage(
        "ProxMaster3 Easy\nProfessional RFID Tool\nv1.0.0",
        Qt.AlignCenter,
        QColor("#ffffff")
    )
    splash.show()
    
    # Задержка для показа splash
    QTimer.singleShot(2000, lambda: splash.finish(None))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
