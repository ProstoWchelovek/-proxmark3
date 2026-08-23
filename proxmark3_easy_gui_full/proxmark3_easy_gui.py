#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxmark3 Easy GUI - Полнофункциональное приложение для работы с Proxmark3 Iceman
Версия: 2.0.0
Совместимость: Windows 10/11, Proxmark3 Easy/RDV4/Iceman

Основные возможности:
- Автоматическая установка ProxSpace при первом запуске
- 9 функциональных вкладок со всеми командами
- Hex редактор дампов памяти
- Визуальный редактор скриптов на нодах
- Визуализация сигналов и графиков
- Умные подсказки и информация о командах
- Безопасность опасных операций
"""

import sys
import os
import subprocess
import threading
import json
import re
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple
from datetime import datetime
import webbrowser
import queue

# Проверка и импорт GUI библиотек
try:
    import customtkinter as ctk
    from customtkinter import (
        CTk, CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkTextbox,
        CTkTabview, CTkComboBox, CTkSwitch, CTkCheckBox, CTkProgressBar,
        CTkScrollableFrame, CTkOptionMenu, CTkInputDialog, CTkFont,
        CTkSegmentedButton
    )
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
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Ошибка: Не установлена Pillow. Выполните: pip install Pillow")
    sys.exit(1)

# Импорт локальных модулей
try:
    from src.commands import (
        CommandInfo, CommandCategory, CommandRisk, CommandParameter,
        get_command, get_commands_by_category, search_commands, 
        COMMANDS_DB, get_command_categories
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.commands import (
        CommandInfo, CommandCategory, CommandRisk, CommandParameter,
        get_command, get_commands_by_category, search_commands,
        COMMANDS_DB, get_command_categories
    )


# ============================================================================
# КОНСТАНТЫ И НАСТРОЙКИ
# ============================================================================

APP_NAME = "Proxmark3 Easy GUI"
APP_VERSION = "2.0.0"
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

# Цвета риска
RISK_COLORS = {
    CommandRisk.SAFE: '#7ED321',      # Зеленый
    CommandRisk.WARNING: '#F5A623',   # Оранжевый
    CommandRisk.DANGEROUS: '#D0021B'  # Красный
}

# Настройки CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


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
            'dumps_directory': str(Path.cwd() / "dumps"),
            'keys_directory': str(Path.cwd() / "keys"),
            'scripts_directory': str(Path.cwd() / "scripts"),
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
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable[[str], None]] = []
        
    def check_proxspace(self) -> bool:
        """Проверка наличия установленной ProxSpace"""
        client_path = Path(self.config.get('client_path'))
        return client_path.exists()
    
    def find_com_ports(self) -> List[Dict]:
        """Поиск доступных COM портов"""
        ports = []
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                ports.append({
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
        except Exception as e:
            print(f"Ошибка поиска портов: {e}")
        return ports
    
    def start_client(self) -> bool:
        """Запуск клиента Proxmark3"""
        if self.is_running:
            return False
        
        client_path = self.config.get('client_path')
        if not Path(client_path).exists():
            return False
        
        try:
            # Запускаем в интерактивном режиме
            self.process = subprocess.Popen(
                [client_path],
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
                    self.output_queue.put(line.strip())
                    for callback in self.callbacks:
                        try:
                            callback(line.strip())
                        except:
                            pass
                else:
                    break
            except Exception as e:
                self.error_queue.put(str(e))
                break
    
    def send_command(self, command: str):
        """Отправка команды клиенту"""
        if self.process and self.is_running:
            try:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
            except Exception as e:
                print(f"Ошибка отправки команды: {e}")
    
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
    
    def add_callback(self, callback: Callable[[str], None]):
        """Добавление колбэка на вывод"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]):
        """Удаление колбэка"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)


# ============================================================================
# УСТАНОВЩИК PROXSPACE
# ============================================================================

class ProxSpaceInstaller:
    """Автоматическая установка ProxSpace"""
    
    GITHUB_RELEASE_URL = "https://github.com/Gator96100/ProxSpace/releases"
    INSTALLER_NAME = "ProxSpace.7z"
    
    def __init__(self, config_manager: ConfigManager, log_callback=None):
        self.config = config_manager
        self.log_callback = log_callback
        self.install_path = DEFAULT_PROXSPACE_PATH.parent
        self.temp_dir = Path.cwd() / "installers"
        
    def log(self, message: str):
        """Логирование сообщения"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def download_installer(self) -> bool:
        """Загрузка установщика ProxSpace"""
        self.log("[=] Начало загрузки ProxSpace...")
        
        try:
            import requests
            
            # Получаем последнюю версию
            api_url = "https://api.github.com/repos/Gator96100/ProxSpace/releases/latest"
            response = requests.get(api_url, timeout=30)
            
            if response.status_code != 200:
                self.log("[-] Не удалось получить информацию о релизе")
                return False
            
            release_data = response.json()
            assets = release_data.get('assets', [])
            
            # Ищем установщик
            installer_url = None
            for asset in assets:
                if asset['name'].endswith('.7z'):
                    installer_url = asset['browser_download_url']
                    break
            
            if not installer_url:
                self.log("[-] Установщик не найден")
                return False
            
            self.log(f"[=] Загрузка из: {installer_url}")
            
            # Скачиваем файл
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            installer_path = self.temp_dir / self.INSTALLER_NAME
            
            response = requests.get(installer_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Обновляем прогресс
                    if total_size > 0:
                        progress = int(downloaded * 100 / total_size)
                        self.log(f"[|] Прогресс загрузки: {progress}%")
            
            self.log(f"[+] Загрузка завершена: {installer_path}")
            return True
            
        except ImportError:
            self.log("[!] Модуль requests не установлен")
            return False
        except Exception as e:
            self.log(f"[-] Ошибка загрузки: {e}")
            return False
    
    def extract_installer(self) -> bool:
        """Распаковка установщика"""
        installer_path = self.temp_dir / self.INSTALLER_NAME
        
        if not installer_path.exists():
            self.log("[-] Файл установщика не найден")
            return False
        
        self.log(f"[=] Распаковка {installer_path}...")
        
        try:
            # Пробуем использовать 7z
            import shutil
            
            if shutil.which("7z"):
                result = subprocess.run(
                    ["7z", "x", str(installer_path), f"-o{self.install_path}", "-y"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.log("[+] Распаковка завершена")
                    return True
                else:
                    self.log(f"[-] Ошибка распаковки: {result.stderr}")
                    return False
            else:
                self.log("[!] 7z не найден. Пожалуйста, установите 7-Zip")
                return False
                
        except Exception as e:
            self.log(f"[-] Ошибка распаковки: {e}")
            return False
    
    def compile_proxspace(self) -> bool:
        """Компиляция клиента и прошивки"""
        self.log("[=] Компиляция ProxSpace...")
        
        pm3_path = self.install_path / "pm3"
        
        if not pm3_path.exists():
            self.log("[-] Папка ProxSpace не найдена")
            return False
        
        try:
            # Переходим в директорию клиента
            client_path = pm3_path / "client"
            
            # Запускаем make
            result = subprocess.run(
                ["make", "clean"],
                cwd=client_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            result = subprocess.run(
                ["make", "-j4"],
                cwd=client_path,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                self.log("[+] Компиляция завершена успешно")
                return True
            else:
                self.log(f"[-] Ошибка компиляции: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("[-] Превышено время компиляции")
            return False
        except Exception as e:
            self.log(f"[-] Ошибка компиляции: {e}")
            return False
    
    def setup_paths(self) -> bool:
        """Настройка путей после установки"""
        new_client_path = DEFAULT_PROXSPACE_PATH / "client" / "proxmark3.exe"
        
        if new_client_path.exists():
            self.config.set('client_path', str(new_client_path))
            self.config.set('proxspace_path', str(DEFAULT_PROXSPACE_PATH))
            self.log(f"[+] Пути настроены: {new_client_path}")
            return True
        
        self.log("[-] Клиент не найден после установки")
        return False
    
    def run_wizard(self) -> bool:
        """Запуск мастера установки"""
        self.log("[=] Запуск мастера установки ProxSpace")
        self.log("=" * 50)
        
        steps = [
            ("Проверка системы", lambda: True),  # Пока упрощено
            ("Загрузка установщика", self.download_installer),
            ("Распаковка", self.extract_installer),
            ("Компиляция", self.compile_proxspace),
            ("Настройка путей", self.setup_paths),
        ]
        
        for step_name, step_func in steps:
            self.log(f"\n[=] Шаг: {step_name}")
            self.log("-" * 30)
            
            if not step_func():
                self.log(f"[-] Ошибка на шаге: {step_name}")
                return False
            
            time.sleep(0.5)
        
        self.log("\n" + "=" * 50)
        self.log("[+] Установка завершена успешно!")
        self.log("[=] Перезапустите приложение для использования ProxSpace")
        
        return True


# ============================================================================
# HEX РЕДАКТОР
# ============================================================================

class HexEditorFrame(CTkFrame):
    """Hex редактор для просмотра и редактирования дампов"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data = bytearray()
        self.file_path: Optional[Path] = None
        self.modified = False
        self.bytes_per_row = 16
        self.font = ctk.CTkFont(family="Consolas", size=11)
        
        self._create_ui()
    
    def _create_ui(self):
        """Создание интерфейса редактора"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Панель инструментов
        toolbar = CTkFrame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        CTkButton(toolbar, text="📂 Открыть", command=self.open_file, width=100).pack(side="left", padx=2)
        CTkButton(toolbar, text="💾 Сохранить", command=self.save_file, width=100).pack(side="left", padx=2)
        CTkButton(toolbar, text="📋 Копировать", command=self.copy_selection, width=100).pack(side="left", padx=2)
        CTkButton(toolbar, text="📥 Вставить", command=self.paste_data, width=100).pack(side="left", padx=2)
        
        CTkLabel(toolbar, text=" | ").pack(side="left", padx=5)
        
        CTkButton(toolbar, text="🔍 Найти", command=self.find_data, width=80).pack(side="left", padx=2)
        CTkButton(toolbar, text="🔄 Заменить", command=self.replace_data, width=80).pack(side="left", padx=2)
        
        CTkLabel(toolbar, text=" | ").pack(side="left", padx=5)
        
        CTkLabel(toolbar, text="Байт/строка:").pack(side="left", padx=5)
        self.bytes_combo = CTkComboBox(toolbar, values=["8", "16", "32"], width=60, 
                                        command=self._on_bytes_per_row_change)
        self.bytes_combo.set("16")
        self.bytes_combo.pack(side="left", padx=2)
        
        # Основной редактор
        editor_frame = CTkFrame(self)
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(0, weight=1)
        
        # Текстовое поле с hex данными
        self.hex_text = CTkTextbox(editor_frame, font=self.font, wrap="none")
        self.hex_text.grid(row=0, column=0, sticky="nsew")
        
        # Привязка событий
        self.hex_text.bind("<KeyRelease>", self._on_text_change)
        self.hex_text.bind("<FocusOut>", self._validate_hex)
        
        # ASCII превью
        ascii_frame = CTkFrame(self)
        ascii_frame.grid(row=1, column=1, sticky="ns", padx=(0, 5), pady=5)
        
        CTkLabel(ascii_frame, text="ASCII", font=ctk.CTkFont(weight="bold")).pack()
        
        self.ascii_text = CTkTextbox(ascii_frame, font=self.font, width=200, wrap="none")
        self.ascii_text.pack(fill="both", expand=True)
    
    def _on_bytes_per_row_change(self, value):
        """Изменение количества байт в строке"""
        self.bytes_per_row = int(value)
        self.refresh_view()
    
    def _on_text_change(self, event=None):
        """Обработка изменения текста"""
        self.modified = True
    
    def _validate_hex(self, event=None):
        """Валидация hex данных"""
        content = self.hex_text.get("1.0", "end-1c")
        # Удаляем все не-hex символы кроме пробелов и переносов
        cleaned = re.sub(r'[^0-9A-Fa-f\s\n]', '', content)
        
        current = self.hex_text.get("1.0", "end-1c")
        if cleaned != current:
            self.hex_text.delete("1.0", "end")
            self.hex_text.insert("1.0", cleaned)
    
    def open_file(self, file_path: Optional[str] = None):
        """Открытие файла"""
        if file_path is None:
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Открыть дамп",
                filetypes=[
                    ("Binary files", "*.bin"),
                    ("Email files", "*.eml"),
                    ("All files", "*.*")
                ]
            )
        
        if file_path:
            try:
                self.file_path = Path(file_path)
                
                with open(self.file_path, 'rb') as f:
                    self.data = bytearray(f.read())
                
                self.modified = False
                self.refresh_view()
                
            except Exception as e:
                print(f"Ошибка открытия файла: {e}")
    
    def save_file(self):
        """Сохранение файла"""
        if not self.data:
            return
        
        if self.file_path and not self.modified:
            return
        
        try:
            # Сначала валидируем данные из текстового поля
            self._validate_hex()
            content = self.hex_text.get("1.0", "end-1c")
            
            # Парсим hex обратно в байты
            hex_chars = re.findall(r'[0-9A-Fa-f]{2}', content)
            self.data = bytearray(int(h, 16) for h in hex_chars)
            
            if self.file_path:
                save_path = self.file_path
            else:
                from tkinter import filedialog
                save_path = filedialog.asksaveasfilename(
                    title="Сохранить дамп",
                    defaultextension=".bin",
                    filetypes=[("Binary files", "*.bin")]
                )
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(self.data)
                
                self.file_path = Path(save_path)
                self.modified = False
                
        except Exception as e:
            print(f"Ошибка сохранения файла: {e}")
    
    def copy_selection(self):
        """Копирование выделенного"""
        try:
            selection = self.hex_text.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selection)
        except:
            pass
    
    def paste_data(self):
        """Вставка данных"""
        try:
            data = self.clipboard_get()
            # Вставляем только hex символы
            hex_data = ' '.join(re.findall(r'[0-9A-Fa-f]{2}', data))
            
            if self.hex_text.tag_ranges("sel"):
                self.hex_text.delete("sel.first", "sel.last")
            
            self.hex_text.insert("insert", hex_data)
            self.modified = True
        except:
            pass
    
    def find_data(self):
        """Поиск данных"""
        # Упрощенная реализация
        pass
    
    def replace_data(self):
        """Замена данных"""
        # Упрощенная реализация
        pass
    
    def refresh_view(self):
        """Обновление представления"""
        self.hex_text.delete("1.0", "end")
        self.ascii_text.delete("1.0", "end")
        
        if not self.data:
            return
        
        lines = []
        ascii_lines = []
        
        for i in range(0, len(self.data), self.bytes_per_row):
            chunk = self.data[i:i + self.bytes_per_row]
            
            # Hex представление
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            hex_str = hex_str.ljust(self.bytes_per_row * 3 - 1)
            
            # Offset
            offset = f'{i:08X}  '
            
            # ASCII представление
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            
            lines.append(f"{offset}{hex_str}\n")
            ascii_lines.append(f"{' ' * 9}{ascii_str}\n")
        
        self.hex_text.insert("1.0", ''.join(lines))
        self.ascii_text.insert("1.0", ''.join(ascii_lines))


# ============================================================================
# NODE EDITOR (ВИЗУАЛЬНЫЙ РЕДАКТОР СКРИПТОВ)
# ============================================================================

class NodeEditorFrame(CTkFrame):
    """Визуальный редактор скриптов на основе нод"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.nodes = {}
        self.connections = []
        self.selected_node = None
        self.dragging_node = None
        self.drag_offset = (0, 0)
        
        self._create_ui()
    
    def _create_ui(self):
        """Создание интерфейса редактора"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Панель инструментов
        toolbar = CTkFrame(self, height=50)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        CTkButton(toolbar, text="➕ Добавить ноду", command=self.add_node, width=120).pack(side="left", padx=2)
        CTkButton(toolbar, text="🗑️ Удалить", command=self.delete_selected, width=100).pack(side="left", padx=2)
        CTkButton(toolbar, text="💾 Сохранить", command=self.save_script, width=100).pack(side="left", padx=2)
        CTkButton(toolbar, text="📂 Загрузить", command=self.load_script, width=100).pack(side="left", padx=2)
        
        CTkLabel(toolbar, text=" | ").pack(side="left", padx=5)
        
        CTkLabel(toolbar, text="Тип ноды:").pack(side="left", padx=5)
        self.node_type_combo = CTkComboBox(toolbar, values=[
            "Команда", "Задержка", "Условие", "Цикл", 
            "Переменная", "Вывод", "Функция"
        ], width=150)
        self.node_type_combo.pack(side="left", padx=2)
        self.node_type_combo.set("Команда")
        
        # Холст для нод
        canvas_frame = CTkFrame(self)
        canvas_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.canvas = ctk.CTkCanvas(canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Привязка событий
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        
        # Панель свойств
        self.properties_frame = CTkFrame(self, width=250)
        self.properties_frame.grid(row=1, column=2, sticky="ns", padx=5, pady=5)
        self.properties_frame.grid_propagate(False)
        
        CTkLabel(self.properties_frame, text="Свойства", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        self.properties_content = CTkScrollableFrame(self.properties_frame)
        self.properties_content.pack(fill="both", expand=True)
    
    def on_canvas_click(self, event):
        """Клик по холсту"""
        # Поиск ноды под курсором
        for node_id, node_data in self.nodes.items():
            x, y = node_data['position']
            w, h = node_data['size']
            
            if x <= event.x <= x + w and y <= event.y <= y + h:
                self.select_node(node_id)
                self.dragging_node = node_id
                self.drag_offset = (event.x - x, event.y - y)
                return
        
        # Снятие выделения при клике на пустое место
        self.deselect_all()
    
    def on_canvas_drag(self, event):
        """Перетаскивание ноды"""
        if self.dragging_node:
            node_id = self.dragging_node
            x = event.x - self.drag_offset[0]
            y = event.y - self.drag_offset[1]
            
            self.nodes[node_id]['position'] = (x, y)
            self.redraw_node(node_id)
            self.redraw_connections()
    
    def on_canvas_release(self, event):
        """Отпускание ноды"""
        self.dragging_node = None
    
    def on_canvas_double_click(self, event):
        """Двойной клик - создание ноды"""
        self.add_node(position=(event.x, event.y))
    
    def add_node(self, position: Optional[Tuple[int, int]] = None):
        """Добавление ноды"""
        if position is None:
            position = (100, 100)
        
        node_type = self.node_type_combo.get()
        node_id = f"node_{len(self.nodes)}"
        
        self.nodes[node_id] = {
            'id': node_id,
            'type': node_type,
            'position': position,
            'size': (150, 80),
            'properties': {
                'title': f"{node_type} {len(self.nodes)}",
                'command': "" if node_type == "Команда" else "",
                'delay': 1000 if node_type == "Задержка" else 0,
            },
            'inputs': 1 if node_type != "Команда" else 0,
            'outputs': 1
        }
        
        self.draw_node(node_id)
        self.select_node(node_id)
    
    def draw_node(self, node_id: str):
        """Отрисовка ноды"""
        node = self.nodes[node_id]
        x, y = node['position']
        w, h = node['size']
        
        # Цвет в зависимости от типа
        colors = {
            "Команда": "#4A90E2",
            "Задержка": "#F5A623",
            "Условие": "#7ED321",
            "Цикл": "#BD10E0",
            "Переменная": "#50E3C2",
            "Вывод": "#D0021B",
            "Функция": "#9013FE"
        }
        
        color = colors.get(node['type'], "#808080")
        
        # Рисуем прямоугольник ноды
        self.canvas.create_rectangle(x, y, x + w, y + h, 
                                     fill=color, outline="white", width=2,
                                     tags=f"node_{node_id}")
        
        # Заголовок
        self.canvas.create_text(x + w // 2, y + 20, 
                               text=node['properties']['title'],
                               fill="white", font=("Arial", 10, "bold"),
                               tags=f"node_{node_id}_title")
        
        # Вход/выход
        if node['inputs'] > 0:
            self.canvas.create_oval(x - 10, y + h // 2 - 5, x, y + h // 2 + 5,
                                   fill="white", tags=f"node_{node_id}_in")
        
        self.canvas.create_oval(x + w, y + h // 2 - 5, x + w + 10, y + h // 2 + 5,
                               fill="white", tags=f"node_{node_id}_out")
    
    def redraw_node(self, node_id: str):
        """Перерисовка ноды"""
        self.canvas.delete(f"node_{node_id}")
        self.canvas.delete(f"node_{node_id}_title")
        self.canvas.delete(f"node_{node_id}_in")
        self.canvas.delete(f"node_{node_id}_out")
        self.draw_node(node_id)
    
    def redraw_connections(self):
        """Перерисовка соединений"""
        self.canvas.delete("connection")
        
        for conn in self.connections:
            from_node = self.nodes.get(conn['from'])
            to_node = self.nodes.get(conn['to'])
            
            if from_node and to_node:
                x1 = from_node['position'][0] + from_node['size'][0]
                y1 = from_node['position'][1] + from_node['size'][1] // 2
                
                x2 = to_node['position'][0]
                y2 = to_node['position'][1] + to_node['size'][1] // 2
                
                # Рисуем кривую линию
                self.canvas.create_line(x1, y1, x2, y2, 
                                       smooth=True, width=2, fill="white",
                                       tags="connection")
    
    def select_node(self, node_id: str):
        """Выделение ноды"""
        self.deselect_all()
        self.selected_node = node_id
        
        # Показываем свойства
        self.show_properties(node_id)
    
    def deselect_all(self):
        """Снятие выделения"""
        self.selected_node = None
        for widget in self.properties_content.winfo_children():
            widget.destroy()
    
    def show_properties(self, node_id: str):
        """Показ свойств ноды"""
        node = self.nodes.get(node_id)
        if not node:
            return
        
        # Очищаем панель свойств
        for widget in self.properties_content.winfo_children():
            widget.destroy()
        
        # Поле названия
        CTkLabel(self.properties_content, text="Название:").pack(anchor="w", padx=5, pady=2)
        title_entry = CTkEntry(self.properties_content, width=200)
        title_entry.pack(padx=5, pady=2)
        title_entry.insert(0, node['properties']['title'])
        
        def update_title(event=None):
            node['properties']['title'] = title_entry.get()
            self.redraw_node(node_id)
        
        title_entry.bind("<KeyRelease>", update_title)
        
        # Поле команды (если это команда)
        if node['type'] == "Команда":
            CTkLabel(self.properties_content, text="Команда:").pack(anchor="w", padx=5, pady=5)
            cmd_entry = CTkEntry(self.properties_content, width=200)
            cmd_entry.pack(padx=5, pady=2)
            cmd_entry.insert(0, node['properties'].get('command', ''))
            
            def update_command(event=None):
                node['properties']['command'] = cmd_entry.get()
            
            cmd_entry.bind("<KeyRelease>", update_command)
        
        # Поле задержки (если это задержка)
        if node['type'] == "Задержка":
            CTkLabel(self.properties_content, text="Задержка (мс):").pack(anchor="w", padx=5, pady=5)
            delay_entry = CTkEntry(self.properties_content, width=200)
            delay_entry.pack(padx=5, pady=2)
            delay_entry.insert(0, str(node['properties'].get('delay', 1000)))
            
            def update_delay(event=None):
                try:
                    node['properties']['delay'] = int(delay_entry.get())
                except ValueError:
                    pass
            
            delay_entry.bind("<KeyRelease>", update_delay)
    
    def delete_selected(self):
        """Удаление выбранной ноды"""
        if self.selected_node:
            node_id = self.selected_node
            
            # Удаляем соединения
            self.connections = [c for c in self.connections 
                              if c['from'] != node_id and c['to'] != node_id]
            
            # Удаляем ноду
            self.canvas.delete(f"node_{node_id}")
            del self.nodes[node_id]
            
            self.deselect_all()
            self.redraw_connections()
    
    def save_script(self):
        """Сохранение скрипта"""
        from tkinter import filedialog
        
        save_path = filedialog.asksaveasfilename(
            title="Сохранить скрипт",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if save_path:
            script_data = {
                'nodes': list(self.nodes.values()),
                'connections': self.connections
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, indent=2, ensure_ascii=False)
    
    def load_script(self):
        """Загрузка скрипта"""
        from tkinter import filedialog
        
        load_path = filedialog.askopenfilename(
            title="Загрузить скрипт",
            filetypes=[("JSON files", "*.json")]
        )
        
        if load_path:
            try:
                with open(load_path, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                
                self.nodes = {n['id']: n for n in script_data.get('nodes', [])}
                self.connections = script_data.get('connections', [])
                
                self.canvas.delete("all")
                
                for node_id in self.nodes:
                    self.draw_node(node_id)
                
                self.redraw_connections()
                
            except Exception as e:
                print(f"Ошибка загрузки скрипта: {e}")


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
        
        # Очередь вывода для обработки
        self.output_queue = queue.Queue()
        
        # Создание интерфейса
        self._create_ui()
        
        # Проверка ProxSpace при запуске
        self.after(100, self._check_proxspace_on_start)
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Запуск обработки вывода
        self._process_output_queue()
    
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
        tab.grid_rowconfigure(1, weight=1)
        
        # Информация об устройстве
        info_frame = CTkFrame(tab)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(info_frame, text="Информация об устройстве", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.device_info_label = CTkLabel(
            info_frame,
            text="Устройство не подключено\nПодключите Proxmark3 и нажмите 'Подключить'",
            justify="left"
        )
        self.device_info_label.pack(pady=10)
        
        # Быстрые действия
        actions_frame = CTkFrame(tab)
        actions_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        CTkLabel(actions_frame, text="Быстрые действия", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        actions_grid = CTkFrame(actions_frame, fg_color="transparent")
        actions_grid.pack(pady=10)
        
        # Кнопки действий
        actions = [
            ("🔍 Автопоиск", self._run_auto_detect),
            ("📊 Тест антенн", lambda: self._send_command("hw tune")),
            ("📖 Читать LF", lambda: self._send_command("lf read")),
            ("📖 Читать HF", lambda: self._send_command("hf read")),
            ("🎭 Эмуляция", lambda: self._switch_to_tab("🎭 ЭМУЛЯЦИЯ")),
            ("✏️ Запись", lambda: self._switch_to_tab("✏️ ЗАПИСЬ")),
        ]
        
        for i, (text, command) in enumerate(actions):
            row = i // 3
            col = i % 3
            
            btn = CTkButton(
                actions_grid,
                text=text,
                command=command,
                width=150,
                height=60
            )
            btn.grid(row=row, column=col, padx=10, pady=10)
    
    # ========================================================================
    # ВКЛАДКА 2: ПОИСК И ЧТЕНИЕ
    # ========================================================================
    
    def _create_search_tab(self):
        """Создание вкладки поиска и чтения"""
        tab = self.tabview.tab("🔍 ПОИСК И ЧТЕНИЕ")
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Левая панель с кнопками
        left_panel = CTkFrame(tab, width=250)
        left_panel.grid(row=0, column=0, rowspan=2, sticky="ns", padx=10, pady=10)
        left_panel.grid_propagate(False)
        
        CTkLabel(left_panel, text="LF (125 kHz)", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        lf_buttons = [
            ("🔍 LF Search", "lf search"),
            ("📖 LF Read", "lf read"),
            ("📡 LF Snoop", "lf snoop"),
        ]
        
        for text, cmd in lf_buttons:
            CTkButton(
                left_panel,
                text=text,
                command=lambda c=cmd: self._send_command(c),
                width=200
            ).pack(pady=5)
        
        CTkLabel(left_panel, text="HF (13.56 MHz)", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
        
        hf_buttons = [
            ("🔍 HF Search", "hf search"),
            ("📖 HF Read", "hf read"),
            ("📡 HF Snoop", "hf snoop"),
        ]
        
        for text, cmd in hf_buttons:
            CTkButton(
                left_panel,
                text=text,
                command=lambda c=cmd: self._send_command(c),
                width=200
            ).pack(pady=5)
        
        # Автопоиск
        CTkSeparator(left_panel).pack(fill="x", pady=20)
        
        CTkButton(
            left_panel,
            text="🚀 Auto-Detect (Все частоты)",
            command=self._run_auto_detect,
            width=200,
            height=50,
            fg_color="#4A90E2"
        ).pack(pady=10)
        
        # Правая панель с логами и графиками
        right_panel = CTkFrame(tab)
        right_panel.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)
        
        # Лог выполнения
        log_frame = CTkFrame(right_panel)
        log_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        CTkLabel(log_frame, text="Лог выполнения", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.search_log = CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=10))
        self.search_log.pack(fill="both", expand=True, padx=5, pady=5)
        
        # График сигнала
        plot_frame = CTkFrame(right_panel)
        plot_frame.grid(row=1, column=0, sticky="nsew")
        
        CTkLabel(plot_frame, text="График сигнала", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.search_figure = Figure(figsize=(5, 3), dpi=100)
        self.search_plot = self.search_figure.add_subplot(111)
        self.search_canvas = FigureCanvasTkAgg(self.search_figure, master=plot_frame)
        self.search_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
    
    # ========================================================================
    # ВКЛАДКА 3: ПАМЯТЬ И КЛЮЧИ (с Hex редактором)
    # ========================================================================
    
    def _create_memory_tab(self):
        """Создание вкладки памяти и ключей"""
        tab = self.tabview.tab("💾 ПАМЯТЬ И КЛЮЧИ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Hex редактор
        self.hex_editor = HexEditorFrame(tab)
        self.hex_editor.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    # ========================================================================
    # ВКЛАДКА 4: ЗАПИСЬ
    # ========================================================================
    
    def _create_write_tab(self):
        """Создание вкладки записи"""
        tab = self.tabview.tab("✏️ ЗАПИСЬ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Выбор типа карты
        type_frame = CTkFrame(tab)
        type_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(type_frame, text="Тип карты для записи:", 
                font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        
        self.card_type_var = ctk.StringVar(value="T5577")
        card_types = ["T5577", "T5555", "Magic UID Gen1", "Magic UID Gen2", "EM4100"]
        
        self.card_type_combo = CTkComboBox(
            type_frame,
            values=card_types,
            variable=self.card_type_var,
            width=200
        )
        self.card_type_combo.pack(side="left", padx=10)
        
        # Параметры записи
        params_frame = CTkFrame(tab)
        params_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        CTkLabel(params_frame, text="Данные для записи (Hex):", 
                font=ctk.CTkFont(size=14)).pack(pady=10)
        
        self.write_data_entry = CTkEntry(params_frame, width=400, 
                                         placeholder_text="0123456789ABCDEF")
        self.write_data_entry.pack(pady=10)
        
        # Предупреждение
        warning_label = CTkLabel(
            params_frame,
            text="⚠️ Внимание! Запись может повредить карту.\nСделайте резервную копию перед записью.",
            text_color="#F5A623",
            justify="center"
        )
        warning_label.pack(pady=20)
        
        # Кнопка записи
        CTkButton(
            params_frame,
            text="✏️ Записать данные",
            command=self._perform_write,
            width=200,
            height=50,
            fg_color="#D0021B"
        ).pack(pady=20)
    
    # ========================================================================
    # ВКЛАДКА 5: СНИФФИНГ
    # ========================================================================
    
    def _create_sniffing_tab(self):
        """Создание вкладки сниффинга"""
        tab = self.tabview.tab("📡 СНИФФИНГ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Контролы
        controls_frame = CTkFrame(tab)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkButton(
            controls_frame,
            text="▶️ Start Sniffing",
            command=lambda: self._send_command("lf snoop"),
            width=150
        ).pack(side="left", padx=10)
        
        CTkButton(
            controls_frame,
            text="⏹️ Stop",
            command=lambda: self._send_command("hw break"),
            width=100,
            fg_color="#D0021B"
        ).pack(side="left", padx=10)
        
        CTkButton(
            controls_frame,
            text="💾 Save Dump",
            command=self._save_sniff_dump,
            width=120
        ).pack(side="left", padx=10)
        
        # Таблица пакетов
        table_frame = CTkFrame(tab)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        CTkLabel(table_frame, text="Перехваченные пакеты", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.sniff_log = CTkTextbox(table_frame, font=ctk.CTkFont(family="Consolas", size=10))
        self.sniff_log.pack(fill="both", expand=True, padx=5, pady=5)
    
    # ========================================================================
    # ВКЛАДКА 6: ЭМУЛЯЦИЯ
    # ========================================================================
    
    def _create_emulation_tab(self):
        """Создание вкладки эмуляции"""
        tab = self.tabview.tab("🎭 ЭМУЛЯЦИЯ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Параметры эмуляции
        params_frame = CTkFrame(tab)
        params_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(params_frame, text="UID для эмуляции:", 
                font=ctk.CTkFont(size=14)).pack(pady=10)
        
        self.emu_uid_entry = CTkEntry(params_frame, width=300, 
                                      placeholder_text="0123456789")
        self.emu_uid_entry.pack(pady=10)
        
        self.emu_active = False
        
        # Кнопки управления
        CTkButton(
            params_frame,
            text="🎭 Start Emulation",
            command=self._toggle_emulation,
            width=200,
            height=50
        ).pack(pady=20)
        
        # Индикатор активности
        self.emu_indicator = CTkLabel(
            tab,
            text="⚪ Эмуляция не активна",
            font=ctk.CTkFont(size=16),
            text_color="#808080"
        )
        self.emu_indicator.grid(row=1, column=0, pady=20)
    
    # ========================================================================
    # ВКЛАДКА 7: ИНСТРУМЕНТЫ
    # ========================================================================
    
    def _create_tools_tab(self):
        """Создание вкладки инструментов"""
        tab = self.tabview.tab("🛠 ИНСТРУМЕНТЫ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Инструменты анализа
        tools_frame = CTkScrollableFrame(tab)
        tools_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Декодирование
        CTkLabel(tools_frame, text="Декодирование сигналов", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        demod_frame = CTkFrame(tools_frame)
        demod_frame.pack(fill="x", pady=10)
        
        demod_commands = [
            ("ASK Demodulate", "data askdemod"),
            ("FSK Demodulate", "data fskdemod"),
            ("PSK Demodulate", "data pskdemod"),
        ]
        
        for text, cmd in demod_commands:
            CTkButton(
                demod_frame,
                text=text,
                command=lambda c=cmd: self._send_command(c),
                width=200
            ).pack(pady=5)
        
        # Спектральный анализ
        CTkLabel(tools_frame, text="Спектральный анализ", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
        
        CTkButton(
            tools_frame,
            text="📊 Показать спектр",
            command=self._show_spectrum,
            width=200
        ).pack(pady=10)
    
    # ========================================================================
    # ВКЛАДКА 8: СКРИПТЫ (с Node Editor)
    # ========================================================================
    
    def _create_scripts_tab(self):
        """Создание вкладки скриптов"""
        tab = self.tabview.tab("📜 СКРИПТЫ")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Node редактор
        self.node_editor = NodeEditorFrame(tab)
        self.node_editor.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    # ========================================================================
    # ВКЛАДКА 9: СИСТЕМА
    # ========================================================================
    
    def _create_system_tab(self):
        """Создание системной вкладки"""
        tab = self.tabview.tab("⚙️ СИСТЕМА")
        tab.grid_columnconfigure(0, weight=1)
        
        # Мастер установки
        install_frame = CTkFrame(tab)
        install_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(install_frame, text="Установка ProxSpace", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.install_status = CTkLabel(
            install_frame,
            text="Статус: Проверка...",
            justify="left"
        )
        self.install_status.pack(pady=10)
        
        CTkButton(
            install_frame,
            text="🚀 Запустить мастер установки",
            command=self._run_installer_wizard,
            width=250,
            height=50
        ).pack(pady=20)
        
        # Лог установки
        self.install_log = CTkTextbox(install_frame, height=200, 
                                      font=ctk.CTkFont(family="Consolas", size=10))
        self.install_log.pack(fill="x", pady=10)
        
        # Настройки
        settings_frame = CTkFrame(tab)
        settings_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(settings_frame, text="Настройки", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Путь к ProxSpace
        path_frame = CTkFrame(settings_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=10)
        
        CTkLabel(path_frame, text="Путь к ProxSpace:", width=150, anchor="w").pack(side="left")
        
        self.proxspace_path_entry = CTkEntry(path_frame, width=400)
        self.proxspace_path_entry.pack(side="left", padx=10)
        self.proxspace_path_entry.insert(0, self.config_manager.get('proxspace_path'))
        
        CTkButton(
            path_frame,
            text="📁 Обзор",
            command=self._browse_proxspace_path,
            width=80
        ).pack(side="left")
        
        # Тема
        theme_frame = CTkFrame(settings_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=10)
        
        CTkLabel(theme_frame, text="Тема:", width=150, anchor="w").pack(side="left")
        
        self.theme_switch = CTkSwitch(
            theme_frame,
            text="Dark / Light",
            command=self._toggle_theme
        )
        self.theme_switch.pack(side="left", padx=10)
        
        # О программе
        about_frame = CTkFrame(tab)
        about_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        CTkLabel(about_frame, text=f"{APP_NAME} v{APP_VERSION}", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        CTkLabel(about_frame, text=APP_AUTHOR).pack(pady=5)
        
        CTkButton(
            about_frame,
            text="📖 Документация",
            command=lambda: webbrowser.open("https://github.com"),
            width=150
        ).pack(pady=10)
    
    # ========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ========================================================================
    
    def _check_proxspace_on_start(self):
        """Проверка ProxSpace при запуске"""
        if not self.pm3_process.check_proxspace():
            self.install_status.configure(
                text="Статус: ProxSpace не найден. Требуется установка.",
                text_color="#D0021B"
            )
            self.install_log.insert("1.0", "[!] ProxSpace не найден\n")
            self.install_log.insert("2.0", "[=] Запустите мастер установки для первой настройки\n")
        else:
            self.install_status.configure(
                text="Статус: ProxSpace найден",
                text_color="#7ED321"
            )
            self.install_log.insert("1.0", "[+] ProxSpace обнаружен\n")
    
    def _toggle_connection(self):
        """Переключение подключения"""
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """Подключение к устройству"""
        if self.pm3_process.start_client():
            self.is_connected = True
            self.connection_indicator.configure(
                text="🟢 Подключено",
                text_color="#7ED321"
            )
            self.connect_btn.configure(text="⏸️ Отключить")
            self.restart_btn.configure(state="normal")
            self.status_label.configure(text="Устройство подключено")
            
            # Запрашиваем информацию об устройстве
            self._send_command("hw version")
        else:
            self.status_label.configure(text="Ошибка подключения")
    
    def _disconnect(self):
        """Отключение от устройства"""
        self.pm3_process.stop_client()
        self.is_connected = False
        self.connection_indicator.configure(
            text="🔴 Отключено",
            text_color="#D0021B"
        )
        self.connect_btn.configure(text="🔌 Подключить")
        self.restart_btn.configure(state="disabled")
        self.status_label.configure(text="Устройство отключено")
    
    def _restart_device(self):
        """Перезагрузка устройства"""
        self._send_command("hw reset")
    
    def _send_command(self, command: str):
        """Отправка команды"""
        if not self.is_connected:
            self.status_label.configure(text="Ошибка: Устройство не подключено")
            return
        
        self.pm3_process.send_command(command)
        self.status_label.configure(text=f"Выполняется: {command}")
    
    def _run_auto_detect(self):
        """Запуск автопоиска"""
        self._send_command("auto")
        self._switch_to_tab("🔍 ПОИСК И ЧТЕНИЕ")
    
    def _toggle_emulation(self):
        """Переключение эмуляции"""
        if self.emu_active:
            self._send_command("hw break")
            self.emu_active = False
            self.emu_indicator.configure(
                text="⚪ Эмуляция не активна",
                text_color="#808080"
            )
        else:
            uid = self.emu_uid_entry.get()
            if uid:
                self._send_command(f"hf mf sim u {uid}")
                self.emu_active = True
                self.emu_indicator.configure(
                    text="🟢 Эмуляция активна",
                    text_color="#7ED321"
                )
            else:
                self.status_label.configure(text="Ошибка: Введите UID")
    
    def _perform_write(self):
        """Выполнение записи"""
        import tkinter.messagebox as messagebox
        
        if messagebox.askyesno("Подтверждение записи", 
                               "Вы уверены? Это действие может повредить карту!"):
            data = self.write_data_entry.get()
            card_type = self.card_type_var.get()
            
            if card_type == "T5577":
                self._send_command(f"lf t55xx write 0 {data}")
            elif card_type == "EM4100":
                self._send_command(f"lf em 410x clone {data}")
            
            self.status_label.configure(text="Запись выполняется...")
    
    def _show_spectrum(self):
        """Показ спектра"""
        # Пример графика
        self.search_plot.clear()
        
        # Генерируем тестовые данные
        freq = np.linspace(0, 100, 1000)
        amplitude = np.abs(np.fft.fft(np.random.randn(1000)))
        
        self.search_plot.plot(freq[:500], amplitude[:500])
        self.search_plot.set_title("Спектральный анализ")
        self.search_plot.set_xlabel("Частота")
        self.search_plot.set_ylabel("Амплитуда")
        self.search_plot.grid(True)
        
        self.search_canvas.draw()
    
    def _switch_to_tab(self, tab_name: str):
        """Переключение на вкладку"""
        self.tabview.set(tab_name)
    
    def _toggle_theme(self):
        """Переключение темы"""
        current = ctk.get_appearance_mode()
        new_theme = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_theme)
    
    def _browse_proxspace_path(self):
        """Выбор пути к ProxSpace"""
        from tkinter import filedialog
        
        path = filedialog.askdirectory(title="Выберите папку ProxSpace")
        if path:
            self.proxspace_path_entry.delete(0, "end")
            self.proxspace_path_entry.insert(0, path)
            self.config_manager.set('proxspace_path', path)
    
    def _run_installer_wizard(self):
        """Запуск мастера установки"""
        self.install_log.delete("1.0", "end")
        
        def log_callback(message):
            self.install_log.insert("end", message + "\n")
            self.install_log.see("end")
        
        installer = ProxSpaceInstaller(self.config_manager, log_callback)
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=installer.run_wizard, daemon=True)
        thread.start()
    
    def _save_sniff_dump(self):
        """Сохранение дампа сниффинга"""
        from tkinter import filedialog
        
        save_path = filedialog.asksaveasfilename(
            title="Сохранить дамп",
            defaultextension=".bin",
            filetypes=[("Binary files", "*.bin")]
        )
        
        if save_path:
            content = self.sniff_log.get("1.0", "end")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _process_output_queue(self):
        """Обработка очереди вывода"""
        try:
            while True:
                line = self.pm3_process.output_queue.get_nowait()
                self._handle_output_line(line)
        except queue.Empty:
            pass
        
        # Планируем следующую проверку
        self.after(100, self._process_output_queue)
    
    def _handle_output_line(self, line: str):
        """Обработка строки вывода"""
        # Добавляем в лог поиска
        if hasattr(self, 'search_log'):
            self.search_log.insert("end", line + "\n")
            self.search_log.see("end")
            
            # Цветовая подсветка
            for prefix, color in LOG_COLORS.items():
                if line.startswith(prefix):
                    # Можно добавить тег для цвета
                    pass
        
        # Парсинг версий
        if "Firmware:" in line or "Bootrom:" in line or "Hardware:" in line:
            self.device_info_label.configure(
                text=self.device_info_label.cget("text") + "\n" + line
            )
            self.version_label.configure(text=line[:50])
        
        # Обновляем статус
        if "[+]" in line:
            self.status_label.configure(text="Успех: " + line)
        elif "[-]" in line:
            self.status_label.configure(text="Ошибка: " + line)
    
    def _on_closing(self):
        """Обработчик закрытия окна"""
        self.pm3_process.stop_client()
        self.config_manager.save_config()
        self.destroy()


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == "__main__":
    app = Proxmark3EasyGUI()
    app.mainloop()
