"""
Менеджер обновлений для ProxMaster Pro
Проверяет и обновляет:
1. Само приложение ProxMaster Pro
2. ProxSpace (Gator96100)
3. Прошивку Iceman (RfidResearchGroup)
4. Базу команд и конфигурацию
"""

import os
import sys
import json
import hashlib
import shutil
import zipfile
import requests
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable


class UpdateChecker:
    """Класс проверки доступности обновлений"""
    
    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
        self.roadmap_path = os.path.join(os.path.dirname(__file__), "..", "data", "roadmap.json")
        self.callbacks = {
            'check_started': [],
            'check_finished': [],
            'error_occurred': [],
            'progress_update': []
        }
    
    def connect(self, signal_name, callback):
        """Подключение к событию"""
        if signal_name in self.callbacks:
            self.callbacks[signal_name].append(callback)
    
    def emit(self, signal_name, *args):
        """Вызов события"""
        for callback in self.callbacks.get(signal_name, []):
            callback(*args)
        
    # Репозитории для проверки
    REPOS = {
        "app": {
            "url": "https://api.github.com/repos/ProxMaster/ProxMaster-Pro/releases/latest",
            "name": "ProxMaster Pro"
        },
        "proxspace": {
            "url": "https://api.github.com/repos/Gator96100/ProxSpace/releases/latest",
            "name": "ProxSpace"
        },
        "iceman": {
            "url": "https://api.github.com/repos/RfidResearchGroup/proxmark3/releases/latest",
            "name": "Iceman Firmware"
        }
    }
    
    def get_current_version(self) -> str:
        """Получает текущую версию приложения"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("version", "1.0.0")
        except Exception:
            pass
        return "1.0.0"
    
    def get_latest_version(self, repo_type: str = "app") -> Optional[str]:
        """Получает последнюю версию из GitHub"""
        try:
            repo_info = self.REPOS.get(repo_type)
            if not repo_info:
                return None
                
            response = requests.get(repo_info["url"], timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("tag_name", "").lstrip("v")
        except Exception as e:
            self.emit('error_occurred', f"Ошибка получения версии {repo_type}: {str(e)}")
        return None
    
    def check_all_updates(self) -> Dict:
        """Проверяет все доступные обновления"""
        self.emit('check_started')
        
        results = {
            "app": {"update_available": False, "current": "", "latest": "", "changelog": ""},
            "proxspace": {"update_available": False, "current": "", "latest": "", "changelog": ""},
            "iceman": {"update_available": False, "current": "", "latest": "", "changelog": ""},
            "roadmap": []
        }
        
        # Проверка приложения
        try:
            self.emit('progress_update', 10, "Проверка обновления приложения...")
            current_ver = self.get_current_version()
            latest_ver = self.get_latest_version("app")
            
            if latest_ver:
                results["app"]["current"] = current_ver
                results["app"]["latest"] = latest_ver
                results["app"]["update_available"] = self._compare_versions(current_ver, latest_ver)
                
                # Получение changelog
                try:
                    response = requests.get(self.REPOS["app"]["url"], timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        results["app"]["changelog"] = data.get("body", "")
                except Exception:
                    pass
                    
        except Exception as e:
            self.emit('error_occurred', f"Ошибка проверки приложения: {str(e)}")
        
        # Проверка ProxSpace
        try:
            self.emit('progress_update', 40, "Проверка обновления ProxSpace...")
            latest_ver = self.get_latest_version("proxspace")
            if latest_ver:
                # Получаем локальную версию ProxSpace
                proxspace_path = os.path.join(os.path.dirname(__file__), "..", "proxspace")
                version_file = os.path.join(proxspace_path, "version.txt")
                
                current_ver = "unknown"
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        current_ver = f.read().strip()
                
                results["proxspace"]["current"] = current_ver
                results["proxspace"]["latest"] = latest_ver
                results["proxspace"]["update_available"] = current_ver != latest_ver
                
        except Exception as e:
            self.emit('error_occurred', f"Ошибка проверки ProxSpace: {str(e)}")
        
        # Проверка прошивки Iceman
        try:
            self.emit('progress_update', 70, "Проверка обновления прошивки Iceman...")
            latest_ver = self.get_latest_version("iceman")
            if latest_ver:
                # Получаем локальную версию прошивки
                firmware_path = os.path.join(os.path.dirname(__file__), "..", "firmware")
                version_file = os.path.join(firmware_path, "version.txt")
                
                current_ver = "unknown"
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        current_ver = f.read().strip()
                
                results["iceman"]["current"] = current_ver
                results["iceman"]["latest"] = latest_ver
                results["iceman"]["update_available"] = current_ver != latest_ver
                
        except Exception as e:
            self.emit('error_occurred', f"Ошибка проверки прошивки: {str(e)}")
        
        # Загрузка roadmap
        try:
            self.emit('progress_update', 90, "Загрузка плана разработки...")
            if os.path.exists(self.roadmap_path):
                with open(self.roadmap_path, 'r', encoding='utf-8') as f:
                    roadmap_data = json.load(f)
                    results["roadmap"] = roadmap_data.get("roadmap", {})
                    results["changelog_history"] = roadmap_data.get("changelog", [])
        except Exception as e:
            self.emit('error_occurred', f"Ошибка загрузки roadmap: {str(e)}")
        
        self.emit('progress_update', 100, "Проверка завершена")
        self.emit
        
        return results
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Сравнивает версии (возвращает True, если есть обновление)"""
        try:
            def parse_version(v):
                return [int(x) for x in v.replace("v", "").split(".")[:3]]
            
            curr_parts = parse_version(current)
            latest_parts = parse_version(latest)
            
            for c, l in zip(curr_parts, latest_parts):
                if l > c:
                    return True
                elif l < c:
                    return False
            return len(latest_parts) > len(curr_parts)
        except Exception:
            return False


class UpdateDownloader:
    """Класс загрузки и установки обновлений"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.callbacks = {
            'download_started': [],
            'download_progress': [],
            'download_finished': [],
            'error_occurred': []
        }
    
    def connect(self, signal_name, callback):
        """Подключение к событию"""
        if signal_name in self.callbacks:
            self.callbacks[signal_name].append(callback)
    
    def emit(self, signal_name, *args):
        """Вызов события"""
        for callback in self.callbacks.get(signal_name, []):
            callback(*args)
        
    def download_app_update(self, version: str, callback: Optional[Callable] = None) -> bool:
        """Загружает обновление приложения"""
        try:
            self.emit(f"Загрузка ProxMaster Pro v{version}...")
            
            # В реальном проекте здесь была бы ссылка на релиз
            # Для примера используем заглушку
            release_url = f"https://github.com/ProxMaster/ProxMaster-Pro/releases/download/v{version}/ProxMaster_Pro_v{version}.zip"
            
            temp_file = os.path.join(self.base_dir, "temp_update.zip")
            
            response = requests.get(release_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            downloaded = 0
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else 50
                        self.emit(progress, f"Загружено {downloaded}/{total_size} байт")
            
            self.emit(100, "Загрузка завершена")
            self.emit(temp_file)
            
            return True
            
        except Exception as e:
            self.emit('error_occurred', f"Ошибка загрузки: {str(e)}")
            return False
    
    def install_app_update(self, archive_path: str) -> bool:
        """Устанавливает обновление приложения"""
        try:
            self.emit(0, "Распаковка обновления...")
            
            # Создаем резервную копию
            backup_dir = os.path.join(self.base_dir, "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(backup_dir, exist_ok=True)
            
            # Копируем важные файлы
            files_to_backup = ["core", "widgets", "data", "main_app.py", "run.py"]
            for item in files_to_backup:
                src = os.path.join(self.base_dir, item)
                if os.path.exists(src):
                    dst = os.path.join(backup_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            self.emit(30, "Резервная копия создана")
            
            # Распаковываем обновление
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(self.base_dir)
            
            self.emit(80, "Файлы обновлены")
            
            # Удаляем временный файл
            os.remove(archive_path)
            
            # Обновляем версию в config
            config_path = os.path.join(self.base_dir, "data", "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Извлекаем версию из имени архива
                version = os.path.basename(archive_path).replace("ProxMaster_Pro_v", "").replace(".zip", "")
                config["version"] = version
                config["last_updated"] = datetime.now().isoformat()
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.emit(100, "Обновление установлено успешно")
            self.emit("Обновление установлено! Перезапустите приложение.")
            
            return True
            
        except Exception as e:
            self.emit('error_occurred', f"Ошибка установки: {str(e)}")
            return False
    
    def update_proxspace(self, version: str) -> bool:
        """Обновляет ProxSpace"""
        try:
            self.emit(f"Обновление ProxSpace до v{version}...")
            
            proxspace_path = os.path.join(self.base_dir, "proxspace")
            
            # Если ProxSpace еще не установлен - скачиваем
            if not os.path.exists(proxspace_path):
                self.emit(0, "Загрузка ProxSpace...")
                
                # URL репозитория
                repo_url = "https://github.com/Gator96100/ProxSpace/archive/master.zip"
                
                response = requests.get(repo_url, stream=True, timeout=60)
                temp_file = os.path.join(self.base_dir, "proxspace_temp.zip")
                
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                self.emit(50, "Распаковка ProxSpace...")
                
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(self.base_dir)
                
                # Переименовываем папку
                extracted_dir = os.path.join(self.base_dir, "ProxSpace-master")
                if os.path.exists(extracted_dir):
                    if os.path.exists(proxspace_path):
                        shutil.rmtree(proxspace_path)
                    os.rename(extracted_dir, proxspace_path)
                
                os.remove(temp_file)
                
                # Сохраняем версию
                version_file = os.path.join(proxspace_path, "version.txt")
                with open(version_file, 'w') as f:
                    f.write(version)
                
                self.emit(100, "ProxSpace установлен")
                self.emit("ProxSpace успешно установлен!")
                return True
            else:
                # Обновление существующей установки через git
                self.emit(0, "Обновление через Git...")
                
                try:
                    subprocess.run(["git", "pull"], cwd=proxspace_path, check=True, capture_output=True)
                    
                    version_file = os.path.join(proxspace_path, "version.txt")
                    with open(version_file, 'w') as f:
                        f.write(version)
                    
                    self.emit(100, "ProxSpace обновлен")
                    self.emit("ProxSpace успешно обновлен!")
                    return True
                    
                except subprocess.CalledProcessError as e:
                    self.emit('error_occurred', f"Ошибка Git: {e.stderr.decode()}")
                    return False
                    
        except Exception as e:
            self.emit('error_occurred', f"Ошибка обновления ProxSpace: {str(e)}")
            return False
    
    def update_firmware(self, version: str) -> bool:
        """Обновляет прошивку Iceman"""
        try:
            self.emit(f"Обновление прошивки Iceman до v{version}...")
            
            firmware_path = os.path.join(self.base_dir, "firmware")
            os.makedirs(firmware_path, exist_ok=True)
            
            # Ссылка на релиз прошивки
            release_url = f"https://github.com/RfidResearchGroup/proxmark3/archive/refs/tags/v{version}.zip"
            
            self.emit(0, "Загрузка прошивки...")
            
            response = requests.get(release_url, stream=True, timeout=120)
            temp_file = os.path.join(self.base_dir, "firmware_temp.zip")
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.emit(40, "Распаковка прошивки...")
            
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(firmware_path)
            
            os.remove(temp_file)
            
            # Компиляция прошивки (требуется установленный toolchain)
            self.emit(60, "Компиляция прошивки...")
            
            firmware_dir = os.path.join(firmware_path, f"proxmark3-{version}")
            if os.path.exists(firmware_dir):
                try:
                    # Попытка компиляции (требует установленных зависимостей)
                    subprocess.run(["make", "clean"], cwd=firmware_dir, check=False)
                    subprocess.run(["make", "-j4"], cwd=firmware_dir, check=False, timeout=300)
                except Exception:
                    self.emit(70, "Компиляция пропущена (требуется toolchain)")
            
            # Сохраняем версию
            version_file = os.path.join(firmware_path, "version.txt")
            with open(version_file, 'w') as f:
                f.write(version)
            
            self.emit(100, "Прошивка обновлена")
            self.emit(f"Прошивка v{version} загружена. Для установки подключите Proxmark3.")
            
            return True
            
        except Exception as e:
            self.emit('error_occurred', f"Ошибка обновления прошивки: {str(e)}")
            return False


class UpdateWorker(threading.Thread):
    """Поток для выполнения операций обновления"""
    
    def __init__(self, operation: str, params: dict = None):
        super().__init__()
        self.operation = operation
        self.params = params or {}
        self.checker = UpdateChecker()
        self.downloader = UpdateDownloader()
        
    def run(self):
        """Выполняет операцию обновления"""
        try:
            if self.operation == "check":
                self.checker.check_all_updates()
                
            elif self.operation == "download_app":
                version = self.params.get("version", "")
                self.downloader.download_app_update(version)
                
            elif self.operation == "install_app":
                archive_path = self.params.get("path", "")
                self.downloader.install_app_update(archive_path)
                
            elif self.operation == "update_proxspace":
                version = self.params.get("version", "")
                self.downloader.update_proxspace(version)
                
            elif self.operation == "update_firmware":
                version = self.params.get("version", "")
                self.downloader.update_firmware(version)
                
        except Exception as e:
            self.downloader.emit('error_occurred', str(e))
