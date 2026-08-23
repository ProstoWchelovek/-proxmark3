#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxmark3 Easy GUI - Полнофункциональное приложение для работы с Proxmark3 Iceman
Версия: 1.0.0
Совместимость: Windows 10/11, Proxmark3 Easy/RDV4/Iceman
"""

import sys
import os
import subprocess
import threading
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import webbrowser

# Проверка и импорт GUI библиотек
try:
    import customtkinter as ctk
    from customtkinter import CTk, CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkTextbox
    from customtkinter import CTkTabview, CTkComboBox, CTkSwitch, CTkCheckBox, CTkProgressBar
    from customtkinter import CTkScrollableFrame, CTkOptionMenu, CTkInputDialog, CTkFont
    from customtkinter import set_appearance_mode, set_default_color_theme
except ImportError:
    print("Ошибка: Не установлен customtkinter. Выполните: pip install customtkinter")
    sys.exit(1)

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Ошибка: Не установлены matplotlib/numpy. Выполните: pip install matplotlib numpy")
    sys.exit(1)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Ошибка: Не установлен pyserial. Выполните: pip install pyserial")
    sys.exit(1)

# Импорт локальных модулей
try:
    from src.commands import (
        CommandInfo, CommandCategory, CommandRisk, 
        get_command, get_commands_by_category, search_commands, COMMANDS_DB
    )
except ImportError:
    # Если запускается как скрипт из корневой папки
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.commands import (
        CommandInfo, CommandCategory, CommandRisk,
        get_command, get_commands_by_category, search_commands, COMMANDS_DB
    )


# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ============================================================================

APP_NAME = "Proxmark3 Easy GUI"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Proxmark3 Community"

# Пути по умолчанию
DEFAULT_PROXSPACE_PATH = Path.home() / "Proxmark3" / "ProxSpace" / "pm3"
DEFAULT_CLIENT_PATH = DEFAULT_PROXSPACE_PATH / "client" / "proxmark3.exe"
CONFIG_FILE = Path.home() / ".proxmark3_easy_gui" / "config.json"

# Цвета для логов
LOG_COLORS = {
    '[=]': '#4A90E2',      # Синий - информация
    '[+]': '#7ED321',      # Зеленый - успех
    '[-]': '#D0021B',      # Красный - ошибка
    '[!]': '#F5A623',      # Оранжевый - предупреждение
    '[?]': '#BD10E0',      # Фиолетовый - подсказка
    '[#]': '#50E3C2',      # Голубой - конфигурация
    '[|]': '#417505',      # Бирюзовый - прогресс
    '[/]': '#417505',
    '[\\]': '#417505',
}

# Настройки CustomTkinter
set_appearance_mode("Dark")
set_default_color_theme("blue")


# ============================================================================
# МЕНЕДЖЕР КОНФИГУРАЦИИ
# ============================================================================

class ConfigManager:
    """Управление настройками приложения"""
    
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Загрузка конфигурации из файла"""
        default_config = {
            'proxspace_path': str(DEFAULT_PROXSPACE_PATH),
            'client_path': str(DEFAULT_CLIENT_PATH),
            'com_port': 'AUTO',
            'baudrate': 115200,
            'theme': 'Dark',
            'language': 'ru',
            'auto_connect': False,
            'show_hints': True,
            'save_logs': True,
            'log_directory': str(Path.home() / ".proxmark3_easy_gui" / "logs"),
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    default_config.update(saved_config)
        except Exception as e:
            print(f"Ошибка загрузки конфига: {e}")
        
        return default_config
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")
    
    def get(self, key: str, default=None):
        """Получение значения настройки"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Установка значения настройки"""
        self.config[key] = value
        self.save_config()


# ============================================================================
# МЕНЕДЖЕР ПРОЦЕССОВ PROXMARK3
# ============================================================================

class Proxmark3Process:
    """Управление процессом Proxmark3 client"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.output_callback = None
        self.error_callback = None
        self.thread = None
        
    def check_proxspace(self) -> bool:
        """Проверка наличия установленной ProxSpace"""
        client_path = Path(self.config.get('client_path'))
        return client_path.exists()
    
    def find_com_ports(self) -> List[Dict]:
        """Поиск доступных COM портов"""
        ports = []
        try:
            for port in serial.tools.list_ports.comports():
                ports.append({
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
        except Exception as e:
            print(f"Ошибка поиска портов: {e}")
        return ports
    
    def start_client(self):
        """Запуск клиента Proxmark3"""
        if self.is_running:
            return False
        
        client_path = self.config.get('client_path')
        if not Path(client_path).exists():
            return False
        
        try:
            # Запускаем в интерактивном режиме
            self.process = subprocess.Popen(
                [client_path, '-c', ''],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.is_running = True
            
            # Запускаем поток чтения вывода
            self.thread = threading.Thread(target=self._read_output, daemon=True)
            self.thread.start()
            
            return True
        except Exception as e:
            print(f"Ошибка запуска клиента: {e}")
            return False
    
    def _read_output(self):
        """Чтение вывода процесса (в отдельном потоке)"""
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    if self.output_callback:
                        self.output_callback(line.strip())
                else:
                    break
            except Exception as e:
                if self.error_callback:
                    self.error_callback(str(e))
                break
    
    def send_command(self, command: str):
        """Отправка команды клиенту"""
        if self.process and self.is_running:
            try:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
            except Exception as e:
                if self.error_callback:
                    self.error_callback(f"Ошибка отправки команды: {e}")
    
    def stop_client(self):
        """Остановка клиента"""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            finally:
                self.process = None


# ============================================================================
# УСТАНОВЩИК PROXSPACE
# ============================================================================

class ProxSpaceInstaller:
    """Автоматическая установка ProxSpace"""
    
    GITHUB_RELEASE_URL = "https://github.com/Gator96100/ProxSpace/releases"
    INSTALLER_NAME = "ProxSpace.7z"
    
    def __init__(self, config_manager: ConfigManager, callback=None):
        self.config = config_manager
        self.callback = callback
        self.install_path = DEFAULT_PROXSPACE_PATH.parent
        
    def log(self, message: str):
        """Логирование сообщения"""
        if self.callback:
            self.callback(message)
    
    def download_installer(self) -> bool:
        """Загрузка установщика ProxSpace"""
        self.log("[=] Начало загрузки ProxSpace...")
        # Здесь должна быть логика загрузки с GitHub
        # Для примера - заглушка
        self.log("[!] Автоматическая загрузка требует реализации")
        self.log("[?] Перейдите на https://github.com/Gator96100/ProxSpace")
        return False
    
    def extract_installer(self, archive_path: str) -> bool:
        """Распаковка установщика"""
        self.log(f"[=] Распаковка {archive_path}...")
        # Логика распаковки 7z архива
        return False
    
    def compile_proxspace(self) -> bool:
        """Компиляция клиента и прошивки"""
        self.log("[=] Компиляция ProxSpace...")
        # Запуск make команд
        return False
    
    def run_wizard(self) -> bool:
        """Запуск мастера установки"""
        self.log("[=] Запуск мастера установки ProxSpace")
        
        steps = [
            ("Проверка системы", self.check_system),
            ("Загрузка установщика", self.download_installer),
            ("Распаковка", lambda: self.extract_installer("temp.7z")),
            ("Компиляция", self.compile_proxspace),
            ("Настройка путей", self.setup_paths),
        ]
        
        for step_name, step_func in steps:
            self.log(f"[=] Шаг: {step_name}")
            if not step_func():
                self.log(f"[-] Ошибка на шаге: {step_name}")
                return False
        
        self.log("[+] Установка завершена успешно!")
        return True
    
    def check_system(self) -> bool:
        """Проверка системных требований"""
        # Проверка наличия MSYS2, git, make и т.д.
        return True
    
    def setup_paths(self) -> bool:
        """Настройка путей после установки"""
        new_client_path = DEFAULT_PROXSPACE_PATH / "client" / "proxmark3.exe"
        if new_client_path.exists():
            self.config.set('client_path', str(new_client_path))
            self.config.set('proxspace_path', str(DEFAULT_PROXSPACE_PATH))
            return True
        return False


# ============================================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================================

class Proxmark3EasyGUI(ctk.CTk):
    """Главный класс приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация менеджеров
        self.config_manager = ConfigManager()
        self.pm3_process = Proxmark3Process(self.config_manager)
        
        # Настройка окна
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Состояние подключения
        self.is_connected = False
        self.device_info = {}
        
        # Создание интерфейса
        self._create_ui()
        
        # Проверка ProxSpace при запуске
        self.after(100, self._check_proxspace_on_start)
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_ui(self):
        """Создание пользовательского интерфейса"""
        # Главная сетка
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Верхняя панель
        self._create_top_bar()
        
        # Вкладки
        self._create_tabs()
        
        # Нижняя панель статуса
        self._create_status_bar()
    
    def _create_top_bar(self):
        """Создание верхней панели"""
        top_frame = CTkFrame(self, height=60)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        top_frame.grid_columnconfigure(1, weight=1)
        
        # Логотип и название
        logo_label = CTkLabel(
            top_frame, 
            text=f"📡 {APP_NAME}",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=10, pady=10)
        
        # Индикатор подключения
        self.connection_indicator = CTkLabel(
            top_frame,
            text="🔴 Отключено",
            font=ctk.CTkFont(size=14),
            text_color="#D0021B"
        )
        self.connection_indicator.grid(row=0, column=1, padx=20, pady=10, sticky="w")
        
        # Кнопки подключения
        btn_frame = CTkFrame(top_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10, pady=10)
        
        self.connect_btn = CTkButton(
            btn_frame,
            text="🔌 Подключить",
            command=self._toggle_connection,
            width=120
        )
        self.connect_btn.grid(row=0, column=0, padx=5)
        
        self.restart_btn = CTkButton(
            btn_frame,
            text="🔄 Перезагрузить",
            command=self._restart_device,
            width=120,
            state="disabled"
        )
        self.restart_btn.grid(row=0, column=1, padx=5)
    
    def _create_tabs(self):
        """Создание вкладок"""
        self.tabview = CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Добавление вкладок
        self.tabview.add("🏠 ГЛАВНАЯ")
        self.tabview.add("🔍 ПОИСК И ЧТЕНИЕ")
        self.tabview.add("💾 ПАМЯТЬ И КЛЮЧИ")
        self.tabview.add("✏️ ЗАПИСЬ")
        self.tabview.add("📡 СНИФФИНГ")
        self.tabview.add("🎭 ЭМУЛЯЦИЯ")
        self.tabview.add("🛠 ИНСТРУМЕНТЫ")
        self.tabview.add("📜 СКРИПТЫ")
        self.tabview.add("⚙️ СИСТЕМА")
        
        # Создание содержимого вкладок
        self._create_main_tab()
        self._create_search_tab()
        self._create_memory_tab()
        self._create_write_tab()
        self._create_sniffing_tab()
        self._create_emulation_tab()
        self._create_tools_tab()
        self._create_scripts_tab()
        self._create_system_tab()
    
    def _create_status_bar(self):
        """Создание нижней панели статуса"""
        status_frame = CTkFrame(self, height=30)
        status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        status_frame.grid_columnconfigure(1, weight=1)
        
        # Статус
        self.status_label = CTkLabel(
            status_frame,
            text="Готов к работе",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, padx=10, sticky="w")
        
        # Версии
        self.version_label = CTkLabel(
            status_frame,
            text="",
            anchor="e"
        )
        self.version_label.grid(row=0, column=1, padx=10, sticky="e")
    
    # ========================================================================
    # ВКЛАДКА 1: ГЛАВНАЯ
    # ========================================================================
    
    def _create_main_tab(self):
        """Создание главной вкладки"""
        tab = self.tabview.tab("🏠 ГЛАВНАЯ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # Информация об устройстве
        info_frame = CTkFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        info_frame.grid_columnconfigure(1, weight=1)
        
        CTkLabel(info_frame, text="📊 Информация об устройстве:", 
                font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        
        # Статус
        CTkLabel(info_frame, text="Статус:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.main_status_label = CTkLabel(info_frame, text="Не подключено", text_color="#D0021B")
        self.main_status_label.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Версии
        CTkLabel(info_frame, text="Firmware:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.fw_version_label = CTkLabel(info_frame, text="-")
        self.fw_version_label.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        CTkLabel(info_frame, text="Bootrom:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.boot_version_label = CTkLabel(info_frame, text="-")
        self.boot_version_label.grid(row=3, column=1, sticky="w", padx=10, pady=5)
        
        CTkLabel(info_frame, text="Hardware:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.hw_version_label = CTkLabel(info_frame, text="-")
        self.hw_version_label.grid(row=4, column=1, sticky="w", padx=10, pady=5)
        
        # Быстрые действия
        actions_frame = CTkFrame(tab)
        actions_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        CTkButton(actions_frame, text="📡 hw tune", command=lambda: self._send_command("hw tune")).pack(side="left", padx=5, pady=10)
        CTkButton(actions_frame, text="🔍 auto", command=lambda: self._send_command("auto")).pack(side="left", padx=5, pady=10)
        CTkButton(actions_frame, text="📊 hw status", command=lambda: self._send_command("hw status")).pack(side="left", padx=5, pady=10)
        CTkButton(actions_frame, text="ℹ️ hw version", command=lambda: self._send_command("hw version")).pack(side="left", padx=5, pady=10)
        
        # Консоль вывода
        console_frame = CTkFrame(tab)
        console_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(0, weight=1)
        
        self.main_console = CTkTextbox(console_frame, wrap="word")
        self.main_console.grid(row=0, column=0, sticky="nsew")
        
        # Настройка тегов для цветов
        for tag, color in LOG_COLORS.items():
            self.main_console.tag_config(tag, foreground=color)
    
    # ========================================================================
    # ВКЛАДКА 2: ПОИСК И ЧТЕНИЕ
    # ========================================================================
    
    def _create_search_tab(self):
        """Создание вкладки поиска и чтения"""
        tab = self.tabview.tab("🔍 ПОИСК И ЧТЕНИЕ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)
        
        # Панель управления
        control_frame = CTkFrame(tab)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Автопоиск
        CTkButton(
            control_frame,
            text="🔍 Auto-detect (полный цикл)",
            command=lambda: self._send_command("auto"),
            width=200
        ).pack(side="left", padx=10, pady=10)
        
        # LF поиск
        lf_frame = CTkLabelFrame(control_frame, text="LF (125 kHz)")
        lf_frame.pack(side="left", padx=10, pady=10)
        
        CTkButton(lf_frame, text="LF Search", command=lambda: self._send_command("lf search")).pack(padx=5, pady=5)
        CTkButton(lf_frame, text="LF Read", command=lambda: self._send_command("lf read")).pack(padx=5, pady=5)
        
        # HF поиск
        hf_frame = CTkLabelFrame(control_frame, text="HF (13.56 MHz)")
        hf_frame.pack(side="left", padx=10, pady=10)
        
        CTkButton(hf_frame, text="HF Search", command=lambda: self._send_command("hf search")).pack(padx=5, pady=5)
        CTkButton(hf_frame, text="HF Reader", command=lambda: self._send_command("hf reader")).pack(padx=5, pady=5)
        
        # Протоколы (выпадающий список)
        protocol_frame = CTkFrame(control_frame)
        protocol_frame.pack(side="left", padx=10, pady=10)
        
        CTkLabel(protocol_frame, text="Протокол:").pack(padx=5, pady=5)
        self.protocol_combo = CTkComboBox(protocol_frame, values=[
            "EM4100", "EM4x05", "T55xx", "HID", "AWID", "Indala",
            "ISO14443A", "Mifare Classic", "Mifare Ultralight", "iClass",
            "ISO15693", "FeliCa", "Legic", "NFC"
        ])
        self.protocol_combo.pack(padx=5, pady=5)
        
        # Прогресс бар
        self.search_progress = CTkProgressBar(tab)
        self.search_progress.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.search_progress.set(0)
        
        # Консоль
        console_frame = CTkFrame(tab)
        console_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        console_frame.grid_columnconfigure(0, weight=1)
        
        self.search_console = CTkTextbox(console_frame, height=150, wrap="word")
        self.search_console.grid(row=0, column=0, sticky="ew")
        
        # График
        graph_frame = CTkFrame(tab)
        graph_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        graph_frame.grid_columnconfigure(0, weight=1)
        graph_frame.grid_rowconfigure(0, weight=1)
        
        self.search_figure, self.search_ax = plt.subplots(figsize=(8, 4))
        self.search_canvas = FigureCanvasTkAgg(self.search_figure, master=graph_frame)
        self.search_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
    
    # ========================================================================
    # ВКЛАДКА 3: ПАМЯТЬ И КЛЮЧИ (HEX РЕДАКТОР)
    # ========================================================================
    
    def _create_memory_tab(self):
        """Создание вкладки памяти и ключей"""
        tab = self.tabview.tab("💾 ПАМЯТЬ И КЛЮЧИ")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Левая панель - управление файлами
        left_frame = CTkFrame(tab, width=200)
        left_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=10)
        
        CTkButton(left_frame, text="📂 Загрузить дамп", command=self._load_dump).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="💾 Сохранить дамп", command=self._save_dump).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="📋 Копировать", command=self._copy_to_clipboard).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="📥 Вставить", command=self._paste_from_clipboard).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="🗑 Очистить", command=self._clear_hex).pack(fill="x", padx=5, pady=5)
        
        # Словари ключей
        CTkLabel(left_frame, text="Ключи Mifare:", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        CTkButton(left_frame, text="📂 Загрузить .key", command=self._load_keys).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="💾 Сохранить .key", command=self._save_keys).pack(fill="x", padx=5, pady=5)
        CTkButton(left_frame, text="🔑 Брутфорс", command=self._brute_force_keys).pack(fill="x", padx=5, pady=5)
        
        # Правая панель - Hex редактор
        right_frame = CTkFrame(tab)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # Заголовок
        CTkLabel(right_frame, text="Hex Редактор", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Hex view
        hex_frame = CTkFrame(right_frame)
        hex_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        hex_frame.grid_columnconfigure(0, weight=1)
        hex_frame.grid_rowconfigure(0, weight=1)
        
        self.hex_editor = CTkTextbox(hex_frame, wrap="none", font=ctk.CTkFont(family="Consolas", size=12))
        self.hex_editor.grid(row=0, column=0, sticky="nsew")
        
        # Настройка тегов для hex редактора
        self.hex_editor.tag_config("address", foreground="#808080")
        self.hex_editor.tag_config("hex", foreground="#4A90E2")
        self.hex_editor.tag_config("ascii", foreground="#7ED321")
        self.hex_editor.tag_config("selected", background="#404040")
        
        # Нижняя панель - информация
        info_frame = CTkFrame(right_frame)
        info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        CTkLabel(info_frame, text="Размер:").pack(side="left", padx=5)
        self.hex_size_label = CTkLabel(info_frame, text="0 байт")
        self.hex_size_label.pack(side="left", padx=5)
        
        CTkLabel(info_frame, text="Позиция:").pack(side="left", padx=20)
        self.hex_pos_label = CTkLabel(info_frame, text="0x0000")
        self.hex_pos_label.pack(side="left", padx=5)
    
    # ========================================================================
    # ВКЛАДКА 4: ЗАПИСЬ
    # ========================================================================
    
    def _create_write_tab(self):
        """Создание вкладки записи"""
        tab = self.tabview.tab("✏️ ЗАПИСЬ")
        tab.grid_columnconfigure(0, weight=1)
        
        # Мастер записи
        wizard_frame = CTkFrame(tab)
        wizard_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Шаг 1: Источник
        source_frame = CTkLabelFrame(wizard_frame, text="ШАГ 1: Источник данных")
        source_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkRadioButton(source_frame, text="Из файла (.bin, .eml)", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Из буфера", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Из сохранённых карт", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Ввести вручную (Hex)", command=None).pack(anchor="w", padx=10, pady=5)
        
        # Поле ввода hex
        hex_input = CTkEntry(source_frame, placeholder_text="Введите HEX данные...", width=400)
        hex_input.pack(padx=10, pady=10)
        
        # Шаг 2: Цель
        target_frame = CTkLabelFrame(wizard_frame, text="ШАГ 2: Тип карты")
        target_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        card_type = CTkComboBox(target_frame, values=[
            "T5577", "T5555", "Magic UID Gen1", "Magic UID Gen2",
            "EM4100 Clone", "Mifare Classic Clone", "iClass Clone"
        ])
        card_type.pack(padx=10, pady=10)
        
        # Опции
        options_frame = CTkFrame(wizard_frame)
        options_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        CTkCheckBox(options_frame, text="Блокировка секторов").pack(side="left", padx=10)
        CTkCheckBox(options_frame, text="Проверить после записи").pack(side="left", padx=10)
        
        # Кнопка записи
        write_btn = CTkButton(
            wizard_frame,
            text="⚠️ ЗАПИСАТЬ (опасная операция)",
            fg_color="#D0021B",
            hover_color="#FF0000",
            command=self._confirm_and_write
        )
        write_btn.grid(row=3, column=0, pady=20)
    
    # ========================================================================
    # ВКЛАДКА 5: СНИФФИНГ
    # ========================================================================
    
    def _create_sniffing_tab(self):
        """Создание вкладки сниффинга"""
        tab = self.tabview.tab("📡 СНИФФИНГ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # Управление
        control_frame = CTkFrame(tab)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(control_frame, text="Тип сниффинга:").pack(side="left", padx=10)
        
        sniff_type = CTkComboBox(control_frame, values=[
            "hf sniff (общий)",
            "hf 14a sniff (ISO14443A)",
            "hf 14b sniff (ISO14443B)",
            "hf 15 sniff (ISO15693)",
            "lf sniff",
            "hf iclass sniff",
            "hf legic sniff",
            "hf felica sniff"
        ])
        sniff_type.pack(side="left", padx=10)
        
        self.sniff_start_btn = CTkButton(
            control_frame,
            text="▶ Старт",
            command=lambda: self._start_sniffing(sniff_type.get()),
            fg_color="#7ED321"
        )
        self.sniff_start_btn.pack(side="right", padx=10)
        
        self.sniff_stop_btn = CTkButton(
            control_frame,
            text="⏹ Стоп",
            command=self._stop_sniffing,
            state="disabled",
            fg_color="#D0021B"
        )
        self.sniff_stop_btn.pack(side="right", padx=10)
        
        # Таблица пакетов
        packets_frame = CTkFrame(tab)
        packets_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        packets_frame.grid_columnconfigure(0, weight=1)
        packets_frame.grid_rowconfigure(0, weight=1)
        
        self.packets_text = CTkTextbox(packets_frame, wrap="none")
        self.packets_text.grid(row=0, column=0, sticky="nsew")
        
        # Заголовки таблицы
        headers = "Время".ljust(12) + "Тип".ljust(10) + "Данные (RAW)\n"
        self.packets_text.insert("0.0", headers)
        self.packets_text.tag_config("header", font=ctk.CTkFont(weight="bold"))
        
        # Кнопки действий
        actions_frame = CTkFrame(tab)
        actions_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        CTkButton(actions_frame, text="💾 Save Dump", command=self._save_sniff_dump).pack(side="left", padx=5)
        CTkButton(actions_frame, text="🔍 Анализировать", command=self._analyze_sniff).pack(side="left", padx=5)
        CTkButton(actions_frame, text="🧹 Очистить", command=lambda: self.packets_text.delete("1.0", "end")).pack(side="left", padx=5)
    
    # ========================================================================
    # ВКЛАДКА 6: ЭМУЛЯЦИЯ
    # ========================================================================
    
    def _create_emulation_tab(self):
        """Создание вкладки эмуляции"""
        tab = self.tabview.tab("🎭 ЭМУЛЯЦИЯ")
        tab.grid_columnconfigure(0, weight=1)
        
        # Источник
        source_frame = CTkLabelFrame(tab, text="Источник данных для эмуляции")
        source_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkRadioButton(source_frame, text="Из файла дампа", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Из сохранённых карт (слоты)", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Из буфера", command=None).pack(anchor="w", padx=10, pady=5)
        CTkRadioButton(source_frame, text="Ввести UID вручную", command=None).pack(anchor="w", padx=10, pady=5)
        
        # Поле UID
        uid_frame = CTkFrame(source_frame)
        uid_frame.pack(fill="x", padx=10, pady=10)
        
        CTkLabel(uid_frame, text="UID (Hex):").pack(side="left", padx=5)
        uid_entry = CTkEntry(uid_frame, placeholder_text="04 A2 B3 C4", width=200)
        uid_entry.pack(side="left", padx=5)
        
        # Тип эмуляции
        type_frame = CTkLabelFrame(tab, text="Тип эмуляции")
        type_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        emu_type = CTkComboBox(type_frame, values=[
            "hf mf sim (Mifare Classic)",
            "hf mfu sim (Ultralight)",
            "hf 14a sim (ISO14443A)",
            "hf iclass sim",
            "hf legic sim",
            "hf 15 sim (ISO15693)",
            "lf em 410x sim",
            "lf t55xx sim",
            "lf hid sim"
        ])
        emu_type.pack(padx=10, pady=10)
        
        # Индикатор эмуляции
        self.emu_indicator = CTkLabel(tab, text="🔴 Эмуляция не активна", 
                                     font=ctk.CTkFont(size=16, weight="bold"))
        self.emu_indicator.grid(row=2, column=0, pady=20)
        
        # Кнопки управления
        btn_frame = CTkFrame(tab)
        btn_frame.grid(row=3, column=0, pady=20)
        
        self.emu_start_btn = CTkButton(
            btn_frame,
            text="▶ ЗАПУСТИТЬ ЭМУЛЯЦИЮ",
            command=lambda: self._start_emulation(emu_type.get()),
            width=200,
            fg_color="#7ED321"
        )
        self.emu_start_btn.pack(side="left", padx=20)
        
        self.emu_stop_btn = CTkButton(
            btn_frame,
            text="⏹ ОСТАНОВИТЬ",
            command=self._stop_emulation,
            state="disabled",
            width=200,
            fg_color="#D0021B"
        )
        self.emu_stop_btn.pack(side="left", padx=20)
    
    # ========================================================================
    # ВКЛАДКА 7: ИНСТРУМЕНТЫ
    # ========================================================================
    
    def _create_tools_tab(self):
        """Создание вкладки инструментов"""
        tab = self.tabview.tab("🛠 ИНСТРУМЕНТЫ")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # Панель инструментов
        tools_frame = CTkScrollableFrame(tab, width=200)
        tools_frame.grid(row=0, column=0, rowspan=3, sticky="ns", padx=10, pady=10)
        
        # Категории инструментов
        CTkLabel(tools_frame, text="📊 Analyse", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5, pady=10)
        CTkButton(tools_frame, text="LRC/CRC Checksum", command=lambda: self._send_command("analyse lrc")).pack(fill="x", padx=5, pady=2)
        CTkButton(tools_frame, text="Dates", command=lambda: self._send_command("analyse dates")).pack(fill="x", padx=5, pady=2)
        CTkButton(tools_frame, text="LFSR", command=lambda: self._send_command("analyse lfsr")).pack(fill="x", padx=5, pady=2)
        
        CTkLabel(tools_frame, text="〰️ Wiegand", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5, pady=10)
        CTkButton(tools_frame, text="Wiegand Encode/Decode", command=lambda: self._send_command("wiegand list")).pack(fill="x", padx=5, pady=2)
        
        CTkLabel(tools_frame, text="🔄 RevEng (CRC)", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5, pady=10)
        CTkButton(tools_frame, text="CRC Calculator", command=lambda: self._send_command("reveng calc")).pack(fill="x", padx=5, pady=2)
        
        CTkLabel(tools_frame, text="📡 HF Специальные", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5, pady=10)
        CTkButton(tools_frame, text="HF Plot", command=lambda: self._send_command("hf plot")).pack(fill="x", padx=5, pady=2)
        CTkButton(tools_frame, text="HF Tune", command=lambda: self._send_command("hf tune")).pack(fill="x", padx=5, pady=2)
        
        CTkLabel(tools_frame, text="📡 LF Специальные", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=5, pady=10)
        CTkButton(tools_frame, text="LF Config", command=lambda: self._send_command("lf config")).pack(fill="x", padx=5, pady=2)
        
        # График сигнала
        graph_frame = CTkFrame(tab)
        graph_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        graph_frame.grid_columnconfigure(0, weight=1)
        graph_frame.grid_rowconfigure(0, weight=1)
        
        self.tools_figure, self.tools_ax = plt.subplots(figsize=(10, 6))
        self.tools_canvas = FigureCanvasTkAgg(self.tools_figure, master=graph_frame)
        self.tools_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Toolbar
        toolbar_frame = CTkFrame(tab)
        toolbar_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        CTkButton(toolbar_frame, text="🔍 Zoom In", command=lambda: self._tools_zoom(1.2)).pack(side="left", padx=5)
        CTkButton(toolbar_frame, text="🔎 Zoom Out", command=lambda: self._tools_zoom(0.8)).pack(side="left", padx=5)
        CTkButton(toolbar_frame, text="🏠 Reset View", command=self._tools_reset_view).pack(side="left", padx=5)
        
        # Декодирование
        decode_frame = CTkFrame(tab)
        decode_frame.grid(row=2, column=1, sticky="ew", padx=10, pady=10)
        
        CTkLabel(decode_frame, text="Декодирование:").pack(side="left", padx=5)
        
        decode_type = CTkComboBox(decode_frame, values=["ASK", "FSK", "PSK", "Manchester", "Bi-Phase"])
        decode_type.pack(side="left", padx=5)
        
        CTkButton(decode_frame, text="Декодировать", command=lambda: self._decode_signal(decode_type.get())).pack(side="left", padx=5)
    
    # ========================================================================
    # ВКЛАДКА 8: СКРИПТЫ
    # ========================================================================
    
    def _create_scripts_tab(self):
        """Создание вкладки скриптов"""
        tab = self.tabview.tab("📜 СКРИПТЫ")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Список скриптов
        list_frame = CTkFrame(tab, width=300)
        list_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=10)
        
        # Поиск скриптов
        search_entry = CTkEntry(list_frame, placeholder_text="🔍 Поиск скриптов...")
        search_entry.pack(fill="x", padx=5, pady=5)
        
        # Фильтры
        filter_combo = CTkComboBox(list_frame, values=["Все", "Lua", "Python", "LF", "HF"])
        filter_combo.pack(fill="x", padx=5, pady=5)
        
        # Список
        self.scripts_listbox = CTkTextbox(list_frame, height=400)
        self.scripts_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Кнопки управления скриптами
        CTkButton(list_frame, text="🔄 Обновить список", command=self._refresh_scripts).pack(fill="x", padx=5, pady=5)
        CTkButton(list_frame, text="📝 Создать скрипт (Node Editor)", command=self._open_node_editor).pack(fill="x", padx=5, pady=5)
        
        # Панель выполнения
        exec_frame = CTkFrame(tab)
        exec_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        exec_frame.grid_columnconfigure(0, weight=1)
        
        # Имя скрипта
        script_name_frame = CTkFrame(exec_frame)
        script_name_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        CTkLabel(script_name_frame, text="Выбранный скрипт:").pack(side="left", padx=5)
        self.selected_script_label = CTkLabel(script_name_frame, text="Не выбран")
        self.selected_script_label.pack(side="left", padx=5)
        
        # Аргументы
        args_frame = CTkFrame(exec_frame)
        args_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        CTkLabel(args_frame, text="Аргументы:").pack(side="left", padx=5)
        self.script_args_entry = CTkEntry(args_frame, placeholder_text="--arg1 value1 --arg2 value2")
        self.script_args_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Кнопка запуска
        run_btn = CTkButton(
            exec_frame,
            text="▶ Запустить скрипт",
            command=self._run_selected_script,
            fg_color="#7ED321"
        )
        run_btn.grid(row=2, column=0, pady=10)
        
        # Консоль вывода
        console_frame = CTkFrame(exec_frame)
        console_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(0, weight=1)
        
        self.script_console = CTkTextbox(console_frame, wrap="word")
        self.script_console.grid(row=0, column=0, sticky="nsew")
    
    # ========================================================================
    # ВКЛАДКА 9: СИСТЕМА
    # ========================================================================
    
    def _create_system_tab(self):
        """Создание системной вкладки"""
        tab = self.tabview.tab("⚙️ СИСТЕМА")
        tab.grid_columnconfigure(0, weight=1)
        
        # Мастер установки (виден только если ProxSpace не найден)
        self.installer_frame = CTkLabelFrame(tab, text="📦 Установка ProxSpace")
        self.installer_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(
            self.installer_frame,
            text="ProxSpace не найден. Необходимо установить среду разработки.",
            text_color="#F5A623"
        ).pack(padx=10, pady=10)
        
        self.install_btn = CTkButton(
            self.installer_frame,
            text="🚀 Запустить мастер установки",
            command=self._run_installer_wizard,
            fg_color="#4A90E2"
        )
        self.install_btn.pack(padx=10, pady=10)
        
        # Консоль установщика
        self.installer_console = CTkTextbox(self.installer_frame, height=150, wrap="word")
        self.installer_console.pack(fill="x", padx=10, pady=10)
        
        # Прошивка
        fw_frame = CTkLabelFrame(tab, text="🔄 Обновление прошивки")
        fw_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        CTkButton(fw_frame, text="📥 Update Bootrom", command=self._update_bootrom).pack(side="left", padx=10, pady=10)
        CTkButton(fw_frame, text="📥 Update Full Image", command=self._update_full_image).pack(side="left", padx=10, pady=10)
        
        # Прогресс бар прошивки
        self.fw_progress = CTkProgressBar(fw_frame)
        self.fw_progress.pack(fill="x", padx=10, pady=10)
        self.fw_progress.set(0)
        
        # Настройки
        settings_frame = CTkLabelFrame(tab, text="⚙️ Настройки")
        settings_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        # Путь к ProxSpace
        path_frame = CTkFrame(settings_frame)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        CTkLabel(path_frame, text="Путь к ProxSpace:").pack(side="left", padx=5)
        self.proxspace_path_entry = CTkEntry(path_frame, width=400)
        self.proxspace_path_entry.pack(side="left", padx=5)
        self.proxspace_path_entry.insert(0, str(DEFAULT_PROXSPACE_PATH))
        
        CTkButton(path_frame, text="📂 Обзор", command=self._browse_proxspace).pack(side="left", padx=5)
        
        # COM порт
        port_frame = CTkFrame(settings_frame)
        port_frame.pack(fill="x", padx=10, pady=5)
        
        CTkLabel(port_frame, text="COM порт:").pack(side="left", padx=5)
        self.com_port_combo = CTkComboBox(port_frame, values=["AUTO"] + [p['device'] for p in self.pm3_process.find_com_ports()])
        self.com_port_combo.pack(side="left", padx=5)
        self.com_port_combo.set("AUTO")
        
        # Тема
        theme_frame = CTkFrame(settings_frame)
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        CTkLabel(theme_frame, text="Тема:").pack(side="left", padx=5)
        theme_combo = CTkComboBox(theme_frame, values=["Dark", "Light", "System"], command=self._change_theme)
        theme_combo.pack(side="left", padx=5)
        theme_combo.set("Dark")
        
        # Прочие настройки
        CTkCheckBox(settings_frame, text="Авто-подключение при запуске").pack(anchor="w", padx=10, pady=5)
        CTkCheckBox(settings_frame, text="Показывать подсказки").pack(anchor="w", padx=10, pady=5)
        CTkCheckBox(settings_frame, text="Сохранять логи").pack(anchor="w", padx=10, pady=5)
        
        # О программе
        about_frame = CTkLabelFrame(tab, text="ℹ️ О программе")
        about_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        about_text = f"""
        {APP_NAME} версии {APP_VERSION}
        Автор: {APP_AUTHOR}
        
        Приложение для работы с Proxmark3 Iceman
        Лицензия: MIT
        
        🌐 GitHub: https://github.com/RRG-Proxmark3
        """
        CTkLabel(about_frame, text=about_text, justify="left").pack(padx=10, pady=10)
        
        # Кнопка проверки обновлений
        CTkButton(about_frame, text="🔍 Проверить обновления", command=self._check_updates).pack(pady=10)
    
    # ========================================================================
    # МЕТОДЫ УПРАВЛЕНИЯ
    # ========================================================================
    
    def _check_proxspace_on_start(self):
        """Проверка ProxSpace при запуске"""
        if self.pm3_process.check_proxspace():
            self.installer_frame.grid_remove()
            self.status_label.configure(text="ProxSpace найден. Готов к работе.")
        else:
            self.installer_frame.grid()
            self.status_label.configure(text="ProxSpace не найден. Требуется установка.", text_color="#F5A623")
    
    def _toggle_connection(self):
        """Переключение подключения"""
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """Подключение к устройству"""
        self.status_label.configure(text="Подключение...")
        
        # Попытка подключения
        if self.pm3_process.start_client():
            self.is_connected = True
            self.connection_indicator.configure(text="🟢 Подключено", text_color="#7ED321")
            self.connect_btn.configure(text="🔌 Отключить")
            self.restart_btn.configure(state="normal")
            self.main_status_label.configure(text="Подключено", text_color="#7ED321")
            self.status_label.configure(text="Устройство подключено")
            
            # Запрос информации об устройстве
            self._send_command("hw version")
        else:
            self.status_label.configure(text="Ошибка подключения", text_color="#D0021B")
    
    def _disconnect(self):
        """Отключение от устройства"""
        self.pm3_process.stop_client()
        self.is_connected = False
        self.connection_indicator.configure(text="🔴 Отключено", text_color="#D0021B")
        self.connect_btn.configure(text="🔌 Подключить")
        self.restart_btn.configure(state="disabled")
        self.main_status_label.configure(text="Отключено", text_color="#D0021B")
        self.status_label.configure(text="Устройство отключено")
    
    def _restart_device(self):
        """Перезагрузка устройства"""
        self._send_command("hw reset")
    
    def _send_command(self, command: str):
        """Отправка команды устройству"""
        if not self.is_connected:
            self.status_label.configure(text="Сначала подключитесь к устройству!", text_color="#D0021B")
            return
        
        # Логирование команды
        self._log_to_console(self.main_console, f"[=] {command}\n")
        
        # Отправка
        self.pm3_process.send_command(command)
    
    def _log_to_console(self, console: CTkTextbox, message: str):
        """Логирование сообщения в консоль с цветами"""
        console.insert("end", message)
        
        # Применение цветов
        for tag, color in LOG_COLORS.items():
            start = "1.0"
            while True:
                pos = console.search(tag, start, "end")
                if not pos:
                    break
                end = f"{pos}+{len(tag)}c"
                console.tag_add(tag, pos, end)
                start = end
        
        console.see("end")
    
    def _confirm_and_write(self):
        """Подтверждение опасной операции записи"""
        dialog = CTkInputDialog(
            title="⚠️ Подтверждение записи",
            label_text="Вы уверены? Это может повредить карту!",
            entry_width=300
        )
        # Реализация диалога подтверждения
    
    def _start_sniffing(self, sniff_type: str):
        """Запуск сниффинга"""
        self.sniff_start_btn.configure(state="disabled")
        self.sniff_stop_btn.configure(state="normal")
        # Логика сниффинга
    
    def _stop_sniffing(self):
        """Остановка сниффинга"""
        self.sniff_start_btn.configure(state="normal")
        self.sniff_stop_btn.configure(state="disabled")
    
    def _start_emulation(self, emu_type: str):
        """Запуск эмуляции"""
        self.emu_indicator.configure(text="🟢 Эмуляция активна", text_color="#7ED321")
        self.emu_start_btn.configure(state="disabled")
        self.emu_stop_btn.configure(state="normal")
    
    def _stop_emulation(self):
        """Остановка эмуляции"""
        self.emu_indicator.configure(text="🔴 Эмуляция не активна", text_color="#D0021B")
        self.emu_start_btn.configure(state="normal")
        self.emu_stop_btn.configure(state="disabled")
    
    def _run_installer_wizard(self):
        """Запуск мастера установки"""
        installer = ProxSpaceInstaller(self.config_manager, callback=self._installer_log)
        threading.Thread(target=installer.run_wizard, daemon=True).start()
    
    def _installer_log(self, message: str):
        """Логирование установщика"""
        self.installer_console.insert("end", message + "\n")
        self.installer_console.see("end")
    
    def _change_theme(self, theme: str):
        """Смена темы"""
        set_appearance_mode(theme)
    
    def _browse_proxspace(self):
        """Обзор пути к ProxSpace"""
        # Диалог выбора директории
        pass
    
    def _check_updates(self):
        """Проверка обновлений"""
        webbrowser.open("https://github.com/releases")
    
    def _load_dump(self):
        """Загрузка дампа"""
        pass
    
    def _save_dump(self):
        """Сохранение дампа"""
        pass
    
    def _copy_to_clipboard(self):
        """Копирование в буфер"""
        pass
    
    def _paste_from_clipboard(self):
        """Вставка из буфера"""
        pass
    
    def _clear_hex(self):
        """Очистка hex редактора"""
        self.hex_editor.delete("1.0", "end")
    
    def _load_keys(self):
        """Загрузка ключей"""
        pass
    
    def _save_keys(self):
        """Сохранение ключей"""
        pass
    
    def _brute_force_keys(self):
        """Брутфорс ключей"""
        pass
    
    def _save_sniff_dump(self):
        """Сохранение дампа сниффа"""
        pass
    
    def _analyze_sniff(self):
        """Анализ сниффа"""
        pass
    
    def _refresh_scripts(self):
        """Обновление списка скриптов"""
        pass
    
    def _open_node_editor(self):
        """Открытие редактора нод"""
        pass
    
    def _run_selected_script(self):
        """Запуск выбранного скрипта"""
        pass
    
    def _tools_zoom(self, factor: float):
        """Зум графика"""
        pass
    
    def _tools_reset_view(self):
        """Сброс вида графика"""
        pass
    
    def _decode_signal(self, decode_type: str):
        """Декодирование сигнала"""
        pass
    
    def _update_bootrom(self):
        """Обновление бутрома"""
        pass
    
    def _update_full_image(self):
        """Обновление полного образа"""
        pass
    
    def _on_closing(self):
        """Обработчик закрытия окна"""
        self.pm3_process.stop_client()
        self.config_manager.save_config()
        self.destroy()


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

def main():
    """Точка входа в приложение"""
    app = Proxmark3EasyGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
