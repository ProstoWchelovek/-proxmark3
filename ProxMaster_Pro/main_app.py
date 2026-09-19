#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster Pro - Профессиональный инструмент для управления Proxmark3
Главное приложение с 9 вкладками
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTextEdit, QPushButton,
                             QLabel, QComboBox, QProgressBar, QSplitter, 
                             QFrame, QScrollArea, QGroupBox, QLineEdit,
                             QMessageBox, QFileDialog, QToolBar, QStatusBar,
                             QSystemTrayIcon, QMenu, QAction)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction

from core.engine import ProxMasterEngine, CommandResult, LogEntry
from widgets.editors import HexEditor, NodeEditor, SettingsPanel


class LogWidget(QTextEdit):
    """Виджет лога с цветным выводом"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont('Consolas', 9))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 5px;
                padding: 5px;
            }
        """)
    
    def append_log(self, entry: LogEntry):
        """Добавить запись лога с цветом"""
        colors = {
            'INFO': '#4CAF50',
            'SUCCESS': '#2196F3',
            'WARNING': '#FF9800',
            'ERROR': '#F44336',
            'DEBUG': '#9E9E9E'
        }
        
        color = colors.get(entry.level, '#D4D4D4')
        time_str = entry.timestamp.strftime('%H:%M:%S')
        
        html = f'<span style="color: {color};">[{time_str}] [{entry.level}]</span> {entry.message}<br>'
        self.append(html)
        self.scrollToBottom()
    
    def clear_log(self):
        """Очистить лог"""
        self.clear()


class CommandButton(QPushButton):
    """Кнопка команды с информацией о риске"""
    
    def __init__(self, cmd_data: dict, parent=None):
        super().__init__(cmd_data.get('name', 'Command'), parent)
        self.cmd_data = cmd_data
        self.setToolTip(f"{cmd_data.get('description', '')}\n\nРиск: {cmd_data.get('risk_level', 'safe')}")
        
        # Цвет по уровню риска
        risk_colors = {
            'safe': '#4CAF50',
            'medium': '#FF9800',
            'high': '#F44336',
            'dangerous': '#9C27B0'
        }
        
        color = risk_colors.get(cmd_data.get('risk_level', 'safe'), '#4CAF50')
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
            QPushButton:pressed {{
                background-color: {color}BB;
            }}
        """)


class MainTab(QWidget):
    """Главная вкладка - быстрые безопасные операции"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Статус устройства
        status_group = QGroupBox('📊 Статус устройства')
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel('Устройство не подключено')
        self.status_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        status_layout.addWidget(self.status_label)
        
        self.version_label = QLabel('Версия: неизвестно')
        status_layout.addWidget(self.version_label)
        
        layout.addWidget(status_group)
        
        # Быстрые команды
        quick_group = QGroupBox('⚡ Быстрые команды')
        quick_layout = QHBoxLayout(quick_group)
        
        # Получаем безопасные команды для главной вкладки
        commands = self.engine.get_commands_for_tab('main')
        
        for cmd in commands[:6]:  # Показываем первые 6
            btn = CommandButton(cmd)
            btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
            quick_layout.addWidget(btn)
        
        layout.addWidget(quick_group)
        
        # Последние результаты
        result_group = QGroupBox('📋 Последние результаты')
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        layout.addStretch()
    
    def execute_command(self, cmd_data: dict):
        """Выполнить команду"""
        cmd_id = cmd_data.get('id')
        
        # Предупреждение для опасных команд
        risk = cmd_data.get('risk_level', 'safe')
        if risk in ['high', 'dangerous']:
            reply = QMessageBox.warning(self, 'Предупреждение',
                                       f"Команда '{cmd_data.get('name')}' имеет уровень риска: {risk}\n\n"
                                       "Продолжить?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Выполнение
        result = self.engine.execute(cmd_id)
        
        # Отображение результата
        self.result_text.append(f"\n=== {cmd_data.get('name')} ===")
        self.result_text.append(result.output)
        
        # Обновление статуса
        if cmd_id == 'version':
            self.version_label.setText(f"Версия: {result.output[:50]}...")
        elif cmd_id == 'status':
            self.status_label.setText('Статус получен')


class SearchTab(QWidget):
    """Вкладка поиска карт"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Категории поиска
        categories = self.engine.get_categories_for_tab('search')
        
        for cat in categories:
            group = QGroupBox(cat.get('name', 'Категория'))
            group_layout = QHBoxLayout(group)
            
            commands = cat.get('commands', [])
            for cmd in commands:
                btn = CommandButton(cmd)
                btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
                group_layout.addWidget(btn)
            
            layout.addWidget(group)
        
        layout.addStretch()
    
    def execute_command(self, cmd_data: dict):
        """Выполнить команду поиска"""
        cmd_id = cmd_data.get('id')
        result = self.engine.execute(cmd_id, timeout=cmd_data.get('timeout', 30000))
        
        self.log_widget.append_log(LogEntry(
            level='SUCCESS' if result.success else 'ERROR',
            message=f"{cmd_data.get('name')}: {result.output[:100]}",
            timestamp=result.timestamp
        ))


class ManagerTab(QWidget):
    """Менеджер карт и ключей с Hex редактором"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Список карт
        cards_group = QGroupBox('💾 Сохраненные карты')
        cards_layout = QVBoxLayout(cards_group)
        
        self.cards_list = QComboBox()
        self.cards_list.addItem('Выберите карту...')
        cards_layout.addWidget(self.cards_list)
        
        btn_load = QPushButton('📂 Загрузить дамп')
        btn_load.clicked.connect(self.load_dump)
        cards_layout.addWidget(btn_load)
        
        btn_save = QPushButton('💾 Сохранить дамп')
        btn_save.clicked.connect(self.save_dump)
        cards_layout.addWidget(btn_save)
        
        splitter.addWidget(cards_group)
        
        # Hex редактор
        hex_group = QGroupBox('🔧 Hex редактор')
        hex_layout = QVBoxLayout(hex_group)
        
        self.hex_editor = HexEditor()
        hex_layout.addWidget(self.hex_editor)
        
        splitter.addWidget(hex_group)
        
        layout.addWidget(splitter)
    
    def load_dump(self):
        """Загрузить дамп"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Загрузить дамп', '', 
                                                  'BIN файлы (*.bin);;Все файлы (*)')
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                self.hex_editor.set_data(data)
                
                # Добавляем в список
                self.cards_list.addItem(os.path.basename(filename))
                
                self.log_widget.append_log(LogEntry(
                    level='SUCCESS',
                    message=f'Загружен дамп: {filename}',
                    timestamp=LogEntry(0, '', None).timestamp
                ))
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить: {e}')
    
    def save_dump(self):
        """Сохранить дамп"""
        data = self.hex_editor.get_data()
        if not data:
            QMessageBox.warning(self, 'Предупреждение', 'Нет данных для сохранения')
            return
        
        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить дамп', '', 
                                                  'BIN файлы (*.bin)')
        if filename:
            try:
                with open(filename, 'wb') as f:
                    f.write(data)
                
                self.log_widget.append_log(LogEntry(
                    level='SUCCESS',
                    message=f'Сохранен дамп: {filename}',
                    timestamp=LogEntry(0, '', None).timestamp
                ))
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить: {e}')


class WriteTab(QWidget):
    """Вкладка записи и клонирования"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Категории записи
        categories = self.engine.get_categories_for_tab('write')
        
        for cat in categories:
            group = QGroupBox(cat.get('name', 'Категория'))
            group_layout = QVBoxLayout(group)
            
            commands = cat.get('commands', [])
            for cmd in commands:
                btn = CommandButton(cmd)
                btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
                group_layout.addWidget(btn)
            
            layout.addWidget(group)
        
        layout.addStretch()
    
    def execute_command(self, cmd_data: dict):
        """Выполнить команду записи"""
        # Проверка риска
        risk = cmd_data.get('risk_level', 'safe')
        if risk in ['high', 'dangerous']:
            reply = QMessageBox.warning(self, 'ОПАСНО!',
                                       f"Команда '{cmd_data.get('name')}' может необратимо изменить карту!\n\n"
                                       f"Уровень риска: {risk}\n\nПродолжить?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        cmd_id = cmd_data.get('id')
        result = self.engine.execute(cmd_id, timeout=cmd_data.get('timeout', 10000))
        
        self.log_widget.append_log(LogEntry(
            level='SUCCESS' if result.success else 'ERROR',
            message=f"{cmd_data.get('name')}: {result.output[:100]}",
            timestamp=result.timestamp
        ))


class EmulationTab(QWidget):
    """Вкладка эмуляции"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel('🎭 Эмуляция карт\n\nВыберите тип карты для эмуляции')
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet('font-size: 16px; padding: 20px;')
        layout.addWidget(info_label)
        
        # Кнопки эмуляции
        emul_commands = [
            {'id': 'hf_14a_sim', 'name': 'Эмуляция ISO14443-A'},
            {'id': 'lf_em_sim', 'name': 'Эмуляция EM4100'},
            {'id': 'lf_hid_sim', 'name': 'Эмуляция HID Prox'},
        ]
        
        for cmd_info in emul_commands:
            btn = QPushButton(cmd_info['name'])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-size: 14px;
                    padding: 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            btn.clicked.connect(lambda checked, cid=cmd_info['id']: self.start_emulation(cid))
            layout.addWidget(btn)
        
        layout.addStretch()
    
    def start_emulation(self, cmd_id: str):
        """Запустить эмуляцию"""
        result = self.engine.execute(cmd_id, timeout=60000)
        
        self.log_widget.append_log(LogEntry(
            level='INFO',
            message=f"Эмуляция запущена: {cmd_id}",
            timestamp=result.timestamp if hasattr(result, 'timestamp') else LogEntry(0, '', None).timestamp
        ))


class SniffingTab(QWidget):
    """Вкладка сниффинга"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        sniff_group = QGroupBox('📡 Сниффинг трафика')
        sniff_layout = QVBoxLayout(sniff_group)
        
        btn_hf_snoop = QPushButton('Сниффинг HF')
        btn_hf_snoop.clicked.connect(lambda: self.start_sniff('hf_14a_snoop'))
        sniff_layout.addWidget(btn_hf_snoop)
        
        btn_lf_snoop = QPushButton('Сниффинг LF')
        btn_lf_snoop.clicked.connect(lambda: self.start_sniff('lf_snoop'))
        sniff_layout.addWidget(btn_lf_snoop)
        
        layout.addWidget(sniff_group)
        
        # Результаты
        self.sniff_result = QTextEdit()
        self.sniff_result.setReadOnly(True)
        self.sniff_result.setPlaceholderText('Здесь появятся результаты сниффинга...')
        layout.addWidget(self.sniff_result)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        btn_list = QPushButton('📋 Показать трассировку')
        btn_list.clicked.connect(self.show_trace)
        btn_layout.addWidget(btn_list)
        
        btn_clear = QPushButton('🗑️ Очистить')
        btn_clear.clicked.connect(self.clear_trace)
        btn_layout.addWidget(btn_clear)
        
        layout.addLayout(btn_layout)
    
    def start_sniff(self, cmd_id: str):
        """Запустить сниффинг"""
        self.sniff_result.append(f"Запуск сниффинга: {cmd_id}...")
        result = self.engine.execute(cmd_id, timeout=60000)
        self.sniff_result.append(result.output)
    
    def show_trace(self):
        """Показать трассировку"""
        result = self.engine.execute('trace_list')
        self.sniff_result.append("\n=== Трассировка ===\n")
        self.sniff_result.append(result.output)
    
    def clear_trace(self):
        """Очистить трассировку"""
        self.engine.execute('trace_clear')
        self.sniff_result.clear()
        self.sniff_result.append('Трассировка очищена')


class ScriptsTab(QWidget):
    """Вкладка скриптов с Node Editor"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Node Editor
        self.node_editor = NodeEditor()
        layout.addWidget(self.node_editor)
        
        # Панель скрипта
        script_group = QGroupBox('📜 Сгенерированный скрипт')
        script_layout = QVBoxLayout(script_group)
        
        self.script_text = QTextEdit()
        self.script_text.setReadOnly(True)
        self.script_text.setFont(QFont('Consolas', 10))
        script_layout.addWidget(self.script_text)
        
        layout.addWidget(script_group)
        
        # Подключение сигнала
        self.node_editor.script_generated.connect(self.script_text.setText)


class ToolsTab(QWidget):
    """Вкладка инструментов (графики, анализ)"""
    
    def __init__(self, engine: ProxMasterEngine, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.log_widget = log_widget
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Графики
        plot_group = QGroupBox('📈 Графики и анализ')
        plot_layout = QVBoxLayout(plot_group)
        
        btn_plot = QPushButton('Построить график сигнала')
        btn_plot.clicked.connect(self.plot_signal)
        plot_layout.addWidget(btn_plot)
        
        btn_samples = QPushButton('Получить сэмплы')
        btn_samples.clicked.connect(self.get_samples)
        plot_layout.addWidget(btn_samples)
        
        layout.addWidget(plot_group)
        
        # Обработка данных
        data_group = QGroupBox('🔧 Обработка данных')
        data_layout = QVBoxLayout(data_group)
        
        data_commands = ['data_hex', 'data_demod', 'data_manchester', 'data_biphase']
        for cmd_id in data_commands:
            cmd = self.engine.get_command(cmd_id)
            if cmd:
                btn = CommandButton(cmd)
                btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
                data_layout.addWidget(btn)
        
        layout.addWidget(data_group)
        
        # Результат
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText('Результаты анализа...')
        layout.addWidget(self.result_text)
        
        layout.addStretch()
    
    def plot_signal(self):
        """Построить график"""
        result = self.engine.execute('plot')
        self.result_text.append("График построен (откроется в отдельном окне)")
        self.result_text.append(result.output)
    
    def get_samples(self):
        """Получить сэмплы"""
        result = self.engine.execute('data_samples')
        self.result_text.append("Сэмплы получены:")
        self.result_text.append(result.output[:500])
    
    def execute_command(self, cmd_data: dict):
        """Выполнить команду"""
        result = self.engine.execute(cmd_data.get('id'))
        self.result_text.append(f"\n{cmd_data.get('name')}:\n{result.output}")


class ProxMasterApp(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация движка
        self.engine = ProxMasterEngine('data/commands.json')
        
        self.init_ui()
        self.apply_dark_theme()
        
        # Таймер обновления лога
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(500)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle('ProxMaster Pro v1.0.0 - Профессиональный инструмент для Proxmark3')
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Верхняя панель
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # Вкладки
        self.tabs = QTabWidget()
        
        # Лог виджет (общий)
        self.log_widget = LogWidget()
        
        # Создание вкладок
        self.main_tab = MainTab(self.engine, self.log_widget)
        self.search_tab = SearchTab(self.engine, self.log_widget)
        self.manager_tab = ManagerTab(self.engine, self.log_widget)
        self.write_tab = WriteTab(self.engine, self.log_widget)
        self.emulation_tab = EmulationTab(self.engine, self.log_widget)
        self.sniffing_tab = SniffingTab(self.engine, self.log_widget)
        self.scripts_tab = ScriptsTab(self.engine, self.log_widget)
        self.tools_tab = ToolsTab(self.engine, self.log_widget)
        self.settings_tab = SettingsPanel()
        
        # Добавление вкладок
        self.tabs.addTab(self.main_tab, '🏠 Главная')
        self.tabs.addTab(self.search_tab, '🔍 Поиск')
        self.tabs.addTab(self.manager_tab, '💾 Менеджер')
        self.tabs.addTab(self.write_tab, '✏️ Запись')
        self.tabs.addTab(self.emulation_tab, '🎭 Эмуляция')
        self.tabs.addTab(self.sniffing_tab, '📡 Сниффинг')
        self.tabs.addTab(self.scripts_tab, '📜 Скрипты')
        self.tabs.addTab(self.tools_tab, '🛠️ Инструменты')
        self.tabs.addTab(self.settings_tab, '⚙️ Настройки')
        
        main_layout.addWidget(self.tabs)
        
        # Лог панель
        log_group = QGroupBox('📋 Лог событий')
        log_layout = QVBoxLayout(log_group)
        log_layout.addWidget(self.log_widget)
        main_layout.addWidget(log_group)
        
        # Статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Готов к работе')
        
        # Меню
        self.create_menu()
    
    def create_top_panel(self) -> QWidget:
        """Создать верхнюю панель"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(panel)
        
        # Подключение
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel('COM порт:'))
        self.port_combo = QComboBox()
        self.refresh_ports()
        conn_layout.addWidget(self.port_combo)
        
        btn_connect = QPushButton('🔌 Подключить')
        btn_connect.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(btn_connect)
        
        btn_refresh = QPushButton('🔄')
        btn_refresh.clicked.connect(self.refresh_ports)
        conn_layout.addWidget(btn_refresh)
        
        layout.addLayout(conn_layout)
        
        # Индикатор подключения
        self.connection_indicator = QLabel('❌ Отключено')
        self.connection_indicator.setStyleSheet('font-weight: bold; color: #F44336;')
        layout.addWidget(self.connection_indicator)
        
        layout.addStretch()
        
        return panel
    
    def create_menu(self):
        """Создать меню"""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu('📁 Файл')
        
        open_action = QAction('Открыть дамп', self)
        file_menu.addAction(open_action)
        
        save_action = QAction('Сохранить дамп', self)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Инструменты
        tools_menu = menubar.addMenu('🛠️ Инструменты')
        
        hex_action = QAction('Hex редактор', self)
        tools_menu.addAction(hex_action)
        
        node_action = QAction('Node Editor', self)
        tools_menu.addAction(node_action)
        
        # Справка
        help_menu = menubar.addMenu('❓ Справка')
        
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def apply_dark_theme(self):
        """Применить темную тему"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QTabWidget::pane {
                border: 1px solid #3C3C3C;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2D2D30;
                color: #CCCCCC;
                padding: 10px 20px;
                border: 1px solid #3C3C3C;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #3E3E42;
            }
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #3C3C3C;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
    
    def refresh_ports(self):
        """Обновить список портов"""
        ports = self.engine.get_ports()
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(f"{port['device']} - {port['description']}")
        
        if ports:
            self.statusBar.showMessage(f'Найдено портов: {len(ports)}')
    
    def toggle_connection(self):
        """Подключить/отключить устройство"""
        if self.engine.is_connected():
            self.engine.disconnect()
            self.connection_indicator.setText('❌ Отключено')
            self.connection_indicator.setStyleSheet('font-weight: bold; color: #F44336;')
            self.statusBar.showMessage('Устройство отключено')
        else:
            port = self.port_combo.currentText().split(' - ')[0]
            if self.engine.connect(port):
                self.connection_indicator.setText('✅ Подключено')
                self.connection_indicator.setStyleSheet('font-weight: bold; color: #4CAF50;')
                self.statusBar.showMessage(f'Подключено к {port}')
                
                # Автозапрос версии
                QTimer.singleShot(500, lambda: self.engine.execute('version'))
            else:
                QMessageBox.critical(self, 'Ошибка', 'Не удалось подключиться к устройству')
    
    def update_log(self):
        """Обновить лог"""
        logs = self.engine.get_log()
        # Можно добавить логику отображения новых записей
    
    def show_about(self):
        """Показать информацию о программе"""
        QMessageBox.about(self, 'О программе',
                         '<h2>ProxMaster Pro v1.0.0</h2>'
                         '<p>Профессиональный инструмент для управления Proxmark3</p>'
                         '<p><b>Возможности:</b></p>'
                         '<ul>'
                         '<li>9 функциональных вкладок</li>'
                         '<li>857+ команд Proxmark3 Iceman</li>'
                         '<li>Hex редактор с Undo/Redo</li>'
                         '<li>Node Editor для скриптов</li>'
                         '<li>Графики и анализ сигналов</li>'
                         '<li>Система обновлений</li>'
                         '</ul>'
                         '<p>© 2024 ProxMaster Team</p>')


def main():
    """Точка входа"""
    app = QApplication(sys.argv)
    
    # Применение стилей
    app.setStyle('Fusion')
    
    window = ProxMasterApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
