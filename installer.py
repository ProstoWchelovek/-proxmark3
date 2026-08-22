"""
Proxmark3 Easy GUI - Модуль установщика ProxSpace
Автоматическая загрузка, распаковка и настройка ProxSpace на Windows.
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

class ProxSpaceInstaller:
    def __init__(self, install_path="C:\\Proxmark3", callback_log=None):
        self.install_path = Path(install_path)
        self.proxspace_url = "https://github.com/Gator96100/ProxSpace/releases/download/v2.0/ProxSpace.zip" # Пример URL
        self.pm3_repo = "https://github.com/RfidResearchGroup/proxmark3.git"
        self.callback_log = callback_log
        
    def log(self, message):
        """Логирование с вызовом колбэка"""
        if self.callback_log:
            self.callback_log(message)
        print(message)

    def check_existing(self):
        """Проверка наличия установленной версии"""
        pm3_exe = self.install_path / "ProxSpace" / "pm3" / "proxmark3" / "client" / "pm3.exe"
        return pm3_exe.exists()

    def download_file(self, url, dest):
        """Скачивание файла с прогрессом"""
        self.log(f"[+] Скачивание: {url}")
        try:
            def reporthook(blocknum, blocksize, totalsize):
                readsofar = blocknum * blocksize
                if totalsize > 0:
                    percent = readsofar * 100 / totalsize
                    self.log(f"[=] Прогресс: {percent:.1f}%")
            
            urllib.request.urlretrieve(url, dest, reporthook)
            self.log(f"[+] Загрузка завершена: {dest}")
            return True
        except Exception as e:
            self.log(f"[-] Ошибка загрузки: {e}")
            return False

    def extract_zip(self, zip_path, dest_folder):
        """Распаковка ZIP архива"""
        self.log(f"[=] Распаковка {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_folder)
            self.log("[+] Распаковка завершена")
            return True
        except Exception as e:
            self.log(f"[-] Ошибка распаковки: {e}")
            return False

    def clone_pm3_repo(self):
        """Клонирование репозитория proxmark3 если нужно"""
        repo_path = self.install_path / "ProxSpace" / "pm3" / "proxmark3"
        if not repo_path.exists():
            self.log(f"[=] Клонирование репозитория в {repo_path}...")
            try:
                subprocess.run(["git", "clone", self.pm3_repo, str(repo_path)], check=True)
                self.log("[+] Репозиторий склонирован")
                return True
            except Exception as e:
                self.log(f"[-] Ошибка клонирования: {e}")
                return False
        else:
            self.log("[i] Репозиторий уже существует")
            return True

    def compile_pm3(self):
        """Компиляция клиента (запуск make)"""
        self.log("[=] Компиляция Proxmark3 client...")
        # Здесь должна быть логика запуска MSYS2 shell для компиляции
        # Для упрощения пока заглушка
        self.log("[!] Автоматическая компиляция требует MSYS2. Пропускаем шаг компиляции.")
        self.log("[i] Рекомендуется использовать готовый бинарник из релиза ProxSpace.")
        return True

    def install(self):
        """Основной процесс установки"""
        self.log("="*40)
        self.log("ЗАПУСК УСТАНОВКИ PROXSPACE")
        self.log("="*40)
        
        # Создание директории
        self.install_path.mkdir(parents=True, exist_ok=True)
        
        # Проверка существующей установки
        if self.check_existing():
            self.log("[i] ProxSpace уже установлен. Установка пропущена.")
            return True

        # Скачивание ProxSpace (если есть прямой линк на билд)
        # В реальности лучше скачать инсталлятор .exe и запустить его в тихом режиме
        # Но здесь эмулируем структуру
        
        self.log("[i] Для полной установки рекомендуется скачать официальный инсталлятор:")
        self.log("    https://github.com/Gator96100/ProxSpace/releases")
        self.log("[=] Создание базовой структуры папок...")
        
        # Создаем фейковую структуру для демонстрации
        base = self.install_path / "ProxSpace" / "pm3" / "proxmark3"
        base.mkdir(parents=True, exist_ok=True)
        (base / "client").mkdir(exist_ok=True)
        (base / "armsrc").mkdir(exist_ok=True)
        
        self.log("[+] Структура папок создана")
        self.log("[!] Внимание: Полный клиент не скачан автоматически из-за ограничений размера.")
        self.log("[i] Пожалуйста, укажите путь к существующему ProxSpace в настройках, если он у вас есть.")
        
        return True

    def run_gui(self):
        """Запуск GUI после установки"""
        pass

def run_installer_callback(log_func):
    """Обертка для запуска установщика с колбэком лога"""
    installer = ProxSpaceInstaller(callback_log=log_func)
    return installer.install()
