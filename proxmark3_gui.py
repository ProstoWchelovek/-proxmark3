#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxmark3 Easy Iceman GUI - Графическая оболочка для Proxmark3
Полностью на русском языке, без CLI (кроме скрытой отладки)
Версия 2.0 - Полная база данных команд с описаниями
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import serial
import serial.tools.list_ports
import threading
import json
import os
import re
from datetime import datetime
from pathlib import Path

# ============================================================================
# ЗАГРУЗКА БАЗЫ ДАННЫХ КОМАНД ИЗ ФАЙЛА ОПИСАНИЙ
# ============================================================================

def load_commands_database():
    """Загружает все команды из файла 'Описание основной структуры.txt'"""
    db_file = Path(__file__).parent / "commands_full.json"
    
    if db_file.exists():
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Если JSON нет, парсим текстовый файл
    desc_file = Path(__file__).parent / "Описание основной структуры.txt"
    if not desc_file.exists():
        return []
    
    commands = []
    current_tab = None
    current_section = None
    current_item = None
    
    with open(desc_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('ВКЛАДКА'):
            if current_item:
                commands.append(current_item)
                current_item = None
            current_tab = stripped
            current_section = None
        elif stripped.startswith('ШАГ') or stripped.startswith('РАЗДЕЛ') or (':' in stripped and any(kw in stripped for kw in ['ПОИСК', 'ЧТЕНИЕ', 'ЗАПИСЬ', 'СТРУКТУРА', 'КЛЮЧИ', 'АТАКИ', 'РЕЗУЛЬТАТ'])):
            current_section = stripped
        elif stripped.endswith('!!') or (stripped.endswith('!') and not stripped.endswith('!!')):
            if not stripped.startswith('Команда:') and not stripped.startswith('Описание:') and not stripped.startswith('Параметры:') and not stripped.startswith('При нажатии:'):
                if current_item:
                    commands.append(current_item)
                icon = '!!' if stripped.endswith('!!') else '!'
                name = stripped[:-2].strip()
                current_item = {
                    'tab': current_tab or '',
                    'section': current_section or '',
                    'name': name,
                    'icon': icon,
                    'cmd': '',
                    'desc': '',
                    'params': '',
                    'action': ''
                }
        elif stripped.startswith('Команда:'):
            if current_item:
                current_item['cmd'] = stripped.replace('Команда:', '').strip()
        elif stripped.startswith('Описание:'):
            if current_item:
                current_item['desc'] = stripped.replace('Описание:', '').strip()
        elif stripped.startswith('Параметры:'):
            if current_item:
                current_item['params'] = stripped.replace('Параметры:', '').strip()
        elif stripped.startswith('При нажатии:'):
            if current_item:
                current_item['action'] = stripped.replace('При нажатии:', '').strip()
    
    if current_item:
        commands.append(current_item)
    
    # Сохраняем в JSON для ускорения последующих загрузок
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(commands, f, ensure_ascii=False, indent=2)
    
    return commands

# Загружаем базу данных при старте
COMMANDS_DB = load_commands_database()

# ============================================================================
# ГРУППИРОВКА КОМАНД ПО ВКЛАДКАМ И РАЗДЕЛАМ
# ============================================================================

def get_commands_by_tab(tab_name):
    """Возвращает список команд для указанной вкладки"""
    return [c for c in COMMANDS_DB if tab_name in c.get('tab', '')]

def get_commands_by_section(tab_name, section_name):
    """Возвращает список команд для указанного раздела вкладки"""
    return [c for c in COMMANDS_DB if tab_name in c.get('tab', '') and section_name in c.get('section', '')]

def get_protocol_commands(protocol_name):
    """Возвращает команды для конкретного протокола"""
    return [c for c in COMMANDS_DB if protocol_name in c.get('name', '')]

# ============================================================================
# ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ
# ============================================================================

class Proxmark3GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxmark3 Easy Iceman GUI")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Состояние подключения
        self.serial_conn = None
        self.is_connected = False
        self.com_port = None
        
        # Буфер данных
        self.data_buffer = ""
        
        # Создание основного интерфейса
        self.create_main_interface()
        
        # Загрузка списка COM-портов
        self.refresh_com_ports()
        
    def create_main_interface(self):
        """Создаёт основной интерфейс с вкладками"""
        # Верхняя панель с информацией о подключении
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.port_label = ttk.Label(self.top_frame, text="COM-порт:")
        self.port_label.pack(side=tk.LEFT)
        
        self.port_combo = ttk.Combobox(self.top_frame, width=15, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(self.top_frame, text="⟳", width=3, command=self.refresh_com_ports)
        self.refresh_btn.pack(side=tk.LEFT)
        
        self.connect_btn = ttk.Button(self.top_frame, text="Подключить", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        self.status_label = ttk.Label(self.top_frame, text="❌ Не подключено", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Создание вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка 1: Главная
        self.tab_main = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_main, text="🏠 Главная")
        self.create_main_tab()
        
        # Вкладка 2: Карта
        self.tab_card = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_card, text="💳 Карта")
        self.create_card_tab()
        
        # Вкладка 3: Запись
        self.tab_write = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_write, text="✏️ Запись")
        self.create_write_tab()
        
        # Вкладка 4: Снифинг
        self.tab_sniff = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sniff, text="📡 Снифинг")
        self.create_sniff_tab()
        
        # Вкладка 5: Эмуляция
        self.tab_emulate = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_emulate, text="🎭 Эмуляция")
        self.create_emulate_tab()
        
        # Вкладка 6: Данные
        self.tab_data = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_data, text="📊 Данные")
        self.create_data_tab()
        
        # Вкладка 7: Инструменты
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tools, text="🔧 Инструменты")
        self.create_tools_tab()
        
        # Вкладка 8: Скрипты
        self.tab_scripts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_scripts, text="📜 Скрипты")
        self.create_scripts_tab()
        
        # Вкладка 9: Система
        self.tab_system = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_system, text="⚙️ Система")
        self.create_system_tab()
        
        # Нижняя информационная панель
        self.bottom_frame = ttk.Frame(self.root)
        self.bottom_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(self.bottom_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Контекстное меню для копирования
        self.output_text.bind("<Button-3>", self.show_copy_menu)
        
    def show_copy_menu(self, event):
        """Показывает контекстное меню для копирования"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: self.root.clipboard_get())
        menu.add_command(label="Копировать всё", command=self.copy_all_output)
        menu.add_command(label="Очистить", command=self.clear_output)
        menu.tk_popup(event.x_root, event.y_root)
        
    def copy_all_output(self):
        """Копирует весь вывод в буфер обмена"""
        content = self.output_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        
    def clear_output(self):
        """Очищает вывод"""
        self.output_text.delete("1.0", tk.END)
        
    def refresh_com_ports(self):
        """Обновляет список доступных COM-портов"""
        ports = serial.tools.list_ports.comports()
        port_list = [f"{p.device} - {p.description}" for p in ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.current(0)
            
    def toggle_connection(self):
        """Подключает/отключает устройство"""
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        """Подключение к устройству"""
        selected = self.port_combo.get()
        if not selected:
            messagebox.showerror("Ошибка", "Выберите COM-порт")
            return
            
        self.com_port = selected.split(" - ")[0]
        
        try:
            self.serial_conn = serial.Serial(self.com_port, 115200, timeout=1)
            self.is_connected = True
            self.connect_btn.config(text="Отключить")
            self.status_label.config(text="✅ Подключено", foreground="green")
            self.log_message(f"Подключено к {self.com_port}")
            
            # Получаем версию устройства
            self.send_command("hw version", show_output=True)
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", str(e))
            self.log_message(f"Ошибка подключения: {e}")
            
    def disconnect(self):
        """Отключение от устройства"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
        self.serial_conn = None
        self.is_connected = False
        self.connect_btn.config(text="Подключить")
        self.status_label.config(text="❌ Не подключено", foreground="red")
        self.log_message("Отключено от устройства")
        
    def send_command(self, cmd, show_output=True):
        """Отправляет команду устройству"""
        if not self.is_connected:
            if show_output:
                self.log_message("❌ Устройство не подключено")
            return
            
        try:
            full_cmd = cmd + "\n"
            self.serial_conn.write(full_cmd.encode('utf-8'))
            
            if show_output:
                self.log_message(f">>> {cmd}")
                
                # Читаем ответ (неблокирующе в потоке)
                threading.Thread(target=self.read_response, daemon=True).start()
                
        except Exception as e:
            self.log_message(f"Ошибка отправки: {e}")
            
    def read_response(self):
        """Читает ответ от устройства"""
        try:
            while self.is_connected and self.serial_conn and self.serial_conn.in_waiting:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self.root.after(0, lambda l=line: self.log_message(l))
        except:
            pass
            
    def log_message(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.output_text.see(tk.END)
        
    def create_info_button(self, parent, command_data):
        """Создаёт кнопку информации с подсказкой"""
        icon = command_data.get('icon', '!')
        name = command_data.get('name', '')
        desc = command_data.get('desc', 'Нет описания')
        cmd = command_data.get('cmd', '')
        params = command_data.get('params', '')
        
        # Цвет иконки: !! = зелёный, ! = синий
        bg_color = "#28a745" if icon == '!!' else "#007bff"
        
        btn = tk.Button(parent, text=icon, width=2, height=1, 
                       bg=bg_color, fg="white", font=("Arial", 9, "bold"),
                       relief=tk.FLAT, cursor="hand2")
        
        # При наведении показываем подсказку
        tooltip_text = f"{name}\n\n{desc}"
        if params:
            tooltip_text += f"\n\nПараметры: {params}"
        if cmd:
            tooltip_text += f"\n\nКоманда: {cmd}"
            
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=tooltip_text, justify=tk.LEFT,
                           background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                           font=("Arial", 9), padx=10, pady=5)
            label.pack()
            
            tooltip.attributes('-topmost', True)
            
            def hide_tooltip(event=None):
                tooltip.destroy()
                
            tooltip.bind("<Leave>", hide_tooltip)
            label.bind("<Leave>", hide_tooltip)
            
        btn.bind("<Enter>", show_tooltip)
        
        # При нажатии: если !! выполняем команду info
        if icon == '!!' and cmd:
            def on_click(event=None):
                # Формируем команду info
                info_cmd = cmd.replace(' info', '') + ' info'
                if not info_cmd.endswith(' info'):
                    info_cmd = cmd + ' info'
                self.send_command(info_cmd, show_output=True)
            btn.bind("<Button-1>", on_click)
            
        return btn
        
    # ========================================================================
    # СОЗДАНИЕ ВКЛАДОК
    # ========================================================================
    
    def create_main_tab(self):
        """Создаёт вкладку Главная"""
        main_frame = ttk.Frame(self.tab_main, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Группа подключения
        conn_group = ttk.LabelFrame(main_frame, text="Подключение", padding=10)
        conn_group.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(conn_group)
        btn_frame.pack(fill=tk.X)
        
        # Кнопка Подключить/Отключить уже в верхней панели
        
        # Кнопка Версии
        versions_cmd = next((c for c in COMMANDS_DB if 'hw version' in c.get('cmd', '')), None)
        if versions_cmd:
            btn = ttk.Button(btn_frame, text="Версии", 
                           command=lambda: self.send_command("hw version", show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, versions_cmd).pack(side=tk.LEFT, padx=2)
            
        # Кнопка Настройка антенн
        tune_cmd = next((c for c in COMMANDS_DB if 'hw tune' in c.get('cmd', '')), None)
        if tune_cmd:
            btn = ttk.Button(btn_frame, text="Настройка антенн",
                           command=lambda: self.send_command("hw tune", show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, tune_cmd).pack(side=tk.LEFT, padx=2)
            
        # Кнопка Автопоиск
        auto_cmd = next((c for c in COMMANDS_DB if c.get('name') == 'Автопоиск'), None)
        if auto_cmd:
            btn = ttk.Button(btn_frame, text="Автопоиск",
                           command=lambda: self.send_command("auto", show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, auto_cmd).pack(side=tk.LEFT, padx=2)
            
        # Индикатор статуса
        status_group = ttk.LabelFrame(main_frame, text="Статус устройства", padding=10)
        status_group.pack(fill=tk.X, pady=5)
        
        self.device_status = ttk.Label(status_group, text="Нет данных")
        self.device_status.pack()
        
        # Кнопка обновления статуса
        status_btn = ttk.Button(status_group, text="Обновить статус",
                              command=lambda: self.send_command("hw status", show_output=True))
        status_btn.pack(pady=5)
        
        status_cmd = next((c for c in COMMANDS_DB if 'hw status' in c.get('cmd', '')), None)
        if status_cmd:
            self.create_info_button(status_group, status_cmd).pack()
            
    def create_card_tab(self):
        """Создаёт вкладку Карта с 6 шагами"""
        card_frame = ttk.Frame(self.tab_card, padding=10)
        card_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаём 6 шагов
        steps = [
            ("1. Поиск", "search"),
            ("2. Чтение", "read"),
            ("3. Структура", "structure"),
            ("4. Ключи", "keys"),
            ("5. Атаки", "attacks"),
            ("6. Результат", "result")
        ]
        
        self.card_step_vars = {}
        
        for step_name, step_id in steps:
            step_frame = ttk.LabelFrame(card_frame, text=step_name, padding=10)
            step_frame.pack(fill=tk.X, pady=5)
            
            self.card_step_vars[step_id] = step_frame
            
            # Добавляем кнопки для каждого шага
            if step_id == "search":
                self.create_search_step(step_frame)
            elif step_id == "read":
                self.create_read_step(step_frame)
            elif step_id == "structure":
                self.create_structure_step(step_frame)
            elif step_id == "keys":
                self.create_keys_step(step_frame)
            elif step_id == "attacks":
                self.create_attacks_step(step_frame)
            elif step_id == "result":
                self.create_result_step(step_frame)
                
    def create_search_step(self, parent):
        """Создаёт шаг поиска"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)
        
        # Общий поиск
        auto_cmd = next((c for c in COMMANDS_DB if c.get('name') == 'ОБЩИЙ ПОИСК'), None)
        btn = ttk.Button(btn_frame, text="Общий поиск (auto)",
                        command=lambda: self.send_command("auto", show_output=True))
        btn.pack(side=tk.LEFT, padx=5)
        if auto_cmd:
            self.create_info_button(btn_frame, auto_cmd).pack(side=tk.LEFT, padx=2)
            
        # Поиск LF
        lf_search_cmd = next((c for c in COMMANDS_DB if c.get('name') == 'ПОИСК LF'), None)
        btn = ttk.Button(btn_frame, text="Поиск LF",
                        command=lambda: self.send_command("lf search", show_output=True))
        btn.pack(side=tk.LEFT, padx=5)
        if lf_search_cmd:
            self.create_info_button(btn_frame, lf_search_cmd).pack(side=tk.LEFT, padx=2)
            
        # Поиск HF
        hf_search_cmd = next((c for c in COMMANDS_DB if c.get('name') == 'ПОИСК HF'), None)
        btn = ttk.Button(btn_frame, text="Поиск HF",
                        command=lambda: self.send_command("hf search", show_output=True))
        btn.pack(side=tk.LEFT, padx=5)
        if hf_search_cmd:
            self.create_info_button(btn_frame, hf_search_cmd).pack(side=tk.LEFT, padx=2)
            
        # Выпадающий список протоколов
        proto_frame = ttk.Frame(parent)
        proto_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(proto_frame, text="Протокол:").pack(side=tk.LEFT)
        
        self.protocol_combo = ttk.Combobox(proto_frame, width=30, state="readonly")
        self.protocol_combo.pack(side=tk.LEFT, padx=5)
        
        # Заполняем список протоколов
        protocols = []
        for cmd in COMMANDS_DB:
            name = cmd.get('name', '')
            if name.startswith('LF:') or name.startswith('HF:') or name in ['NFC', 'EMV', 'Smart card (ISO 7816)', 'PIV']:
                protocols.append(name)
                
        self.protocol_combo['values'] = protocols
        self.protocol_combo.bind("<<ComboboxSelected>>", self.on_protocol_selected)
        
    def on_protocol_selected(self, event):
        """Обработчик выбора протокола"""
        selected = self.protocol_combo.get()
        # Здесь можно показать специфичные команды для выбранного протокола
        self.log_message(f"Выбран протокол: {selected}")
        
    def create_read_step(self, parent):
        """Создаёт шаг чтения"""
        # Кнопки будут добавляться динамически в зависимости от выбранного протокола
        ttk.Label(parent, text="Выберите протокол на шаге 1 для отображения команд чтения").pack()
        
    def create_structure_step(self, parent):
        """Создаёт шаг анализа структуры"""
        ttk.Label(parent, text="Команды анализа структуры карты").pack()
        
        structure_cmds = [c for c in COMMANDS_DB if 'структур' in c.get('section', '').lower()]
        for cmd in structure_cmds[:5]:  # Показываем первые 5
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill=tk.X, pady=2)
            
            btn_name = cmd.get('name', 'Unknown')
            btn_cmd = cmd.get('cmd', '')
            
            btn = ttk.Button(btn_frame, text=btn_name,
                           command=lambda c=btn_cmd: self.send_command(c, show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, cmd).pack(side=tk.LEFT, padx=2)
            
    def create_keys_step(self, parent):
        """Создаёт шаг работы с ключами"""
        ttk.Label(parent, text="Проверка ключей из словаря").pack()
        
        key_cmds = [c for c in COMMANDS_DB if any(kw in c.get('name', '').lower() for kw in ['chk', 'ключ', 'key'])]
        for cmd in key_cmds[:5]:
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill=tk.X, pady=2)
            
            btn_name = cmd.get('name', 'Unknown')
            btn_cmd = cmd.get('cmd', '')
            
            btn = ttk.Button(btn_frame, text=btn_name,
                           command=lambda c=btn_cmd: self.send_command(c, show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, cmd).pack(side=tk.LEFT, padx=2)
            
    def create_attacks_step(self, parent):
        """Создаёт шаг атак"""
        ttk.Label(parent, text="Атаки и восстановление ключей").pack()
        
        attack_cmds = [c for c in COMMANDS_DB if any(kw in c.get('name', '').lower() for kw in ['attack', 'nested', 'hardnested', 'darkside', 'brute'])]
        for cmd in attack_cmds[:5]:
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill=tk.X, pady=2)
            
            btn_name = cmd.get('name', 'Unknown')
            btn_cmd = cmd.get('cmd', '')
            
            btn = ttk.Button(btn_frame, text=btn_name,
                           command=lambda c=btn_cmd: self.send_command(c, show_output=True))
            btn.pack(side=tk.LEFT, padx=5)
            self.create_info_button(btn_frame, cmd).pack(side=tk.LEFT, padx=2)
            
    def create_result_step(self, parent):
        """Создаёт шаг результата"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Сохранить в файл", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Перейти в Запись", 
                  command=lambda: self.notebook.select(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Перейти в Эмуляцию",
                  command=lambda: self.notebook.select(4)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть в Данных",
                  command=lambda: self.notebook.select(5)).pack(side=tk.LEFT, padx=5)
                  
    def save_to_file(self):
        """Сохраняет текущий вывод в файл"""
        filename = filedialog.asksaveasfilename(defaultextension=".txt",
                                               filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")])
        if filename:
            content = self.output_text.get("1.0", tk.END)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_message(f"Сохранено в {filename}")
            
    def create_write_tab(self):
        """Создаёт вкладку Запись"""
        write_frame = ttk.Frame(self.tab_write, padding=10)
        write_frame.pack(fill=tk.BOTH, expand=True)
        
        # Шаг 1: Источник
        source_group = ttk.LabelFrame(write_frame, text="Шаг 1: Источник данных", padding=10)
        source_group.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(source_group, text="Из файла", variable=tk.StringVar(value="file")).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(source_group, text="Из буфера", variable=tk.StringVar(value="buffer")).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(source_group, text="Из сохранённых карт", variable=tk.StringVar(value="saved")).pack(side=tk.LEFT, padx=10)
        
        # Шаг 2: Цель
        target_group = ttk.LabelFrame(write_frame, text="Шаг 2: Цель", padding=10)
        target_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(target_group, text="Определить тип карты",
                  command=lambda: self.send_command("auto", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Шаг 3: Запись
        write_group = ttk.LabelFrame(write_frame, text="Шаг 3: Запись", padding=10)
        write_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(write_group, text="Записать (HF)",
                  command=lambda: self.log_message("Выберите конкретную команду записи")).pack(side=tk.LEFT, padx=5)
        ttk.Button(write_group, text="Записать (LF)",
                  command=lambda: self.log_message("Выберите конкретную команду записи")).pack(side=tk.LEFT, padx=5)
                  
        # Шаг 4: Верификация
        verify_group = ttk.LabelFrame(write_frame, text="Шаг 4: Верификация", padding=10)
        verify_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(verify_group, text="Проверить запись",
                  command=lambda: self.send_command("hf search", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
    def create_sniff_tab(self):
        """Создаёт вкладку Снифинг"""
        sniff_frame = ttk.Frame(self.tab_sniff, padding=10)
        sniff_frame.pack(fill=tk.BOTH, expand=True)
        
        # Тип сниффинга
        type_group = ttk.LabelFrame(sniff_frame, text="Тип сниффинга", padding=10)
        type_group.pack(fill=tk.X, pady=5)
        
        self.sniff_type = ttk.Combobox(type_group, values=[
            "Общий HF", "ISO 14443A", "ISO 14443B", "ISO 15693", 
            "LF", "Legic", "iClass", "FeliCa", "Hitag", "Автономный режим"
        ], state="readonly")
        self.sniff_type.current(0)
        self.sniff_type.pack(side=tk.LEFT, padx=5)
        
        # Управление
        control_group = ttk.LabelFrame(sniff_frame, text="Управление", padding=10)
        control_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_group, text="Старт захвата",
                  command=lambda: self.send_command("hf 14a sniff", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_group, text="Стоп захвата",
                  command=lambda: self.send_command("", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Анализ
        analysis_group = ttk.LabelFrame(sniff_frame, text="Анализ", padding=10)
        analysis_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(analysis_group, text="Разбор трейса (trace list)",
                  command=lambda: self.send_command("trace list", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(analysis_group, text="Извлечь параметры (trace extract)",
                  command=lambda: self.send_command("trace extract", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(analysis_group, text="Сохранить трейс",
                  command=lambda: self.send_command("trace save", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(analysis_group, text="Загрузить трейс",
                  command=lambda: self.send_command("trace load", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
    def create_emulate_tab(self):
        """Создаёт вкладку Эмуляция"""
        emulate_frame = ttk.Frame(self.tab_emulate, padding=10)
        emulate_frame.pack(fill=tk.BOTH, expand=True)
        
        # Источник
        source_group = ttk.LabelFrame(emulate_frame, text="Источник данных", padding=10)
        source_group.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(source_group, text="Из файла", variable=tk.StringVar(value="file")).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(source_group, text="Из буфера", variable=tk.StringVar(value="buffer")).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(source_group, text="Ввести вручную", variable=tk.StringVar(value="manual")).pack(side=tk.LEFT, padx=10)
        
        # Загрузка в эмулятор
        load_group = ttk.LabelFrame(emulate_frame, text="Загрузка в эмулятор", padding=10)
        load_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(load_group, text="Загрузить (eload)",
                  command=lambda: self.send_command("hf mf eload", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Тип эмуляции
        sim_group = ttk.LabelFrame(emulate_frame, text="Тип эмуляции", padding=10)
        sim_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(sim_group, text="Эмуляция Mifare",
                  command=lambda: self.send_command("hf mf sim", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(sim_group, text="Эмуляция ISO 14443A",
                  command=lambda: self.send_command("hf 14a sim", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Запуск
        run_group = ttk.LabelFrame(emulate_frame, text="Запуск", padding=10)
        run_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(run_group, text="Старт эмуляции",
                  command=lambda: self.log_message("Эмуляция запущена")).pack(side=tk.LEFT, padx=5)
        ttk.Button(run_group, text="Стоп эмуляции",
                  command=lambda: self.log_message("Эмуляция остановлена")).pack(side=tk.LEFT, padx=5)
                  
    def create_data_tab(self):
        """Создаёт вкладку Данные"""
        data_frame = ttk.Frame(self.tab_data, padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True)
        
        # Сохранённые дампы
        dumps_group = ttk.LabelFrame(data_frame, text="Сохранённые дампы", padding=10)
        dumps_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(dumps_group, text="Загрузить дамп",
                  command=lambda: self.log_message("Загрузка дампа")).pack(side=tk.LEFT, padx=5)
        ttk.Button(dumps_group, text="Сохранить дамп",
                  command=self.save_to_file).pack(side=tk.LEFT, padx=5)
                  
        # Словари ключей
        dicts_group = ttk.LabelFrame(data_frame, text="Словари ключей (.dic)", padding=10)
        dicts_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(dicts_group, text="Просмотреть словари",
                  command=lambda: self.log_message("Просмотр словарей")).pack(side=tk.LEFT, padx=5)
        ttk.Button(dicts_group, text="Добавить словарь",
                  command=lambda: self.log_message("Добавление словаря")).pack(side=tk.LEFT, padx=5)
                  
        # Flash-память
        flash_group = ttk.LabelFrame(data_frame, text="Flash-память", padding=10)
        flash_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(flash_group, text="mem info",
                  command=lambda: self.send_command("mem info", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(flash_group, text="mem dump",
                  command=lambda: self.send_command("mem dump", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(flash_group, text="mem wipe",
                  command=lambda: self.confirm_dangerous("mem wipe")).pack(side=tk.LEFT, padx=5)
                  
        # Трейсы
        traces_group = ttk.LabelFrame(data_frame, text="Трейсы", padding=10)
        traces_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(traces_group, text="trace list",
                  command=lambda: self.send_command("trace list", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(traces_group, text="trace load",
                  command=lambda: self.send_command("trace load", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(traces_group, text="trace save",
                  command=lambda: self.send_command("trace save", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(traces_group, text="trace extract",
                  command=lambda: self.send_command("trace extract", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Буфер данных
        buffer_group = ttk.LabelFrame(data_frame, text="Буфер данных", padding=10)
        buffer_group.pack(fill=tk.X, pady=5)
        
        data_cmds = ["data plot", "data rawdemod", "data detectclock", "data manrawdecode", 
                    "data biphaserawdecode", "data fsktonrz", "data num", "data crypto", "data asn1"]
        for cmd in data_cmds:
            ttk.Button(buffer_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
    def create_tools_tab(self):
        """Создаёт вкладку Инструменты"""
        tools_frame = ttk.Frame(self.tab_tools, padding=10)
        tools_frame.pack(fill=tk.BOTH, expand=True)
        
        # Analyse
        analyse_group = ttk.LabelFrame(tools_frame, text="Analyse", padding=10)
        analyse_group.pack(fill=tk.X, pady=5)
        
        analyse_cmds = ["analyse lrc", "analyse crc", "analyse chksum", "analyse dates", 
                       "analyse lfsr", "analyse nuid"]
        for cmd in analyse_cmds:
            ttk.Button(analyse_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # Wiegand
        wiegand_group = ttk.LabelFrame(tools_frame, text="Wiegand", padding=10)
        wiegand_group.pack(fill=tk.X, pady=5)
        
        wiegand_cmds = ["wiegand list", "wiegand encode", "wiegand decode"]
        for cmd in wiegand_cmds:
            ttk.Button(wiegand_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # RevEng (CRC)
        reveng_group = ttk.LabelFrame(tools_frame, text="RevEng (CRC)", padding=10)
        reveng_group.pack(fill=tk.X, pady=5)
        
        reveng_cmds = ["reveng calc", "reveng search"]
        for cmd in reveng_cmds:
            ttk.Button(reveng_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # USART / Bluetooth
        usart_group = ttk.LabelFrame(tools_frame, text="USART / Bluetooth", padding=10)
        usart_group.pack(fill=tk.X, pady=5)
        
        usart_cmds = ["usart tx", "usart rx", "usart txhex", "usart rxhex", 
                     "bluetooth btpin", "bluetooth btfactory"]
        for cmd in usart_cmds:
            ttk.Button(usart_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # MQTT
        mqtt_group = ttk.LabelFrame(tools_frame, text="MQTT", padding=10)
        mqtt_group.pack(fill=tk.X, pady=5)
        
        mqtt_cmds = ["mqtt send", "mqtt receive"]
        for cmd in mqtt_cmds:
            ttk.Button(mqtt_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # HF специальные
        hf_spec_group = ttk.LabelFrame(tools_frame, text="HF специальные", padding=10)
        hf_spec_group.pack(fill=tk.X, pady=5)
        
        hf_spec_cmds = ["hf plot", "hf tune", "hf 14a config"]
        for cmd in hf_spec_cmds:
            ttk.Button(hf_spec_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # LF специальные
        lf_spec_group = ttk.LabelFrame(tools_frame, text="LF специальные", padding=10)
        lf_spec_group.pack(fill=tk.X, pady=5)
        
        lf_spec_cmds = ["lf config", "lf cmdread", "lf relay"]
        for cmd in lf_spec_cmds:
            ttk.Button(lf_spec_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
    def create_scripts_tab(self):
        """Создаёт вкладку Скрипты"""
        scripts_frame = ttk.Frame(self.tab_scripts, padding=10)
        scripts_frame.pack(fill=tk.BOTH, expand=True)
        
        # Список скриптов
        list_group = ttk.LabelFrame(scripts_frame, text="Список скриптов", padding=10)
        list_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(list_group, text="script list",
                  command=lambda: self.send_command("script list", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Выбор скрипта
        select_group = ttk.LabelFrame(scripts_frame, text="Запустить скрипт", padding=10)
        select_group.pack(fill=tk.X, pady=5)
        
        self.script_combo = ttk.Combobox(select_group, width=40, state="readonly")
        self.script_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(select_group, text="Запустить",
                  command=self.run_selected_script).pack(side=tk.LEFT, padx=5)
                  
        # Python-скрипты
        python_group = ttk.LabelFrame(scripts_frame, text="Python-скрипты", padding=10)
        python_group.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.python_scripts_text = scrolledtext.ScrolledText(python_group, height=5)
        self.python_scripts_text.pack(fill=tk.BOTH, expand=True)
        
        # Lua-скрипты
        lua_group = ttk.LabelFrame(scripts_frame, text="Lua-скрипты", padding=10)
        lua_group.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.lua_scripts_text = scrolledtext.ScrolledText(lua_group, height=5)
        self.lua_scripts_text.pack(fill=tk.BOTH, expand=True)
        
        # Загрузка списка скриптов
        self.load_scripts_list()
        
    def load_scripts_list(self):
        """Загружает список доступных скриптов"""
        self.send_command("script list", show_output=False)
        # В реальном приложении здесь был бы парсинг ответа
        
    def run_selected_script(self):
        """Запускает выбранный скрипт"""
        selected = self.script_combo.get()
        if selected:
            self.send_command(f"script run {selected}", show_output=True)
        else:
            messagebox.showwarning("Предупреждение", "Выберите скрипт из списка")
            
    def create_system_tab(self):
        """Создаёт вкладку Система"""
        system_frame = ttk.Frame(self.tab_system, padding=10)
        system_frame.pack(fill=tk.BOTH, expand=True)
        
        # Прошивка
        fw_group = ttk.LabelFrame(system_frame, text="Прошивка", padding=10)
        fw_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(fw_group, text="Обновить прошивку",
                  command=lambda: self.log_message("Обновление прошивки")).pack(side=tk.LEFT, padx=5)
        ttk.Button(fw_group, text="Режим загрузчика",
                  command=lambda: self.log_message("Режим загрузчика")).pack(side=tk.LEFT, padx=5)
                  
        # Устройство
        device_group = ttk.LabelFrame(system_frame, text="Устройство", padding=10)
        device_group.pack(fill=tk.X, pady=5)
        
        device_cmds = ["hw status", "hw reset", "hw check", "hw tune", 
                      "mem info", "hw mux", "hw antennas", "hw cancel"]
        for cmd in device_cmds:
            ttk.Button(device_group, text=cmd,
                      command=lambda c=cmd: self.send_command(c, show_output=True)).pack(side=tk.LEFT, padx=2)
                      
        # Настройки клиента
        prefs_group = ttk.LabelFrame(system_frame, text="Настройки клиента", padding=10)
        prefs_group.pack(fill=tk.X, pady=5)
        
        ttk.Button(prefs_group, text="prefs show",
                  command=lambda: self.send_command("prefs show", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        self.pref_entry = ttk.Entry(prefs_group, width=30)
        self.pref_entry.pack(side=tk.LEFT, padx=5)
        self.pref_entry.insert(0, "client.debug")
        
        ttk.Button(prefs_group, text="prefs set",
                  command=lambda: self.send_command(f"prefs set {self.pref_entry.get()} 1", show_output=True)).pack(side=tk.LEFT, padx=5)
                  
        # Отладка (скрытая по умолчанию)
        self.debug_visible = tk.BooleanVar(value=False)
        debug_check = ttk.Checkbutton(system_frame, text="☢️ Показать отладку", 
                                     variable=self.debug_visible, command=self.toggle_debug)
        debug_check.pack(anchor=tk.W, pady=5)
        
        self.debug_frame = ttk.LabelFrame(system_frame, text="Отладка", padding=10)
        if not self.debug_visible.get():
            self.debug_frame.pack_forget()
            
        ttk.Button(self.debug_frame, text="data setdebugmode",
                  command=lambda: self.send_command("data setdebugmode", show_output=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.debug_frame, text="CLI-режим",
                  command=self.enable_cli_mode).pack(side=tk.LEFT, padx=5)
                  
        # Опасные операции
        danger_group = ttk.LabelFrame(system_frame, text="⚠️ Опасные операции", padding=10)
        danger_group.pack(fill=tk.X, pady=5)
        
        danger_cmds = [
            ("mem wipe", "mem wipe"),
            ("HF 15 cfinalize", "hf 15 cfinalize"),
            ("HF Mifare gen3freeze", "hf mf gen3freeze"),
            ("HF CIPURSE formatall", "hf cipurse formatall"),
            ("HF DESFire formatpicc", "hf mfdes formatpicc"),
            ("LF T55xx wipe", "lf t55xx wipe"),
            ("HF Mifare gchpwd", "hf mf gchpwd"),
            ("HF Mifare cwipe", "hf mf cwipe"),
            ("HF Mifare gdmwipe", "hf mf gdmwipe")
        ]
        
        for name, cmd in danger_cmds:
            ttk.Button(danger_group, text=name,
                      command=lambda c=cmd: self.confirm_dangerous(c)).pack(side=tk.LEFT, padx=2)
                      
    def toggle_debug(self):
        """Переключает видимость панели отладки"""
        if self.debug_visible.get():
            self.debug_frame.pack(fill=tk.X, pady=5)
        else:
            self.debug_frame.pack_forget()
            
    def enable_cli_mode(self):
        """Включает CLI-режим"""
        if messagebox.askyesno("Подтверждение", "Включить CLI-режим?\nЭто может быть опасно!"):
            self.send_command("data setdebugmode", show_output=True)
            self.log_message("⚠️ CLI-режим включён")
            
    def confirm_dangerous(self, cmd):
        """Подтверждение опасной операции"""
        if messagebox.askyesno("⚠️ ОПАСНАЯ ОПЕРАЦИЯ", 
                              f"Вы уверены, что хотите выполнить:\n{cmd}\n\nЭто действие может быть необратимым!",
                              icon=messagebox.WARNING):
            self.send_command(cmd, show_output=True)
            self.log_message(f"⚠️ Выполнена опасная операция: {cmd}")


# ============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = Proxmark3GUI(root)
    root.mainloop()
