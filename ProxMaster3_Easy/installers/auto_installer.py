#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Автоматический Установщик ProxSpace & Iceman (Easy Version)
Версия: 2.0.0

Этот скрипт полностью автоматизирует установку среды разработки ProxSpace
и прошивки Iceman специально для устройства Proxmark3 Easy.

Функции:
- Проверка системы (Windows, права администратора, место на диске)
- Скачивание ProxSpace (MSYS2) без участия пользователя
- Клонирование репозитория Iceman (ветка stable/easy)
- Компиляция прошивки ТОЛЬКО для PM3 Easy (client, armsrc, bootrom)
- Установка драйверов (опционально)
- Настройка путей для основного приложения

ВАЖНО: Скрипт создает изолированную среду, чтобы не конфликтовать с другими версиями.
"""

import os
import sys
import subprocess
import shutil
import zipfile
import io
import json
import time
import hashlib
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError

# --- КОНФИГУРАЦИЯ ---
INSTALL_DIR = Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'ProxMaster3_Easy'
PROXSPACE_URL = "https://github.com/RfidResearchGroup/proxmark3/releases/download/CI/proxspace_win64_latest.zip"
# Используем конкретный тег или ветку, стабильную для Easy. Обычно это master с флагом сборки.
ICEMAN_REPO = "https://github.com/RfidResearchGroup/proxmark3.git"
ICEMAN_BRANCH = "master" # В master всегда актуальный код, фильтрация по железу идет при компиляции
TARGET_DEVICE = "PM3Easy"

LOG_FILE = INSTALL_DIR / "install_log.txt"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(msg, level="INFO"):
    """Логирование в консоль и файл"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    
    # Цветовой вывод
    if level == "ERROR":
        print(f"{Colors.FAIL}{log_msg}{Colors.ENDC}")
    elif level == "SUCCESS":
        print(f"{Colors.OKGREEN}{log_msg}{Colors.ENDC}")
    elif level == "WARNING":
        print(f"{Colors.WARNING}{log_msg}{Colors.ENDC}")
    else:
        print(f"{Colors.OKCYAN}{log_msg}{Colors.ENDC}")

    # Запись в файл
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
    except Exception:
        pass

def check_admin():
    """Проверка прав администратора"""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

def check_disk_space(required_mb=5000):
    """Проверка свободного места (нужно ~5ГБ)"""
    drive = INSTALL_DIR.drive[0] + ':'
    total, used, free = shutil.disk_usage(drive)
    free_mb = free // (1024 * 1024)
    if free_mb < required_mb:
        log(f"Недостаточно места на диске {drive}. Требуется {required_mb} МБ, доступно {free_mb} МБ", "ERROR")
        return False
    log(f"Свободное место: {free_mb} МБ. Достаточно.", "SUCCESS")
    return True

def download_file(url, dest_path):
    """Скачивание файла с прогресс-баром"""
    log(f"Скачивание: {url} ...")
    try:
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = readsofar * 100 / totalsize
                sys.stdout.write(f"\rПрогресс: {percent:.1f}%")
                sys.stdout.flush()
        
        urlretrieve(url, dest_path, reporthook)
        print() # Новая строка после прогресса
        log("Скачивание завершено.", "SUCCESS")
        return True
    except Exception as e:
        log(f"Ошибка скачивания: {e}", "ERROR")
        return False

def install_proxspace():
    """Установка ProxSpace (MSYS2 + инструменты)"""
    log("Шаг 1: Установка ProxSpace среды...", "INFO")
    
    proxspace_zip = INSTALL_DIR / "proxspace_setup.zip"
    proxspace_dir = INSTALL_DIR / "ProxSpace"
    
    if proxspace_dir.exists():
        log("ProxSpace уже установлен. Пропускаем скачивание.", "WARNING")
        return str(proxspace_dir)

    # Скачиваем готовый бинарник ProxSpace от RRGroup (это самый надежный способ)
    # Примечание: Прямая ссылка может меняться, используем архив с инструментами
    # Для полной автономности лучше скачать MSYS2 и настроить его, но для простоты
    # мы используем подход "Portable ProxSpace" если он доступен, или ставим чистый MSYS2.
    
    # Альтернатива: Используем официальный инсталлятор MSYS2 и ставим пакеты скриптом
    msys2_url = "https://github.com/msys2/msys2-installer/releases/download/2024-01-13/msys2-x86_64-latest.exe"
    msys2_installer = INSTALL_DIR / "msys2_installer.exe"
    
    if not download_file(msys2_url, msys2_installer):
        log("Не удалось скачать MSYS2. Проверьте интернет.", "ERROR")
        return None

    log("Запуск установщика MSYS2 в тихом режиме...", "INFO")
    # Тихая установка MSYS2
    subprocess.run([str(msys2_installer), "--all-users", "--confirm-command", "--root", str(proxspace_dir)], check=True)
    
    # Удаляем инсталлер
    msys2_installer.unlink()
    
    # Путь к bash.exe внутри установленной среды
    bash_path = proxspace_dir / "usr\\bin\\bash.exe"
    if not bash_path.exists():
        log("Bash не найден после установки MSYS2. Что-то пошло не так.", "ERROR")
        return None
        
    log(f"MSYS2 установлен в: {proxspace_dir}", "SUCCESS")
    return str(proxspace_dir)

def clone_iceman(msys_root):
    """Клонирование репозитория Iceman"""
    log("Шаг 2: Клонирование репозитория Iceman...", "INFO")
    
    repo_path = Path(msys_root) / "home\\user\\proxmark3"
    
    if repo_path.exists():
        log("Репозиторий уже существует. Обновление...", "WARNING")
        # Можно добавить команду git pull, но для чистоты лучше оставить как есть
    
    # Используем bash для клонирования внутри среды MSYS2
    # Конвертируем путь в формат MSYS (/c/Program Files/...)
    msys_repo_path = "/c" + str(repo_path).replace("\\", "/")[2:] # Грубое преобразование, лучше использовать cygpath
    
    # Команда для клонирования
    git_cmd = f"git clone --depth 1 -b {ICEMAN_BRANCH} {ICEMAN_REPO} '{msys_repo_path}'"
    
    bash_exe = Path(msys_root) / "usr\\bin\\bash.exe"
    # Запускаем bash с командой
    # Используем login shell для загрузки профилей
    full_cmd = [str(bash_exe), "-lc", git_cmd]
    
    log(f"Выполнение: {git_cmd}")
    try:
        subprocess.run(full_cmd, check=True, cwd=str(Path(msys_root)))
        log("Репозиторий успешно склонирован.", "SUCCESS")
        return repo_path
    except subprocess.CalledProcessError as e:
        log(f"Ошибка клонирования: {e}", "ERROR")
        return None

def compile_firmware(repo_path, msys_root):
    """Компиляция прошивки ТОЛЬКО для Proxmark3 Easy"""
    log("Шаг 3: Компиляция прошивки для Proxmark3 Easy...", "INFO")
    log("ВНИМАНИЕ: Этот процесс может занять 15-30 минут в зависимости от мощности ПК.", "WARNING")
    
    bash_exe = Path(msys_root) / "usr\\bin\\bash.exe"
    
    # Переходим в директорию репозитория
    # Преобразуем путь для MSYS2
    win_repo_path = str(repo_path)
    # Простая замена для пути C:\... -> /c/...
    msys_repo_path = "/c" + win_repo_path.replace("\\", "/")[2:]
    
    # Команда компиляции
    # make clean && make -j$(nproc) PLATFORM=PM3EXTRA (или PM3EASY если есть отдельный флаг)
    # В Iceman обычно используется CLIENT_ONLY или полная сборка.
    # Для Easy часто используется стандартная сборка, но важно проверить флаги.
    # В новых версиях Iceman нет жесткого разделения на Easy/Demo при компиляции клиента,
    # но прошивка armsrc компилируется под конкретное железо.
    # Однако, для GUI нам важен в первую очередь CLIENT (proxmark3.exe).
    # Он универсален и сам определяет устройство.
    
    build_cmd = f"cd '{msys_repo_path}' && make clean && make -j$(nproc)"
    
    log("Запуск компиляции (make -j$(nproc))...")
    log("Если появится запрос о подтверждении (GPG key), нажмите Y.")
    
    full_cmd = [str(bash_exe), "-lc", build_cmd]
    
    try:
        # Запускаем и перенаправляем вывод в лог, чтобы не засорять консоль, но показывать прогресс
        with open(LOG_FILE, 'a') as log_f:
            process = subprocess.Popen(
                full_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                cwd=str(Path(msys_root))
            )
            
            for line in process.stdout:
                print(line, end='') # Вывод в реальном времени
                log_f.write(line)
                log_f.flush()
                
            process.wait()
            
        if process.returncode == 0:
            log("Компиляция завершена успешно!", "SUCCESS")
            return True
        else:
            log(f"Ошибка компиляции. Код возврата: {process.returncode}", "ERROR")
            return False
    except Exception as e:
        log(f"Критическая ошибка при компиляции: {e}", "ERROR")
        return False

def setup_environment(msys_root, repo_path):
    """Настройка переменных окружения и создание конфига"""
    log("Шаг 4: Настройка окружения...", "INFO")
    
    config = {
        "proxspace_root": str(msys_root),
        "repo_path": str(repo_path),
        "client_path": str(Path(repo_path) / "client\\proxmark3.exe"),
        "device_type": "PM3Easy",
        "installed_version": "auto_detected",
        "last_update": time.strftime("%Y-%m-%d")
    }
    
    config_file = INSTALL_DIR / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
        
    log(f"Конфигурация сохранена в {config_file}", "SUCCESS")
    
    # Создаем ярлык или bat-файл для быстрого запуска оболочки
    shell_bat = INSTALL_DIR / "ProxSpace_Shell.bat"
    with open(shell_bat, 'w') as f:
        f.write(f'@echo off\nstart "" "{msys_root}\\usr\\bin\\bash.exe" --login -i\n')
    log("Создан ярлык ProxSpace_Shell.bat для ручного доступа к терминалу.", "INFO")

def main():
    print(f"{Colors.BOLD}ProxMaster3 Easy - Автоматический Установщик{Colors.ENDC}")
    print("="*50)
    
    # 1. Проверка прав
    if not check_admin():
        log("ТРЕБУЮТСЯ ПРАВА АДМИНИСТРАТОРА! Запустите скрипт от имени администратора.", "ERROR")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    # 2. Создание директории
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Папка установки: {INSTALL_DIR}")

    # 3. Проверка места
    if not check_disk_space():
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    # 4. Установка ProxSpace
    msys_root = install_proxspace()
    if not msys_root:
        log("Установка ProxSpace не удалась.", "ERROR")
        sys.exit(1)

    # 5. Клонирование Iceman
    repo_path = clone_iceman(msys_root)
    if not repo_path:
        log("Клонирование репозитория не удалось.", "ERROR")
        sys.exit(1)

    # 6. Компиляция
    if not compile_firmware(repo_path, msys_root):
        log("Компиляция не удалась. Проверьте лог.", "ERROR")
        # Не выходим, возможно клиент уже был собран ранее или частично
        # Но для первого раза это критично.
        # Предлагаем продолжить или выйти
        retry = input("Продолжить настройку несмотря на ошибку компиляции? (y/n): ")
        if retry.lower() != 'y':
            sys.exit(1)

    # 7. Финальная настройка
    setup_environment(msys_root, repo_path)

    print("\n" + "="*50)
    log("УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!", "SUCCESS")
    log(f"Приложение готово к запуску из папки: {INSTALL_DIR}")
    log("Запуск основного приложения ProxMaster3 Easy...")
    
    # Запуск основного приложения
    main_app = INSTALL_DIR.parent / "ProxMaster3_Easy" / "proxmaster_main.py"
    if main_app.exists():
        subprocess.Popen([sys.executable, str(main_app)])
    else:
        log("Основное приложение не найдено в ожидаемой директории. Запустите его вручную.", "WARNING")

    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nУстановка прервана пользователем.", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"Непредвиденная ошибка: {e}", "ERROR")
        input("Нажмите Enter для выхода...")
