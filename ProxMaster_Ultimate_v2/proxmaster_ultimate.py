#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster Ultimate v2.0.0
Профессиональное приложение для Proxmark3 Easy с прошивкой Iceman
Автор: ProxMaster Team
Лицензия: MIT
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
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("Ошибка: Требуется tkinter. Установите: sudo apt-get install python3-tk")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Предупреждение: matplotlib не найден. Графики будут недоступны.")

# Пути и константы
APP_DIR = Path(__file__).parent
COMMANDS_FILE = APP_DIR / "commands.json"
CONFIG_FILE = APP_DIR / "config.json"
LOGS_DIR = APP_DIR / "logs"
DUMPS_DIR = APP_DIR / "dumps"
SCRIPTS_DIR = APP_DIR / "scripts"

# Создаём необходимые директории
for directory in [LOGS_DIR, DUMPS_DIR, SCRIPTS_DIR]:
    directory.mkdir(exist_ok=True)


class CommandManager:
    """Менеджер команд - загрузка и управление командами из JSON"""
    
    def __init__(self, commands_file: Path):
        self.commands_file = commands_file
        self.commands_data = {}
        self.tabs = []
        self.categories = {}
        self.load_commands()
    
    def load_commands(self):
        """Загрузка команд из JSON файла"""
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                self.commands_data = json.load(f)
                self.tabs = self.commands_data.get('tabs', [])
                self.categories = self.commands_data.get('categories', {})
            print(f"[+] Команды загружены: {len(self.tabs)} вкладок")
        except FileNotFoundError:
            print(f"[-] Файл команд не найден: {self.commands_file}")
            self._create_default_commands()
        except json.JSONDecodeError as e:
            print(f"[-] Ошибка JSON в файле команд: {e}")
            self._create_default_commands()
    
    def _create_default_commands(self):
        """Создание структуры команд по умолчанию"""
        self.tabs = []
        self.categories = {}
    
    def get_tab_by_id(self, tab_id: str) -> Optional[Dict]:
        """Получение вкладки по ID"""
        for tab in self.tabs:
            if tab.get('id') == tab_id:
                return tab
        return None
    
    def get_command_by_id(self, command_id: str) -> Optional[Dict]:
        """Получение команды по ID"""
        for tab in self.tabs:
            for cmd in tab.get('commands', []):
                if cmd.get('id') == command_id:
                    return cmd
        return None
    
    def get_category_name(self, category_id: str) -> str:
        """Получение названия категории"""
        return self.categories.get(category_id, category_id)


class ProxmarkDevice:
    """Класс для работы с устройством Proxmark3"""
    
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.port_name: Optional[str] = None
        self.output_queue = queue.Queue()
        self.read_thread: Optional[threading.Thread] = None
        self.is_reading = False
        self.device_info = {}
        self.proxspace_path: Optional[Path] = None
        self.pm3_cli_path: Optional[Path] = None
    
    def find_proxspace(self) -> Optional[Path]:
        """Поиск установленной ProxSpace"""
        # Типичные пути установки ProxSpace на Windows
        possible_paths = [
            Path("C:/ProxSpace"),
            Path("C:/Program Files/ProxSpace"),
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / "ProxSpace",
            Path.home() / "ProxSpace",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "pm3" / "client" / "proxmark3.exe").exists():
                self.proxspace_path = path
                self.pm3_cli_path = path / "pm3" / "client" / "proxmark3.exe"
                print(f"[+] ProxSpace найден: {self.proxspace_path}")
                return self.proxspace_path
        
        # Поиск через переменные окружения
        pm3_home = os.environ.get('PM3_HOME')
        if pm3_home:
            path = Path(pm3_home)
            if path.exists():
                self.proxspace_path = path
                cli_path = path / "client" / "proxmark3.exe"
                if cli_path.exists():
                    self.pm3_cli_path = cli_path
                else:
                    cli_path = path / "pm3" / "client" / "proxmark3.exe"
                    if cli_path.exists():
                        self.pm3_cli_path = cli_path
                print(f"[+] ProxSpace найден через PM3_HOME: {self.proxspace_path}")
                return self.proxspace_path
        
        print("[-] ProxSpace не найден")
        return None
    
    def list_com_ports(self) -> List[Dict]:
        """Список доступных COM портов"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports
    
    def connect(self, port_name: Optional[str] = None) -> bool:
        """Подключение к устройству"""
        if self.is_connected:
            self.disconnect()
        
        # Если порт не указан, пытаемся найти автоматически
        if not port_name:
            ports = self.list_com_ports()
            # Ищем порты с описанием содержащим "Proxmark" или "FTDI"
            for port in ports:
                if any(keyword in port['description'].upper() for keyword in ['PROXMARK', 'FTDI', 'USB SERIAL']):
                    port_name = port['device']
                    break
            
            # Если не нашли, берём первый доступный
            if not port_name and ports:
                port_name = ports[0]['device']
        
        if not port_name:
            print("[-] COM порт не найден")
            return False
        
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=115200,
                timeout=1
            )
            self.port_name = port_name
            self.is_connected = True
            self.is_reading = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            print(f"[+] Подключено к {port_name}")
            return True
        except serial.SerialException as e:
            print(f"[-] Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение от устройства"""
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.is_connected = False
        self.port_name = None
        print("[-] Отключено")
    
    def _read_loop(self):
        """Цикл чтения данных из порта"""
        while self.is_reading and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.output_queue.put(line)
                time.sleep(0.01)
            except Exception as e:
                print(f"Ошибка чтения: {e}")
                break
    
    def send_command(self, command: str) -> bool:
        """Отправка команды устройству"""
        if not self.is_connected or not self.serial_port:
            # Если не подключены, пробуем через CLI ProxSpace
            return self.send_via_cli(command)
        
        try:
            full_command = f"{command}\n"
            self.serial_port.write(full_command.encode('utf-8'))
            self.serial_port.flush()
            print(f"[>] {command}")
            return True
        except serial.SerialException as e:
            print(f"[-] Ошибка отправки: {e}")
            return self.send_via_cli(command)
    
    def send_via_cli(self, command: str) -> bool:
        """Отправка команды через CLI ProxSpace"""
        if not self.pm3_cli_path or not self.pm3_cli_path.exists():
            print("[-] Proxmark3 CLI не найден")
            return False
        
        try:
            # Запускаем команду через CLI
            process = subprocess.Popen(
                [str(self.pm3_cli_path), "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.pm3_cli_path.parent)
            )
            
            # Читаем вывод
            for line in process.stdout:
                self.output_queue.put(line.strip())
            
            stderr = process.stderr.read()
            if stderr:
                self.output_queue.put(f"[ERROR] {stderr}")
            
            return True
        except Exception as e:
            print(f"[-] Ошибка выполнения CLI: {e}")
            return False
    
    def get_device_info(self) -> Dict:
        """Получение информации об устройстве"""
        return self.device_info
    
    def flash_firmware(self, firmware_path: str) -> bool:
        """Обновление прошивки"""
        if not self.pm3_cli_path:
            return False
        
        try:
            process = subprocess.Popen(
                [str(self.pm3_cli_path), "-c", f"hw flash {firmware_path}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            for line in process.stdout:
                self.output_queue.put(line.strip())
            
            return process.returncode == 0
        except Exception as e:
            print(f"[-] Ошибка прошивки: {e}")
            return False


class HexEditor(tk.Frame):
    """Встроенный Hex редактор"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.data = bytearray()
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Панель инструментов
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="📂 Открыть", command=self.load_file).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="💾 Сохранить", command=self.save_file).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="📋 Копировать", command=self.copy_hex).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="📥 Вставить", command=self.paste_hex).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🔄 Инвертировать", command=self.invert_selection).pack(side=tk.LEFT, padx=2)
        
        # Основное поле
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Адреса
        addr_label = tk.Label(main_frame, text="Address", font=("Consolas", 10))
        addr_label.grid(row=0, column=0, sticky=tk.W)
        
        self.addr_text = scrolledtext.ScrolledText(
            main_frame, width=10, height=20, 
            font=("Consolas", 10), state=tk.DISABLED, bg="#f0f0f0"
        )
        self.addr_text.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 5))
        
        # Hex данные
        hex_label = tk.Label(main_frame, text="Hex", font=("Consolas", 10))
        hex_label.grid(row=0, column=1, sticky=tk.W)
        
        self.hex_text = scrolledtext.ScrolledText(
            main_frame, width=47, height=20,
            font=("Consolas", 10)
        )
        self.hex_text.grid(row=1, column=1, sticky=tk.NSEW, padx=(0, 5))
        
        # ASCII представление
        ascii_label = tk.Label(main_frame, text="ASCII", font=("Consolas", 10))
        ascii_label.grid(row=0, column=2, sticky=tk.W)
        
        self.ascii_text = scrolledtext.ScrolledText(
            main_frame, width=16, height=20,
            font=("Consolas", 10), state=tk.DISABLED
        )
        self.ascii_text.grid(row=1, column=2, sticky=tk.NSEW)
        
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
    
    def load_data(self, data: bytes):
        """Загрузка данных в редактор"""
        self.data = bytearray(data)
        self._update_display()
    
    def load_file(self):
        """Загрузка файла"""
        filename = filedialog.askopenfilename(
            title="Открыть файл",
            filetypes=[
                ("Binary files", "*.bin"),
                ("EML files", "*.eml"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                with open(filename, 'rb') as f:
                    self.load_data(f.read())
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def save_file(self):
        """Сохранение файла"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить файл",
            defaultextension=".bin",
            filetypes=[
                ("Binary files", "*.bin"),
                ("EML files", "*.eml"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                with open(filename, 'wb') as f:
                    f.write(self.data)
                messagebox.showinfo("Успех", "Файл сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def copy_hex(self):
        """Копирование hex данных"""
        self.clipboard_clear()
        self.clipboard_append(self.data.hex())
    
    def paste_hex(self):
        """Вставка hex данных"""
        try:
            hex_data = self.clipboard_get()
            # Удаляем все пробелы и переводы строк
            hex_data = re.sub(r'\s+', '', hex_data)
            self.data = bytearray.fromhex(hex_data)
            self._update_display()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неверный формат hex: {e}")
    
    def invert_selection(self):
        """Инвертирование выделенных байтов"""
        # Простая инверсия всех данных
        self.data = bytearray(~b & 0xFF for b in self.data)
        self._update_display()
    
    def _update_display(self):
        """Обновление отображения"""
        self.addr_text.config(state=tk.NORMAL)
        self.addr_text.delete(1.0, tk.END)
        self.hex_text.delete(1.0, tk.END)
        self.ascii_text.config(state=tk.NORMAL)
        self.ascii_text.delete(1.0, tk.END)
        
        for i in range(0, len(self.data), 16):
            chunk = self.data[i:i+16]
            
            # Адрес
            self.addr_text.insert(tk.END, f"{i:08X}\n")
            
            # Hex
            hex_line = ' '.join(f'{b:02X}' for b in chunk)
            hex_line += '   ' * (16 - len(chunk))
            self.hex_text.insert(tk.END, hex_line + '\n')
            
            # ASCII
            ascii_line = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            self.ascii_text.insert(tk.END, ascii_line + '\n')
        
        self.addr_text.config(state=tk.DISABLED)
        self.ascii_text.config(state=tk.DISABLED)


class NodeEditor(tk.Frame):
    """Редактор Node.js для создания скриптов"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        toolbar = tk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="📄 Новый", command=self.new_script).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="📂 Открыть", command=self.open_script).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="💾 Сохранить", command=self.save_script).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="▶️ Запустить", command=self.run_script).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🐛 Отладка", command=self.debug_script).pack(side=tk.LEFT, padx=2)
        
        # Панель кода
        code_frame = tk.Frame(self)
        code_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.code_editor = scrolledtext.ScrolledText(
            code_frame, font=("Consolas", 11), wrap=tk.NONE,
            bg="#1e1e1e", fg="#d4d4d4", insertbackground='white'
        )
        self.code_editor.pack(fill=tk.BOTH, expand=True)
        
        # Настройка цветов для подсветки синтаксиса (базовая)
        self.code_editor.tag_configure("keyword", foreground="#569cd6")
        self.code_editor.tag_configure("string", foreground="#ce9178")
        self.code_editor.tag_configure("comment", foreground="#6a9955")
        self.code_editor.tag_configure("function", foreground="#dcdcaa")
        
        # Консоль вывода
        console_label = tk.Label(self, text="Консоль вывода:", anchor=tk.W)
        console_label.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.console = scrolledtext.ScrolledText(
            self, height=10, font=("Consolas", 10),
            bg="#1e1e1e", fg="#cccccc"
        )
        self.console.pack(fill=tk.X, padx=5, pady=5)
    
    def new_script(self):
        """Новый скрипт"""
        self.code_editor.delete(1.0, tk.END)
        template = """// ProxMaster Ultimate - Node.js Script Template
// Шаблон скрипта для работы с Proxmark3

const pm3 = require('proxmark3');

async function main() {
    console.log('Запуск скрипта...');
    
    // Пример: подключение к устройству
    const device = await pm3.connect();
    
    // Пример: выполнение команды
    const result = await device.command('hf search');
    console.log('Результат:', result);
    
    // Пример: чтение данных
    const data = await device.read();
    
    // Пример: запись данных
    // await device.write(data);
    
    await device.disconnect();
    console.log('Скрипт завершён');
}

main().catch(console.error);
"""
        self.code_editor.insert(1.0, template)
    
    def open_script(self):
        """Открыть скрипт"""
        filename = filedialog.askopenfilename(
            title="Открыть скрипт",
            filetypes=[
                ("JavaScript files", "*.js"),
                ("Node files", "*.node"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_editor.delete(1.0, tk.END)
                self.code_editor.insert(1.0, content)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def save_script(self):
        """Сохранить скрипт"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить скрипт",
            defaultextension=".js",
            filetypes=[
                ("JavaScript files", "*.js"),
                ("Node files", "*.node"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                content = self.code_editor.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Успех", "Скрипт сохранён")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def run_script(self):
        """Запуск скрипта"""
        self.console.insert(tk.END, "Запуск скрипта...\n")
        # Здесь должна быть логика выполнения Node.js скрипта
        self.console.insert(tk.END, "Требуется установка Node.js и зависимостей\n")
    
    def debug_script(self):
        """Отладка скрипта"""
        self.console.insert(tk.END, "Режим отладки...\n")


class AIAssistant(tk.Toplevel):
    """ИИ-помощник с поддержкой локальных моделей"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🤖 ИИ-помощник")
        self.geometry("600x500")
        self.model_selected = "local"
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Выбор модели
        model_frame = tk.Frame(self)
        model_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(model_frame, text="Модель:").pack(side=tk.LEFT)
        
        self.model_var = tk.StringVar(value="local")
        models = ["local", "LM Studio", "Cherry Studio", "Ollama"]
        model_combo = ttk.Combobox(
            model_frame, 
            textvariable=self.model_var,
            values=models,
            state="readonly",
            width=20
        )
        model_combo.pack(side=tk.LEFT, padx=10)
        model_combo.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # Режим разработчика
        self.dev_mode = tk.BooleanVar(value=False)
        dev_check = tk.Checkbutton(
            model_frame,
            text="Режим разработчика",
            variable=self.dev_mode
        )
        dev_check.pack(side=tk.RIGHT)
        
        # Область чата
        chat_frame = tk.Frame(self)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_history = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD,
            font=("Arial", 11)
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        
        # Поле ввода
        input_frame = tk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.input_field = scrolledtext.ScrolledText(
            input_frame, height=3, wrap=tk.WORD,
            font=("Arial", 11)
        )
        self.input_field.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        tk.Button(
            input_frame, 
            text="Отправить",
            command=self.send_message,
            bg="#4CAF50",
            fg="white"
        ).pack(side=tk.RIGHT, padx=5)
        
        # Приветственное сообщение
        self.chat_history.insert(tk.END, "🤖 Привет! Я ваш ИИ-помощник для работы с Proxmark3.\n")
        self.chat_history.insert(tk.END, "Я могу помочь с:\n")
        self.chat_history.insert(tk.END, "• Управлением устройством\n")
        self.chat_history.insert(tk.END, "• Редактированием данных карт\n")
        self.chat_history.insert(tk.END, "• Созданием скриптов\n")
        self.chat_history.insert(tk.END, "• Адаптацией приложения под ваши нужды\n\n")
    
    def on_model_change(self, event=None):
        """Изменение модели"""
        model = self.model_var.get()
        self.chat_history.insert(tk.END, f"\n🔄 Переключено на модель: {model}\n")
    
    def send_message(self):
        """Отправка сообщения"""
        message = self.input_field.get(1.0, tk.END).strip()
        if not message:
            return
        
        self.chat_history.insert(tk.END, f"\n👤 Вы: {message}\n")
        self.input_field.delete(1.0, tk.END)
        
        # Имитация ответа (здесь должна быть интеграция с реальной моделью)
        response = self._generate_response(message)
        self.chat_history.insert(tk.END, f"\n🤖 ИИ: {response}\n")
        self.chat_history.see(tk.END)
    
    def _generate_response(self, message: str) -> str:
        """Генерация ответа (заглушка для будущей интеграции)"""
        message_lower = message.lower()
        
        if 'привет' in message_lower or 'здравствуй' in message_lower:
            return "Здравствуйте! Чем я могу помочь вам сегодня?"
        elif 'команда' in message_lower:
            return "Все команды доступны в соответствующих вкладках. Используйте значок ! для получения справки."
        elif 'скрипт' in message_lower:
            return "Перейдите во вкладку 'СКРИПТЫ' для создания или выполнения Lua/Node.js скриптов."
        elif 'hex' in message_lower or 'редактор' in message_lower:
            return "Hex-редактор доступен во вкладке 'МЕНЕДЖЕР ДАННЫХ'. Он позволяет просматривать и редактировать дампы."
        elif 'обновление' in message_lower:
            return "Проверка обновлений доступна во вкладке 'НАСТРОЙКИ'."
        else:
            return "Я понимаю вопросы о командах, скриптах, hex-редакторе и обновлениях. Спросите меня о чём-то конкретном!"


class ProxMasterApp:
    """Основное приложение ProxMaster Ultimate"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ProxMaster Ultimate v2.0.0 - Proxmark3 Easy GUI")
        self.root.geometry("1400x900")
        
        # Настройка стиля
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Цветовая схема
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#0078D4',
            'success': '#4CAF50',
            'warning': '#FFC107',
            'error': '#F44336',
            'tab_bg': '#2d2d2d',
            'tab_fg': '#ffffff'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Инициализация компонентов
        self.command_manager = CommandManager(COMMANDS_FILE)
        self.device = ProxmarkDevice()
        self.current_tab = None
        self.active_process = None
        
        # Загрузка конфигурации
        self.config = self.load_config()
        
        self.setup_ui()
        self.setup_menu()
        
        # Проверка наличия ProxSpace
        self.root.after(1000, self.check_proxspace)
    
    def load_config(self) -> Dict:
        """Загрузка конфигурации"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'theme': 'dark',
            'language': 'ru',
            'proxspace_path': None,
            'com_port': None
        }
    
    def save_config(self):
        """Сохранение конфигурации"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def setup_ui(self):
        """Настройка основного интерфейса"""
        # Верхняя панель
        top_frame = tk.Frame(self.root, bg=self.colors['bg'])
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Логотип и название
        logo_label = tk.Label(
            top_frame, 
            text="🎯 ProxMaster Ultimate",
            font=("Arial", 20, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['accent']
        )
        logo_label.pack(side=tk.LEFT)
        
        # Индикатор подключения
        self.connection_indicator = tk.Label(
            top_frame,
            text="● Отключено",
            font=("Arial", 12),
            bg=self.colors['bg'],
            fg=self.colors['error']
        )
        self.connection_indicator.pack(side=tk.RIGHT, padx=20)
        
        # Кнопка ИИ-помощника
        ai_button = tk.Button(
            top_frame,
            text="🤖 ИИ-помощник",
            command=self.open_ai_assistant,
            bg=self.colors['accent'],
            fg='white',
            font=("Arial", 11, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        ai_button.pack(side=tk.RIGHT, padx=10)
        
        # Вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создание вкладок из JSON
        for tab_data in self.command_manager.tabs:
            self.create_tab(tab_data)
        
        # Нижняя панель с логом
        bottom_frame = tk.Frame(self.root, bg=self.colors['bg'])
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        log_label = tk.Label(
            bottom_frame,
            text="Лог операций:",
            font=("Arial", 11, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['fg']
        )
        log_label.pack(anchor=tk.W)
        
        self.log_console = scrolledtext.ScrolledText(
            bottom_frame,
            height=10,
            font=("Consolas", 10),
            bg='#1e1e1e',
            fg='#cccccc',
            insertbackground='white'
        )
        self.log_console.pack(fill=tk.X, pady=5)
        
        # Настройка цветов лога
        self.log_console.tag_configure("info", foreground="#4FC3F7")
        self.log_console.tag_configure("success", foreground="#81C784")
        self.log_console.tag_configure("warning", foreground="#FFB74D")
        self.log_console.tag_configure("error", foreground="#E57373")
        self.log_console.tag_configure("command", foreground="#BA68C8")
        
        # Строка состояния
        self.status_bar = tk.Label(
            self.root,
            text="Готов к работе",
            font=("Arial", 10),
            bg=self.colors['accent'],
            fg='white',
            anchor=tk.W,
            padx=10
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_menu(self):
        """Настройка меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть дамп", command=self.open_dump)
        file_menu.add_command(label="Сохранить дамп", command=self.save_dump)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Устройство
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Устройство", menu=device_menu)
        device_menu.add_command(label="Подключить", command=self.connect_device)
        device_menu.add_command(label="Отключить", command=self.disconnect_device)
        device_menu.add_separator()
        device_menu.add_command(label="Обновить прошивку", command=self.update_firmware)
        
        # Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_command(label="Hex-редактор", command=self.open_hex_editor)
        tools_menu.add_command(label="Node Editor", command=self.open_node_editor)
        tools_menu.add_separator()
        tools_menu.add_command(label="Настройки", command=self.open_settings)
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Документация", command=self.show_docs)
    
    def create_tab(self, tab_data: Dict):
        """Создание вкладки"""
        tab_id = tab_data.get('id', 'unknown')
        tab_name = tab_data.get('name', 'Вкладка')
        tab_icon = tab_data.get('icon', '')
        
        frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(frame, text=f"{tab_icon} {tab_name}")
        
        # Заголовок вкладки
        header_frame = tk.Frame(frame, bg=self.colors['tab_bg'])
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = tk.Label(
            header_frame,
            text=f"{tab_icon} {tab_name}",
            font=("Arial", 16, "bold"),
            bg=self.colors['tab_bg'],
            fg=self.colors['tab_fg']
        )
        title_label.pack(side=tk.LEFT)
        
        desc_label = tk.Label(
            header_frame,
            text=tab_data.get('description', ''),
            font=("Arial", 10),
            bg=self.colors['tab_bg'],
            fg='#aaaaaa'
        )
        desc_label.pack(side=tk.LEFT, padx=20)
        
        # Контент вкладки
        content_frame = tk.Frame(frame, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создание кнопок команд
        self.create_command_buttons(content_frame, tab_data.get('commands', []))
        
        # Специфичный контент для некоторых вкладок
        if tab_id == 'memory':
            # Hex-редактор для вкладки памяти
            hex_editor = HexEditor(content_frame)
            hex_editor.pack(fill=tk.BOTH, expand=True, pady=10)
        
        elif tab_id == 'scripts':
            # Node Editor для вкладки скриптов
            node_editor = NodeEditor(content_frame)
            node_editor.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def create_command_buttons(self, parent, commands: List[Dict]):
        """Создание кнопок команд"""
        # Группировка команд по категориям
        categories = {}
        for cmd in commands:
            cat = cmd.get('category', 'other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(cmd)
        
        # Создание кнопок для каждой категории
        row = 0
        col = 0
        max_cols = 4
        
        for cat_name, cat_commands in categories.items():
            # Название категории
            cat_label = tk.Label(
                parent,
                text=self.command_manager.get_category_name(cat_name),
                font=("Arial", 12, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['accent']
            )
            cat_label.grid(row=row, column=col, sticky=tk.W, pady=(10, 5))
            row += 1
            
            # Кнопки команд
            for cmd in cat_commands:
                btn = tk.Button(
                    parent,
                    text=cmd.get('name', 'Команда'),
                    font=("Arial", 10),
                    bg='#2d2d2d',
                    fg='white',
                    relief=tk.FLAT,
                    padx=15,
                    pady=8,
                    cursor='hand2',
                    command=lambda c=cmd: self.execute_command(c)
                )
                btn.grid(row=row, column=col, sticky=tk.W, padx=5, pady=5)
                
                # Добавление индикатора уровня
                level = cmd.get('level', '!')
                level_label = tk.Label(
                    parent,
                    text="ℹ" if level == '!!' else "ⓘ",
                    font=("Arial", 10),
                    bg='#2d2d2d',
                    fg='#ffd700',
                    cursor='hand2'
                )
                level_label.grid(row=row, column=col, sticky=tk.E, padx=5, pady=5)
                level_label.bind('<Button-1>', lambda e, c=cmd: self.show_command_info(c))
                
                row += 1
                if row > 10:
                    row = 0
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row = 0
                        # Новая секция
                        separator = tk.Frame(parent, height=2, bg='#3d3d3d')
                        separator.grid(row=0, column=col, columnspan=max_cols, sticky=tk.EW, pady=10)
                        row = 1
    
    def execute_command(self, command_data: Dict):
        """Выполнение команды"""
        cmd_str = command_data.get('command', '')
        if not cmd_str:
            # Это инструмент, а не команда
            return
        
        safe = command_data.get('safe', True)
        
        # Предупреждение для опасных команд
        if not safe:
            confirm = messagebox.askyesno(
                "Предупреждение",
                f"Вы собираетесь выполнить опасную операцию:\n{command_data.get('name')}\n\nПродолжить?",
                icon='warning'
            )
            if not confirm:
                return
        
        # Вывод в лог
        self.log(f"[COMMAND] {cmd_str}", "command")
        self.status_bar.config(text=f"Выполнение: {cmd_str}")
        
        # Отправка команды устройству
        threading.Thread(target=self._execute_command_thread, args=(cmd_str,), daemon=True).start()
    
    def _execute_command_thread(self, command: str):
        """Поток выполнения команды"""
        self.device.send_command(command)
        
        # Чтение ответа
        while True:
            try:
                line = self.device.output_queue.get(timeout=0.5)
                self.root.after(0, lambda l=line: self.log(l, "info"))
            except queue.Empty:
                break
        
        self.root.after(0, lambda: self.status_bar.config(text="Готов к работе"))
    
    def show_command_info(self, command_data: Dict):
        """Показ информации о команде"""
        info_window = tk.Toplevel(self.root)
        info_window.title(f"ℹ {command_data.get('name')}")
        info_window.geometry("500x400")
        
        text_widget = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, font=("Arial", 11))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Информация
        info = f"Команда: {command_data.get('command', 'N/A')}\n\n"
        info += f"Описание:\n{command_data.get('description', 'Нет описания')}\n\n"
        
        # Параметры
        params = command_data.get('params', [])
        if params:
            info += "Параметры:\n"
            for param in params:
                flag = param.get('flag', '')
                desc = param.get('description', '')
                has_value = param.get('has_value', False)
                info += f"  {flag}" + (" <значение>" if has_value else "") + f" - {desc}\n"
        
        text_widget.insert(1.0, info)
        text_widget.config(state=tk.DISABLED)
    
    def log(self, message: str, level: str = "info"):
        """Вывод сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        
        self.log_console.insert(tk.END, formatted_msg, level)
        self.log_console.see(tk.END)
    
    def connect_device(self):
        """Подключение к устройству"""
        if self.device.is_connected:
            return
        
        port = self.config.get('com_port')
        if self.device.connect(port):
            self.connection_indicator.config(text="● Подключено", fg=self.colors['success'])
            self.log("Устройство подключено", "success")
        else:
            messagebox.showerror("Ошибка", "Не удалось подключиться к устройству")
    
    def disconnect_device(self):
        """Отключение от устройства"""
        self.device.disconnect()
        self.connection_indicator.config(text="● Отключено", fg=self.colors['error'])
        self.log("Устройство отключено", "warning")
    
    def check_proxspace(self):
        """Проверка наличия ProxSpace"""
        if not self.device.find_proxspace():
            self.log("ProxSpace не найден. Некоторые функции могут быть недоступны.", "warning")
            # Можно показать мастер установки
            # self.show_proxspace_wizard()
    
    def open_ai_assistant(self):
        """Открытие ИИ-помощника"""
        ai_window = AIAssistant(self.root)
        ai_window.transient(self.root)
    
    def open_hex_editor(self):
        """Открытие Hex-редактора"""
        # Hex-редактор уже есть во вкладке Memory
        self.notebook.select(2)  # Переключение на вкладку Memory
    
    def open_node_editor(self):
        """Открытие Node Editor"""
        # Node Editor уже есть во вкладке Scripts
        self.notebook.select(5)  # Переключение на вкладку Scripts
    
    def open_settings(self):
        """Открытие настроек"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("500x400")
        
        # Путь к ProxSpace
        proxspace_frame = tk.Frame(settings_window)
        proxspace_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(proxspace_frame, text="Путь к ProxSpace:").pack(anchor=tk.W)
        proxspace_entry = tk.Entry(proxspace_frame, width=50)
        proxspace_entry.pack(fill=tk.X, pady=5)
        if self.config.get('proxspace_path'):
            proxspace_entry.insert(0, str(self.config['proxspace_path']))
        
        tk.Button(
            proxspace_frame,
            text="Обзор...",
            command=lambda: self.browse_proxspace(proxspace_entry)
        ).pack(anchor=tk.W)
        
        # COM порт
        com_frame = tk.Frame(settings_window)
        com_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(com_frame, text="COM порт:").pack(anchor=tk.W)
        com_var = tk.StringVar(value=self.config.get('com_port', ''))
        com_combo = ttk.Combobox(com_frame, textvariable=com_var, width=47)
        com_combo.pack(fill=tk.X, pady=5)
        com_combo['values'] = [p['device'] for p in self.device.list_com_ports()]
        
        # Тема
        theme_frame = tk.Frame(settings_window)
        theme_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(theme_frame, text="Тема:").pack(anchor=tk.W)
        theme_var = tk.StringVar(value=self.config.get('theme', 'dark'))
        ttk.Radiobutton(theme_frame, text="Тёмная", variable=theme_var, value='dark').pack(anchor=tk.W)
        ttk.Radiobutton(theme_frame, text="Светлая", variable=theme_var, value='light').pack(anchor=tk.W)
        
        # Кнопки
        button_frame = tk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(
            button_frame,
            text="Сохранить",
            command=lambda: self.save_settings(
                proxspace_entry.get(),
                com_var.get(),
                theme_var.get(),
                settings_window
            ),
            bg=self.colors['success'],
            fg='white'
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            button_frame,
            text="Отмена",
            command=settings_window.destroy
        ).pack(side=tk.RIGHT)
    
    def browse_proxspace(self, entry: tk.Entry):
        """Выбор пути к ProxSpace"""
        directory = filedialog.askdirectory(title="Выберите папку ProxSpace")
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)
    
    def save_settings(self, proxspace_path: str, com_port: str, theme: str, window: tk.Toplevel):
        """Сохранение настроек"""
        self.config['proxspace_path'] = proxspace_path
        self.config['com_port'] = com_port
        self.config['theme'] = theme
        self.save_config()
        
        messagebox.showinfo("Успех", "Настройки сохранены")
        window.destroy()
    
    def open_dump(self):
        """Открытие дампа"""
        filename = filedialog.askopenfilename(
            title="Открыть дамп",
            filetypes=[
                ("Binary files", "*.bin"),
                ("EML files", "*.eml"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                # Найти вкладку Memory и передать данные в hex-редактор
                self.log(f"Открыт файл: {filename}", "info")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
    
    def save_dump(self):
        """Сохранение дампа"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить дамп",
            defaultextension=".bin",
            filetypes=[
                ("Binary files", "*.bin"),
                ("EML files", "*.eml"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.log(f"Сохранение в: {filename}", "info")
    
    def update_firmware(self):
        """Обновление прошивки"""
        if not messagebox.askyesno(
            "Предупреждение",
            "Обновление прошивки может занять несколько минут.\nНе отключайте устройство!\n\nПродолжить?",
            icon='warning'
        ):
            return
        
        filename = filedialog.askopenfilename(
            title="Выберите файл прошивки",
            filetypes=[
                ("Binary files", "*.bin"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.log(f"Обновление прошивки: {filename}", "warning")
            # threading.Thread(target=self.device.flash_firmware, args=(filename,), daemon=True).start()
    
    def show_about(self):
        """О программе"""
        messagebox.showinfo(
            "О программе",
            "ProxMaster Ultimate v2.0.0\n\n"
            "Профессиональное приложение для работы с Proxmark3 Easy\n"
            "с прошивкой Iceman.\n\n"
            "Автор: ProxMaster Team\n"
            "Лицензия: MIT\n\n"
            "Поддержка:\n"
            "https://github.com/RfidResearchGroup/proxmark3\n"
            "https://github.com/Gator96100/ProxSpace"
        )
    
    def show_docs(self):
        """Документация"""
        docs_window = tk.Toplevel(self.root)
        docs_window.title("Документация")
        docs_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(docs_window, wrap=tk.WORD, font=("Arial", 11))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        docs = """
ProxMaster Ultimate - Руководство пользователя

1. ПОДКЛЮЧЕНИЕ УСТРОЙСТВА
   - Убедитесь, что ProxSpace установлен
   - Подключите Proxmark3 Easy к USB
   - Нажмите "Подключить" в меню "Устройство"

2. РАБОТА С КАРТАМИ
   - Вкладка "ПОИСК": автоматическое определение карт
   - Вкладка "МЕНЕДЖЕР ДАННЫХ": просмотр и редактирование дампов
   - Вкладка "ЗАПИСЬ": запись данных на карты
   - Вкладка "ЭМУЛЯЦИЯ": эмуляция карт

3. HEX-РЕДАКТОР
   - Доступен во вкладке "МЕНЕДЖЕР ДАННЫХ"
   - Поддержка загрузки/сохранения файлов .bin, .eml
   - Просмотр в hex и ASCII формате

4. СКРИПТЫ
   - Вкладка "СКРИПТЫ": Lua и Node.js скрипты
   - Node Editor для создания собственных скриптов
   - Выполнение встроенных атак

5. ИИ-ПОМОЩНИК
   - Кнопка "🤖 ИИ-помощник" в верхней панели
   - Помощь в управлении устройством
   - Генерация скриптов
   - Режим разработчика

6. НАСТРОЙКИ
   - Путь к ProxSpace
   - Выбор COM порта
   - Тема оформления

Безопасность:
- Опасные операции требуют подтверждения
- Всегда делайте резервные копии дампов
"""
        
        text_widget.insert(1.0, docs)
        text_widget.config(state=tk.DISABLED)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Точка входа"""
    print("=" * 60)
    print("ProxMaster Ultimate v2.0.0")
    print("Профессиональное приложение для Proxmark3 Easy")
    print("=" * 60)
    
    app = ProxMasterApp()
    app.run()


if __name__ == "__main__":
    main()
