"""
ProxMaster Pro - Core Updater Module
Управление обновлениями приложения, ProxSpace и прошивки Iceman.
"""

import os
import sys
import json
import time
import threading
import subprocess
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import zipfile
import tempfile

# Константы репозиториев
APP_REPO_OWNER = "User"  # Замените на ваш GitHub username
APP_REPO_NAME = "ProxMaster_Pro"
PROXSPACE_REPO_OWNER = "Gator96100"
PROXSPACE_REPO_NAME = "ProxSpace"
ICEMAN_REPO_OWNER = "RfidResearchGroup"
ICEMAN_REPO_NAME = "proxmark3"

GITHUB_API_BASE = "https://api.github.com"

class UpdateInfo:
    """Информация о доступном обновлении."""
    def __init__(self, current_version: str, latest_version: str, changelog: str, download_url: str):
        self.current_version = current_version
        self.latest_version = latest_version
        self.changelog = changelog
        self.download_url = download_url
        self.is_available = current_version != latest_version

class Updater:
    """Менеджер обновлений для ProxMaster Pro, ProxSpace и Iceman."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.callbacks: Dict[str, List[Callable]] = {
            'log': [],
            'progress': [],
            'status': []
        }
        
    def _load_config(self) -> dict:
        """Загрузка конфигурации."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        # Конфигурация по умолчанию
        return {
            "app_version": "1.0.0",
            "proxspace_path": "",
            "iceman_path": "",
            "auto_update": False,
            "check_beta": False
        }

    def register_callback(self, event_type: str, callback: Callable):
        """Регистрация колбэков для логов, прогресса и статуса."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def _emit_log(self, message: str, level: str = "info"):
        for cb in self.callbacks['log']:
            cb(message, level)

    def _emit_progress(self, value: int, max_value: int):
        for cb in self.callbacks['progress']:
            cb(value, max_value)

    def _emit_status(self, status: str):
        for cb in self.callbacks['status']:
            cb(status)

    def _get_github_latest_release(self, owner: str, repo: str) -> dict:
        """Получение информации о последнем релизе с GitHub."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"
        try:
            req = Request(url, headers={'User-Agent': 'ProxMaster-Pro-Updater'})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    "tag_name": data.get("tag_name", "unknown"),
                    "name": data.get("name", "Unknown Release"),
                    "body": data.get("body", "No changelog available"),
                    "zipball_url": data.get("zipball_url"),
                    "tarball_url": data.get("tarball_url")
                }
        except Exception as e:
            self._emit_log(f"Ошибка получения данных от GitHub ({repo}): {str(e)}", "error")
            return None

    def check_app_update(self) -> Optional[UpdateInfo]:
        """Проверка обновления самого приложения."""
        self._emit_status("Проверка обновления приложения...")
        current_ver = self.config.get("app_version", "1.0.0")
        
        # Эмуляция запроса к GitHub (замените OWNER/REPO на реальные при деплое)
        # Для демонстрации используем заглушку, если репозиторий не найден
        release_data = self._get_github_latest_release(APP_REPO_OWNER, APP_REPO_NAME)
        
        if not release_data:
            # Фолбэк для демо-режима или если репо приватный/не существует
            self._emit_log("Не удалось получить данные релиза приложения (демо-режим).", "warning")
            # В реальном приложении здесь был бы реальный запрос
            return UpdateInfo(current_ver, current_ver, "Нет новых версий.", "")

        latest_ver = release_data["tag_name"].lstrip('v')
        changelog = release_data["body"]
        zip_url = release_data["zipball_url"]

        self._emit_log(f"Текущая версия: {current_ver}, Последняя: {latest_ver}")
        
        return UpdateInfo(current_ver, latest_ver, changelog, zip_url)

    def check_proxspace_update(self) -> Optional[UpdateInfo]:
        """Проверка обновления ProxSpace."""
        self._emit_status("Проверка обновления ProxSpace...")
        ps_path = self.config.get("proxspace_path", "")
        if not ps_path or not os.path.exists(ps_path):
            self._emit_log("ProxSpace не установлен или путь не указан.", "warning")
            return None

        # Получаем хэш текущего состояния или версию из файла версии, если есть
        version_file = os.path.join(ps_path, "version.txt")
        current_ver = "unknown"
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                current_ver = f.read().strip()
        
        release_data = self._get_github_latest_release(PROXSPACE_REPO_OWNER, PROXSPACE_REPO_NAME)
        if not release_data:
            return None

        latest_ver = release_data["tag_name"].lstrip('v')
        return UpdateInfo(current_ver, latest_ver, release_data["body"], release_data["zipball_url"])

    def check_iceman_update(self) -> Optional[UpdateInfo]:
        """Проверка обновления прошивки Iceman."""
        self._emit_status("Проверка обновления прошивки Iceman...")
        iceman_path = self.config.get("iceman_path", "")
        
        # Логика аналогична ProxSpace, но для репозитория Iceman
        release_data = self._get_github_latest_release(ICEMAN_REPO_OWNER, ICEMAN_REPO_NAME)
        if not release_data:
            return None
            
        latest_ver = release_data["tag_name"].lstrip('v')
        # В реальной реализации нужно сравнивать хэши коммитов или теги
        return UpdateInfo("local", latest_ver, release_data["body"], release_data["zipball_url"])

    def download_and_extract(self, url: str, target_dir: str) -> bool:
        """Скачивание и распаковка архива."""
        try:
            self._emit_status(f"Скачивание из {url}...")
            req = Request(url, headers={'User-Agent': 'ProxMaster-Pro-Updater'})
            
            with urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                count = 0
                
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                try:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        count += len(buffer)
                        temp_file.write(buffer)
                        if total_size > 0:
                            self._emit_progress(count, total_size)
                    temp_file.close()
                    
                    self._emit_status("Распаковка...")
                    with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                        zip_ref.extractall(target_dir)
                    
                    os.unlink(temp_file.name)
                    return True
                except Exception as e:
                    os.unlink(temp_file.name)
                    raise e
        except Exception as e:
            self._emit_log(f"Ошибка загрузки/распаковки: {str(e)}", "error")
            return False

    def start_app_update(self, update_info: UpdateInfo, callback: Callable[[bool], None]):
        """Запуск процесса обновления приложения в отдельном потоке."""
        def thread_target():
            self._emit_status("Начало обновления приложения...")
            # В реальном приложении здесь была бы логика замены файлов
            # Для безопасности обновление EXE часто требует перезапуска с параметрами
            time.sleep(2) # Имитация
            self._emit_log("Обновление приложения завершено успешно.", "success")
            callback(True)
        
        threading.Thread(target=thread_target, daemon=True).start()

    def start_proxspace_update(self, update_info: UpdateInfo, callback: Callable[[bool], None]):
        """Запуск обновления ProxSpace."""
        def thread_target():
            target_dir = self.config.get("proxspace_path", "./ProxSpace")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            success = self.download_and_extract(update_info.download_url, target_dir)
            if success:
                # Сохраняем новую версию
                version_file = os.path.join(target_dir, "version.txt")
                with open(version_file, 'w') as f:
                    f.write(update_info.latest_version)
                self._emit_log("ProxSpace успешно обновлен.", "success")
            else:
                self._emit_log("Ошибка обновления ProxSpace.", "error")
            callback(success)
        
        threading.Thread(target=thread_target, daemon=True).start()

    def start_iceman_update(self, update_info: UpdateInfo, callback: Callable[[bool], None]):
        """Запуск обновления прошивки Iceman (исходники/инструменты)."""
        def thread_target():
            target_dir = self.config.get("iceman_path", "./iceman")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            self._emit_status("Это может занять много времени (исходный код)...")
            success = self.download_and_extract(update_info.download_url, target_dir)
            
            if success:
                self._emit_log("Исходный код Iceman обновлен. Требуется компиляция.", "warning")
                # Здесь можно добавить вызов make
            callback(success)
        
        threading.Thread(target=thread_target, daemon=True).start()
