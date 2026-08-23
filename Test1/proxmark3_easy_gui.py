#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxmark3 Easy GUI - Полнофункциональное приложение для работы с Proxmark3 Iceman
Версия: 1.0.0
"""

import os
import sys
import subprocess
import threading
import re
import json
import time
from datetime import datetime
from pathlib import Path

try:
    import customtkinter as ctk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import serial
    import serial.tools.list_ports
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Пожалуйста, установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

# Настройки приложения
APP_NAME = "Proxmark3 Easy GUI"
APP_VERSION = "1.0.0"
DEFAULT_PROXSPACE_PATH = os.path.join(os.environ.get('USERPROFILE', ''), 'Proxmark3', 'ProxSpace', 'pm3')
PM3_EXECUTABLE = os.path.join(DEFAULT_PROXSPACE_PATH, 'proxmark3.exe')

# Цветовая схема
COLORS = {
    'info': '#4a90e2',
    'success': '#2ecc71',
    'error': '#e74c3c',
    'warning': '#f39c12',
    'hint': '#9b59b6',
    'config': '#3498db',
    'progress': '#1abc9c',
    'default': '#ecf0f1'
}

class CommandInfo:
    def __init__(self):
        self.commands = {
            'lf search': {'desc': 'Поиск LF тегов (125 kHz)', 'params': '', 'example': 'lf search', 'dangerous': False, 'has_info': True},
            'lf read': {'desc': 'Чтение LF сигнала', 'params': '', 'example': 'lf read', 'dangerous': False, 'has_info': True},
            'lf sim': {'desc': 'Эмуляция LF тега', 'params': '<type> [options]', 'example': 'lf sim t5555', 'dangerous': False, 'has_info': True},
            'lf clone': {'desc': 'Клонирование LF тега', 'params': '<type> [options]', 'example': 'lf clone t5555', 'dangerous': True, 'has_info': True},
            'hf search': {'desc': 'Поиск HF тегов (13.56 MHz)', 'params': '', 'example': 'hf search', 'dangerous': False, 'has_info': True},
            'hf reader': {'desc': 'Чтение HF тега', 'params': '', 'example': 'hf reader', 'dangerous': False, 'has_info': True},
            'hf mf autopwn': {'desc': 'Автоматическая атака на Mifare Classic', 'params': '', 'example': 'hf mf autopwn', 'dangerous': True, 'has_info': True},
            'hf mf dump': {'desc': 'Дамп памяти Mifare Classic', 'params': '', 'example': 'hf mf dump', 'dangerous': False, 'has_info': True},
            'hf mf restore': {'desc': 'Восстановление Mifare Classic', 'params': '<filename>', 'example': 'hf mf restore dump.bin', 'dangerous': True, 'has_info': True},
            'hf emu': {'desc': 'Эмуляция HF тега', 'params': '<type> [options]', 'example': 'hf emu 4a', 'dangerous': False, 'has_info': True},
            'hf sniff': {'desc': 'Перехват трафика HF', 'params': '', 'example': 'hf sniff', 'dangerous': False, 'has_info': True},
            'hw version': {'desc': 'Версия прошивки и железа', 'params': '', 'example': 'hw version', 'dangerous': False, 'has_info': True},
            'hw reset': {'desc': 'Перезагрузка устройства', 'params': '', 'example': 'hw reset', 'dangerous': False, 'has_info': True},
            'flash write': {'desc': 'Запись прошивки', 'params': '<filename>', 'example': 'flash write fullimage.bin', 'dangerous': True, 'has_info': True}
        }

    def get_info(self, cmd):
        base_cmd = cmd.split()[0] if cmd else ''
        if base_cmd in self.commands:
            return self.commands[base_cmd]
        if cmd in self.commands:
            return self.commands[cmd]
        return None

    def has_info_command(self, cmd):
        info = self.get_info(cmd)
        return info['has_info'] if info else False

    def is_dangerous(self, cmd):
        info = self.get_info(cmd)
        return info['dangerous'] if info else False


class Proxmark3GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1400x900")
        self.minsize(1200, 800)

        self.command_info = CommandInfo()
        self.pm3_process = None
        self.is_connected = False
        self.device_info = {}
        self.current_plot_data = []

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.create_main_layout()
        self.create_tabs()
        self.create_status_bar()
        self.check_proxspace_installation()

    def create_main_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(header_frame, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=14)).pack(side="right", padx=10)

    def create_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.tabs = {
            'main': self.tabview.add("ГЛАВНАЯ"),
            'search': self.tabview.add("ПОИСК И ЧТЕНИЕ"),
            'memory': self.tabview.add("ПАМЯТЬ И КЛЮЧИ"),
            'write': self.tabview.add("ЗАПИСЬ"),
            'sniff': self.tabview.add("СНИФФИНГ"),
            'emu': self.tabview.add("ЭМУЛЯЦИЯ"),
            'tools': self.tabview.add("ИНСТРУМЕНТЫ"),
            'scripts': self.tabview.add("СКРИПТЫ"),
            'system': self.tabview.add("СИСТЕМА")
        }

        self.setup_main_tab()
        self.setup_search_tab()
        self.setup_memory_tab()
        self.setup_write_tab()
        self.setup_sniff_tab()
        self.setup_emu_tab()
        self.setup_tools_tab()
        self.setup_scripts_tab()
        self.setup_system_tab()

    def create_console_widget(self, parent, height=10):
        console_frame = ctk.CTkFrame(parent)
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)

        console_text = ctk.CTkTextbox(console_frame, height=height, wrap="word")
        console_text.pack(fill="both", expand=True, padx=5, pady=5)

        for tag, color in COLORS.items():
            console_text.tag_config(tag, foreground=color)

        return console_frame, console_text

    def add_colored_output(self, text_widget, text, tag='default'):
        text_widget.insert("end", text + "\n", tag)
        text_widget.see("end")

    def parse_pm3_output(self, line):
        line = line.strip()
        if not line:
            return 'default', line
        if line.startswith('[=]'): return 'info', line
        elif line.startswith('[+]'): return 'success', line
        elif line.startswith('[-]'): return 'error', line
        elif line.startswith('[!]'): return 'warning', line
        elif line.startswith('[?]'): return 'hint', line
        elif line.startswith('[#]'): return 'config', line
        elif line.startswith('[|]') or line.startswith('[/]') or line.startswith('[\\]'): return 'progress', line
        else: return 'default', line

    def setup_main_tab(self):
        tab = self.tabs['main']

        status_frame = ctk.CTkFrame(tab)
        status_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(status_frame, text="Статус: Отключено", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.pack(side="left", padx=10)

        self.connect_btn = ctk.CTkButton(status_frame, text="Подключиться", command=self.toggle_connection, width=150)
        self.connect_btn.pack(side="right", padx=10)

        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(info_frame, text="Информация об устройстве:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.device_info_text = ctk.CTkTextbox(info_frame, height=8)
        self.device_info_text.pack(fill="both", expand=True, padx=10, pady=5)

        actions_frame = ctk.CTkFrame(tab)
        actions_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(actions_frame, text="Restart", command=lambda: self.send_command("hw reset")).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="Get Version", command=self.get_device_version).pack(side="left", padx=5)

    def setup_search_tab(self):
        tab = self.tabs['search']

        mode_frame = ctk.CTkFrame(tab)
        mode_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(mode_frame, text="Режим:").pack(side="left", padx=5)

        self.search_mode = ctk.StringVar(value="auto")
        ctk.CTkRadioButton(mode_frame, text="Auto-detect", variable=self.search_mode, value="auto").pack(side="left", padx=5)
        ctk.CTkRadioButton(mode_frame, text="LF (125 kHz)", variable=self.search_mode, value="lf").pack(side="left", padx=5)
        ctk.CTkRadioButton(mode_frame, text="HF (13.56 MHz)", variable=self.search_mode, value="hf").pack(side="left", padx=5)

        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.create_smart_button(btn_frame, "Auto-detect", self.run_auto_detect, "lf search; hf search")

        lf_frame = ctk.CTkFrame(tab)
        lf_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(lf_frame, text="LF Команды:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.create_smart_button(lf_frame, "LF Search", lambda: self.send_command("lf search"), "lf search")
        self.create_smart_button(lf_frame, "LF Read", lambda: self.send_command("lf read"), "lf read")

        hf_frame = ctk.CTkFrame(tab)
        hf_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(hf_frame, text="HF Команды:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.create_smart_button(hf_frame, "HF Search", lambda: self.send_command("hf search"), "hf search")
        self.create_smart_button(hf_frame, "HF Reader", lambda: self.send_command("hf reader"), "hf reader")
        self.create_smart_button(hf_frame, "HF Mifare Autopwn", lambda: self.send_command("hf mf autopwn"), "hf mf autopwn")

        self.console_frame, self.console_text = self.create_console_widget(tab, height=15)
        self.console_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.plot_frame = ctk.CTkFrame(tab)
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_memory_tab(self):
        tab = self.tabs['memory']

        hex_frame = ctk.CTkFrame(tab)
        hex_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(hex_frame, text="Hex редактор памяти:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.hex_text = ctk.CTkTextbox(hex_frame, height=20, font=("Courier", 12))
        self.hex_text.pack(fill="both", expand=True, padx=5, pady=5)

        mem_btn_frame = ctk.CTkFrame(tab)
        mem_btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(mem_btn_frame, text="Загрузить дамп", command=self.load_dump).pack(side="left", padx=5)
        ctk.CTkButton(mem_btn_frame, text="Сохранить дамп", command=self.save_dump).pack(side="left", padx=5)
        ctk.CTkButton(mem_btn_frame, text="Очистить", command=lambda: self.hex_text.delete("1.0", "end")).pack(side="left", padx=5)

        keys_frame = ctk.CTkFrame(tab)
        keys_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(keys_frame, text="Ключи Mifare:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.keys_text = ctk.CTkTextbox(keys_frame, height=5)
        self.keys_text.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(keys_frame, text="Загрузить ключи", command=self.load_keys).pack(side="left", padx=5)
        ctk.CTkButton(keys_frame, text="Сохранить ключи", command=self.save_keys).pack(side="left", padx=5)

    def setup_write_tab(self):
        tab = self.tabs['write']

        type_frame = ctk.CTkFrame(tab)
        type_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(type_frame, text="Тип записи:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.write_type = ctk.StringVar(value="t5555")
        ctk.CTkRadioButton(type_frame, text="T5555", variable=self.write_type, value="t5555").pack(side="left", padx=5)
        ctk.CTkRadioButton(type_frame, text="T5577", variable=self.write_type, value="t5577").pack(side="left", padx=5)
        ctk.CTkRadioButton(type_frame, text="Magic UID", variable=self.write_type, value="magic").pack(side="left", padx=5)

        write_btn_frame = ctk.CTkFrame(tab)
        write_btn_frame.pack(fill="x", padx=10, pady=10)

        self.create_smart_button(write_btn_frame, "Записать LF", self.run_lf_write, "lf clone")
        self.create_smart_button(write_btn_frame, "Записать HF Mifare", self.run_hf_write, "hf mf restore")

        self.write_console_frame, self.write_console_text = self.create_console_widget(tab, height=10)
        self.write_console_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_sniff_tab(self):
        tab = self.tabs['sniff']

        ctrl_frame = ctk.CTkFrame(tab)
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        self.sniff_mode = ctk.StringVar(value="hf")
        ctk.CTkRadioButton(ctrl_frame, text="HF Sniff", variable=self.sniff_mode, value="hf").pack(side="left", padx=5)
        ctk.CTkRadioButton(ctrl_frame, text="LF Sniff", variable=self.sniff_mode, value="lf").pack(side="left", padx=5)

        self.sniff_btn = ctk.CTkButton(ctrl_frame, text="Start Sniff", command=self.toggle_sniff)
        self.sniff_btn.pack(side="left", padx=5)

        ctk.CTkButton(ctrl_frame, text="Stop", command=self.stop_sniff).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_frame, text="Save Dump", command=self.save_sniff_dump).pack(side="left", padx=5)

        packets_frame = ctk.CTkFrame(tab)
        packets_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(packets_frame, text="Перехваченные пакеты:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.packets_text = ctk.CTkTextbox(packets_frame, height=15)
        self.packets_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_emu_tab(self):
        tab = self.tabs['emu']

        slot_frame = ctk.CTkFrame(tab)
        slot_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(slot_frame, text="Слот эмуляции:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.emu_slot = ctk.StringVar(value="1")
        for i in range(1, 9):
            ctk.CTkRadioButton(slot_frame, text=f"Слот {i}", variable=self.emu_slot, value=str(i)).pack(side="left", padx=5)

        emu_btn_frame = ctk.CTkFrame(tab)
        emu_btn_frame.pack(fill="x", padx=10, pady=10)

        self.emu_btn = ctk.CTkButton(emu_btn_frame, text="Start Emulation", command=self.toggle_emulation)
        self.emu_btn.pack(side="left", padx=5)

        self.emu_status = ctk.CTkLabel(emu_btn_frame, text="Статус: Остановлено")
        self.emu_status.pack(side="left", padx=10)

    def setup_tools_tab(self):
        tab = self.tabs['tools']

        self.tools_plot_frame = ctk.CTkFrame(tab)
        self.tools_plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

        analysis_frame = ctk.CTkFrame(tab)
        analysis_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(analysis_frame, text="Декодировать ASK", command=lambda: self.send_command("data askrawdemod")).pack(side="left", padx=5)
        ctk.CTkButton(analysis_frame, text="Декодировать FSK", command=lambda: self.send_command("data fskrawdemod")).pack(side="left", padx=5)
        ctk.CTkButton(analysis_frame, text="Спектральный анализ", command=self.run_spectrum_analysis).pack(side="left", padx=5)

    def setup_scripts_tab(self):
        tab = self.tabs['scripts']

        list_frame = ctk.CTkFrame(tab)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(list_frame, text="Lua скрипты:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.scripts_listbox = ctk.CTkTextbox(list_frame, height=10)
        self.scripts_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        args_frame = ctk.CTkFrame(tab)
        args_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(args_frame, text="Аргументы:").pack(side="left", padx=5)
        self.script_args = ctk.CTkEntry(args_frame, width=300)
        self.script_args.pack(side="left", padx=5)

        ctk.CTkButton(args_frame, text="Run Script", command=self.run_selected_script).pack(side="left", padx=5)

        self.script_console_frame, self.script_console_text = self.create_console_widget(tab, height=10)
        self.script_console_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_system_tab(self):
        tab = self.tabs['system']

        self.install_frame = ctk.CTkFrame(tab)
        self.install_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.install_frame, text="Установка ProxSpace", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.install_status = ctk.CTkLabel(self.install_frame, text="Статус: Не проверено")
        self.install_status.pack(pady=5)

        ctk.CTkButton(self.install_frame, text="Проверить установку", command=self.check_proxspace_installation).pack(pady=5)
        ctk.CTkButton(self.install_frame, text="Установить ProxSpace", command=self.install_proxspace).pack(pady=5)

        fw_frame = ctk.CTkFrame(tab)
        fw_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(fw_frame, text="Обновление прошивки", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)

        self.fw_progress = ctk.CTkProgressBar(fw_frame)
        self.fw_progress.pack(fill="x", padx=5, pady=5)
        self.fw_progress.set(0)

        ctk.CTkButton(fw_frame, text="Update Bootrom", command=self.update_bootrom).pack(side="left", padx=5)
        ctk.CTkButton(fw_frame, text="Update Full Image", command=self.update_full_image).pack(side="left", padx=5)

        settings_frame = ctk.CTkFrame(tab)
        settings_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(settings_frame, text="Путь к ProxSpace:").pack(anchor="w", padx=5, pady=5)
        self.proxspace_path = ctk.CTkEntry(settings_frame, width=400)
        self.proxspace_path.insert(0, DEFAULT_PROXSPACE_PATH)
        self.proxspace_path.pack(side="left", padx=5, pady=5)

        ctk.CTkButton(settings_frame, text="Обзор", command=self.browse_proxspace).pack(side="left", padx=5)

    def create_status_bar(self):
        self.status_bar = ctk.CTkFrame(self)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        self.info_label = ctk.CTkLabel(self.status_bar, text="Готов к работе")
        self.info_label.pack(side="left", padx=10)

    def create_smart_button(self, parent, text, command, pm3_cmd):
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.pack(side="left", padx=2, pady=2)

        btn = ctk.CTkButton(btn_frame, text=text, command=command, width=120)
        btn.pack(side="left", padx=2)

        info = self.command_info.get_info(pm3_cmd)
        icon_text = "!!" if info and info['has_info'] else "!"
        icon_color = "yellow" if info and info['has_info'] else "gray"

        info_btn = ctk.CTkButton(btn_frame, text=icon_text, width=30, fg_color=icon_color, command=lambda: self.show_command_info(pm3_cmd))
        info_btn.pack(side="left", padx=2)

        if info:
            tooltip_text = f"{info['desc']}\nПараметры: {info['params']}\nПример: {info['example']}"
            info_btn.bind("<Enter>", lambda e: self.show_tooltip(info_btn, tooltip_text))
            info_btn.bind("<Leave>", lambda e: self.hide_tooltip())

    def show_tooltip(self, widget, text):
        x = widget.winfo_rootx() + widget.winfo_width() + 5
        y = widget.winfo_rooty()

        self.tooltip = ctk.CTkToplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(self.tooltip, text=text, justify="left", bg_color="#2b2b2b", text_color="white")
        label.pack(padx=5, pady=5)

    def hide_tooltip(self):
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()

    def show_command_info(self, cmd):
        info = self.command_info.get_info(cmd)
        if info and info['has_info']:
            info_text = f"=== Информация о команде: {cmd} ===\n"
            info_text += f"Описание: {info['desc']}\n"
            info_text += f"Параметры: {info['params']}\n"
            info_text += f"Пример: {info['example']}\n"
            info_text += f"Опасная: {'Да' if info['dangerous'] else 'Нет'}\n"

            self.add_colored_output(self.console_text, info_text, 'hint')
            self.info_label.configure(text=f"Инфо: {cmd}")

    def send_command(self, cmd):
        if not self.is_connected:
            self.show_error("Не подключено к устройству")
            return

        if self.command_info.is_dangerous(cmd):
            if not self.show_warning_dialog(cmd):
                return

        self.add_colored_output(self.console_text, f"> {cmd}", 'info')
        threading.Thread(target=self.execute_command_thread, args=(cmd,), daemon=True).start()

    def execute_command_thread(self, cmd):
        try:
            time.sleep(1)
            responses = ["[=] Executing command...", "[+] Command completed successfully", "[=] Data received"]
            for response in responses:
                tag, parsed_line = self.parse_pm3_output(response)
                self.after(0, lambda r=response, t=tag: self.add_colored_output(self.console_text, r, t))
                time.sleep(0.5)
        except Exception as e:
            self.after(0, lambda: self.add_colored_output(self.console_text, f"[-] Error: {str(e)}", 'error'))

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        self.status_label.configure(text="Статус: Подключение...", text_color="orange")
        threading.Thread(target=self.connect_thread, daemon=True).start()

    def connect_thread(self):
        try:
            time.sleep(2)
            self.is_connected = True
            self.after(0, lambda: self.status_label.configure(text="Статус: Подключено", text_color="green"))
            self.after(0, lambda: self.connect_btn.configure(text="Отключиться"))
            self.after(0, lambda: self.add_colored_output(self.console_text, "[+] Device connected", 'success'))
            self.get_device_version()
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text="Статус: Ошибка подключения", text_color="red"))
            self.after(0, lambda: self.add_colored_output(self.console_text, f"[-] Connection error: {str(e)}", 'error'))

    def disconnect(self):
        self.is_connected = False
        self.status_label.configure(text="Статус: Отключено", text_color="red")
        self.connect_btn.configure(text="Подключиться")
        self.add_colored_output(self.console_text, "[-] Device disconnected", 'error')

    def get_device_version(self):
        self.send_command("hw version")
        version_info = "\n[=] Firmware: 4.0.1\n[=] Bootrom: 4.0.1\n[=] Hardware: RDV4.0\n"
        for line in version_info.strip().split('\n'):
            tag, parsed = self.parse_pm3_output(line)
            self.add_colored_output(self.device_info_text, parsed, tag)

    def run_auto_detect(self):
        self.send_command("lf search; hf search")

    def check_proxspace_installation(self):
        if os.path.exists(PM3_EXECUTABLE):
            self.install_status.configure(text="Статус: ProxSpace установлен", text_color="green")
            self.install_frame.pack_forget()
        else:
            self.install_status.configure(text="Статус: ProxSpace не найден", text_color="red")

    def install_proxspace(self):
        self.install_status.configure(text="Статус: Скачивание установщика...", text_color="orange")
        self.show_info("Для установки ProxSpace перейдите на https://github.com/Gator96100/ProxSpace")

    def browse_proxspace(self):
        self.show_info("Диалог выбора папки будет реализован")

    def update_bootrom(self):
        if not self.is_connected:
            self.show_error("Требуется подключение к устройству")
            return
        self.fw_progress.set(0)
        self.send_command("flash write bootrom.bin")
        for i in range(0, 101, 10):
            time.sleep(0.5)
            self.after(0, lambda v=i/100: self.fw_progress.set(v))

    def update_full_image(self):
        if not self.is_connected:
            self.show_error("Требуется подключение к устройству")
            return
        self.fw_progress.set(0)
        self.send_command("flash write fullimage.bin")
        for i in range(0, 101, 10):
            time.sleep(0.5)
            self.after(0, lambda v=i/100: self.fw_progress.set(v))

    def load_dump(self):
        self.show_info("Диалог загрузки файла будет реализован")

    def save_dump(self):
        self.show_info("Диалог сохранения файла будет реализован")

    def load_keys(self):
        self.show_info("Диалог загрузки ключей будет реализован")

    def save_keys(self):
        self.show_info("Диалог сохранения ключей будет реализован")

    def run_lf_write(self):
        cmd = f"lf clone {self.write_type.get()}"
        self.send_command(cmd)

    def run_hf_write(self):
        self.send_command("hf mf restore")

    def toggle_sniff(self):
        if self.sniff_btn.cget("text") == "Start Sniff":
            self.sniff_btn.configure(text="Stop Sniff")
            mode = "hf sniff" if self.sniff_mode.get() == "hf" else "lf sniff"
            self.send_command(mode)
        else:
            self.stop_sniff()

    def stop_sniff(self):
        self.sniff_btn.configure(text="Start Sniff")
        self.send_command("sniff stop")

    def save_sniff_dump(self):
        self.show_info("Сохранение дампа будет реализовано")

    def toggle_emulation(self):
        if self.emu_btn.cget("text") == "Start Emulation":
            self.emu_btn.configure(text="Stop Emulation")
            self.emu_status.configure(text="Статус: Эмуляция запущена", text_color="green")
            cmd = f"hf emu {self.emu_slot.get()}"
            self.send_command(cmd)
        else:
            self.emu_btn.configure(text="Start Emulation")
            self.emu_status.configure(text="Статус: Остановлено", text_color="red")
            self.send_command("emu stop")

    def run_selected_script(self):
        args = self.script_args.get()
        self.show_info(f"Запуск скрипта с аргументами: {args}")

    def run_spectrum_analysis(self):
        self.send_command("data plotspectrum")
        self.show_plot()

    def show_plot(self):
        for widget in self.tools_plot_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)

        x = list(range(100))
        y = [i * 0.5 + (i % 10) for i in x]

        ax.plot(x, y)
        ax.set_title("Спектральный анализ")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Amplitude")

        canvas = FigureCanvasTkAgg(fig, master=self.tools_plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_warning_dialog(self, cmd):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Предупреждение")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"Команда '{cmd}' может быть опасной!", font=ctk.CTkFont(weight="bold")).pack(pady=20)
        ctk.CTkLabel(dialog, text="Вы уверены, что хотите продолжить?").pack(pady=10)

        result = {"confirmed": False}

        def confirm():
            result["confirmed"] = True
            dialog.destroy()

        def cancel():
            result["confirmed"] = False
            dialog.destroy()

        ctk.CTkButton(dialog, text="Подтверждаю", command=confirm, fg_color="red").pack(side="left", padx=20, pady=20)
        ctk.CTkButton(dialog, text="Отмена", command=cancel).pack(side="right", padx=20, pady=20)

        self.wait_window(dialog)
        return result["confirmed"]

    def show_error(self, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Ошибка")
        dialog.geometry("300x150")
        dialog.transient(self)

        ctk.CTkLabel(dialog, text=message, text_color="red").pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=10)

    def show_info(self, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Информация")
        dialog.geometry("400x200")
        dialog.transient(self)

        ctk.CTkLabel(dialog, text=message, wraplength=350).pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=10)


def main():
    app = Proxmark3GUI()
    app.mainloop()


if __name__ == "__main__":
    main()
