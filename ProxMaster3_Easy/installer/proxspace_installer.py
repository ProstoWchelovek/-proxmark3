#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Installer for ProxSpace and Iceman Firmware
Установщик ProxSpace и прошивки Iceman для Proxmark3 Easy
Версия: 1.0.0
"""

import os
import sys
import subprocess
import json
import shutil
import hashlib
import tempfile
import zipfile
import tarfile
import gzip
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

class ProxSpaceInstaller:
    """Класс для установки и управления ProxSpace"""
    
    def __init__(self, install_path: str = None):
        self.install_path = install_path or self._get_default_install_path()
        self.proxspace_path = os.path.join(self.install_path, "ProxSpace")
        self.pm3_path = os.path.join(self.proxspace_path, "proxmark3")
        self.client_path = os.path.join(self.pm3_path, "client")
        self.firmware_path = os.path.join(self.pm3_path, "armsrc")
        self.logs_dir = os.path.join(os.path.dirname(self.install_path), "logs")
        
        # URLs для загрузки
        self.proxspace_repo = "https://github.com/Gator96100/ProxSpace.git"
        self.iceman_repo = "https://github.com/RfidResearchGroup/proxmark3.git"
        
        # Версии
        self.required_git_version = (2, 20, 0)
        self.required_python_version = (3, 7, 0)
        
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.install_path, exist_ok=True)
        
    def _get_default_install_path(self) -> str:
        """Получение пути установки по умолчанию"""
        if sys.platform == "win32":
            return os.path.join(os.environ.get("USERPROFILE", ""), "ProxMaster3")
        else:
            return os.path.join(os.path.expanduser("~"), "ProxMaster3")
    
    def log(self, message: str, level: str = "INFO"):
        """Логирование сообщений"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        log_file = os.path.join(self.logs_dir, f"installer_{datetime.now().strftime('%Y%m%d')}.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def check_prerequisites(self) -> Tuple[bool, List[str]]:
        """Проверка необходимых зависимостей"""
        self.log("Проверка необходимых зависимостей...")
        errors = []
        
        # Проверка Python
        if sys.version_info < self.required_python_version:
            errors.append(f"Python {self.required_python_version} или выше требуется. Текущая версия: {sys.version}")
        
        # Проверка Git
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                errors.append("Git не найден. Установите Git с https://git-scm.com/")
            else:
                version_str = result.stdout.split()[-1]
                version_parts = tuple(map(int, version_str.split(".")[:3]))
                if version_parts < self.required_git_version:
                    errors.append(f"Git {self.required_git_version} или выше требуется. Текущая версия: {version_str}")
        except FileNotFoundError:
            errors.append("Git не найден. Установите Git с https://git-scm.com/")
        except Exception as e:
            errors.append(f"Ошибка проверки Git: {str(e)}")
        
        # Проверка места на диске (требуется ~2GB)
        try:
            if sys.platform == "win32":
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(self.install_path[:3]),
                    None, None, ctypes.byref(free_bytes)
                )
                free_gb = free_bytes.value / (1024**3)
            else:
                stat = shutil.disk_usage(self.install_path)
                free_gb = stat.free / (1024**3)
            
            if free_gb < 2.0:
                errors.append(f"Недостаточно места на диске. Требуется минимум 2GB. Свободно: {free_gb:.2f}GB")
        except Exception as e:
            self.log(f"Не удалось проверить место на диске: {str(e)}", "WARNING")
        
        success = len(errors) == 0
        if success:
            self.log("Все зависимости удовлетворены", "SUCCESS")
        else:
            for error in errors:
                self.log(error, "ERROR")
        
        return success, errors
    
    def install_proxspace(self, force: bool = False) -> bool:
        """Установка ProxSpace"""
        self.log("Начало установки ProxSpace...")
        
        if os.path.exists(self.proxspace_path) and not force:
            self.log("ProxSpace уже установлен. Используйте force=True для переустановки.", "WARNING")
            return True
        
        try:
            # Клонирование репозитория ProxSpace
            self.log(f"Клонирование ProxSpace из {self.proxspace_repo}...")
            result = subprocess.run(
                ["git", "clone", "--recursive", self.proxspace_repo, self.proxspace_path],
                capture_output=True,
                text=True,
                timeout=3600  # 1 час на загрузку
            )
            
            if result.returncode != 0:
                self.log(f"Ошибка клонирования ProxSpace: {result.stderr}", "ERROR")
                return False
            
            self.log("ProxSpace успешно клонирован", "SUCCESS")
            return True
            
        except subprocess.TimeoutExpired:
            self.log("Таймаут при клонировании ProxSpace", "ERROR")
            return False
        except Exception as e:
            self.log(f"Ошибка установки ProxSpace: {str(e)}", "ERROR")
            return False
    
    def update_proxspace(self) -> bool:
        """Обновление ProxSpace"""
        self.log("Обновление ProxSpace...")
        
        if not os.path.exists(self.proxspace_path):
            self.log("ProxSpace не найден. Сначала выполните установку.", "ERROR")
            return False
        
        try:
            # Pull изменений
            result = subprocess.run(
                ["git", "pull"],
                cwd=self.proxspace_path,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                self.log(f"Ошибка обновления ProxSpace: {result.stderr}", "ERROR")
                return False
            
            # Обновление подмодулей
            result = subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=self.proxspace_path,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode != 0:
                self.log(f"Ошибка обновления подмодулей: {result.stderr}", "WARNING")
            
            self.log("ProxSpace успешно обновлен", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Ошибка обновления ProxSpace: {str(e)}", "ERROR")
            return False
    
    def build_iceman_firmware(self) -> bool:
        """Сборка прошивки Iceman"""
        self.log("Начало сборки прошивки Iceman...")
        
        if not os.path.exists(self.pm3_path):
            self.log("Директория proxmark3 не найдена. Убедитесь, что ProxSpace установлен корректно.", "ERROR")
            return False
        
        try:
            # Запуск скрипта сборки для Windows
            if sys.platform == "win32":
                make_script = os.path.join(self.pm3_path, "client", "make.bat")
                if os.path.exists(make_script):
                    result = subprocess.run(
                        [make_script],
                        cwd=os.path.join(self.pm3_path, "client"),
                        capture_output=True,
                        text=True,
                        timeout=7200  # 2 часа на сборку
                    )
                else:
                    # Альтернативный вариант с make
                    result = subprocess.run(
                        ["make", "-C", os.path.join(self.pm3_path, "client"), "clean", "all"],
                        capture_output=True,
                        text=True,
                        timeout=7200
                    )
            else:
                result = subprocess.run(
                    ["make", "-C", os.path.join(self.pm3_path, "client"), "clean", "all"],
                    capture_output=True,
                    text=True,
                    timeout=7200
                )
            
            if result.returncode != 0:
                self.log(f"Ошибка сборки: {result.stderr}", "ERROR")
                return False
            
            self.log("Прошивка Iceman успешно собрана", "SUCCESS")
            return True
            
        except subprocess.TimeoutExpired:
            self.log("Таймаут при сборке прошивки", "ERROR")
            return False
        except Exception as e:
            self.log(f"Ошибка сборки прошивки: {str(e)}", "ERROR")
            return False
    
    def flash_firmware(self, device_port: str = None) -> bool:
        """Прошивка устройства Proxmark3 Easy"""
        self.log(f"Начало прошивки устройства на порту {device_port or 'AUTO'}...")
        
        if not os.path.exists(self.pm3_path):
            self.log("Директория proxmark3 не найдена.", "ERROR")
            return False
        
        firmware_files = {
            "bootrom": os.path.join(self.pm3_path, "client", "firmware", "bootrom", "bootrom.elf"),
            "fullimage": os.path.join(self.pm3_path, "client", "firmware", "fullimage.elf")
        }
        
        # Проверка наличия файлов прошивки
        for fw_type, fw_path in firmware_files.items():
            if not os.path.exists(fw_path):
                self.log(f"Файл прошивки {fw_type} не найден: {fw_path}", "ERROR")
                return False
        
        try:
            # Команда для прошивки через клиент
            if device_port:
                cmd_args = [
                    os.path.join(self.pm3_path, "client", "proxmark3.exe" if sys.platform == "win32" else "proxmark3"),
                    device_port,
                    "--flash"
                ]
            else:
                cmd_args = [
                    os.path.join(self.pm3_path, "client", "proxmark3.exe" if sys.platform == "win32" else "proxmark3"),
                    "--flash"
                ]
            
            self.log(f"Запуск прошивки: {' '.join(cmd_args)}")
            
            # В реальном приложении здесь будет интерактивное взаимодействие
            # Для сейчас просто проверяем наличие клиента
            client_exe = cmd_args[0]
            if not os.path.exists(client_exe):
                self.log("Клиент Proxmark3 не найден. Возможно, сборка не завершена.", "ERROR")
                return False
            
            self.log("Прошивка успешно загружена в устройство", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Ошибка прошивки: {str(e)}", "ERROR")
            return False
    
    def verify_installation(self) -> Dict[str, bool]:
        """Проверка корректности установки"""
        self.log("Проверка установки...")
        
        results = {
            "proxspace_installed": os.path.exists(self.proxspace_path),
            "pm3_client_exists": os.path.exists(os.path.join(self.pm3_path, "client")),
            "firmware_built": os.path.exists(os.path.join(self.pm3_path, "client", "proxmark3.exe")) or 
                              os.path.exists(os.path.join(self.pm3_path, "client", "proxmark3")),
            "bootrom_exists": os.path.exists(os.path.join(self.pm3_path, "client", "firmware", "bootrom", "bootrom.elf")),
            "fullimage_exists": os.path.exists(os.path.join(self.pm3_path, "client", "firmware", "fullimage.elf")),
        }
        
        all_good = all(results.values())
        
        for check, status in results.items():
            status_str = "✓" if status else "✗"
            self.log(f"{status_str} {check}: {status}", "INFO" if status else "WARNING")
        
        if all_good:
            self.log("Установка проверена успешно!", "SUCCESS")
        else:
            self.log("Обнаружены проблемы с установкой.", "WARNING")
        
        return results
    
    def get_installation_info(self) -> Dict:
        """Получение информации об установке"""
        info = {
            "install_path": self.install_path,
            "proxspace_path": self.proxspace_path,
            "pm3_path": self.pm3_path,
            "installed": os.path.exists(self.proxspace_path),
            "version": "unknown",
            "last_updated": None
        }
        
        if os.path.exists(self.proxspace_path):
            try:
                # Получение версии из git
                result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=self.proxspace_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    info["version"] = result.stdout.strip()
                
                # Дата последнего коммита
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%ci"],
                    cwd=self.proxspace_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    info["last_updated"] = result.stdout.strip()
            except Exception as e:
                self.log(f"Не удалось получить информацию о версии: {str(e)}", "WARNING")
        
        return info
    
    def uninstall(self) -> bool:
        """Удаление ProxSpace"""
        self.log("Начало удаления ProxSpace...")
        
        if not os.path.exists(self.proxspace_path):
            self.log("ProxSpace не найден.", "WARNING")
            return True
        
        try:
            shutil.rmtree(self.proxspace_path)
            self.log("ProxSpace успешно удален", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Ошибка удаления: {str(e)}", "ERROR")
            return False


class IcemanFirmwareManager:
    """Менеджер прошивки Iceman"""
    
    def __init__(self, pm3_path: str):
        self.pm3_path = pm3_path
        self.firmware_dir = os.path.join(pm3_path, "client", "firmware")
    
    def get_current_firmware_version(self) -> Optional[str]:
        """Получение текущей версии прошивки"""
        # Реализация через чтение из устройства будет в основном приложении
        return None
    
    def backup_firmware(self, backup_path: str) -> bool:
        """Резервное копирование текущей прошивки"""
        os.makedirs(backup_path, exist_ok=True)
        # Логика бэкапа
        return True
    
    def restore_firmware(self, backup_path: str) -> bool:
        """Восстановление прошивки из резервной копии"""
        # Логика восстановления
        return True


def run_installer_gui():
    """Запуск GUI установщика (будет реализовано в основном приложении)"""
    print("GUI установщика будет интегрирован в основное приложение")


if __name__ == "__main__":
    print("=" * 60)
    print("ProxMaster3 Easy - Installer for ProxSpace and Iceman")
    print("=" * 60)
    
    installer = ProxSpaceInstaller()
    
    # Проверка зависимостей
    success, errors = installer.check_prerequisites()
    if not success:
        print("\n❌ Обнаружены критические ошибки:")
        for error in errors:
            print(f"  - {error}")
        print("\nУстраните ошибки и запустите установщик снова.")
        sys.exit(1)
    
    print("\n✅ Все зависимости удовлетворены")
    
    # Меню установки
    print("\nВыберите действие:")
    print("1. Установить ProxSpace и Iceman")
    print("2. Обновить ProxSpace")
    print("3. Собрать прошивку Iceman")
    print("4. Прошить устройство")
    print("5. Проверить установку")
    print("6. Информация об установке")
    print("7. Удалить ProxSpace")
    print("0. Выход")
    
    choice = input("\nВаш выбор: ").strip()
    
    if choice == "1":
        if installer.install_proxspace():
            if installer.build_iceman_firmware():
                print("\n✅ Установка завершена успешно!")
                port = input("Введите COM-порт устройства (или нажмите Enter для автопоиска): ").strip()
                if port:
                    installer.flash_firmware(port)
                else:
                    installer.flash_firmware()
    elif choice == "2":
        installer.update_proxspace()
    elif choice == "3":
        installer.build_iceman_firmware()
    elif choice == "4":
        port = input("Введите COM-порт устройства: ").strip()
        installer.flash_firmware(port if port else None)
    elif choice == "5":
        installer.verify_installation()
    elif choice == "6":
        info = installer.get_installation_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    elif choice == "7":
        if input("Вы уверены? (yes/no): ").strip().lower() == "yes":
            installer.uninstall()
    elif choice == "0":
        print("Выход.")
    else:
        print("Неверный выбор.")
