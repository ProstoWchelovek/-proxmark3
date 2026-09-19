#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster Pro v3.0 - Профессиональный инструмент управления Proxmark3
Главный файл запуска приложения
© 2024 ProxMaster Pro Team - GPL-3.0 License
"""

import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("❌ Ошибка: Требуется tkinter (python3-tk)")
    print("Установите: sudo apt-get install python3-tk")
    sys.exit(1)

from core.main import (
    ApplicationCore, 
    LogLevel, 
    RiskLevel,
    CommunicationLayer,
    CommandManager,
    DataManager,
    Logger,
    SignalProcessor
)

# Проверяем наличие matplotlib для графиков
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  Предупреждение: matplotlib не установлен. Графики будут недоступны.")
    print("Установите: pip install matplotlib numpy")

# Проверяем наличие numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class ProxMasterApp:
    """Основное приложение ProxMaster Pro"""
    
    def __init__(self):
        # Создаем главное окно
        self.root = tk.Tk()
        self.root.title("🔐 ProxMaster Pro v3.0 - Профессиональный инструмент Proxmark3")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        # Настраиваем стили
        self._setup_styles()
        
        # Определяем пути
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.commands_file = os.path.join(self.base_dir, 'data', 'commands_complete_part1.json')
        
        # Инициализируем ядро приложения
        try:
            self.core = ApplicationCore(
                base_dir=self.base_dir,
                commands_file=self.commands_file
            )
            self.core.add_progress_callback(self._on_progress_update)
            self.core.logger.add_callback(self._on_log_entry)
        except Exception as e:
            messagebox.showerror("Критическая ошибка", f"Не удалось инициализировать ядро:\n{e}")
            sys.exit(1)
        
        # Состояние приложения
        self.device_connected = False
        self.current_tab = None
        self.log_entries = []
        
        # Создаем интерфейс
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()
        self._bind_events()
        
        # Загружаем данные
        self._load_saved_state()
        
        # Пишем приветственное сообщение
        self._log_message("ProxMaster Pro v3.0 запущен", LogLevel.INFO)
        self._log_message(f"Загружено команд: {len(self.core.command_manager.commands)}", LogLevel.INFO)
        self._log_message(f"Категорий: {len(self.core.command_manager.get_all_categories())}", LogLevel.INFO)
        
        if not HAS_MATPLOTLIB:
            self._log_message("Графики недоступны - установите matplotlib", LogLevel.WARNING)
    
    def _setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        
        # Темная тема
        bg_color = '#1e1e1e'
        fg_color = '#ffffff'
        accent_color = '#0078d4'
        
        self.root.configure(bg=bg_color)
        
        # Настраиваем цвета для виджетов
        style.configure('Dark.TFrame', background=bg_color)
        style.configure('Dark.TLabel', background=bg_color, foreground=fg_color, font=('Arial', 10))
        style.configure('Header.TLabel', background=bg_color, foreground=accent_color, 
                       font=('Arial', 12, 'bold'))
        style.configure('Accent.TButton', background=accent_color, foreground='white',
                       font=('Arial', 10, 'bold'))
        style.configure('Warning.TLabel', background=bg_color, foreground='#ff9800')
        style.configure('Error.TLabel', background=bg_color, foreground='#f44336')
        style.configure('Success.TLabel', background=bg_color, foreground='#4caf50')
        
        # Treeview
        style.configure('Dark.Treeview', background='#2d2d2d', foreground=fg_color,
                       fieldbackground='#2d2d2d', font=('Consolas', 10))
        style.configure('Dark.Treeview.Heading', background='#333333', foreground=fg_color,
                       font=('Arial', 10, 'bold'))
        
        # Notebook
        style.configure('Dark.TNotebook', background=bg_color)
        style.configure('Dark.TNotebook.Tab', background='#333333', foreground=fg_color,
                       padding=[20, 10], font=('Arial', 10, 'bold'))
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', accent_color)],
                 foreground=[('selected', 'white')])
    
    def _create_menu(self):
        """Создание главного меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Файл", menu=file_menu)
        file_menu.add_command(label="📂 Открыть дамп", command=self._open_dump, accelerator="Ctrl+O")
        file_menu.add_command(label="💾 Сохранить дамп", command=self._save_dump, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Выход", command=self._on_close, accelerator="Alt+F4")
        
        # Устройство
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📱 Устройство", menu=device_menu)
        device_menu.add_command(label="🔌 Подключить", command=self._connect_device)
        device_menu.add_command(label="🔌 Отключить", command=self._disconnect_device)
        device_menu.add_command(label="🔍 Сканировать порты", command=self._scan_ports)
        device_menu.add_separator()
        device_menu.add_command(label="ℹ️ Информация", command=self._show_device_info)
        
        # Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🛠 Инструменты", menu=tools_menu)
        tools_menu.add_command(label="📊 Hex редактор", command=self._open_hex_editor)
        tools_menu.add_command(label="🔗 Node редактор", command=self._open_node_editor)
        tools_menu.add_command(label="📈 Анализ сигнала", command=self._open_signal_analyzer)
        tools_menu.add_separator()
        tools_menu.add_command(label="⚙️ Настройки", command=self._open_settings)
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Справка", menu=help_menu)
        help_menu.add_command(label="📖 Документация", command=self._open_docs)
        help_menu.add_command(label="📝 О программе", command=self._show_about)
    
    def _create_main_layout(self):
        """Создание основной компоновки"""
        # Главный контейнер
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Верхняя панель с информацией об устройстве
        top_panel = ttk.Frame(main_frame, style='Dark.TFrame')
        top_panel.pack(fill=tk.X, pady=(0, 10))
        
        self.device_label = ttk.Label(top_panel, text="🔴 Устройство не подключено", 
                                     style='Warning.TLabel', font=('Arial', 11, 'bold'))
        self.device_label.pack(side=tk.LEFT)
        
        self.port_label = ttk.Label(top_panel, text="", style='Dark.TLabel')
        self.port_label.pack(side=tk.LEFT, padx=20)
        
        # Кнопки подключения
        btn_frame = ttk.Frame(top_panel, style='Dark.TFrame')
        btn_frame.pack(side=tk.RIGHT)
        
        self.btn_connect = ttk.Button(btn_frame, text="🔌 Подключить", 
                                     command=self._connect_device)
        self.btn_connect.pack(side=tk.LEFT, padx=5)
        
        self.btn_disconnect = ttk.Button(btn_frame, text="🔌 Отключить",
                                        command=self._disconnect_device, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT, padx=5)
        
        self.btn_scan = ttk.Button(btn_frame, text="🔍 Порты",
                                  command=self._scan_ports)
        self.btn_scan.pack(side=tk.LEFT, padx=5)
        
        # Разделитель
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        # Notebook с вкладками
        self.notebook = ttk.Notebook(main_frame, style='Dark.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Создаем вкладки
        self._create_tabs()
        
        # Правая панель с логами
        right_panel = ttk.Frame(main_frame, style='Dark.TFrame', width=400)
        right_panel.pack(fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Заголовок логов
        ttk.Label(right_panel, text="📋 Журнал событий", 
                 style='Header.TLabel').pack(anchor='w', pady=(0, 5))
        
        # Контейнер для кнопок управления логами
        log_controls = ttk.Frame(right_panel, style='Dark.TFrame')
        log_controls.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(log_controls, text="🗑 Очистить", 
                  command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_controls, text="💾 Сохранить", 
                  command=self._save_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_controls, text="📤 Экспорт", 
                  command=self._export_logs).pack(side=tk.LEFT, padx=2)
        
        # Текстовое поле логов
        log_frame = ttk.Frame(right_panel, style='Dark.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, bg='#1e1e1e', fg='#ffffff',
                               font=('Consolas', 9), insertbackground='white',
                               selectbackground='#0078d4', selectforeground='white')
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Настраиваем теги для цветов логов
        self.log_text.tag_configure('DEBUG', foreground='#808080')
        self.log_text.tag_configure('INFO', foreground='#4caf50')
        self.log_text.tag_configure('WARNING', foreground='#ff9800')
        self.log_text.tag_configure('ERROR', foreground='#f44336')
        self.log_text.tag_configure('CRITICAL', foreground='#f44336', font=('Consolas', 9, 'bold'))
    
    def _create_tabs(self):
        """Создание вкладок приложения"""
        
        # Вкладка 1: Главная / Поиск
        tab_search = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_search, text="🔍 Поиск тегов")
        self._create_search_tab(tab_search)
        
        # Вкладка 2: Mifare Classic
        tab_mifare = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_mifare, text="💳 Mifare Classic")
        self._create_mifare_tab(tab_mifare)
        
        # Вкладка 3: Запись карт
        tab_write = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_write, text="✏️ Запись карт")
        self._create_write_tab(tab_write)
        
        # Вкладка 4: Эмуляция
        tab_emulate = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_emulate, text="🎭 Эмуляция")
        self._create_emulate_tab(tab_emulate)
        
        # Вкладка 5: Сниффинг
        tab_sniff = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_sniff, text="📡 Сниффинг")
        self._create_sniff_tab(tab_sniff)
        
        # Вкладка 6: LF операции
        tab_lf = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_lf, text="📶 LF (125 kHz)")
        self._create_lf_tab(tab_lf)
        
        # Вкладка 7: Hex редактор
        tab_hex = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_hex, text="📊 Hex редактор")
        self._create_hex_tab(tab_hex)
        
        # Вкладка 8: Node редактор
        tab_nodes = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_nodes, text="🔗 Node редактор")
        self._create_node_tab(tab_nodes)
        
        # Вкладка 9: Графики и анализ
        tab_analysis = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_analysis, text="📈 Анализ сигнала")
        self._create_analysis_tab(tab_analysis)
        
        # Вкладка 10: Команды
        tab_commands = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_commands, text="⌨️ Все команды")
        self._create_commands_tab(tab_commands)
        
        # Вкладка 11: Устройство
        tab_device = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(tab_device, text="⚙️ Устройство")
        self._create_device_tab(tab_device)
    
    def _create_search_tab(self, parent):
        """Вкладка поиска тегов"""
        # Заголовок
        ttk.Label(parent, text="🔍 Поиск и чтение RFID тегов", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Панель управления
        control_frame = ttk.LabelFrame(parent, text="Параметры поиска", padding=10)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Чекбоксы для типов тегов
        tk.Label(control_frame, text="Типы тегов:", bg='#1e1e1e', fg='white').grid(row=0, column=0, sticky='w')
        
        self.var_hf = tk.BooleanVar(value=True)
        self.var_lf = tk.BooleanVar(value=True)
        self.var_auto = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(control_frame, text="HF (13.56 MHz)", variable=self.var_hf).grid(row=0, column=1, padx=10)
        ttk.Checkbutton(control_frame, text="LF (125 kHz)", variable=self.var_lf).grid(row=0, column=2, padx=10)
        ttk.Checkbutton(control_frame, text="Автоопределение", variable=self.var_auto).grid(row=0, column=3, padx=10)
        
        # Кнопки действий
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=10, sticky='w')
        
        ttk.Button(btn_frame, text="▶ Начать поиск", 
                  command=self._start_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹ Стоп", 
                  command=self._stop_search, state=tk.DISABLED).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Копировать UID", 
                  command=self._copy_uid).pack(side=tk.LEFT, padx=5)
        
        # Результаты поиска
        result_frame = ttk.LabelFrame(parent, text="Результаты", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Treeview для результатов
        columns = ('Type', 'UID', 'ATQA', 'SAK', 'Protocol', 'Info')
        self.search_tree = ttk.Treeview(result_frame, columns=columns, show='headings', 
                                       style='Dark.Treeview', height=15)
        
        for col in columns:
            self.search_tree.heading(col, text=col)
            self.search_tree.column(col, width=100)
        
        self.search_tree.column('UID', width=200)
        self.search_tree.column('Info', width=300)
        
        tree_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, 
                                   command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=tree_scroll.set)
        
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Кнопки действий с найденным тегом
        action_frame = ttk.Frame(result_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(action_frame, text="💾 Сохранить дамп", 
                  command=self._save_tag_dump).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🔑 Получить ключи", 
                  command=self._get_tag_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📊 Показать детали", 
                  command=self._show_tag_details).pack(side=tk.LEFT, padx=5)
    
    def _create_mifare_tab(self, parent):
        """Вкладка Mifare Classic"""
        ttk.Label(parent, text="💳 Работа с Mifare Classic картами", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Выбор типа атаки
        attack_frame = ttk.LabelFrame(parent, text="Метод взлома ключей", padding=10)
        attack_frame.pack(fill=tk.X, pady=10)
        
        self.attack_method = tk.StringVar(value="nested")
        
        methods = [
            ("Nested (классический)", "nested"),
            ("Hardnested (быстрый)", "hardnested"),
            ("Darkside (слепой)", "darkside"),
            ("Staticnested (статичный)", "staticnested"),
            ("Bruteforce (перебор)", "bruteforce")
        ]
        
        for i, (text, value) in enumerate(methods):
            ttk.Radiobutton(attack_frame, text=text, variable=self.attack_method, 
                          value=value).grid(row=i//3, column=i%3, sticky='w', padx=10, pady=5)
        
        # Параметры атаки
        param_frame = ttk.LabelFrame(parent, text="Параметры", padding=10)
        param_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(param_frame, text="UID карты:").grid(row=0, column=0, sticky='w', pady=5)
        self.mf_uid_entry = ttk.Entry(param_frame, width=20)
        self.mf_uid_entry.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(param_frame, text="Номер сектора:").grid(row=0, column=2, sticky='w', pady=5)
        self.mf_sector_spin = ttk.Spinbox(param_frame, from_=0, to=39, width=5)
        self.mf_sector_spin.grid(row=0, column=3, sticky='w', padx=10, pady=5)
        self.mf_sector_spin.set(0)
        
        ttk.Label(param_frame, text="Ключ A:").grid(row=1, column=0, sticky='w', pady=5)
        self.mf_key_a_entry = ttk.Entry(param_frame, width=20)
        self.mf_key_a_entry.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        self.mf_key_a_entry.insert(0, "FFFFFFFFFFFF")
        
        ttk.Label(param_frame, text="Ключ B:").grid(row=1, column=2, sticky='w', pady=5)
        self.mf_key_b_entry = ttk.Entry(param_frame, width=20)
        self.mf_key_b_entry.grid(row=1, column=3, sticky='w', padx=10, pady=5)
        self.mf_key_b_entry.insert(0, "FFFFFFFFFFFF")
        
        # Кнопки действий
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="🔑 Взломать ключи", 
                  command=self._crack_mifare_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📖 Читать сектор", 
                  command=self._read_mifare_sector).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Записать сектор", 
                  command=self._write_mifare_sector).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Полный дамп", 
                  command=self._dump_mifare).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📤 Восстановить из дампа", 
                  command=self._restore_mifare).pack(side=tk.LEFT, padx=5)
        
        # Таблица ключей
        keys_frame = ttk.LabelFrame(parent, text="Найденные ключи", padding=10)
        keys_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('Sector', 'Key A', 'Key B', 'Access Bits')
        self.keys_tree = ttk.Treeview(keys_frame, columns=columns, show='headings',
                                     style='Dark.Treeview', height=10)
        
        for col in columns:
            self.keys_tree.heading(col, text=col)
            self.keys_tree.column(col, width=150)
        
        keys_scroll = ttk.Scrollbar(keys_frame, orient=tk.VERTICAL,
                                   command=self.keys_tree.yview)
        self.keys_tree.configure(yscrollcommand=keys_scroll.set)
        
        keys_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.keys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_write_tab(self, parent):
        """Вкладка записи карт"""
        ttk.Label(parent, text="✏️ Запись данных на карты", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Источник данных
        source_frame = ttk.LabelFrame(parent, text="Источник данных", padding=10)
        source_frame.pack(fill=tk.X, pady=10)
        
        self.write_source = tk.StringVar(value="manual")
        
        ttk.Radiobutton(source_frame, text="Ввести вручную", variable=self.write_source,
                       value="manual", command=self._toggle_write_source).grid(row=0, column=0, padx=10)
        ttk.Radiobutton(source_frame, text="Загрузить из файла", variable=self.write_source,
                       value="file", command=self._toggle_write_source).grid(row=0, column=1, padx=10)
        ttk.Radiobutton(source_frame, text="Клонировать с карты", variable=self.write_source,
                       value="clone", command=self._toggle_write_source).grid(row=0, column=2, padx=10)
        
        # Поле для ручного ввода
        self.manual_frame = ttk.Frame(source_frame)
        self.manual_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky='w')
        
        ttk.Label(self.manual_frame, text="Hex данные:").pack(side=tk.LEFT)
        self.write_data_entry = ttk.Entry(self.manual_frame, width=50)
        self.write_data_entry.pack(side=tk.LEFT, padx=10)
        self.write_data_entry.insert(0, "00000000000000000000000000000000")
        
        # Файловый выбор
        self.file_frame = ttk.Frame(source_frame)
        
        ttk.Label(self.file_frame, text="Файл:").pack(side=tk.LEFT)
        self.write_file_entry = ttk.Entry(self.file_frame, width=40)
        self.write_file_entry.pack(side=tk.LEFT, padx=10)
        ttk.Button(self.file_frame, text="📂 Обзор", 
                  command=self._browse_write_file).pack(side=tk.LEFT)
        
        # Параметры записи
        write_params = ttk.LabelFrame(parent, text="Параметры записи", padding=10)
        write_params.pack(fill=tk.X, pady=10)
        
        ttk.Label(write_params, text="Тип карты:").grid(row=0, column=0, sticky='w', pady=5)
        self.card_type_combo = ttk.Combobox(write_params, values=[
            "Mifare Classic 1K",
            "Mifare Classic 4K", 
            "Mifare Ultralight",
            "Mifare DESFire",
            "ISO 14443-A"
        ], width=20)
        self.card_type_combo.grid(row=0, column=1, sticky='w', padx=10)
        self.card_type_combo.set("Mifare Classic 1K")
        
        ttk.Label(write_params, text="Начальный сектор:").grid(row=0, column=2, sticky='w', pady=5)
        self.write_start_sector = ttk.Spinbox(write_params, from_=0, to=39, width=5)
        self.write_start_sector.grid(row=0, column=3, sticky='w', padx=10)
        self.write_start_sector.set(0)
        
        # Кнопки
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="✏️ Записать данные", 
                  command=self._write_card_data, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🔄 Клонировать карту", 
                  command=self._clone_card, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="⚠️ Сбросить карту", 
                  command=self._wipe_card, width=20).pack(side=tk.LEFT, padx=10)
        
        # Лог операций
        log_frame = ttk.LabelFrame(parent, text="Журнал записи", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.write_log = tk.Text(log_frame, height=10, bg='#1e1e1e', fg='#4caf50',
                                font=('Consolas', 9))
        write_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.write_log.yview)
        self.write_log.configure(yscrollcommand=write_scroll.set)
        
        write_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.write_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_emulate_tab(self, parent):
        """Вкладка эмуляции"""
        ttk.Label(parent, text="🎭 Эмуляция RFID карт и тегов", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Тип эмуляции
        type_frame = ttk.LabelFrame(parent, text="Тип эмуляции", padding=10)
        type_frame.pack(fill=tk.X, pady=10)
        
        self.emu_type = tk.StringVar(value="mf_classic")
        
        types = [
            ("Mifare Classic", "mf_classic"),
            ("ISO 14443-A", "iso14443a"),
            ("ISO 14443-B", "iso14443b"),
            ("ISO 15693", "iso15693"),
            ("EM4100 (LF)", "em4100"),
            ("HID Prox (LF)", "hidprox"),
            ("Indala (LF)", "indala")
        ]
        
        for i, (text, value) in enumerate(types):
            ttk.Radiobutton(type_frame, text=text, variable=self.emu_type,
                          value=value).grid(row=i//4, column=i%4, sticky='w', padx=10, pady=5)
        
        # Параметры эмуляции
        params_frame = ttk.LabelFrame(parent, text="Параметры", padding=10)
        params_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(params_frame, text="UID:").grid(row=0, column=0, sticky='w', pady=5)
        self.emu_uid = ttk.Entry(params_frame, width=20)
        self.emu_uid.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        self.emu_uid.insert(0, "04A2B3C4")
        
        ttk.Label(params_frame, text="ATQA:").grid(row=0, column=2, sticky='w', pady=5)
        self.emu_atqa = ttk.Entry(params_frame, width=10)
        self.emu_atqa.grid(row=0, column=3, sticky='w', padx=10, pady=5)
        self.emu_atqa.insert(0, "0004")
        
        ttk.Label(params_frame, text="SAK:").grid(row=1, column=0, sticky='w', pady=5)
        self.emu_sak = ttk.Entry(params_frame, width=10)
        self.emu_sak.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        self.emu_sak.insert(0, "08")
        
        ttk.Label(params_frame, text="Данные (hex):").grid(row=1, column=2, sticky='w', pady=5)
        self.emu_data = ttk.Entry(params_frame, width=30)
        self.emu_data.grid(row=1, column=3, sticky='w', padx=10, pady=5)
        
        # Кнопки управления
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)
        
        self.btn_start_emu = ttk.Button(btn_frame, text="▶ Запустить эмуляцию",
                                       command=self._start_emulation)
        self.btn_start_emu.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop_emu = ttk.Button(btn_frame, text="⏹ Остановить",
                                      command=self._stop_emulation, state=tk.DISABLED)
        self.btn_stop_emu.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="📂 Загрузить из дампа",
                  command=self._load_emu_dump).pack(side=tk.LEFT, padx=10)
        
        # Статус эмуляции
        status_frame = ttk.LabelFrame(parent, text="Статус эмуляции", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.emu_status = tk.Text(status_frame, height=8, bg='#1e1e1e', fg='#ffffff',
                                 font=('Consolas', 9))
        emu_scroll = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.emu_status.yview)
        self.emu_status.configure(yscrollcommand=emu_scroll.set)
        
        emu_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.emu_status.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_sniff_tab(self, parent):
        """Вкладка сниффинга"""
        ttk.Label(parent, text="📡 Перехват трафика (сниффинг)", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Настройки сниффинга
        settings_frame = ttk.LabelFrame(parent, text="Настройки перехвата", padding=10)
        settings_frame.pack(fill=tk.X, pady=10)
        
        self.sniff_protocol = tk.StringVar(value="iso14443a")
        
        protocols = [
            ("ISO 14443-A", "iso14443a"),
            ("ISO 14443-B", "iso14443b"),
            ("ISO 15693", "iso15693"),
            ("Mifare Classic", "mifare"),
            ("LF EM4100", "em4100")
        ]
        
        for i, (text, value) in enumerate(protocols):
            ttk.Radiobutton(settings_frame, text=text, variable=self.sniff_protocol,
                          value=value).grid(row=i//3, column=i%3, sticky='w', padx=10, pady=5)
        
        # Дополнительные опции
        self.var_save_raw = tk.BooleanVar(value=True)
        self.var_decrypt = tk.BooleanVar(value=False)
        self.var_show_live = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(settings_frame, text="Сохранять RAW данные", 
                       variable=self.var_save_raw).grid(row=2, column=0, sticky='w', padx=10, pady=5)
        ttk.Checkbutton(settings_frame, text="Пытаться расшифровать", 
                       variable=self.var_decrypt).grid(row=2, column=1, sticky='w', padx=10, pady=5)
        ttk.Checkbutton(settings_frame, text="Показывать в реальном времени", 
                       variable=self.var_show_live).grid(row=2, column=2, sticky='w', padx=10, pady=5)
        
        # Кнопки управления
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start_sniff = ttk.Button(btn_frame, text="▶ Начать перехват",
                                         command=self._start_sniffing)
        self.btn_start_sniff.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop_sniff = ttk.Button(btn_frame, text="⏹ Остановить",
                                        command=self._stop_sniffing, state=tk.DISABLED)
        self.btn_stop_sniff.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="💾 Сохранить трассу",
                  command=self._save_sniff_trace).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="📂 Загрузить трассу",
                  command=self._load_sniff_trace).pack(side=tk.LEFT, padx=10)
        
        # Окно просмотра трафика
        traffic_frame = ttk.LabelFrame(parent, text="Перехваченный трафик", padding=10)
        traffic_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Разделяем на две панели
        paned = ttk.PanedWindow(traffic_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель - список пакетов
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        columns = ('Time', 'Type', 'Source', 'Data', 'RSSI')
        self.traffic_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                        style='Dark.Treeview', height=15)
        
        for col in columns:
            self.traffic_tree.heading(col, text=col)
            self.traffic_tree.column(col, width=100)
        
        self.traffic_tree.column('Data', width=300)
        
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=self.traffic_tree.yview)
        self.traffic_tree.configure(yscrollcommand=list_scroll.set)
        
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.traffic_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Правая панель - детали пакета
        detail_frame = ttk.LabelFrame(paned, text="Детали пакета", padding=10)
        paned.add(detail_frame, weight=1)
        
        self.packet_detail = tk.Text(detail_frame, wrap=tk.WORD, bg='#1e1e1e', fg='#ffffff',
                                    font=('Consolas', 9))
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL,
                                     command=self.packet_detail.yview)
        self.packet_detail.configure(yscrollcommand=detail_scroll.set)
        
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.packet_detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_lf_tab(self, parent):
        """Вкладка LF операций"""
        ttk.Label(parent, text="📶 Низкочастотные операции (125 kHz)", 
                 style='Header.TLabel').pack(anchor='w', pady=10)
        
        # Выбор типа LF тега
        type_frame = ttk.LabelFrame(parent, text="Тип LF тега", padding=10)
        type_frame.pack(fill=tk.X, pady=10)
        
        self.lf_type = tk.StringVar(value="em4100")
        
        lf_types = [
            ("EM4100 / EM4200", "em4100"),
            ("HID Prox", "hidprox"),
            ("Indala", "indala"),
            ("AWID", "awid"),
            ("IO Prox", "ioprox"),
            ("Viking", "viking"),
            ("T55xx (записываемый)", "t55xx"),
            ("HiTag2", "hitag2")
        ]
        
        for i, (text, value) in enumerate(lf_types):
            ttk.Radiobutton(type_frame, text=text, variable=self.lf_type,
                          value=value).grid(row=i//4, column=i%4, sticky='w', padx=10, pady=5)
        
        # Параметры для T55xx
        self.t55_frame = ttk.LabelFrame(parent, text="Параметры T55xx", padding=10)
        
        ttk.Label(self.t55_frame, text="Блок:").grid(row=0, column=0, sticky='w', pady=5)
        self.t55_block = ttk.Spinbox(self.t55_frame, from_=0, to=7, width=5)
        self.t55_block.grid(row=0, column=1, sticky='w', padx=10)
        self.t55_block.set(0)
        
        ttk.Label(self.t55_frame, text="Данные (hex):").grid(row=0, column=2, sticky='w', pady=5)
        self.t55_data = ttk.Entry(self.t55_frame, width=20)
        self.t55_data.grid(row=0, column=3, sticky='w', padx=10)
        self.t55_data.insert(0, "00000000")
        
        # Кнопки действий
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="🔍 Найти LF тег",
                  command=self._find_lf_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📖 Прочитать",
                  command=self._read_lf_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Записать (T55xx)",
                  command=self._write_lf_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🎭 Эмулировать",
                  command=self._emulate_lf_tag).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 График сигнала",
                  command=self._plot_lf_signal).pack(side=tk.LEFT, padx=5)
        
        # Результаты
        result_frame = ttk.LabelFrame(parent, text="Результаты LF сканирования", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lf_result = tk.Text(result_frame, height=15, bg='#1e1e1e', fg='#ffffff',
                                font=('Consolas', 9))
        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL,
                                     command=self.lf_result.yview)
        self.lf_result.configure(yscrollcommand=result_scroll.set)
        
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.lf_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_hex_tab(self, parent):
        """Вкладка Hex редактора"""
        from widgets.editors import HexEditor
        
        hex_editor = HexEditor(parent)
        hex_editor.pack(fill=tk.BOTH, expand=True)
        
        self.hex_editor_instance = hex_editor
    
    def _create_node_tab(self, parent):
        """Вкладка Node редактора"""
        from widgets.editors import NodeEditor
        
        node_editor = NodeEditor(parent, commands_manager=self.core.command_manager)
        node_editor.pack(fill=tk.BOTH, expand=True)
        
        self.node_editor_instance = node_editor
    
    def _create_analysis_tab(self, parent):
        """Вкладка анализа сигнала"""
        if not HAS_MATPLOTLIB:
            ttk.Label(parent, text="⚠️ Matplotlib не установлен. Графики недоступны.",
                     style='Warning.TLabel').pack(pady=20)
            ttk.Label(parent, text="Установите: pip install matplotlib numpy",
                     style='Dark.TLabel').pack()
            return
        
        # Панель управления
        control_frame = ttk.LabelFrame(parent, text="Источники данных", padding=10)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(control_frame, text="Источник:").grid(row=0, column=0, sticky='w', pady=5)
        self.plot_source = ttk.Combobox(control_frame, values=[
            "Текущая трасса",
            "Из файла",
            "Сниффинг",
            "Demo данные"
        ], width=20)
        self.plot_source.grid(row=0, column=1, sticky='w', padx=10)
        self.plot_source.set("Demo данные")
        
        ttk.Label(control_frame, text="Тип графика:").grid(row=0, column=2, sticky='w', pady=5)
        self.plot_type = ttk.Combobox(control_frame, values=[
            "Временной сигнал",
            "FFT спектр",
            "Waterfall",
            "IQ диаграмма"
        ], width=15)
        self.plot_type.grid(row=0, column=3, sticky='w', padx=10)
        self.plot_type.set("Временной сигнал")
        
        ttk.Button(control_frame, text="📊 Построить график",
                  command=self._build_plot).grid(row=0, column=4, padx=20)
        
        # Область графика
        plot_frame = ttk.Frame(parent)
        plot_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Создаем фигуру matplotlib
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor='#1e1e1e')
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Панель инструментов
        toolbar = NavigationToolbar2Tk(self.canvas, plot_frame)
        toolbar.update()
        
        # Демо данные
        self._generate_demo_plot()
    
    def _create_commands_tab(self, parent):
        """Вкладка всех команд"""
        # Поиск команд
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(search_frame, text="🔍 Поиск команды:").pack(side=tk.LEFT, padx=5)
        
        self.cmd_search_entry = ttk.Entry(search_frame, width=40)
        self.cmd_search_entry.pack(side=tk.LEFT, padx=5)
        self.cmd_search_entry.bind('<KeyRelease>', self._filter_commands)
        
        ttk.Label(search_frame, text="Категория:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.cmd_category = ttk.Combobox(search_frame, values=["Все"] + 
                                        self.core.command_manager.get_all_categories(),
                                        width=20)
        self.cmd_category.pack(side=tk.LEFT, padx=5)
        self.cmd_category.set("Все")
        self.cmd_category.bind('<<ComboboxSelected>>', self._filter_commands)
        
        # Таблица команд
        table_frame = ttk.LabelFrame(parent, text="Доступные команды", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('ID', 'Name', 'Category', 'Risk', 'Description')
        self.cmd_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                    style='Dark.Treeview', height=20)
        
        for col in columns:
            self.cmd_tree.heading(col, text=col)
            self.cmd_tree.column(col, width=150)
        
        self.cmd_tree.column('Description', width=400)
        
        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                                   command=self.cmd_tree.yview)
        self.cmd_tree.configure(yscrollcommand=tree_scroll.set)
        
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cmd_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Заполняем таблицу
        self._populate_commands_table()
        
        # Детали команды
        detail_frame = ttk.LabelFrame(parent, text="Детали команды", padding=10)
        detail_frame.pack(fill=tk.X, pady=10)
        
        self.cmd_detail = tk.Text(detail_frame, height=6, bg='#1e1e1e', fg='#ffffff',
                                 font=('Consolas', 9))
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL,
                                     command=self.cmd_detail.yview)
        self.cmd_detail.configure(yscrollcommand=detail_scroll.set)
        
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cmd_detail.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Привязка выбора
        self.cmd_tree.bind('<<TreeviewSelect>>', self._on_command_selected)
        
        # Кнопка выполнения
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="▶ Выполнить команду",
                  command=self._execute_selected_command).pack(side=tk.LEFT, padx=10)
    
    def _create_device_tab(self, parent):
        """Вкладка информации об устройстве"""
        # Информация об устройстве
        info_frame = ttk.LabelFrame(parent, text="Информация об устройстве", padding=15)
        info_frame.pack(fill=tk.X, pady=10)
        
        self.device_info_labels = {}
        
        labels = [
            ("Статус:", "device_status"),
            ("Порт:", "device_port"),
            ("Прошивка:", "device_firmware"),
            ("Hardware:", "device_hardware"),
            ("Serial:", "device_serial"),
            ("Чип:", "device_chip")
        ]
        
        for i, (text, key) in enumerate(labels):
            ttk.Label(info_frame, text=text, style='Dark.TLabel').grid(row=i, column=0, sticky='w', pady=5)
            label = ttk.Label(info_frame, text="Неизвестно", style='Dark.TLabel')
            label.grid(row=i, column=1, sticky='w', padx=20, pady=5)
            self.device_info_labels[key] = label
        
        # Кнопки управления устройством
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="🔄 Обновить информацию",
                  command=self._refresh_device_info).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="⚙️ Настройки устройства",
                  command=self._device_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="🔧 Тест антенны",
                  command=self._antenna_test).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="💾 Сохранить конфиг",
                  command=self._save_device_config).pack(side=tk.LEFT, padx=10)
        
        # Статистика операций
        stats_frame = ttk.LabelFrame(parent, text="Статистика операций", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('Operation', 'Count', 'Success', 'Failed', 'Last Time')
        self.stats_tree = ttk.Treeview(stats_frame, columns=columns, show='headings',
                                      style='Dark.Treeview', height=10)
        
        for col in columns:
            self.stats_tree.heading(col, text=col)
            self.stats_tree.column(col, width=150)
        
        stats_scroll = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL,
                                    command=self.stats_tree.yview)
        self.stats_tree.configure(yscrollcommand=stats_scroll.set)
        
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self):
        """Создание строки состояния"""
        self.status_bar = ttk.Label(self.root, text="Готов", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _bind_events(self):
        """Привязка событий"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind('<Control-o>', lambda e: self._open_dump())
        self.root.bind('<Control-s>', lambda e: self._save_dump())
    
    # ========================================================================
    # Методы работы с устройством
    # ========================================================================
    
    def _scan_ports(self):
        """Сканирование доступных портов"""
        ports = self.core.scan_ports()
        
        if not ports:
            messagebox.showinfo("Порты", "COM порты не найдены")
            return
        
        port_list = "\n".join([f"{p['device']} - {p['description']}" for p in ports])
        messagebox.showinfo("Найденные порты", port_list)
    
    def _connect_device(self):
        """Подключение к устройству"""
        ports = self.core.scan_ports()
        
        if not ports:
            messagebox.showerror("Ошибка", "COM порты не найдены")
            return
        
        # Диалог выбора порта
        dialog = tk.Toplevel(self.root)
        dialog.title("Выберите порт")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Доступные порты:").pack(pady=10)
        
        port_var = tk.StringVar(value=ports[0]['device'] if ports else "")
        
        for port in ports:
            ttk.Radiobutton(dialog, text=f"{port['device']} - {port['description']}",
                          variable=port_var, value=port['device']).pack(anchor='w', padx=20)
        
        def connect():
            selected_port = port_var.get()
            if selected_port:
                success = self.core.connect_device(selected_port)
                if success:
                    self.device_connected = True
                    self.device_label.config(text="🟢 Устройство подключено", 
                                           style='Success.TLabel')
                    self.btn_connect.config(state=tk.DISABLED)
                    self.btn_disconnect.config(state=tk.NORMAL)
                    self.port_label.config(text=f"Порт: {selected_port}")
                    self._log_message(f"Подключено к {selected_port}", LogLevel.INFO)
                    self._refresh_device_info()
                else:
                    messagebox.showerror("Ошибка", "Не удалось подключиться к устройству")
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Подключить", command=connect).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        dialog.wait_window()
    
    def _disconnect_device(self):
        """Отключение от устройства"""
        self.core.disconnect_device()
        self.device_connected = False
        self.device_label.config(text="🔴 Устройство не подключено", style='Warning.TLabel')
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.port_label.config(text="")
        self._log_message("Устройство отключено", LogLevel.INFO)
    
    def _refresh_device_info(self):
        """Обновление информации об устройстве"""
        if not self.device_connected:
            return
        
        dev_info = self.core.communication.device_info
        
        self.device_info_labels['device_status'].config(text="Подключено")
        self.device_info_labels['device_port'].config(text=dev_info.port or "N/A")
        self.device_info_labels['device_firmware'].config(text=dev_info.firmware_version or "N/A")
        self.device_info_labels['device_hardware'].config(text=dev_info.hardware_version or "N/A")
        self.device_info_labels['device_serial'].config(text=dev_info.serial_number or "N/A")
        self.device_info_labels['device_chip'].config(text=dev_info.chip_info or "N/A")
    
    # ========================================================================
    # Методы логирования
    # ========================================================================
    
    def _log_message(self, message: str, level: LogLevel = LogLevel.INFO):
        """Добавление сообщения в лог"""
        timestamp = f"[{level.value.upper()}]"
        self.log_text.insert(tk.END, f"{timestamp} {message}\n", level.value)
        self.log_text.see(tk.END)
    
    def _on_log_entry(self, entry):
        """Callback для новых записей лога"""
        self.log_entries.append(entry)
        self._log_message(f"{entry.source}: {entry.message}", entry.level)
    
    def _on_progress_update(self, percent: int, message: str):
        """Callback обновления прогресса"""
        self.status_bar.config(text=f"{message} ({percent}%)")
    
    def _clear_logs(self):
        """Очистка логов"""
        self.log_text.delete(1.0, tk.END)
        self.log_entries.clear()
    
    def _save_logs(self):
        """Сохранение логов"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self.log_entries:
                    f.write(f"[{entry.timestamp}] [{entry.level.value}] {entry.source}: {entry.message}\n")
            
            messagebox.showinfo("Успешно", f"Логи сохранены в {filepath}")
    
    def _export_logs(self):
        """Экспорт логов в JSON"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            import json
            data = [
                {
                    'timestamp': e.timestamp,
                    'level': e.level.value,
                    'message': e.message,
                    'source': e.source
                }
                for e in self.log_entries
            ]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Успешно", f"Логи экспортированы в {filepath}")
    
    # ========================================================================
    # Методы-заглушки для вкладок (будут реализованы полностью)
    # ========================================================================
    
    def _start_search(self):
        self._log_message("Запуск поиска тегов...", LogLevel.INFO)
        # TODO: Реализовать поиск
    
    def _stop_search(self):
        self._log_message("Поиск остановлен", LogLevel.INFO)
    
    def _copy_uid(self):
        self._log_message("UID скопирован в буфер", LogLevel.INFO)
    
    def _save_tag_dump(self):
        self._log_message("Сохранение дампа тега", LogLevel.INFO)
    
    def _get_tag_keys(self):
        self._log_message("Получение ключей тега", LogLevel.INFO)
    
    def _show_tag_details(self):
        self._log_message("Показ деталей тега", LogLevel.INFO)
    
    def _crack_mifare_keys(self):
        self._log_message("Взлом ключей Mifare", LogLevel.INFO)
    
    def _read_mifare_sector(self):
        self._log_message("Чтение сектора Mifare", LogLevel.INFO)
    
    def _write_mifare_sector(self):
        self._log_message("Запись сектора Mifare", LogLevel.INFO)
    
    def _dump_mifare(self):
        self._log_message("Полный дамп Mifare", LogLevel.INFO)
    
    def _restore_mifare(self):
        self._log_message("Восстановление Mifare из дампа", LogLevel.INFO)
    
    def _toggle_write_source(self):
        source = self.write_source.get()
        self.manual_frame.grid_forget()
        self.file_frame.grid_forget()
        
        if source == "manual":
            self.manual_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky='w')
        elif source == "file":
            self.file_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky='w')
    
    def _browse_write_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.write_file_entry.delete(0, tk.END)
            self.write_file_entry.insert(0, filepath)
    
    def _write_card_data(self):
        self._log_message("Запись данных на карту", LogLevel.INFO)
    
    def _clone_card(self):
        self._log_message("Клонирование карты", LogLevel.INFO)
    
    def _wipe_card(self):
        self._log_message("Сброс карты", LogLevel.INFO)
    
    def _start_emulation(self):
        self._log_message("Запуск эмуляции", LogLevel.INFO)
        self.btn_start_emu.config(state=tk.DISABLED)
        self.btn_stop_emu.config(state=tk.NORMAL)
    
    def _stop_emulation(self):
        self._log_message("Остановка эмуляции", LogLevel.INFO)
        self.btn_start_emu.config(state=tk.NORMAL)
        self.btn_stop_emu.config(state=tk.DISABLED)
    
    def _load_emu_dump(self):
        self._log_message("Загрузка дампа для эмуляции", LogLevel.INFO)
    
    def _start_sniffing(self):
        self._log_message("Запуск сниффинга", LogLevel.INFO)
        self.btn_start_sniff.config(state=tk.DISABLED)
        self.btn_stop_sniff.config(state=tk.NORMAL)
    
    def _stop_sniffing(self):
        self._log_message("Остановка сниффинга", LogLevel.INFO)
        self.btn_start_sniff.config(state=tk.NORMAL)
        self.btn_stop_sniff.config(state=tk.DISABLED)
    
    def _save_sniff_trace(self):
        self._log_message("Сохранение трассы сниффинга", LogLevel.INFO)
    
    def _load_sniff_trace(self):
        self._log_message("Загрузка трассы сниффинга", LogLevel.INFO)
    
    def _find_lf_tag(self):
        self._log_message("Поиск LF тега", LogLevel.INFO)
    
    def _read_lf_tag(self):
        self._log_message("Чтение LF тега", LogLevel.INFO)
    
    def _write_lf_tag(self):
        self._log_message("Запись LF тега", LogLevel.INFO)
    
    def _emulate_lf_tag(self):
        self._log_message("Эмуляция LF тега", LogLevel.INFO)
    
    def _plot_lf_signal(self):
        self._log_message("Построение графика LF сигнала", LogLevel.INFO)
    
    def _build_plot(self):
        self._log_message("Построение графика", LogLevel.INFO)
        self._generate_demo_plot()
    
    def _generate_demo_plot(self):
        """Генерация демо графика"""
        if not HAS_MATPLOTLIB:
            return
        
        import numpy as np
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#2d2d2d')
        
        # Генерируем демо данные
        x = np.linspace(0, 10, 1000)
        y = np.sin(x) * np.exp(-x/5) + np.random.normal(0, 0.1, 1000)
        
        ax.plot(x, y, '#0078d4', linewidth=1)
        ax.set_xlabel('Время (ms)', color='white')
        ax.set_ylabel('Амплитуда', color='white')
        ax.set_title('Демо сигнал ASK модуляции', color='white', fontsize=12)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#808080')
        
        self.canvas.draw()
    
    def _filter_commands(self, event=None):
        """Фильтрация команд"""
        search_text = self.cmd_search_entry.get().lower()
        category = self.cmd_category.get()
        
        # Очищаем таблицу
        for item in self.cmd_tree.get_children():
            self.cmd_tree.delete(item)
        
        # Фильтруем команды
        count = 0
        for cmd_id, cmd in self.core.command_manager.commands.items():
            # Фильтр по категории
            if category != "Все" and cmd.category != category:
                continue
            
            # Фильтр по поиску
            if search_text and search_text not in cmd.name.lower() and \
               search_text not in cmd.description.lower() and \
               search_text not in cmd_id.lower():
                continue
            
            risk_colors = {
                RiskLevel.SAFE: '#4caf50',
                RiskLevel.MEDIUM: '#ff9800',
                RiskLevel.HIGH: '#f44336',
                RiskLevel.DANGEROUS: '#9c27b0'
            }
            
            self.cmd_tree.insert('', tk.END, values=(
                cmd_id,
                cmd.name,
                cmd.category,
                cmd.risk_level.value,
                cmd.description[:80] + "..." if len(cmd.description) > 80 else cmd.description
            ), tags=(cmd.risk_level.value,))
            
            count += 1
        
        self.cmd_tree.tag_configure(RiskLevel.SAFE.value, foreground='#4caf50')
        self.cmd_tree.tag_configure(RiskLevel.MEDIUM.value, foreground='#ff9800')
        self.cmd_tree.tag_configure(RiskLevel.HIGH.value, foreground='#f44336')
        self.cmd_tree.tag_configure(RiskLevel.DANGEROUS.value, foreground='#9c27b0')
    
    def _populate_commands_table(self):
        """Заполнение таблицы команд"""
        self._filter_commands()
    
    def _on_command_selected(self, event):
        """Выбор команды в таблице"""
        selection = self.cmd_tree.selection()
        if not selection:
            return
        
        item = self.cmd_tree.item(selection[0])
        cmd_id = item['values'][0]
        
        cmd = self.core.command_manager.get_command(cmd_id)
        if cmd:
            detail_text = f"""Команда: {cmd.name}
ID: {cmd_id}
Категория: {cmd.category}
Уровень риска: {cmd.risk_level.value}
Таймаут: {cmd.timeout} мс

Описание:
{cmd.description}

Шаблон: {cmd.template}

Примеры:
{chr(10).join(cmd.examples)}

Советы:
{chr(10).join(cmd.tips)}
"""
            self.cmd_detail.delete(1.0, tk.END)
            self.cmd_detail.insert(tk.END, detail_text)
    
    def _execute_selected_command(self):
        """Выполнение выбранной команды"""
        selection = self.cmd_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите команду")
            return
        
        item = self.cmd_tree.item(selection[0])
        cmd_id = item['values'][0]
        
        if not self.device_connected:
            messagebox.showerror("Ошибка", "Устройство не подключено")
            return
        
        self._log_message(f"Выполнение команды {cmd_id}...", LogLevel.INFO)
        success, response = self.core.execute_command(cmd_id)
        
        if success:
            self._log_message(f"Команда выполнена успешно ({len(response)} строк)", LogLevel.INFO)
        else:
            self._log_message(f"Ошибка выполнения: {response}", LogLevel.ERROR)
    
    def _open_hex_editor(self):
        """Открытие Hex редактора"""
        self.notebook.select(6)  # Переключаем на вкладку Hex редактора
    
    def _open_node_editor(self):
        """Открытие Node редактора"""
        self.notebook.select(7)  # Переключаем на вкладку Node редактора
    
    def _open_signal_analyzer(self):
        """Открытие анализатора сигнала"""
        self.notebook.select(8)  # Переключаем на вкладку Анализа
    
    def _open_settings(self):
        """Открытие настроек"""
        messagebox.showinfo("Настройки", "Окно настроек в разработке")
    
    def _open_docs(self):
        """Открытие документации"""
        messagebox.showinfo("Документация", "Документация в разработке")
    
    def _show_about(self):
        """О программе"""
        about_text = """ProxMaster Pro v3.0

Профессиональный инструмент управления Proxmark3

© 2024 ProxMaster Pro Team
License: GPL-3.0

Разработано для сообщества Proxmark3 Iceman RRG

Версия прошивки: Iceman 4.16000+
Всего команд: 857
Категорий: 18

GitHub: github.com/ProxMaster-Pro
"""
        messagebox.showinfo("О программе", about_text)
    
    def _show_device_info(self):
        """Показать информацию об устройстве"""
        self._refresh_device_info()
        self.notebook.select(10)  # Переключаем на вкладку Устройства
    
    def _open_dump(self):
        """Открыть дамп"""
        filepath = filedialog.askopenfilename(
            title="Открыть дамп",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if filepath and hasattr(self, 'hex_editor_instance'):
            self.hex_editor_instance.load_file(filepath)
            self.notebook.select(6)
    
    def _save_dump(self):
        """Сохранить дамп"""
        if hasattr(self, 'hex_editor_instance'):
            self.hex_editor_instance.save_file()
    
    def _load_saved_state(self):
        """Загрузка сохраненного состояния"""
        # TODO: Загрузить последние настройки
        pass
    
    def _on_close(self):
        """Закрытие приложения"""
        if self.device_connected:
            if messagebox.askyesno("Подтверждение", "Устройство подключено. Отключиться и выйти?"):
                self.core.disconnect_device()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Точка входа"""
    print("=" * 60)
    print("  ProxMaster Pro v3.0 - Профессиональный инструмент Proxmark3")
    print("=" * 60)
    print()
    
    app = ProxMasterApp()
    app.run()


if __name__ == "__main__":
    main()
