#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Установщик ProxSpace и Iceman Firmware
Автоматическая установка среды разработки Proxmark3
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import requests
import zipfile
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProxSpaceInstaller:
    """Установщик ProxSpace для Windows"""
    
    PROXSPACE_URL = "https://github.com/Gator96100/ProxSpace/archive/refs/heads/main.zip"
    ICEMAN_REPO = "https://github.com/RfidResearchGroup/proxmark3.git"
    
    def __init__(self, install_dir: Optional[str] = None):
        self.install_dir = Path(install_dir) if install_dir else Path.home() / "ProxSpace"
        self.msys_path = self.install_dir / "msys2" / "usr" / "bin"
        self.pm3_path = self.install_dir / "proxmark3"
        
    def check_existing_installation(self) -> Tuple[bool, Dict]:
        """Проверить существующую установку ProxSpace"""
        status = {
            'proxspace_installed': False,
            'iceman_firmware': False,
            'msys2_installed': False,
            'proxmark_client': False,
            'install_path': None
        }
        
        # Проверка ProxSpace
        if self.install_dir.exists():
            status['proxspace_installed'] = True
            status['install_path'] = str(self.install_dir)
            logger.info(f"ProxSpace найден: {self.install_dir}")
        
        # Проверка MSYS2
        msys_exe = self.msys_path / "bash.exe"
        if msys_exe.exists():
            status['msys2_installed'] = True
            logger.info("MSYS2 найден")
        
        # Проверка прошивки Iceman
        if self.pm3_path.exists():
            client_exe = self.pm3_path / "client" / "proxmark3.exe"
            if client_exe.exists():
                status['proxmark_client'] = True
                status['iceman_firmware'] = True
                logger.info("Proxmark3 клиент с Iceman прошивкой найден")
        
        return status['proxspace_installed'] or status['proxmark_client'], status
    
    def download_proxspace(self) -> bool:
        """Скачать ProxSpace"""
        logger.info("Загрузка ProxSpace...")
        
        try:
            response = requests.get(self.PROXSPACE_URL, stream=True, timeout=300)
            response.raise_for_status()
            
            zip_path = self.install_dir.parent / "ProxSpace.zip"
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"ProxSpace загружен: {zip_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки ProxSpace: {e}")
            return False
    
    def extract_proxspace(self) -> bool:
        """Распаковать ProxSpace"""
        zip_path = self.install_dir.parent / "ProxSpace.zip"
        
        if not zip_path.exists():
            logger.error("Архив ProxSpace не найден")
            return False
        
        try:
            logger.info(f"Распаковка в {self.install_dir}...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.install_dir.parent)
            
            # Перемещение из подпапки
            extracted_dir = self.install_dir.parent / "ProxSpace-main"
            if extracted_dir.exists() and not self.install_dir.exists():
                shutil.move(str(extracted_dir), str(self.install_dir))
            
            # Удаление архива
            zip_path.unlink()
            
            logger.info("ProxSpace распакован успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка распаковки: {e}")
            return False
    
    def run_installer_script(self) -> bool:
        """Запустить скрипт установки ProxSpace"""
        install_script = self.install_dir / "install.sh"
        
        if not install_script.exists():
            logger.warning("Скрипт install.sh не найден, пропускаем...")
            return True
        
        logger.info("Запуск установки ProxSpace...")
        logger.info("Это может занять несколько минут...")
        
        # Примечание: для полноценной установки требуется запуск через MSYS2 bash
        print("\n⚠️  Для завершения установки ProxSpace:")
        print(f"   1. Откройте {self.install_dir}\\msys2\\usr\\bin\\bash.exe")
        print(f"   2. Выполните: cd /home/{os.getenv('USERNAME')}/ProxSpace")
        print("   3. Выполните: ./install.sh")
        print("\nИли используйте готовый установщик с официального сайта ProxSpace.")
        
        return True
    
    def clone_iceman_firmware(self) -> bool:
        """Клонировать репозиторий Iceman"""
        if self.pm3_path.exists():
            logger.info("Репозиторий Iceman уже существует")
            return True
        
        logger.info(f"Клонирование Iceman firmware в {self.pm3_path}...")
        
        try:
            subprocess.run(
                ['git', 'clone', '--recursive', self.ICEMAN_REPO, str(self.pm3_path)],
                check=True,
                timeout=600
            )
            logger.info("Iceman firmware склонирована")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка клонирования: {e}")
            return False
        except FileNotFoundError:
            logger.error("Git не найден! Установите Git с https://git-scm.com/")
            return False
    
    def compile_firmware(self) -> bool:
        """Скомпилировать прошивку"""
        logger.info("Компиляция прошивки Iceman...")
        logger.info("Это может занять 10-30 минут...")
        
        make_cmd = ['make', '-j4']
        
        try:
            # Установка PATH для MSYS2
            env = os.environ.copy()
            env['PATH'] = str(self.msys_path) + os.pathsep + env['PATH']
            
            subprocess.run(
                make_cmd,
                cwd=str(self.pm3_path / 'client'),
                env=env,
                check=True,
                timeout=1800
            )
            
            logger.info("Прошивка скомпилирована успешно")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Таймаут компиляции! Попробуйте вручную.")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка компиляции: {e}")
            return False
    
    def full_install(self) -> Tuple[bool, str]:
        """Полная установка ProxSpace и Iceman"""
        logger.info("=" * 60)
        logger.info("Начало установки ProxSpace + Iceman Firmware")
        logger.info("=" * 60)
        
        # Проверка существующей установки
        exists, status = self.check_existing_installation()
        if exists:
            logger.info("Найдена существующая установка:")
            for key, value in status.items():
                logger.info(f"  {key}: {value}")
            
            if status.get('proxmark_client'):
                return True, f"ProxSpace уже установлен: {status['install_path']}"
        
        # Создание директории
        self.install_dir.mkdir(parents=True, exist_ok=True)
        
        # Загрузка и распаковка ProxSpace
        if not self.download_proxspace():
            return False, "Ошибка загрузки ProxSpace"
        
        if not self.extract_proxspace():
            return False, "Ошибка распаковки ProxSpace"
        
        # Запуск скрипта установки
        if not self.run_installer_script():
            return False, "Ошибка установки ProxSpace"
        
        # Клонирование Iceman
        if not self.clone_iceman_firmware():
            return False, "Ошибка клонирования Iceman"
        
        # Компиляция (опционально)
        print("\n⚠️  Компиляция может занять много времени.")
        print("   Рекомендуется компилировать вручную через MSYS2.")
        
        # if not self.compile_firmware():
        #     return False, "Ошибка компиляции"
        
        return True, f"Установка завершена: {self.install_dir}"


def main():
    """Точка входа установщика"""
    print("\n" + "=" * 60)
    print("  ProxSpace + Iceman Firmware Installer")
    print("  для ProxMaster3 Easy")
    print("=" * 60 + "\n")
    
    installer = ProxSpaceInstaller()
    
    success, message = installer.full_install()
    
    print("\n" + "=" * 60)
    if success:
        print(f"✅ УСПЕХ: {message}")
    else:
        print(f"❌ ОШИБКА: {message}")
        print("\nПопробуйте установить вручную:")
        print("1. Скачайте ProxSpace: https://github.com/Gator96100/ProxSpace")
        print("2. Следуйте инструкции на GitHub")
        print("3. После установки запустите ProxMaster3 Easy")
    print("=" * 60 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
