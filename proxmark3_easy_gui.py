import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
import queue
import re
import os
import sys
import json
import serial
import serial.tools.list_ports
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import time
from datetime import datetime

# Настройки внешнего вида
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class Proxmark3App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Proxmark3 Easy GUI")
        self.geometry("1200x800")
        
        # Очередь для безопасного обновления GUI из потоков
        self.message_queue = queue.Queue()
        
        # Состояние приложения
        self.is_connected = False
        self.pm3_path = ""
        self.process = None
        self.serial_conn = None
        
        # Пути по умолчанию
        self.default_paths = [
            r"C:\Proxmark3\ProxSpace\pm3",
            r"C:\ProxSpace\pm3",
            os.path.expanduser("~") + "\\Proxmark3\\ProxSpace\\pm3"
        ]
        
        # База команд (упрощенная версия для примера)
        self.commands_db = self.load_commands_db()
        
        # Создание интерфейса
        self.create_menu()
        self.create_tabs()
        self.create_console()
        
        # Проверка установки при запуске
        self.after(100, self.check_installation)
        
        # Запуск обработки очереди сообщений
        self.process_queue()

    def load_commands_db(self):
        """Загрузка базы команд с описанием и типами иконок"""
        return {
            "hf search": {"desc": "Поиск карт HF (13.56 MHz)", "params": "", "example": "hf search", "icon": "!!", "danger": False},
            "lf search": {"desc": "Поиск карт LF (125 kHz)", "params": "", "example": "lf search", "icon": "!!", "danger": False},
            "hf mf autopwn": {"desc": "Автоматическая атака на Mifare Classic", "params": "<uid>", "example": "hf mf autopwn -u 04AABBCC", "icon": "!!", "danger": True},
            "lf sim": {"desc": "Эмуляция LF карты", "params": "<type>", "example": "lf sim em410x -i 48005500AA", "icon": "!", "danger": False},
            "hf mf dump": {"desc": "Дамп памяти Mifare Classic", "params": "", "example": "hf mf dump", "icon": "!!", "danger": False},
            "flash write": {"desc": "Прошивка устройства", "params": "<file>", "example": "flash write -i fullimage.bin", "icon": "!!", "danger": True},
            "data plot": {"desc": "Построение графика сигнала", "params": "", "example": "data plot", "icon": "!", "danger": False},
        }

    def create_menu(self):
        """Создание верхнего меню"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Сохранить лог", command=self.save_log)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

    def create_tabs(self):
        """Создание вкладок"""
        self.tabview = ctk.CTkTabview(self, width=1180, height=600)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Добавление вкладок
        self.tabs = {
            "ГЛАВНАЯ": self.tabview.add("ГЛАВНАЯ"),
            "ПОИСК И ЧТЕНИЕ": self.tabview.add("ПОИСК И ЧТЕНИЕ"),
            "ПАМЯТЬ И КЛЮЧИ": self.tabview.add("ПАМЯТЬ И КЛЮЧИ"),
            "ЗАПИСЬ": self.tabview.add("ЗАПИСЬ"),
            "СНИФФИНГ": self.tabview.add("СНИФФИНГ"),
            "ЭМУЛЯЦИЯ": self.tabview.add("ЭМУЛЯЦИЯ"),
            "ИНСТРУМЕНТЫ": self.tabview.add("ИНСТРУМЕНТЫ"),
            "СКРИПТЫ": self.tabview.add("СКРИПТЫ"),
            "СИСТЕМА": self.tabview.add("СИСТЕМА")
        }
        
        # Инициализация содержимого вкладок
        self.setup_dashboard_tab()
        self.setup_search_read_tab()
        self.setup_memory_keys_tab()
        self.setup_write_tab()
        self.setup_sniffing_tab()
        self.setup_emulation_tab()
        self.setup_tools_tab()
        self.setup_scripts_tab()
        self.setup_system_tab()

    def setup_dashboard_tab(self):
        """Вкладка ГЛАВНАЯ"""
        tab = self.tabs["ГЛАВНАЯ"]
        
        # Статус подключения
        status_frame = ctk.CTkFrame(tab)
        status_frame.pack(padx=20, pady=20, fill="x")
        
        self.status_label = ctk.CTkLabel(status_frame, text="Статус: Отключено", font=("Arial", 16, "bold"))
        self.status_label.pack(side="left", padx=10)
        
        self.connect_btn = ctk.CTkButton(status_frame, text="Подключить", command=self.toggle_connection, width=120)
        self.connect_btn.pack(side="right", padx=10)
        
        # Информация об устройстве
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(info_frame, text="Информация об устройстве:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.device_info = ctk.CTkTextbox(info_frame, height=200)
        self.device_info.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Быстрые действия
        actions_frame = ctk.CTkFrame(tab)
        actions_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkButton(actions_frame, text="Restart", command=lambda: self.send_command("hw reset")).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Clear All", command=self.clear_console).pack(side="left", padx=5)

    def setup_search_read_tab(self):
        """Вкладка ПОИСК И ЧТЕНИЕ"""
        tab = self.tabs["ПОИСК И ЧТЕНИЕ"]
        
        # Переключатель LF/HF
        freq_frame = ctk.CTkFrame(tab)
        freq_frame.pack(padx=20, pady=10, fill="x")
        
        self.freq_var = tk.StringVar(value="HF")
        ctk.CTkRadioButton(freq_frame, text="HF (13.56 MHz)", variable=self.freq_var, value="HF").pack(side="left", padx=10)
        ctk.CTkRadioButton(freq_frame, text="LF (125 kHz)", variable=self.freq_var, value="LF").pack(side="left", padx=10)
        
        # Кнопки действий
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkButton(btn_frame, text="Auto-Detect", command=self.auto_detect).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Search", command=self.search_card).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Read", command=self.read_card).pack(side="left", padx=5)
        
        # Выпадающий список конкретных команд
        cmd_frame = ctk.CTkFrame(tab)
        cmd_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(cmd_frame, text="Конкретные команды:").pack(side="left", padx=5)
        
        self.cmd_combo = ctk.CTkComboBox(cmd_frame, values=[
            "hf search", "hf reader", "hf list", "hf mf autopwn", "hf mf dump",
            "lf search", "lf read", "lf sim em410x", "lf sim hid"
        ], width=300)
        self.cmd_combo.pack(side="left", padx=5)
        
        ctk.CTkButton(cmd_frame, text="Выполнить", command=self.run_selected_cmd).pack(side="left", padx=5)
        
        # График сигнала
        self.plot_frame = ctk.CTkFrame(tab)
        self.plot_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.ax.set_title("Сигнал")
        self.ax.grid(True)

    def setup_memory_keys_tab(self):
        """Вкладка ПАМЯТЬ И КЛЮЧИ"""
        tab = self.tabs["ПАМЯТЬ И КЛЮЧИ"]
        
        # Hex редактор
        hex_frame = ctk.CTkFrame(tab)
        hex_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(hex_frame, text="Редактор памяти (Hex):").pack(anchor="w", padx=10, pady=5)
        
        self.hex_editor = ctk.CTkTextbox(hex_frame, font=("Consolas", 12))
        self.hex_editor.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Кнопки управления памятью
        mem_btns = ctk.CTkFrame(tab)
        mem_btns.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkButton(mem_btns, text="Загрузить дамп", command=self.load_dump).pack(side="left", padx=5)
        ctk.CTkButton(mem_btns, text="Сохранить дамп", command=self.save_dump).pack(side="left", padx=5)
        ctk.CTkButton(mem_btns, text="Заполнить нулями", command=self.clear_hex).pack(side="left", padx=5)
        
        # Управление ключами
        keys_frame = ctk.CTkFrame(tab)
        keys_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(keys_frame, text="Ключи Mifare:").pack(side="left", padx=5)
        self.key_entry = ctk.CTkEntry(keys_frame, width=200, placeholder_text="FFFFFFFFFFFF")
        self.key_entry.pack(side="left", padx=5)
        ctk.CTkButton(keys_frame, text="Добавить ключ", command=self.add_key).pack(side="left", padx=5)

    def setup_write_tab(self):
        """Вкладка ЗАПИСЬ"""
        tab = self.tabs["ЗАПИСЬ"]
        
        ctk.CTkLabel(tab, text="Выберите тип операции записи:").pack(pady=10)
        
        write_type = ctk.CTkSegmentedButton(tab, values=["Запись на карту", "Клонирование T5577", "Magic UID"])
        write_type.pack(pady=10)
        write_type.set("Запись на карту")
        
        file_frame = ctk.CTkFrame(tab)
        file_frame.pack(padx=20, pady=10, fill="x")
        
        self.file_path = ctk.CTkEntry(file_frame, width=400, placeholder_text="Путь к файлу дампа")
        self.file_path.pack(side="left", padx=5)
        ctk.CTkButton(file_frame, text="Обзор", command=self.browse_file).pack(side="left", padx=5)
        
        ctk.CTkButton(tab, text="Начать запись", command=self.start_write, fg_color="orange").pack(pady=20)

    def setup_sniffing_tab(self):
        """Вкладка СНИФФИНГ"""
        tab = self.tabs["СНИФФИНГ"]
        
        sniff_controls = ctk.CTkFrame(tab)
        sniff_controls.pack(padx=20, pady=10, fill="x")
        
        self.sniff_btn = ctk.CTkButton(sniff_controls, text="Start Sniff", command=self.toggle_sniff)
        self.sniff_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(sniff_controls, text="Save Dump", command=self.save_sniff).pack(side="left", padx=5)
        
        # Таблица пакетов
        columns = ("Time", "Type", "Data")
        self.sniff_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        self.sniff_tree.heading("Time", text="Время")
        self.sniff_tree.heading("Type", text="Тип")
        self.sniff_tree.heading("Data", text="Данные")
        self.sniff_tree.column("Time", width=100)
        self.sniff_tree.column("Type", width=100)
        self.sniff_tree.column("Data", width=400)
        
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.sniff_tree.yview)
        self.sniff_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sniff_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

    def setup_emulation_tab(self):
        """Вкладка ЭМУЛЯЦИЯ"""
        tab = self.tabs["ЭМУЛЯЦИЯ"]
        
        ctk.CTkLabel(tab, text="Выберите дамп для эмуляции:").pack(pady=10)
        
        self.emu_combo = ctk.CTkComboBox(tab, values=["Slot 1", "Slot 2", "Slot 3", "File..."], width=300)
        self.emu_combo.pack(pady=10)
        self.emu_combo.set("Slot 1")
        
        self.emu_btn = ctk.CTkButton(tab, text="Start Emulation", command=self.toggle_emulation, fg_color="green")
        self.emu_btn.pack(pady=20)
        
        self.emu_status = ctk.CTkLabel(tab, text="Статус: Остановлено", font=("Arial", 14))
        self.emu_status.pack(pady=10)

    def setup_tools_tab(self):
        """Вкладка ИНСТРУМЕНТЫ"""
        tab = self.tabs["ИНСТРУМЕНТЫ"]
        
        tools_frame = ctk.CTkFrame(tab)
        tools_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(tools_frame, text="Анализ сигналов и декодирование:").pack(anchor="w", padx=10, pady=5)
        
        # Большой график для детального анализа
        self.analysis_fig, self.analysis_ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.analysis_canvas = FigureCanvasTkAgg(self.analysis_fig, master=tools_frame)
        self.analysis_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.analysis_ax.set_title("Детальный анализ")
        self.analysis_ax.grid(True)
        
        analysis_btns = ctk.CTkFrame(tab)
        analysis_btns.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkButton(analysis_btns, text="Demod ASK", command=lambda: self.send_command("data demod ask")).pack(side="left", padx=5)
        ctk.CTkButton(analysis_btns, text="Demod FSK", command=lambda: self.send_command("data demod fsk")).pack(side="left", padx=5)
        ctk.CTkButton(analysis_btns, text="Spectrum", command=lambda: self.send_command("data spectrum")).pack(side="left", padx=5)

    def setup_scripts_tab(self):
        """Вкладка СКРИПТЫ"""
        tab = self.tabs["СКРИПТЫ"]
        
        script_list_frame = ctk.CTkFrame(tab)
        script_list_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        ctk.CTkLabel(script_list_frame, text="Доступные Lua скрипты:").pack(anchor="w", padx=10, pady=5)
        
        self.script_listbox = tk.Listbox(script_list_frame, font=("Consolas", 10))
        self.script_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Заполнение тестовыми скриптами
        test_scripts = ["hf_mf_autopwn.lua", "lf_em410x_sim.lua", "hf_reader.lua", "data_plot.lua"]
        for script in test_scripts:
            self.script_listbox.insert(tk.END, script)
        
        args_frame = ctk.CTkFrame(tab)
        args_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(args_frame, text="Аргументы:").pack(side="left", padx=5)
        self.script_args = ctk.CTkEntry(args_frame, width=300)
        self.script_args.pack(side="left", padx=5)
        
        ctk.CTkButton(args_frame, text="Run Script", command=self.run_script).pack(side="left", padx=5)

    def setup_system_tab(self):
        """Вкладка СИСТЕМА"""
        tab = self.tabs["СИСТЕМА"]
        
        # Мастер установки (скрыт по умолчанию, показывается если нужно)
        self.install_frame = ctk.CTkFrame(tab)
        # Показываем только если установка нужна
        # self.install_frame.pack(padx=20, pady=10, fill="both", expand=True) 
        
        ctk.CTkLabel(self.install_frame, text="Мастер установки ProxSpace", font=("Arial", 18, "bold")).pack(pady=20)
        ctk.CTkLabel(self.install_frame, text="ProxSpace не найден. Необходимо установить.").pack(pady=10)
        
        self.install_progress = ctk.CTkProgressBar(self.install_frame)
        self.install_progress.pack(pady=10, fill="x")
        self.install_progress.set(0)
        
        ctk.CTkButton(self.install_frame, text="Начать установку", command=self.start_installation).pack(pady=20)
        
        # Прошивка
        fw_frame = ctk.CTkFrame(tab)
        fw_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(fw_frame, text="Обновление прошивки:", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkButton(fw_frame, text="Update Bootrom", command=lambda: self.flash_firmware("bootrom")).pack(side="left", padx=5)
        ctk.CTkButton(fw_frame, text="Update Full Image", command=lambda: self.flash_firmware("full")).pack(side="left", padx=5)
        
        # Настройки
        settings_frame = ctk.CTkFrame(tab)
        settings_frame.pack(padx=20, pady=10, fill="x")
        
        ctk.CTkLabel(settings_frame, text="Путь к ProxSpace:").pack(anchor="w", padx=10, pady=5)
        self.path_entry = ctk.CTkEntry(settings_frame, width=500)
        self.path_entry.pack(padx=10, pady=5)
        self.path_entry.insert(0, self.default_paths[0])
        
        ctk.CTkButton(settings_frame, text="Проверить путь", command=self.check_path).pack(pady=5)

    def create_console(self):
        """Создание нижней панели консоли"""
        console_frame = ctk.CTkFrame(self, height=150)
        console_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(console_frame, text="Консоль вывода:").pack(anchor="w", padx=5)
        
        self.console = ctk.CTkTextbox(console_frame, height=100, font=("Consolas", 10))
        self.console.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Цветные теги для консоли
        self.console.tag_config("info", foreground="#00FF00")  # Зеленый [=]
        self.console.tag_config("success", foreground="#00FFFF")  # Голубой [+]
        self.console.tag_config("error", foreground="#FF0000")  # Красный [-]
        self.console.tag_config("warning", foreground="#FFFF00")  # Желтый [!]
        self.console.tag_config("hint", foreground="#FFA500")  # Оранжевый [?]

    def check_installation(self):
        """Проверка наличия ProxSpace"""
        found = False
        for path in self.default_paths:
            if os.path.exists(os.path.join(path, "client", "pm3.exe")):
                self.pm3_path = path
                found = True
                self.log_message(f"[+] ProxSpace найден: {path}", "success")
                break
        
        if not found:
            self.log_message("[-] ProxSpace не найден. Требуется установка.", "error")
            self.install_frame.pack(padx=20, pady=10, fill="both", expand=True)
        else:
            self.log_message("[=] Готов к работе.", "info")

    def start_installation(self):
        """Запуск процесса установки ProxSpace"""
        self.install_progress.set(0.1)
        self.log_message("[=] Начало загрузки ProxSpace...", "info")
        
        # Эмуляция процесса установки
        def install_thread():
            steps = [
                "Скачивание установщика...",
                "Распаковка файлов...",
                "Настройка среды MSYS2...",
                "Компиляция клиента...",
                "Компиляция прошивки...",
                "Установка завершена!"
            ]
            for i, step in enumerate(steps):
                time.sleep(1) # Эмуляция задержки
                progress = (i + 1) / len(steps)
                self.install_progress.set(progress)
                self.log_message(f"[=] {step}", "info")
            
            self.after(0, lambda: messagebox.showinfo("Установка", "ProxSpace успешно установлен!"))
            self.after(0, lambda: self.install_frame.pack_forget())
            self.after(0, lambda: self.check_path())
        
        threading.Thread(target=install_thread, daemon=True).start()

    def toggle_connection(self):
        """Подключение/отключение от устройства"""
        if not self.is_connected:
            # Поиск устройства
            ports = serial.tools.list_ports.comports()
            pm3_port = None
            for port in ports:
                if "FTDI" in port.description or "Arduino" in port.description or "Proxmark" in port.description:
                    pm3_port = port.device
                    break
            
            if pm3_port:
                try:
                    # В реальном приложении здесь было бы открытие serial порта
                    # self.serial_conn = serial.Serial(pm3_port, 115200, timeout=1)
                    self.is_connected = True
                    self.status_label.configure(text="Статус: Подключено (" + pm3_port + ")", text_color="green")
                    self.connect_btn.configure(text="Отключить")
                    self.log_message(f"[+] Устройство подключено: {pm3_port}", "success")
                    self.query_device_info()
                except Exception as e:
                    self.log_message(f"[-] Ошибка подключения: {e}", "error")
            else:
                self.log_message("[-] Устройство Proxmark3 не найдено.", "error")
                messagebox.showwarning("Внимание", "Устройство не найдено. Убедитесь, что оно подключено.")
        else:
            self.is_connected = False
            self.status_label.configure(text="Статус: Отключено", text_color="red")
            self.connect_btn.configure(text="Подключить")
            self.log_message("[=] Устройство отключено.", "info")

    def query_device_info(self):
        """Запрос информации об устройстве"""
        # Эмуляция ответа устройства
        info_text = """
Firmware: Iceman v4.15000
Bootrom: Iceman v4.15000
Hardware: PM3 RDV4.0
OS: Custom
"""
        self.device_info.delete("1.0", tk.END)
        self.device_info.insert("1.0", info_text)
        self.log_message("[=] Информация об устройстве получена.", "info")

    def send_command(self, cmd):
        """Отправка команды устройству"""
        if not self.is_connected and "flash" not in cmd:
            self.log_message("[-] Устройство не подключено.", "error")
            return
        
        self.log_message(f"[usb] pm3 --> {cmd}", "info")
        
        # Эмуляция выполнения команды в отдельном потоке
        def run_cmd():
            # Здесь должен быть реальный вызов subprocess или serial.write
            time.sleep(0.5) # Эмуляция задержки
            
            # Парсинг ответа (эмуляция)
            if "search" in cmd:
                responses = [
                    "[=] Note: False Positives ARE possible",
                    "[=] Checking for known tags...",
                    "[|] Searching for tag...",
                    "[+] Found tag: EM410x ID 48005500AA",
                    "[=] Done."
                ]
                for resp in responses:
                    tag = "info"
                    if resp.startswith("[+]"): tag = "success"
                    if resp.startswith("[-]"): tag = "error"
                    if resp.startswith("[!]"): tag = "warning"
                    if resp.startswith("[?]"): tag = "hint"
                    self.log_message(resp, tag)
                    time.sleep(0.2)
            
            elif "plot" in cmd or "read" in cmd:
                self.log_message("[+] Got samples, plotting...", "success")
                self.update_plot()
            
            else:
                self.log_message("[=] Command executed.", "info")

        threading.Thread(target=run_cmd, daemon=True).start()

    def log_message(self, message, tag="info"):
        """Вывод сообщения в консоль с цветом"""
        self.message_queue.put((message, tag))

    def process_queue(self):
        """Обработка очереди сообщений для потока GUI"""
        try:
            while True:
                message, tag = self.message_queue.get_nowait()
                self.console.insert(tk.END, message + "\n", tag)
                self.console.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def update_plot(self):
        """Обновление графика сигнала"""
        self.ax.clear()
        import random
        data = [random.randint(-100, 100) for _ in range(100)]
        self.ax.plot(data, color='cyan')
        self.ax.set_title("Сигнал (Live)")
        self.ax.grid(True)
        self.canvas.draw()
        
        # Обновление большого графика
        self.analysis_ax.clear()
        self.analysis_ax.plot(data, color='green', linewidth=0.5)
        self.analysis_ax.set_title("Детальный спектр")
        self.analysis_ax.grid(True)
        self.analysis_canvas.draw()

    def auto_detect(self):
        """Авто-определение карт"""
        self.send_command("hf search")
        self.after(1000, lambda: self.send_command("lf search"))

    def search_card(self):
        """Поиск карты"""
        freq = self.freq_var.get()
        cmd = f"{freq.lower()} search"
        self.send_command(cmd)

    def read_card(self):
        """Чтение карты"""
        freq = self.freq_var.get()
        cmd = f"{freq.lower()} read"
        self.send_command(cmd)

    def run_selected_cmd(self):
        """Выполнение выбранной команды из списка"""
        cmd = self.cmd_combo.get()
        if cmd:
            self.send_command(cmd)

    def clear_console(self):
        """Очистка консоли"""
        self.console.delete("1.0", tk.END)

    def save_log(self):
        """Сохранение лога"""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.console.get("1.0", tk.END))
            self.log_message(f"[+] Лог сохранен: {filename}", "success")

    def show_about(self):
        """О программе"""
        messagebox.showinfo("О программе", "Proxmark3 Easy GUI\nВерсия 1.0\n\nИнструмент для работы с Proxmark3 Iceman.\nРазработано для сообщества.")

    # Заглушки для остальных функций (реализация аналогична send_command)
    def load_dump(self): pass
    def save_dump(self): pass
    def clear_hex(self): pass
    def add_key(self): pass
    def browse_file(self): 
        filename = filedialog.askopenfilename()
        if filename:
            self.file_path.delete(0, tk.END)
            self.file_path.insert(0, filename)
    
    def start_write(self):
        if messagebox.askyesno("Предупреждение", "Запись на карту может повредить данные. Продолжить?"):
            self.send_command("hf mf write")
    
    def toggle_sniff(self):
        if self.sniff_btn.cget("text") == "Start Sniff":
            self.sniff_btn.configure(text="Stop Sniff")
            self.send_command("hf sniffer")
        else:
            self.sniff_btn.configure(text="Start Sniff")
            self.send_command("trace stop")
    
    def save_sniff(self):
        self.send_command("trace save")
    
    def toggle_emulation(self):
        if self.emu_btn.cget("text") == "Start Emulation":
            self.emu_btn.configure(text="Stop Emulation", fg_color="red")
            self.emu_status.configure(text="Статус: Эмуляция активна", text_color="green")
            self.send_command("hf mf sim")
        else:
            self.emu_btn.configure(text="Start Emulation", fg_color="green")
            self.emu_status.configure(text="Статус: Остановлено", text_color="white")
            self.send_command("trace stop")
    
    def run_script(self):
        script = self.script_listbox.get(tk.ACTIVE)
        args = self.script_args.get()
        cmd = f"script run {script} {args}"
        self.send_command(cmd)
    
    def check_path(self):
        path = self.path_entry.get()
        if os.path.exists(os.path.join(path, "client", "pm3.exe")):
            self.pm3_path = path
            self.log_message(f"[+] Путь проверен: {path}", "success")
        else:
            self.log_message("[-] Файл pm3.exe не найден по указанному пути.", "error")
    
    def flash_firmware(self, type):
        if messagebox.askyesno("Опасно!", "Процесс прошивки может вывести устройство из строя при ошибке питания.\nПродолжить?"):
            cmd = f"flash write -i {type}.bin"
            self.send_command(cmd)

if __name__ == "__main__":
    app = Proxmark3App()
    app.mainloop()
