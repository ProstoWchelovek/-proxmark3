import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import re
import json
import time
from datetime import datetime
from pathlib import Path

# Попытка импорта современного стиля, если нет - используем стандартный
try:
    import customtkinter as ctk
    USE_MODERN = True
except ImportError:
    USE_MODERN = False
    print("Библиотека customtkinter не найдена. Используем стандартный Tkinter. Для лучшего вида установите: pip install customtkinter")

class ColorText:
    """Класс для цветного вывода текста в текстовое поле"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.tags = {
            'info': ('blue', None),      # [=]
            'success': ('green', None),  # [+]
            'error': ('red', None),      # [-], [!]
            'warning': ('orange', None), # [?]
            'prompt': ('cyan', None),    # [usb]
            'progress': ('gray', None),  # Прогресс бары
            'normal': ('black', None)
        }
        
        # Настройка тегов для стандартного Tkinter
        if not USE_MODERN:
            for tag, (color, _) in self.tags.items():
                self.text_widget.tag_config(tag, foreground=color)

    def write(self, message, tag='normal'):
        self.text_widget.insert('end', message, tag)
        self.text_widget.see('end')
        self.text_widget.update()

    def parse_and_write(self, line):
        """Анализирует строку и применяет цвета в зависимости от содержания"""
        line = line.rstrip('\n') + '\n'
        
        if line.startswith('[=]'):
            self.write(line, 'info')
        elif line.startswith('[+]'):
            self.write(line, 'success')
        elif line.startswith('[-]') or line.startswith('[!]'):
            self.write(line, 'error')
        elif line.startswith('[?]'):
            self.write(line, 'warning')
        elif line.startswith('[usb]') or line.startswith('pm3'):
            self.write(line, 'prompt')
        elif re.search(r'\[\d+/(\d+)\]', line):
            self.write(line, 'progress')
        else:
            self.write(line, 'normal')

class Proxmark3App:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxmark3 Studio - All-in-One")
        self.root.geometry("1200x800")
        
        # Пути по умолчанию
        self.default_paths = [
            r"C:\Proxmark3\ProxSpace\pm3\proxmark3\pm3.exe",
            r"C:\Proxmark3\ProxSpace\pm3\client\pm3.exe",
            r".\pm3.exe",
            r".\client\pm3.exe"
        ]
        self.pm3_path = None
        self.process = None
        self.is_running = False
        
        # Настройка стилей
        if USE_MODERN:
            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("blue")
            self.style_frame = ctk.CTkFrame
            self.style_button = ctk.CTkButton
            self.style_label = ctk.CTkLabel
            self.style_entry = ctk.CTkEntry
            self.style_tabview = ctk.CTkTabview
        else:
            self.style_frame = tk.Frame
            self.style_button = tk.Button
            self.style_label = tk.Label
            self.style_entry = tk.Entry
            self.style_tabview = ttk.Notebook
            
        self.setup_ui()
        self.check_installation()

    def setup_ui(self):
        # Основной контейнер
        if USE_MODERN:
            main_frame = ctk.CTkFrame(self.root, padding=10)
            main_frame.pack(fill="both", expand=True)
        else:
            main_frame = tk.Frame(self.root)
            main_frame.pack(fill="both", expand=True)

        # Верхняя панель: Статус и Путь
        top_panel = self.style_frame(main_frame)
        top_panel.pack(fill="x", pady=(0, 10))

        self.lbl_status = self.style_label(top_panel, text="Статус: Не подключено", font=("Arial", 12, "bold"))
        self.lbl_status.pack(side="left", padx=10)

        self.lbl_path = self.style_label(top_panel, text="Путь к pm3: Не найден", font=("Arial", 9))
        self.lbl_path.pack(side="left", padx=10)

        btn_browse = self.style_button(top_panel, text="Выбрать путь", command=self.browse_path)
        btn_browse.pack(side="right", padx=10)

        btn_install = self.style_button(top_panel, text="Установить ProxSpace", command=self.run_installer)
        btn_install.pack(side="right", padx=10)

        # Вкладки
        if USE_MODERN:
            self.tab_view = ctk.CTkTabview(main_frame)
            self.tab_view.pack(fill="both", expand=True)
            
            # Создание вкладок
            self.tabs = {
                "Главная": self.tab_view.add("Главная"),
                "LF (НЧ)": self.tab_view.add("LF (НЧ)"),
                "HF (ВЧ)": self.tab_view.add("HF (ВЧ)"),
                "Эмуляция": self.tab_view.add("Эмуляция"),
                "Сниффинг": self.tab_view.add("Сниффинг"),
                "Прошивка": self.tab_view.add("Прошивка"),
                "Скрипты": self.tab_view.add("Скрипты"),
                "Настройки": self.tab_view.add("Настройки"),
                "О программе": self.tab_view.add("О программе")
            }
        else:
            self.tab_view = ttk.Notebook(main_frame)
            self.tab_view.pack(fill="both", expand=True)
            
            self.tabs = {}
            tab_names = ["Главная", "LF (НЧ)", "HF (ВЧ)", "Эмуляция", "Сниффинг", "Прошивка", "Скрипты", "Настройки", "О программе"]
            for name in tab_names:
                frame = tk.Frame(self.tab_view)
                self.tab_view.add(frame, text=name)
                self.tabs[name] = frame

        # Консоль вывода (общая для всех вкладок, внизу)
        console_frame = self.style_frame(main_frame, height=200)
        console_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        self.lbl_console = self.style_label(console_frame, text="Консоль вывода:", anchor="w")
        self.lbl_console.pack(fill="x")
        
        self.console_text = tk.Text(console_frame, height=10, bg="black", fg="white", font=("Consolas", 9))
        self.console_text.pack(fill="both", expand=True)
        
        self.color_printer = ColorText(self.console_text)
        
        # Кнопки управления консолью
        console_controls = tk.Frame(console_frame)
        console_controls.pack(fill="x")
        
        btn_clear = tk.Button(console_controls, text="Очистить", command=lambda: self.console_text.delete(1.0, 'end'))
        btn_clear.pack(side="left")
        
        btn_save = tk.Button(console_controls, text="Сохранить лог", command=self.save_log)
        btn_save.pack(side="left", padx=5)

        # Заполнение вкладок контентом
        self.setup_home_tab()
        self.setup_lf_tab()
        self.setup_hf_tab()
        # Остальные вкладки можно заполнить аналогично...

    def setup_home_tab(self):
        tab = self.tabs["Главная"]
        
        if USE_MODERN:
            lbl = ctk.CTkLabel(tab, text="Добро пожаловать в Proxmark3 Studio", font=("Arial", 20, "bold"))
            lbl.pack(pady=20)
            
            btn_connect = ctk.CTkButton(tab, text="Подключиться к устройству", command=self.connect_device, width=300, height=40)
            btn_connect.pack(pady=10)
            
            btn_auto = ctk.CTkButton(tab, text="Автопоиск карты (LF + HF)", command=lambda: self.run_command("auto"), width=300, height=40)
            btn_auto.pack(pady=10)
        else:
            tk.Label(tab, text="Добро пожаловать в Proxmark3 Studio", font=("Arial", 20, "bold")).pack(pady=20)
            tk.Button(tab, text="Подключиться к устройству", command=self.connect_device, width=40, height=2).pack(pady=10)
            tk.Button(tab, text="Автопоиск карты (LF + HF)", command=lambda: self.run_command("auto"), width=40, height=2).pack(pady=10)

    def setup_lf_tab(self):
        tab = self.tabs["LF (НЧ)"]
        frame = tk.Frame(tab)
        frame.pack(pady=20)
        
        commands = [
            ("Поиск LF карт", "lf search"),
            ("Чтение сырых данных", "lf read"),
            ("Симуляция EM4100", "lf sim em 1234567890"),
            ("Запись EM4100 (T55x7)", "lf t55xx write 0 12345678"),
            ("Сканирование частот", "lf tune")
        ]
        
        for i, (name, cmd) in enumerate(commands):
            btn = tk.Button(frame, text=name, command=lambda c=cmd: self.run_command(c), width=40, anchor="w")
            btn.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

    def setup_hf_tab(self):
        tab = self.tabs["HF (ВЧ)"]
        frame = tk.Frame(tab)
        frame.pack(pady=20)
        
        commands = [
            ("Поиск HF карт", "hf search"),
            ("Чтение Mifare Classic", "hf mf auto"),
            ("Сниффинг ISO14443a", "hf sniffer 14443a"),
            ("Эмуляция Mifare", "hf mf emulator"),
            ("Запись UID (Magic)", "hf mf wrbl 0 u 11223344")
        ]
        
        for i, (name, cmd) in enumerate(commands):
            btn = tk.Button(frame, text=name, command=lambda c=cmd: self.run_command(c), width=40, anchor="w")
            btn.grid(row=i, column=0, padx=10, pady=5, sticky="ew")

    def check_installation(self):
        """Проверка наличия pm3.exe"""
        for path in self.default_paths:
            if os.path.exists(path):
                self.pm3_path = path
                self.lbl_path.config(text=f"Путь: {path}")
                self.update_status("Готов к работе", "green")
                return
        
        self.update_status("ProxSpace не найден. Требуется установка.", "red")
        self.color_printer.parse_and_write("[!] Proxmark3 клиент не найден. Пожалуйста, выберите путь или нажмите 'Установить ProxSpace'.\n")

    def browse_path(self):
        filename = filedialog.askopenfilename(title="Выберите pm3.exe", filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if filename:
            self.pm3_path = filename
            self.lbl_path.config(text=f"Путь: {filename}")
            self.update_status("Путь установлен", "green")
            # Сохранить путь в реестр или конфиг можно здесь

    def update_status(self, message, color="black"):
        self.lbl_status.config(text=f"Статус: {message}")
        if not USE_MODERN:
            self.lbl_status.config(fg=color)

    def run_command(self, command):
        if not self.pm3_path or not os.path.exists(self.pm3_path):
            messagebox.showerror("Ошибка", "Не указан путь к pm3.exe")
            return

        def thread_target():
            self.color_printer.parse_and_write(f"[usb] pm3 --> {command}\n")
            
            try:
                # Запуск процесса
                # Используем shell=True для Windows, чтобы корректно обрабатывать пути
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(
                    [self.pm3_path, "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,
                    startupinfo=startupinfo
                )
                
                # Чтение вывода в реальном времени
                for line in process.stdout:
                    if not self.is_running and process.poll() is not None:
                        break
                    self.root.after(0, self.color_printer.parse_and_write, line)
                
                process.wait()
                self.root.after(0, self.color_printer.parse_and_write, "\n[=] Команда завершена.\n")
                
            except Exception as e:
                self.root.after(0, self.color_printer.parse_and_write, f"[!] Ошибка выполнения: {str(e)}\n")

        # Запуск в потоке, чтобы не замораживать GUI
        threading.Thread(target=thread_target, daemon=True).start()

    def connect_device(self):
        self.run_command("connect")

    def save_log(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.console_text.get(1.0, 'end'))
            messagebox.showinfo("Успех", f"Лог сохранен в {filename}")

    def run_installer(self):
        """Запуск скрипта установки ProxSpace"""
        installer_script = """
@echo off
echo ==========================================
echo  ProxSpace Installer for Windows
echo ==========================================
echo.
echo Этот скрипт скачает и установит ProxSpace (MSYS2 environment).
echo Это может занять несколько минут.
echo.
pause

:: Создаем директорию
if not exist "C:\Proxmark3" mkdir "C:\Proxmark3"
cd /d "C:\Proxmark3"

:: Скачивание установщика (ссылка на актуальный релиз Iceman)
echo Скачивание установщика ProxSpace...
curl -L -o ProxSpaceSetup.exe "https://github.com/RfidResearchGroup/proxmark3/releases/download/latest/ProxSpaceSetup.exe"

if errorlevel 1 (
    echo Ошибка скачивания. Проверьте интернет.
    pause
    exit /b 1
)

echo Запуск установщика...
:: Запуск в тихом режиме (если поддерживается) или обычном
start /wait ProxSpaceSetup.exe

echo.
echo Установка завершена!
echo Запустите приложение снова, оно должно найти клиент автоматически.
pause
"""
        # Сохраняем временный bat файл и запускаем
        temp_bat = os.path.join(os.getenv("TEMP"), "install_proxspace.bat")
        with open(temp_bat, 'w') as f:
            f.write(installer_script)
        
        subprocess.Popen([temp_bat])
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = Proxmark3App(root)
    root.mainloop()
