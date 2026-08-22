"""
Proxmark3 Easy GUI - Главный файл приложения
Точка входа и сборка всех модулей
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import sys
import os

# Импорт наших модулей
from commands_db import COMMANDS_DB, DROPDOWN_GROUPS, get_command_info
from installer import ProxSpaceInstaller, run_installer_callback
from pm3_core import Proxmark3Core, parse_log_line, extract_progress

# Настройки темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class Proxmark3GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Proxmark3 Easy GUI")
        self.geometry("1200x800")
        
        # Состояние
        self.pm3_core = None
        self.proxspace_path = "C:\\Proxmark3"
        self.is_installed = False
        
        # Проверка установки при старте
        self.check_installation()
        
        # Создание интерфейса
        self.create_ui()
        
        # Инициализация ядра если установлено
        if self.is_installed:
            self.init_core()
    
    def check_installation(self):
        """Проверка наличия ProxSpace"""
        installer = ProxSpaceInstaller(self.proxspace_path)
        self.is_installed = installer.check_existing()
        
    def init_core(self):
        """Инициализация ядра связи"""
        self.pm3_core = Proxmark3Core(self.proxspace_path, log_callback=self.append_log)
        
    def append_log(self, message):
        """Добавление сообщения в лог консоли"""
        self.console_text.configure(state="normal")
        self.console_text.insert("end", message + "\n")
        
        # Цветная подсветка
        tag = "normal"
        if "[+]" in message: tag = "success"
        elif "[-]" in message: tag = "error"
        elif "[!]" in message: tag = "warning"
        elif "[=]" in message: tag = "info"
        
        # Применяем тег к последней строке (упрощенно)
        self.console_text.tag_configure(tag, foreground=self.get_color_for_tag(tag))
        
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
        
        # Обновление прогресс бара если есть данные
        current, total = extract_progress(message)
        if current and total:
            progress = (current / total) * 100
            self.progress_bar.set(progress / 100)
            self.status_label.configure(text=f"Прогресс: {progress:.1f}%")
    
    def get_color_for_tag(self, tag):
        colors = {
            "success": "#00ff00",
            "error": "#ff0000",
            "warning": "#ffa500",
            "info": "#00bfff",
            "normal": "#ffffff"
        }
        return colors.get(tag, "#ffffff")

    def create_ui(self):
        """Создание основного интерфейса"""
        # Верхняя панель с вкладками
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Добавление 9 вкладок
        self.tabs = {
            "Главная": self.tabview.add("ГЛАВНАЯ"),
            "Поиск и Чтение": self.tabview.add("ПОИСК И ЧТЕНИЕ"),
            "Память и Ключи": self.tabview.add("ПАМЯТЬ И КЛЮЧИ"),
            "Запись": self.tabview.add("ЗАПИСЬ"),
            "Сниффинг": self.tabview.add("СНИФФИНГ"),
            "Эмуляция": self.tabview.add("ЭМУЛЯЦИЯ"),
            "Инструменты": self.tabview.add("ИНСТРУМЕНТЫ"),
            "Скрипты": self.tabview.add("СКРИПТЫ"),
            "Система": self.tabview.add("СИСТЕМА")
        }
        
        # Построение содержимого каждой вкладки
        self.build_dashboard()
        self.build_search_read()
        self.build_memory()
        self.build_write()
        self.build_sniffing()
        self.build_emulation()
        self.build_tools()
        self.build_scripts()
        self.build_system()
        
        # Нижняя панель с консолью
        self.build_console_panel()
        
    def build_console_panel(self):
        """Панель лога и прогресса внизу"""
        console_frame = ctk.CTkFrame(self, height=200)
        console_frame.pack(fill="x", side="bottom", padx=10, pady=(0, 10))
        
        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(console_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=(10, 5))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(console_frame, text="Готов", font=("Arial", 12))
        self.status_label.pack(anchor="w", padx=10)
        
        # Текстовое поле лога
        self.console_text = ctk.CTkTextbox(console_frame, height=120)
        self.console_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.console_text.configure(state="disabled", font=("Consolas", 10))
        
        # Кнопка очистки
        clear_btn = ctk.CTkButton(console_frame, text="Очистить", width=100, 
                                  command=lambda: self.console_text.configure(state="normal") or self.console_text.delete("1.0", "end") or self.console_text.configure(state="disabled"))
        clear_btn.pack(anchor="e", padx=10, pady=5)

    def build_dashboard(self):
        """Вкладка ГЛАВНАЯ"""
        tab = self.tabs["Главная"]
        
        # Статус блок
        status_frame = ctk.CTkFrame(tab)
        status_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(status_frame, text="Статус устройства", font=("Arial", 16, "bold")).pack(anchor="w")
        
        self.conn_status = ctk.CTkLabel(status_frame, text="Отключено", text_color="red")
        self.conn_status.pack(anchor="w")
        
        info_grid = ctk.CTkFrame(status_frame)
        info_grid.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_grid, text="Firmware:").grid(row=0, column=0, sticky="w", padx=5)
        self.lbl_fw = ctk.CTkLabel(info_grid, text="-")
        self.lbl_fw.grid(row=0, column=1, sticky="w", padx=5)
        
        ctk.CTkLabel(info_grid, text="Bootrom:").grid(row=1, column=0, sticky="w", padx=5)
        self.lbl_boot = ctk.CTkLabel(info_grid, text="-")
        self.lbl_boot.grid(row=1, column=1, sticky="w", padx=5)
        
        ctk.CTkLabel(info_grid, text="Hardware:").grid(row=2, column=0, sticky="w", padx=5)
        self.lbl_hw = ctk.CTkLabel(info_grid, text="-")
        self.lbl_hw.grid(row=2, column=1, sticky="w", padx=5)
        
        # Кнопки действий
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="Подключить", command=self.cmd_connect).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отключить", command=self.cmd_disconnect).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Перезагрузка", command=lambda: self.send_cmd("hw restart")).pack(side="left", padx=5)

    def build_search_read(self):
        """Вкладка ПОИСК И ЧТЕНИЕ"""
        tab = self.tabs["Поиск и Чтение"]
        
        # Кнопка Auto-Detect
        auto_btn = ctk.CTkButton(tab, text="Auto-Detect (Полный поиск)", 
                                 fg_color="#ff9800", hover_color="#e68900",
                                 command=lambda: self.send_cmd("search"))
        auto_btn.pack(pady=20)
        
        # Разделение на LF и HF
        content_frame = ctk.CTkFrame(tab)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # LF Секция
        lf_frame = ctk.CTkFrame(content_frame)
        lf_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(lf_frame, text="LF (125 kHz)", font=("Arial", 14, "bold")).pack(pady=10)
        
        lf_cmds = [
            ("Поиск LF", "lf search"),
            ("Чтение LF", "lf read"),
            ("EM410x Decode", "lf em 410xread"),
            ("HID Decode", "lf hid fskdemod")
        ]
        
        for label, cmd in lf_cmds:
            ctk.CTkButton(lf_frame, text=label, command=lambda c=cmd: self.send_cmd(c)).pack(fill="x", padx=10, pady=5)
            
        # HF Секция
        hf_frame = ctk.CTkFrame(content_frame)
        hf_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(hf_frame, text="HF (13.56 MHz)", font=("Arial", 14, "bold")).pack(pady=10)
        
        hf_cmds = [
            ("Поиск HF", "hf search"),
            ("Чтение HF", "hf reader"),
            ("Список пакетов", "hf list"),
            ("Mifare Autopwn", "hf mf autopwn")
        ]
        
        for label, cmd in hf_cmds:
            ctk.CTkButton(hf_frame, text=label, command=lambda c=cmd: self.send_cmd(c)).pack(fill="x", padx=10, pady=5)

    def build_memory(self):
        """Вкладка ПАМЯТЬ И КЛЮЧИ"""
        tab = self.tabs["Память и Ключи"]
        ctk.CTkLabel(tab, text="Менеджер памяти и ключей (В разработке)").pack(pady=20)
        # Здесь будет Hex редактор и таблица ключей

    def build_write(self):
        """Вкладка ЗАПИСЬ"""
        tab = self.tabs["Запись"]
        ctk.CTkLabel(tab, text="Инструменты записи и клонирования (В разработке)").pack(pady=20)

    def build_sniffing(self):
        """Вкладка СНИФФИНГ"""
        tab = self.tabs["Сниффинг"]
        ctk.CTkLabel(tab, text="Сниффинг трафика (В разработке)").pack(pady=20)

    def build_emulation(self):
        """Вкладка ЭМУЛЯЦИЯ"""
        tab = self.tabs["Эмуляция"]
        ctk.CTkLabel(tab, text="Эмуляция карт (В разработке)").pack(pady=20)

    def build_tools(self):
        """Вкладка ИНСТРУМЕНТЫ"""
        tab = self.tabs["Инструменты"]
        ctk.CTkLabel(tab, text="Графики и анализ сигналов (В разработке)").pack(pady=20)

    def build_scripts(self):
        """Вкладка СКРИПТЫ"""
        tab = self.tabs["Скрипты"]
        ctk.CTkLabel(tab, text="Lua скрипты (В разработке)").pack(pady=20)

    def build_system(self):
        """Вкладка СИСТЕМА"""
        tab = self.tabs["Система"]
        
        # Блок установки
        install_frame = ctk.CTkFrame(tab)
        install_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(install_frame, text="Установка ProxSpace", font=("Arial", 14, "bold")).pack(anchor="w")
        
        if not self.is_installed:
            ctk.CTkLabel(install_frame, text="ProxSpace не найден. Требуется установка.", text_color="orange").pack(anchor="w")
            ctk.CTkButton(install_frame, text="Установить ProxSpace", command=self.run_installer).pack(anchor="w", pady=10)
        else:
            ctk.CTkLabel(install_frame, text="ProxSpace установлен.", text_color="green").pack(anchor="w")
            
        # Блок прошивки
        fw_frame = ctk.CTkFrame(tab)
        fw_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(fw_frame, text="Обновление прошивки", font=("Arial", 14, "bold")).pack(anchor="w")
        ctk.CTkButton(fw_frame, text="Обновить всё (Bootrom + Full)", fg_color="red", 
                      command=lambda: self.show_warning_and_run("hw flash")).pack(anchor="w", pady=10)
        
        # Настройки
        settings_frame = ctk.CTkFrame(tab)
        settings_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(settings_frame, text="Настройки", font=("Arial", 14, "bold")).pack(anchor="w")
        ctk.CTkLabel(settings_frame, text=f"Путь: {self.proxspace_path}").pack(anchor="w")

    def run_installer(self):
        """Запуск мастера установки"""
        def log_handler(msg):
            self.append_log(msg)
            
        threading.Thread(target=run_installer_callback, args=(log_handler,), daemon=True).start()

    def send_cmd(self, cmd):
        """Отправка команды ядру"""
        if self.pm3_core:
            threading.Thread(target=self.pm3_core.send_command, args=(cmd,), daemon=True).start()
        else:
            self.append_log("[-] Ошибка: Ядро не инициализировано")
            
    def show_warning_and_run(self, cmd):
        """Показ предупреждения для опасных команд"""
        if messagebox.askyesno("Предупреждение", "Эта операция может быть опасной для устройства. Продолжить?"):
            self.send_cmd(cmd)

    def cmd_connect(self):
        """Подключение к устройству"""
        if self.pm3_core:
            if self.pm3_core.start_client():
                self.conn_status.configure(text="Подключено", text_color="green")
                # Запрос статуса
                self.send_cmd("hw status")
        else:
            self.append_log("[-] Сначала установите ProxSpace")

    def cmd_disconnect(self):
        """Отключение"""
        if self.pm3_core:
            self.pm3_core.stop()
            self.conn_status.configure(text="Отключено", text_color="red")

if __name__ == "__main__":
    app = Proxmark3GUI()
    app.mainloop()
