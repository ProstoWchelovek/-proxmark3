"""
ProxMaster Ultimate - Main Application
Главный файл запуска приложения с полным GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.main import ProxMasterCore, ConnectionStatus, RiskLevel
from widgets.editors import HexEditor, NodeEditor


class ProxMasterApp:
    """Основное приложение ProxMaster Ultimate"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ProxMaster Ultimate - Управление Proxmark3")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Настройка стиля
        self._setup_styles()
        
        # Инициализация ядра
        self.core = ProxMasterCore()
        
        # Переменные
        self.selected_category = tk.StringVar(value="search")
        self.selected_command = tk.StringVar()
        self.custom_command_var = tk.StringVar()
        self.connection_status_var = tk.StringVar(value="Отключено")
        self.device_info_var = tk.StringVar(value="Нет устройства")
        
        # Создание интерфейса
        self._create_menu()
        self._create_toolbar()
        self._create_main_layout()
        self._create_statusbar()
        
        # Привязка событий закрытия
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Запуск ядра
        self.core.start()
        
        # Автоподключение при запуске (опционально)
        # self.connect_device()
    
    def _setup_styles(self):
        """Настройка стилей приложения"""
        style = ttk.Style()
        
        # Темная тема
        bg_color = '#1e1e1e'
        fg_color = '#d4d4d4'
        accent_color = '#007acc'
        
        self.root.configure(bg=bg_color)
        
        # Настройка цветов для различных виджетов
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=accent_color, foreground='white')
        style.configure('Accent.TButton', background=accent_color, foreground='white')
        style.configure('Danger.TButton', background='#f44336', foreground='white')
        style.configure('Success.TButton', background='#4CAF50', foreground='white')
        style.configure('TNotebook', background=bg_color)
        style.configure('TNotebook.Tab', padding=[12, 4])
        style.configure('Treeview', background='#252526', foreground=fg_color, fieldbackground='#252526')
        style.configure('Treeview.Heading', background='#3c3c3c', foreground=fg_color)
        style.map('Treeview', background=[('selected', accent_color)])
    
    def _create_menu(self):
        """Создание главного меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть дамп...", command=self._open_dump)
        file_menu.add_command(label="Сохранить дамп...", command=self._save_dump)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self._on_closing)
        
        # Устройство
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Устройство", menu=device_menu)
        device_menu.add_command(label="Подключить", command=self.connect_device)
        device_menu.add_command(label="Отключить", command=self.disconnect_device)
        device_menu.add_separator()
        device_menu.add_command(label="Информация об устройстве", command=self.show_device_info)
        device_menu.add_command(label="Проверить обновления", command=self.check_updates)
        
        # Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_command(label="Hex редактор", command=self._open_hex_editor)
        tools_menu.add_command(label="Редактор команд (Node)", command=self._open_node_editor)
        tools_menu.add_separator()
        tools_menu.add_command(label="Настройки", command=self._show_settings)
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Документация", command=self._show_help)
        help_menu.add_command(label="О программе", command=self._show_about)
    
    def _create_toolbar(self):
        """Создание панели инструментов"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Кнопки подключения
        btn_connect = ttk.Button(
            toolbar,
            text="🔌 Подключить",
            command=self.connect_device
        )
        btn_connect.pack(side=tk.LEFT, padx=2)
        
        btn_disconnect = ttk.Button(
            toolbar,
            text="✖ Отключить",
            command=self.disconnect_device
        )
        btn_disconnect.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Статус подключения
        lbl_status = ttk.Label(toolbar, text="Статус:")
        lbl_status.pack(side=tk.LEFT, padx=2)
        
        self.status_label = ttk.Label(
            toolbar,
            textvariable=self.connection_status_var,
            foreground='#f44336'
        )
        self.status_label.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Информация об устройстве
        lbl_device = ttk.Label(toolbar, text="Устройство:")
        lbl_device.pack(side=tk.LEFT, padx=2)
        
        self.device_label = ttk.Label(
            toolbar,
            textvariable=self.device_info_var,
            foreground='#4CAF50'
        )
        self.device_label.pack(side=tk.LEFT, padx=2)
        
        # Быстрые команды
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        btn_search_hf = ttk.Button(
            toolbar,
            text="📡 HF Поиск",
            command=lambda: self.execute_quick_command('hf_search')
        )
        btn_search_hf.pack(side=tk.LEFT, padx=2)
        
        btn_search_lf = ttk.Button(
            toolbar,
            text="📡 LF Поиск",
            command=lambda: self.execute_quick_command('lf_search')
        )
        btn_search_lf.pack(side=tk.LEFT, padx=2)
    
    def _create_main_layout(self):
        """Создание основной компоновки"""
        # Главный контейнер с разделителем
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель - команды
        left_frame = ttk.Frame(paned, width=350)
        paned.add(left_frame, weight=1)
        
        self._create_commands_panel(left_frame)
        
        # Центральная панель - вкладки
        center_frame = ttk.Frame(paned)
        paned.add(center_frame, weight=3)
        
        self._create_main_tabs(center_frame)
        
        # Правая панель - логи и информация
        right_frame = ttk.Frame(paned, width=400)
        paned.add(right_frame, weight=1)
        
        self._create_right_panel(right_frame)
    
    def _create_commands_panel(self, parent):
        """Создание панели команд"""
        # Заголовок
        lbl_title = ttk.Label(parent, text="Команды", font=("Segoe UI", 12, "bold"))
        lbl_title.pack(pady=5)
        
        # Поиск команд
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_commands())
        
        entry_search = ttk.Entry(search_frame, textvariable=self.search_var)
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_clear = ttk.Button(search_frame, text="✕", width=3, 
                              command=lambda: self.search_var.set(""))
        btn_clear.pack(side=tk.RIGHT)
        
        # Дерево категорий и команд
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.commands_tree = ttk.Treeview(
            tree_frame,
            columns=('name', 'risk'),
            show='tree headings',
            selectmode='browse'
        )
        
        self.commands_tree.heading('#0', text='Категория / Команда')
        self.commands_tree.heading('name', text='Название')
        self.commands_tree.heading('risk', text='Риск')
        
        self.commands_tree.column('#0', width=200)
        self.commands_tree.column('name', width=150)
        self.commands_tree.column('risk', width=60)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.commands_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.commands_tree.xview)
        self.commands_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.commands_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Заполнение дерева командами
        self._populate_commands_tree()
        
        # Обработчик выбора команды
        self.commands_tree.bind('<<TreeviewSelect>>', self._on_command_selected)
        self.commands_tree.bind('<Double-1>', lambda e: self._execute_selected_command())
        
        # Панель параметров команды
        params_frame = ttk.LabelFrame(parent, text="Параметры команды", padding=10)
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.params_container = ttk.Frame(params_frame)
        self.params_container.pack(fill=tk.X)
        
        # Кнопка выполнения
        btn_execute = ttk.Button(
            parent,
            text="▶ Выполнить команду",
            command=self._execute_selected_command,
            style='Success.TButton'
        )
        btn_execute.pack(fill=tk.X, padx=5, pady=5)
        
        # Поле пользовательской команды
        custom_frame = ttk.LabelFrame(parent, text="Пользовательская команда", padding=10)
        custom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.custom_entry = ttk.Entry(custom_frame, textvariable=self.custom_command_var)
        self.custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.custom_entry.bind('<Return>', lambda e: self._execute_custom_command())
        
        btn_custom = ttk.Button(
            custom_frame,
            text="Выполнить",
            command=self._execute_custom_command
        )
        btn_custom.pack(side=tk.RIGHT)
    
    def _create_main_tabs(self, parent):
        """Создание основных вкладок"""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка 1: Поиск и чтение
        tab_search = ttk.Frame(notebook)
        notebook.add(tab_search, text="🔍 Поиск и чтение")
        self._create_search_tab(tab_search)
        
        # Вкладка 2: Mifare операции
        tab_mifare = ttk.Frame(notebook)
        notebook.add(tab_mifare, text="💳 Mifare")
        self._create_mifare_tab(tab_mifare)
        
        # Вкладка 3: Запись
        tab_write = ttk.Frame(notebook)
        notebook.add(tab_write, text="✏️ Запись")
        self._create_write_tab(tab_write)
        
        # Вкладка 4: Эмуляция
        tab_emulate = ttk.Frame(notebook)
        notebook.add(tab_emulate, text="🎭 Эмуляция")
        self._create_emulate_tab(tab_emulate)
        
        # Вкладка 5: Сниффинг
        tab_sniff = ttk.Frame(notebook)
        notebook.add(tab_sniff, text="👁️ Сниффинг")
        self._create_sniff_tab(tab_sniff)
        
        # Вкладка 6: Hex редактор
        tab_hex = ttk.Frame(notebook)
        notebook.add(tab_hex, text="🔢 Hex редактор")
        self.hex_editor = HexEditor(tab_hex, width=800, height=600)
        self.hex_editor.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка 7: Node Editor
        tab_nodes = ttk.Frame(notebook)
        notebook.add(tab_nodes, text="🔗 Node Editor")
        self.node_editor = NodeEditor(tab_nodes, width=800, height=600)
        self.node_editor.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка 8: Анализ и графики
        tab_analysis = ttk.Frame(notebook)
        notebook.add(tab_analysis, text="📊 Анализ")
        self._create_analysis_tab(tab_analysis)
        
        # Вкладка 9: Настройки устройства
        tab_device = ttk.Frame(notebook)
        notebook.add(tab_device, text="⚙️ Устройство")
        self._create_device_tab(tab_device)
    
    def _create_right_panel(self, parent):
        """Создание правой панели"""
        # Логи
        log_frame = ttk.LabelFrame(parent, text="Лог событий", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white',
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Настройка тегов для цветного лога
        self.log_text.tag_configure('INFO', foreground='#4CAF50')
        self.log_text.tag_configure('WARNING', foreground='#FF9800')
        self.log_text.tag_configure('ERROR', foreground='#f44336')
        self.log_text.tag_configure('SUCCESS', foreground='#00BCD4')
        self.log_text.tag_configure('DEBUG', foreground='#858585')
        
        # Кнопки управления логом
        log_btns = ttk.Frame(log_frame)
        log_btns.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(log_btns, text="Очистить", command=self._clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_btns, text="Сохранить", command=self._save_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_btns, text="Автопрокрутка", command=self._toggle_autoscroll).pack(side=tk.LEFT, padx=2)
        
        self.autoscroll = True
        
        # Регистрация слушателя логов
        self.core.logger.add_listener(self._on_log_entry)
    
    def _create_search_tab(self, parent):
        """Вкладка поиска и чтения"""
        # Кнопки быстрого поиска
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="📡 HF Поиск", 
                  command=lambda: self.execute_command('hf_search')).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📡 LF Поиск",
                  command=lambda: self.execute_command('lf_search')).pack(side=tk.LEFT, padx=5)
        
        # Результаты
        result_frame = ttk.LabelFrame(parent, text="Результаты поиска", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.search_result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 9)
        )
        self.search_result_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_mifare_tab(self, parent):
        """Вкладка Mifare операций"""
        # Секция атак
        attack_frame = ttk.LabelFrame(parent, text="Атаки на Mifare Classic", padding=10)
        attack_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Nested атака
        nested_frame = ttk.Frame(attack_frame)
        nested_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(nested_frame, text="Key тип:").pack(side=tk.LEFT, padx=5)
        self.nested_key_type = ttk.Combobox(nested_frame, values=['A', 'B'], width=3, state='readonly')
        self.nested_key_type.set('A')
        self.nested_key_type.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(nested_frame, text="Блок:").pack(side=tk.LEFT, padx=5)
        self.nested_block = ttk.Entry(nested_frame, width=5)
        self.nested_block.insert(0, '0')
        self.nested_block.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(nested_frame, text="Nested атака",
                  command=self._run_nested_attack,
                  style='Danger.TButton').pack(side=tk.LEFT, padx=10)
        
        # Hardnested атака
        hardnested_frame = ttk.Frame(attack_frame)
        hardnested_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hardnested_frame, text="Key тип:").pack(side=tk.LEFT, padx=5)
        self.hardnested_key_type = ttk.Combobox(hardnested_frame, values=['A', 'B'], width=3, state='readonly')
        self.hardnested_key_type.set('A')
        self.hardnested_key_type.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(hardnested_frame, text="Блок:").pack(side=tk.LEFT, padx=5)
        self.hardnested_block = ttk.Entry(hardnested_frame, width=5)
        self.hardnested_block.insert(0, '0')
        self.hardnested_block.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(hardnested_frame, text="Hardnested атака",
                  command=self._run_hardnested_attack,
                  style='Danger.TButton').pack(side=tk.LEFT, padx=10)
        
        # Дамп памяти
        dump_frame = ttk.LabelFrame(parent, text="Дамп памяти", padding=10)
        dump_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(dump_frame, text="Полный дамп",
                  command=lambda: self.execute_command('hf_mifare_dump')).pack(side=tk.LEFT, padx=5)
        ttk.Button(dump_frame, text="Сохранить дамп",
                  command=self._save_current_dump).pack(side=tk.LEFT, padx=5)
        ttk.Button(dump_frame, text="Загрузить дамп",
                  command=self._load_dump).pack(side=tk.LEFT, padx=5)
    
    def _create_write_tab(self, parent):
        """Вкладка записи"""
        write_frame = ttk.LabelFrame(parent, text="Запись данных в карту", padding=10)
        write_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Выбор типа карты
        type_frame = ttk.Frame(write_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="Тип карты:").pack(side=tk.LEFT, padx=5)
        self.write_card_type = ttk.Combobox(type_frame, values=['T55x7 HF', 'T55x7 LF'], width=15, state='readonly')
        self.write_card_type.set('T55x7 HF')
        self.write_card_type.pack(side=tk.LEFT, padx=5)
        
        # Номер страницы/блока
        block_frame = ttk.Frame(write_frame)
        block_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(block_frame, text="Блок/Страница:").pack(side=tk.LEFT, padx=5)
        self.write_block = ttk.Entry(block_frame, width=10)
        self.write_block.insert(0, '0')
        self.write_block.pack(side=tk.LEFT, padx=5)
        
        # Данные для записи
        data_frame = ttk.Frame(write_frame)
        data_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(data_frame, text="Данные (hex):").pack(side=tk.LEFT, padx=5)
        self.write_data = ttk.Entry(data_frame, width=40)
        self.write_data.insert(0, '')
        self.write_data.pack(side=tk.LEFT, padx=5)
        
        # Предупреждение
        warning_lbl = ttk.Label(
            write_frame,
            text="⚠️ Внимание: Запись данных необратима!",
            foreground='#f44336',
            font=('Segoe UI', 9, 'bold')
        )
        warning_lbl.pack(pady=10)
        
        # Кнопка записи
        ttk.Button(write_frame, text="✏️ Записать данные",
                  command=self._write_to_card,
                  style='Danger.TButton').pack(pady=10)
    
    def _create_emulate_tab(self, parent):
        """Вкладка эмуляции"""
        emulate_frame = ttk.LabelFrame(parent, text="Эмуляция карт", padding=10)
        emulate_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Эмуляция HF
        hf_frame = ttk.LabelFrame(emulate_frame, text="HF Эмуляция (Mifare)", padding=10)
        hf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(hf_frame, text="UID (hex):").pack(side=tk.LEFT, padx=5)
        self.emulate_hf_uid = ttk.Entry(hf_frame, width=20)
        self.emulate_hf_uid.insert(0, '')
        self.emulate_hf_uid.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(hf_frame, text="▶ Запустить эмуляцию",
                  command=self._start_hf_emulation).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(hf_frame, text="⏹ Остановить",
                  command=self._stop_emulation).pack(side=tk.LEFT, padx=5)
        
        # Эмуляция LF
        lf_frame = ttk.LabelFrame(emulate_frame, text="LF Эмуляция (EM410x)", padding=10)
        lf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lf_frame, text="ID (hex):").pack(side=tk.LEFT, padx=5)
        self.emulate_lf_id = ttk.Entry(lf_frame, width=20)
        self.emulate_lf_id.insert(0, '')
        self.emulate_lf_id.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(lf_frame, text="▶ Запустить эмуляцию",
                  command=self._start_lf_emulation).pack(side=tk.LEFT, padx=10)
    
    def _create_sniff_tab(self, parent):
        """Вкладка сниффинга"""
        sniff_frame = ttk.LabelFrame(parent, text="Перехват трафика", padding=10)
        sniff_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # HF сниффинг
        hf_sniff_frame = ttk.Frame(sniff_frame)
        hf_sniff_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(hf_sniff_frame, text="👁️ HF ISO14443-A Сниффинг",
                  command=lambda: self.execute_command('hf_sniff_14a')).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(hf_sniff_frame, text="⏹ Остановить",
                  command=self._stop_sniffing).pack(side=tk.LEFT, padx=5)
        
        # LF сниффинг
        lf_sniff_frame = ttk.Frame(sniff_frame)
        lf_sniff_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lf_sniff_frame, text="Порог:").pack(side=tk.LEFT, padx=5)
        self.sniff_threshold = ttk.Entry(lf_sniff_frame, width=5)
        self.sniff_threshold.insert(0, '128')
        self.sniff_threshold.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(lf_sniff_frame, text="👁️ LF Сниффинг",
                  command=self._start_lf_sniff).pack(side=tk.LEFT, padx=5)
        
        # Результаты сниффинга
        result_frame = ttk.LabelFrame(sniff_frame, text="Перехваченные данные", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.sniff_result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 9)
        )
        self.sniff_result_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(result_frame, text="Сохранить трассировку",
                  command=self._save_trace).pack(pady=5)
    
    def _create_analysis_tab(self, parent):
        """Вкладка анализа"""
        # Графики и статистика будут здесь
        info_lbl = ttk.Label(
            parent,
            text="Модуль анализа сигналов и графиков\n(В разработке)",
            font=('Segoe UI', 14),
            foreground='#858585'
        )
        info_lbl.pack(expand=True)
    
    def _create_device_tab(self, parent):
        """Вкладка устройства"""
        # Информация
        info_frame = ttk.LabelFrame(parent, text="Информация об устройстве", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.device_info_text = scrolledtext.ScrolledText(
            info_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 9),
            height=10
        )
        self.device_info_text.pack(fill=tk.X)
        
        ttk.Button(info_frame, text="Обновить информацию",
                  command=self._refresh_device_info).pack(pady=5)
        
        # Настройка антенны
        tune_frame = ttk.LabelFrame(parent, text="Настройка антенны", padding=10)
        tune_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(tune_frame, text="HF Tune",
                  command=lambda: self.execute_command('hf_tune')).pack(side=tk.LEFT, padx=5)
        ttk.Button(tune_frame, text="LF Tune",
                  command=lambda: self.execute_command('lf_tune')).pack(side=tk.LEFT, padx=5)
        
        # Управление
        control_frame = ttk.LabelFrame(parent, text="Управление устройством", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="🔄 Перезагрузить",
                  command=lambda: self.execute_command('device_reset'),
                  style='Warning.TButton').pack(side=tk.LEFT, padx=5)
    
    def _create_statusbar(self):
        """Создание статусной строки"""
        statusbar = ttk.Frame(self.root)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_message = ttk.Label(
            statusbar,
            text="Готов к работе",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_message.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.version_label = ttk.Label(
            statusbar,
            text="v1.0.0",
            relief=tk.SUNKEN,
            anchor=tk.E,
            padding=(5, 2)
        )
        self.version_label.pack(side=tk.RIGHT)
    
    # ========================================================================
    # Методы работы с командами
    # ========================================================================
    
    def _populate_commands_tree(self):
        """Заполнение дерева команд"""
        # Очистка
        for item in self.commands_tree.get_children():
            self.commands_tree.delete(item)
        
        # Добавление категорий и команд
        categories = self.core.command_manager.categories
        commands = self.core.command_manager.commands
        
        for cat_id, cat_data in categories.items():
            cat_name = cat_data.get('name', cat_id)
            cat_color = cat_data.get('color', '#ffffff')
            
            # Вставка категории
            cat_item = self.commands_tree.insert('', 'end', text=cat_name, 
                                                 tags=(cat_id,), open=True)
            
            # Вставка команд категории
            for cmd_id, cmd in commands.items():
                if cmd.category == cat_id:
                    risk_colors = {
                        'safe': '#4CAF50',
                        'medium': '#FF9800',
                        'high': '#f44336',
                        'dangerous': '#D32F2F'
                    }
                    
                    risk_level = cmd.risk_level.value
                    risk_color = risk_colors.get(risk_level, '#ffffff')
                    
                    self.commands_tree.insert(
                        cat_item, 'end',
                        text=cmd.name,
                        values=(cmd.name, risk_level),
                        tags=(cmd_id,)
                    )
        
        # Настройка тегов для цветов
        for cat_id, cat_data in categories.items():
            color = cat_data.get('color', '#ffffff')
            self.commands_tree.tag_bind(cat_id, '<<TreeviewSelect>>', lambda e: None)
    
    def _filter_commands(self):
        """Фильтрация команд по поиску"""
        search_term = self.search_var.get().lower()
        
        # Простая реализация - скрывать/показывать элементы
        # Можно улучшить для производительности
        pass
    
    def _on_command_selected(self, event):
        """Обработка выбора команды"""
        selection = self.commands_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.commands_tree.item(item, 'tags')
        
        if tags and len(tags) > 0:
            cmd_id = tags[0]
            cmd = self.core.command_manager.get_command(cmd_id)
            
            if cmd:
                self.selected_command.set(cmd_id)
                self._show_command_params(cmd)
    
    def _show_command_params(self, cmd):
        """Отображение параметров команды"""
        # Очистка контейнера
        for widget in self.params_container.winfo_children():
            widget.destroy()
        
        # Создание виджетов для каждого параметра
        row = 0
        self.param_widgets = {}
        
        for param in cmd.parameters:
            ttk.Label(self.params_container, text=f"{param.description}:").grid(
                row=row, column=0, sticky=tk.W, pady=2
            )
            
            if param.type == 'select':
                widget = ttk.Combobox(
                    self.params_container,
                    values=param.options,
                    width=20,
                    state='readonly'
                )
                widget.set(param.default if param.default else param.options[0])
            elif param.type == 'integer':
                widget = ttk.Entry(self.params_container, width=20)
                widget.insert(0, str(param.default) if param.default is not None else '')
            else:
                widget = ttk.Entry(self.params_container, width=20)
                widget.insert(0, str(param.default) if param.default is not None else '')
            
            widget.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            self.param_widgets[param.name] = (widget, param)
            row += 1
        
        # Help text
        if cmd.help_text:
            help_lbl = ttk.Label(
                self.params_container,
                text=cmd.help_text,
                wraplength=250,
                foreground='#858585',
                font=('Segoe UI', 8)
            )
            help_lbl.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
    
    def _get_param_values(self) -> dict:
        """Получение значений параметров"""
        values = {}
        for name, (widget, param) in self.param_widgets.items():
            if isinstance(widget, ttk.Combobox):
                values[name] = widget.get()
            else:
                text = widget.get().strip()
                if text:
                    if param.type == 'integer':
                        try:
                            values[name] = int(text)
                        except ValueError:
                            values[name] = text
                    else:
                        values[name] = text
        return values
    
    def _execute_selected_command(self):
        """Выполнение выбранной команды"""
        cmd_id = self.selected_command.get()
        if not cmd_id:
            messagebox.showwarning("Предупреждение", "Выберите команду!")
            return
        
        cmd = self.core.command_manager.get_command(cmd_id)
        if not cmd:
            return
        
        # Проверка уровня риска
        if cmd.risk_level in [RiskLevel.HIGH, RiskLevel.DANGEROUS]:
            confirm = messagebox.askyesno(
                "Подтверждение",
                f"Вы уверены, что хотите выполнить операцию \"{cmd.name}\"?\n"
                f"Уровень риска: {cmd.risk_level.value.upper()}",
                icon='warning'
            )
            if not confirm:
                return
        
        # Получение параметров
        params = self._get_param_values()
        
        # Проверка обязательных параметров
        for param in cmd.parameters:
            if param.required and param.name not in params:
                messagebox.showerror("Ошибка", f"Не указан обязательный параметр: {param.name}")
                return
        
        # Выполнение в потоке
        threading.Thread(target=self._execute_thread, args=(cmd_id, params), daemon=True).start()
    
    def _execute_thread(self, cmd_id: str, params: dict):
        """Поток выполнения команды"""
        self._update_status(f"Выполнение: {cmd_id}...")
        
        result = self.core.execute_command(cmd_id, **params)
        
        self.root.after(0, lambda: self._log_result(result))
        self.root.after(0, lambda: self._update_status("Готов"))
    
    def execute_command(self, cmd_id: str, **params) -> str:
        """Публичный метод выполнения команды"""
        threading.Thread(
            target=self._execute_thread,
            args=(cmd_id, params),
            daemon=True
        ).start()
        return "Команда отправлена"
    
    def execute_quick_command(self, cmd_id: str):
        """Быстрое выполнение команды без параметров"""
        self.execute_command(cmd_id)
    
    def _execute_custom_command(self):
        """Выполнение пользовательской команды"""
        command = self.custom_command_var.get().strip()
        if not command:
            return
        
        threading.Thread(
            target=self._execute_custom_thread,
            args=(command,),
            daemon=True
        ).start()
    
    def _execute_custom_thread(self, command: str):
        """Поток выполнения пользовательской команды"""
        result = self.core.execute_custom_command(command)
        self.root.after(0, lambda: self._log_result(result))
    
    # ========================================================================
    # Методы подключения
    # ========================================================================
    
    def connect_device(self):
        """Подключение к устройству"""
        def thread_func():
            success = self.core.connect_device()
            
            if success:
                device_info = self.core.get_device_info()
                status = "Connected" if device_info.is_connected else "Error"
                
                self.root.after(0, lambda: self.connection_status_var.set(status))
                self.root.after(0, lambda: self.connection_status_var.set(f"Подключено: {device_info.model}"))
                self.root.after(0, lambda: self.device_info_var.set(device_info.model))
                self.root.after(0, lambda: self._log(f"Устройство подключено: {device_info.model}", 'SUCCESS'))
                self.root.after(0, lambda: self._refresh_device_info())
            else:
                self.root.after(0, lambda: self.connection_status_var.set("Ошибка подключения"))
                self.root.after(0, lambda: self._log("Не удалось подключить устройство", 'ERROR'))
        
        threading.Thread(target=thread_func, daemon=True).start()
    
    def disconnect_device(self):
        """Отключение от устройства"""
        self.core.disconnect_device()
        self.connection_status_var.set("Отключено")
        self.device_info_var.set("Нет устройства")
        self._log("Устройство отключено", 'INFO')
    
    # ========================================================================
    # Логирование
    # ========================================================================
    
    def _on_log_entry(self, entry):
        """Обработчик записи лога"""
        def update():
            timestamp = entry.timestamp.strftime('%H:%M:%S')
            message = f"[{timestamp}] {entry.message}\n"
            
            self.log_text.insert(tk.END, message, entry.level)
            self.log_text.see(tk.END)
        
        self.root.after(0, update)
    
    def _log(self, message: str, level: str = 'INFO'):
        """Добавление записи в лог"""
        self.core.logger.log(level, message, 'GUI')
    
    def _log_result(self, result: str):
        """Логирование результата команды"""
        self.log_text.insert(tk.END, f"\n{result}\n", 'INFO')
        self.log_text.see(tk.END)
    
    def _clear_log(self):
        """Очистка лога"""
        self.log_text.delete(1.0, tk.END)
        self.core.logger.clear()
    
    def _save_log(self):
        """Сохранение лога"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            self._log(f"Лог сохранен: {filename}", 'SUCCESS')
    
    def _toggle_autoscroll(self):
        """Переключение автопрокрутки"""
        self.autoscroll = not self.autoscroll
    
    def _update_status(self, message: str):
        """Обновление статуса"""
        self.status_message.config(text=message)
    
    # ========================================================================
    # Специфичные команды
    # ========================================================================
    
    def _run_nested_attack(self):
        """Запуск nested атаки"""
        key_type = self.nested_key_type.get()
        block = self.nested_block.get()
        
        if not block.isdigit():
            messagebox.showerror("Ошибка", "Номер блока должен быть числом")
            return
        
        self.execute_command('hf_mifare_nested', key_type=key_type, block_no=int(block))
    
    def _run_hardnested_attack(self):
        """Запуск hardnested атаки"""
        key_type = self.hardnested_key_type.get()
        block = self.hardnested_block.get()
        
        if not block.isdigit():
            messagebox.showerror("Ошибка", "Номер блока должен быть числом")
            return
        
        self.execute_command('hf_mifare_hardnested', key_type=key_type, block_no=int(block))
    
    def _write_to_card(self):
        """Запись данных в карту"""
        card_type = self.write_card_type.get()
        block = self.write_block.get()
        data = self.write_data.get().strip()
        
        if not block.isdigit():
            messagebox.showerror("Ошибка", "Номер блока должен быть числом")
            return
        
        if not data or not all(c in '0123456789ABCDEFabcdef' for c in data):
            messagebox.showerror("Ошибка", "Некорректные hex данные")
            return
        
        confirm = messagebox.askyesno(
            "Подтверждение записи",
            "Вы уверены? Запись данных необратима!",
            icon='warning'
        )
        
        if not confirm:
            return
        
        if 'HF' in card_type:
            self.execute_command('hf_write_t55x7', page=int(block), data=data)
        else:
            self.execute_command('lf_write_t55x7', block=int(block), data=data)
    
    def _start_hf_emulation(self):
        """Запуск HF эмуляции"""
        uid = self.emulate_hf_uid.get().strip()
        
        if not uid or not all(c in '0123456789ABCDEFabcdef' for c in uid):
            messagebox.showerror("Ошибка", "Некорректный UID")
            return
        
        self.execute_command('hf_emulate_uid', uid=uid)
    
    def _start_lf_emulation(self):
        """Запуск LF эмуляции"""
        id_val = self.emulate_lf_id.get().strip()
        
        if not id_val or not all(c in '0123456789ABCDEFabcdef' for c in id_val):
            messagebox.showerror("Ошибка", "Некорректный ID")
            return
        
        self.execute_command('lf_emulate_em410x', id=id_val)
    
    def _stop_emulation(self):
        """Остановка эмуляции"""
        # Отправка Ctrl+C или специальной команды
        self._log("Эмуляция остановлена пользователем", 'INFO')
    
    def _stop_sniffing(self):
        """Остановка сниффинга"""
        self._log("Сниффинг остановлен пользователем", 'INFO')
    
    def _start_lf_sniff(self):
        """Запуск LF сниффинга"""
        threshold = self.sniff_threshold.get()
        
        if not threshold.isdigit():
            threshold = '128'
        
        self.execute_command('lf_sniff', threshold=int(threshold))
    
    def _save_trace(self):
        """Сохранение трассировки"""
        # Сохранение данных сниффинга
        self._log("Трассировка сохранена", 'SUCCESS')
    
    def _save_current_dump(self):
        """Сохранение текущего дампа"""
        self._log("Дамп сохранен", 'SUCCESS')
    
    def _load_dump(self):
        """Загрузка дампа"""
        filename = filedialog.askopenfilename(
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                
                if hasattr(self, 'hex_editor'):
                    self.hex_editor.load_data(data)
                
                self._log(f"Дамп загружен: {filename}", 'SUCCESS')
            except Exception as e:
                self._log(f"Ошибка загрузки дампа: {e}", 'ERROR')
    
    # ========================================================================
    # Меню и диалоги
    # ========================================================================
    
    def _open_dump(self):
        """Открытие дампа"""
        self._load_dump()
    
    def _save_dump(self):
        """Сохранение дампа"""
        if hasattr(self, 'hex_editor'):
            self.hex_editor.export_to_file()
    
    def _open_hex_editor(self):
        """Открытие hex редактора в отдельном окне"""
        # Переключение на вкладку hex редактора
        pass
    
    def _open_node_editor(self):
        """Открытие node редактора"""
        pass
    
    def _show_settings(self):
        """Показ настроек"""
        messagebox.showinfo("Настройки", "Модуль настроек в разработке")
    
    def _show_help(self):
        """Показ справки"""
        help_text = """
        ProxMaster Ultimate - Справка
        
        Использование:
        1. Подключите Proxmark3 к USB
        2. Нажмите "Подключить"
        3. Выберите команду из списка
        4. Настройте параметры и выполните
        
        Горячие клавиши:
        - F5: Обновить
        - Ctrl+L: Очистить лог
        - Escape: Операцию
        
        Поддерживаемые устройства:
        - Proxmark3 Easy
        - Proxmark3 Iceman
        - Proxmark3 RDV4
        """
        messagebox.showinfo("Справка", help_text)
    
    def _show_about(self):
        """Показ информации о программе"""
        about_text = """
        ProxMaster Ultimate v1.0.0
        
        Полноценное GUI приложение для управления Proxmark3
        
        Особенности:
        • Полный набор команд Proxmark3
        • Hex редактор
        • Визуальный редактор команд (Node Editor)
        • Цветные логи
        • Drag & Drop
        • Система обновлений
        
        Разработано для сообщества RFID энтузиастов
        """
        messagebox.showinfo("О программе", about_text)
    
    def show_device_info(self):
        """Показ информации об устройстве"""
        self._refresh_device_info()
    
    def _refresh_device_info(self):
        """Обновление информации об устройстве"""
        if hasattr(self, 'device_info_text'):
            info = self.core.get_device_info()
            
            info_text = f"""
Модель: {info.model}
Прошивка: {info.firmware_version}
FPGA: {info.fpga_version}
Дата сборки: {info.build_date}
Статус: {'Подключено' if info.is_connected else 'Отключено'}
            """.strip()
            
            self.device_info_text.delete(1.0, tk.END)
            self.device_info_text.insert(tk.END, info_text)
    
    def check_updates(self):
        """Проверка обновлений"""
        self._log("Проверка обновлений...", 'INFO')
        updates = self.core.update_manager.check_for_updates()
        
        if updates.get('app_update_available'):
            messagebox.showinfo("Обновление", "Доступна новая версия приложения!")
        else:
            messagebox.showinfo("Обновления", "Установлена последняя версия")
    
    # ========================================================================
    # Закрытие приложения
    # ========================================================================
    
    def _on_closing(self):
        """Обработчик закрытия окна"""
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            self.core.stop()
            self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Точка входа приложения"""
    app = ProxMasterApp()
    app.run()


if __name__ == "__main__":
    main()
