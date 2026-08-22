#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxmark3 Iceman Seamless Application
Единое приложение для установки, прошивки и работы с Proxmark3
Версия 1.0 - "Из коробки"
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import sys
import os
import json
import re
import platform
from pathlib import Path
from datetime import datetime
import serial
import serial.tools.list_ports

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

class Config:
    """Глобальная конфигурация приложения"""
    APP_NAME = "Proxmark3 Iceman Seamless"
    VERSION = "1.0"
    PM3_REPO_URL = "https://github.com/RfidResearchGroup/proxmark3.git"
    PM3_DIR = Path.home() / "proxmark3"
    CLIENT_PATH = PM3_DIR / "client" / "pm3"
    FIRMWARE_PATH = PM3_DIR / "armsrc" / "obj" / "fullimage.elf"
    BOOTROM_PATH = PM3_DIR / "bootrom" / "obj" / "bootrom.elf"
    LOG_FILE = Path.home() / ".proxmark3_seamless.log"
    
    @classmethod
    def get_platform(cls):
        """Определяет платформу"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            return "linux"
    
    @classmethod
    def is_installed(cls):
        """Проверяет, установлен ли Proxmark3"""
        return cls.PM3_DIR.exists() and (cls.CLIENT_PATH.exists() or 
                (platform.system() != "Windows" and (cls.PM3_DIR / "client" / "pm3").exists()))

# ============================================================================
# МЕНЕДЖЕР УСТАНОВКИ
# ============================================================================

class InstallationManager:
    """Управляет установкой всех компонентов"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.process = None
        self.is_running = False
    
    def log(self, message):
        """Логирование сообщения"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"
        if self.log_callback:
            self.log_callback(full_msg)
        print(full_msg)
    
    def check_dependencies(self):
        """Проверяет наличие зависимостей"""
        self.log("🔍 Проверка зависимостей...")
        missing = []
        
        # Python
        try:
            import serial
            self.log("✅ Python и pyserial найдены")
        except ImportError:
            missing.append("pyserial")
        
        # Компиляторы
        compilers = {
            "gcc": "GCC компилятор",
            "make": "Make",
            "git": "Git"
        }
        
        for cmd, name in compilers.items():
            try:
                result = subprocess.run([cmd, "--version"], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.log(f"✅ {name} найден")
                else:
                    missing.append(name)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                missing.append(name)
        
        if missing:
            self.log(f"⚠️ Отсутствуют: {', '.join(missing)}")
            return False
        
        self.log("✅ Все зависимости установлены")
        return True
    
    def install_dependencies_linux(self):
        """Устанавливает зависимости на Linux"""
        self.log("📦 Установка зависимостей...")
        
        distro_commands = {
            "ubuntu": "apt-get update && apt-get install -y git gcc make libreadline-dev libncurses5-dev libbluetooth-dev libusb-1.0-0-dev qt5-default qtmultimedia5-dev libssl-dev liblua5.3-dev libpython3-dev python3-pip",
            "debian": "apt-get update && apt-get install -y git gcc make libreadline-dev libncurses5-dev libbluetooth-dev libusb-1.0-0-dev qt5-default qtmultimedia5-dev libssl-dev liblua5.3-dev libpython3-dev python3-pip",
            "fedora": "dnf install -y git gcc make readline-devel ncurses-devel bluetooth-devel libusb1-devel qt5-qtmultimedia-devel openssl-devel lua-devel python3-devel python3-pip",
            "arch": "pacman -S --noconfirm git gcc make readline ncurses bluez libusb qt5-multimedia openssl lua python python-pip"
        }
        
        # Определяем дистрибутив
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                distro = "ubuntu"
                if "fedora" in content:
                    distro = "fedora"
                elif "arch" in content:
                    distro = "arch"
                elif "debian" in content:
                    distro = "debian"
            
            cmd = distro_commands.get(distro, distro_commands["ubuntu"])
            self.log(f"📦 Установка для {distro}...")
            
            self.process = subprocess.Popen(
                ["sudo", "bash", "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            for line in self.process.stdout:
                self.log(line.decode().strip())
            
            self.process.wait()
            
            # Установка pyserial
            subprocess.run([sys.executable, "-m", "pip", "install", "pyserial"], 
                          check=True)
            
            self.log("✅ Зависимости установлены")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка установки: {e}")
            return False
    
    def clone_repository(self):
        """Клонирует репозиторий Proxmark3"""
        if not self.check_dependencies():
            self.log("⚠️ Сначала установите зависимости")
            return False
        
        self.log(f"📥 Клонирование репозитория в {Config.PM3_DIR}...")
        
        try:
            if Config.PM3_DIR.exists():
                self.log("ℹ️ Репозиторий уже существует, обновляем...")
                self.process = subprocess.Popen(
                    ["git", "-C", str(Config.PM3_DIR), "pull"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            else:
                self.process = subprocess.Popen(
                    ["git", "clone", Config.PM3_REPO_URL, str(Config.PM3_DIR)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            
            for line in self.process.stdout:
                self.log(line.strip())
            
            self.process.wait()
            
            if self.process.returncode == 0:
                self.log("✅ Репозиторий готов")
                return True
            else:
                self.log("❌ Ошибка клонирования/обновления")
                return False
                
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            return False
    
    def compile_firmware(self):
        """Компилирует прошивку и клиент"""
        self.log("🔨 Компиляция прошивки и клиента...")
        
        try:
            # Переходим в директорию
            os.chdir(Config.PM3_DIR)
            
            # Компиляция
            self.process = subprocess.Popen(
                ["make", "clean", "&&", "make", "-j4"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True
            )
            
            for line in self.process.stdout:
                self.log(line.strip())
            
            self.process.wait()
            
            if self.process.returncode == 0:
                self.log("✅ Компиляция завершена успешно")
                return True
            else:
                self.log("❌ Ошибка компиляции")
                return False
                
        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            return False
    
    def flash_device(self, device_path=None):
        """Прошивает устройство"""
        self.log("💾 Прошивка устройства...")
        
        try:
            # Поиск устройства
            if not device_path:
                devices = self.find_devices()
                if not devices:
                    self.log("❌ Устройство не найдено. Подключите Proxmark3")
                    return False
                device_path = devices[0][0]
                self.log(f"📱 Найдено устройство: {device_path}")
            
            # Прошивка bootrom
            self.log("🔄 Прошивка bootrom...")
            if Config.BOOTROM_PATH.exists():
                result = subprocess.run(
                    [str(Config.CLIENT_PATH), "-c", f"flash write {Config.BOOTROM_PATH}"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                self.log(result.stdout)
                if result.returncode != 0:
                    self.log(f"⚠️ Bootrom: {result.stderr}")
            
            # Прошивка fullimage
            self.log("🔄 Прошивка fullimage...")
            if Config.FIRMWARE_PATH.exists():
                result = subprocess.run(
                    [str(Config.CLIENT_PATH), "-c", f"flash write {Config.FIRMWARE_PATH}"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                self.log(result.stdout)
                if result.returncode != 0:
                    self.log(f"⚠️ Fullimage: {result.stderr}")
            
            self.log("✅ Прошивка завершена")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка прошивки: {e}")
            return False
    
    def find_devices(self):
        """Ищет подключенные устройства Proxmark3"""
        devices = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Ищем по VID/PID Proxmark3
            if port.vid == 0x9AC4 or port.vid == 0x29B9 or "proxmark" in port.description.lower():
                devices.append((port.device, port.description))
        
        return devices
    
    def run_client(self):
        """Запускает клиент Proxmark3"""
        self.log("🚀 Запуск клиента...")
        
        try:
            if not Config.CLIENT_PATH.exists():
                self.log("❌ Клиент не найден. Сначала выполните компиляцию")
                return False
            
            subprocess.Popen([str(Config.CLIENT_PATH)])
            self.log("✅ Клиент запущен")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка запуска: {e}")
            return False

# ============================================================================
# GUI ПРИЛОЖЕНИЕ
# ============================================================================

class SeamlessApp:
    """Основное приложение"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{Config.APP_NAME} v{Config.VERSION}")
        self.root.geometry("1000x700")
        
        # Менеджер установки
        self.installer = InstallationManager(self.log_message)
        
        # Создание интерфейса
        self.create_ui()
        
        # Начальная проверка
        self.check_status()
    
    def create_ui(self):
        """Создает пользовательский интерфейс"""
        # Стили
        style = ttk.Style()
        style.theme_use('clam')
        
        # Главная рамка
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = ttk.Label(main_frame, 
                               text=f"🔷 {Config.APP_NAME}",
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)
        
        # Вкладки
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Вкладка установки
        install_frame = ttk.Frame(notebook, padding="10")
        notebook.add(install_frame, text="📦 Установка")
        self.create_install_tab(install_frame)
        
        # Вкладка прошивки
        flash_frame = ttk.Frame(notebook, padding="10")
        notebook.add(flash_frame, text="💾 Прошивка")
        self.create_flash_tab(flash_frame)
        
        # Вкладка управления
        control_frame = ttk.Frame(notebook, padding="10")
        notebook.add(control_frame, text="🎮 Управление")
        self.create_control_tab(control_frame)
        
        # Вкладка лога
        log_frame = ttk.Frame(notebook, padding="10")
        notebook.add(log_frame, text="📋 Лог")
        self.create_log_tab(log_frame)
        
        # Строка состояния
        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(main_frame, 
                              textvariable=self.status_var,
                              relief=tk.SUNKEN,
                              anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def create_install_tab(self, parent):
        """Создает вкладку установки"""
        # Инструкция
        instr_frame = ttk.LabelFrame(parent, text="📖 Инструкция", padding="10")
        instr_frame.pack(fill=tk.X, pady=5)
        
        instructions = [
            "1. Убедитесь, что у вас есть подключение к интернету",
            "2. Нажмите 'Авто-установка' для установки всех зависимостей",
            "3. Дождитесь клонирования репозитория Proxmark3",
            "4. Выполните компиляцию прошивки и клиента",
            "5. Подключите устройство Proxmark3 по USB",
            "6. Перейдите на вкладку 'Прошивка' для прошивки устройства"
        ]
        
        for instr in instructions:
            ttk.Label(instr_frame, text=instr).pack(anchor=tk.W)
        
        # Кнопки установки
        btn_frame = ttk.Frame(parent, padding="10")
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="🔍 Проверить зависимости",
                  command=self.check_dependencies_thread).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📦 Авто-установка (Linux)",
                  command=self.auto_install_thread).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📥 Клонировать репозиторий",
                  command=self.clone_repo_thread).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔨 Компилировать",
                  command=self.compile_thread).pack(side=tk.LEFT, padx=5)
        
        # Статус установки
        status_frame = ttk.LabelFrame(parent, text="📊 Статус установки", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.install_status = ttk.Treeview(status_frame, columns=("status",), height=5)
        self.install_status.heading("#0", text="Компонент")
        self.install_status.heading("status", text="Статус")
        self.install_status.column("status", width=150)
        self.install_status.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем элементы
        items = [
            ("Python", ""),
            ("Git", ""),
            ("GCC/Make", ""),
            ("Репозиторий", ""),
            ("Клиент", ""),
            ("Прошивка", "")
        ]
        
        for item, status in items:
            self.install_status.insert("", tk.END, text=item, values=(status,))
    
    def create_flash_tab(self, parent):
        """Создает вкладку прошивки"""
        # Информация об устройстве
        device_frame = ttk.LabelFrame(parent, text="📱 Устройство", padding="10")
        device_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(device_frame, text="🔍 Найти устройства",
                  command=self.find_devices_thread).pack(side=tk.LEFT, padx=5)
        
        self.device_var = tk.StringVar(value="Устройства не найдены")
        ttk.Label(device_frame, textvariable=self.device_var).pack(side=tk.LEFT, padx=10)
        
        # Прошивка
        flash_frame = ttk.LabelFrame(parent, text="💾 Прошивка", padding="10")
        flash_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(flash_frame, text="🔄 Прошить Bootrom",
                  command=lambda: self.flash_thread("bootrom")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(flash_frame, text="🔄 Прошить Fullimage",
                  command=lambda: self.flash_thread("fullimage")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(flash_frame, text="🔄 Полная прошивка",
                  command=lambda: self.flash_thread("full")).pack(side=tk.LEFT, padx=5)
        
        # Прогресс
        self.progress = ttk.Progressbar(parent, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
    
    def create_control_tab(self, parent):
        """Создает вкладку управления"""
        # Быстрые команды
        quick_frame = ttk.LabelFrame(parent, text="⚡ Быстрые команды", padding="10")
        quick_frame.pack(fill=tk.X, pady=5)
        
        commands = [
            ("hw status", "Статус устройства"),
            ("hw tune", "Настройка антенн"),
            ("hf search", "Поиск HF карт"),
            ("lf search", "Поиск LF карт"),
            ("hf mf reader", "Чтение Mifare"),
            ("data plot", "График данных")
        ]
        
        for cmd, desc in commands:
            ttk.Button(quick_frame, text=f"{desc} ({cmd})",
                      command=lambda c=cmd: self.send_command(c)).pack(side=tk.LEFT, padx=2)
        
        # Консоль
        console_frame = ttk.LabelFrame(parent, text="💻 Консоль", padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.console_output = scrolledtext.ScrolledText(console_frame, height=10)
        self.console_output.pack(fill=tk.BOTH, expand=True)
        
        cmd_frame = ttk.Frame(console_frame)
        cmd_frame.pack(fill=tk.X, pady=5)
        
        self.cmd_entry = ttk.Entry(cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.cmd_entry.bind("<Return>", lambda e: self.send_console_command())
        
        ttk.Button(cmd_frame, text="Отправить",
                  command=self.send_console_command).pack(side=tk.LEFT)
        
        ttk.Button(cmd_frame, text="Очистить",
                  command=lambda: self.console_output.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
        
        # Запуск GUI
        gui_frame = ttk.LabelFrame(parent, text="🖼️ Графический интерфейс", padding="10")
        gui_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(gui_frame, text="🚀 Запустить оригинальный клиент",
                  command=self.run_client_thread).pack(side=tk.LEFT, padx=5)
        
        if Path("proxmark3_gui.py").exists():
            ttk.Button(gui_frame, text="🎨 Запустить Russian GUI",
                      command=self.run_russian_gui_thread).pack(side=tk.LEFT, padx=5)
    
    def create_log_tab(self, parent):
        """Создает вкладку лога"""
        self.log_text = scrolledtext.ScrolledText(parent)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="📄 Сохранить лог",
                  command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Очистить лог",
                  command=lambda: self.log_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
    
    def log_message(self, message):
        """Добавляет сообщение в лог"""
        def update():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, update)
    
    def set_status(self, message):
        """Устанавливает статус"""
        self.status_var.set(message)
    
    def check_status(self):
        """Проверяет текущий статус установки"""
        self.log_message("🔍 Проверка статуса...")
        
        # Обновляем дерево статуса
        for item in self.install_status.get_children():
            text = self.install_status.item(item)["text"]
            status = ""
            
            if text == "Python":
                status = "✅" if sys.executable else "❌"
            elif text == "Git":
                try:
                    subprocess.run(["git", "--version"], capture_output=True, check=True)
                    status = "✅"
                except:
                    status = "❌"
            elif text == "GCC/Make":
                try:
                    subprocess.run(["gcc", "--version"], capture_output=True, check=True)
                    subprocess.run(["make", "--version"], capture_output=True, check=True)
                    status = "✅"
                except:
                    status = "❌"
            elif text == "Репозиторий":
                status = "✅" if Config.PM3_DIR.exists() else "❌"
            elif text == "Клиент":
                status = "✅" if Config.CLIENT_PATH.exists() else "❌"
            elif text == "Прошивка":
                status = "✅" if Config.FIRMWARE_PATH.exists() else "❌"
            
            self.install_status.item(item, values=(status,))
        
        self.set_status("Статус обновлен")
    
    # Потоковые операции
    
    def check_dependencies_thread(self):
        """Проверка зависимостей в потоке"""
        thread = threading.Thread(target=self.installer.check_dependencies)
        thread.daemon = True
        thread.start()
    
    def auto_install_thread(self):
        """Авто-установка в потоке"""
        def run():
            self.progress.start()
            self.set_status("📦 Установка зависимостей...")
            self.installer.install_dependencies_linux()
            self.progress.stop()
            self.set_status("✅ Установка завершена")
            self.root.after(100, self.check_status)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def clone_repo_thread(self):
        """Клонирование в потоке"""
        def run():
            self.progress.start()
            self.set_status("📥 Клонирование репозитория...")
            self.installer.clone_repository()
            self.progress.stop()
            self.set_status("✅ Клонирование завершено")
            self.root.after(100, self.check_status)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def compile_thread(self):
        """Компиляция в потоке"""
        def run():
            self.progress.start()
            self.set_status("🔨 Компиляция...")
            self.installer.compile_firmware()
            self.progress.stop()
            self.set_status("✅ Компиляция завершена")
            self.root.after(100, self.check_status)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def find_devices_thread(self):
        """Поиск устройств в потоке"""
        def run():
            devices = self.installer.find_devices()
            if devices:
                device_list = ", ".join([f"{d[0]} ({d[1]})" for d in devices])
                self.device_var.set(f"Найдено: {device_list}")
            else:
                self.device_var.set("Устройства не найдены")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def flash_thread(self, mode):
        """Прошивка в потоке"""
        def run():
            self.progress.start()
            self.set_status("💾 Прошивка устройства...")
            
            if mode == "bootrom":
                self.installer.flash_device()
            elif mode == "fullimage":
                self.installer.flash_device()
            else:
                self.installer.flash_device()
            
            self.progress.stop()
            self.set_status("✅ Прошивка завершена")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def send_command(self, cmd):
        """Отправляет команду устройству"""
        self.log_message(f"➤ {cmd}")
        # Здесь будет реальная отправка через последовательный порт
        self.console_output.insert(tk.END, f"> {cmd}\n")
    
    def send_console_command(self):
        """Отправляет команду из консоли"""
        cmd = self.cmd_entry.get().strip()
        if cmd:
            self.send_command(cmd)
            self.cmd_entry.delete(0, tk.END)
    
    def run_client_thread(self):
        """Запуск клиента в потоке"""
        def run():
            self.installer.run_client()
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def run_russian_gui_thread(self):
        """Запуск Russian GUI в потоке"""
        def run():
            try:
                subprocess.Popen([sys.executable, "proxmark3_gui.py"])
            except Exception as e:
                self.log_message(f"❌ Ошибка запуска GUI: {e}")
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def save_log(self):
        """Сохраняет лог в файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"✅ Лог сохранен: {filename}")
            except Exception as e:
                self.log_message(f"❌ Ошибка сохранения: {e}")

# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SeamlessApp(root)
    root.mainloop()
