"""
ProxMaster3 Easy - Менеджер файлов
Управление дампами, ключами и скриптами
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


class FileManager:
    """Класс для управления файлами приложения"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.dumps_dir = self.base_dir / "dumps"
        self.keys_dir = self.base_dir / "keys"
        self.scripts_dir = self.base_dir / "scripts"
        self.logs_dir = self.base_dir / "logs"
        
        # Создание директорий если не существуют
        for dir_path in [self.dumps_dir, self.keys_dir, self.scripts_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def list_dumps(self) -> List[Dict[str, Any]]:
        """Получение списка всех дампов"""
        return self._list_files(self.dumps_dir, ['.bin', '.hex', '.eml'])
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """Получение списка всех ключей"""
        return self._list_files(self.keys_dir, ['.key', '.txt', '.json'])
    
    def list_scripts(self) -> List[Dict[str, Any]]:
        """Получение списка всех скриптов"""
        return self._list_files(self.scripts_dir, ['.lua', '.js', '.py'])
    
    def _list_files(self, directory: Path, extensions: List[str]) -> List[Dict[str, Any]]:
        """Сканирование директории на наличие файлов"""
        files = []
        if not directory.exists():
            return files
        
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'extension': file_path.suffix
                })
        
        # Сортировка по дате изменения (новые первыми)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files
    
    def load_dump(self, filename: str) -> Optional[bytes]:
        """Загрузка дампа из файла"""
        file_path = self.dumps_dir / filename
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def save_dump(self, filename: str, data: bytes) -> bool:
        """Сохранение дампа в файл"""
        file_path = self.dumps_dir / filename
        try:
            with open(file_path, 'wb') as f:
                f.write(data)
            return True
        except Exception:
            return False
    
    def load_keys(self, filename: str) -> Optional[Dict[str, Any]]:
        """Загрузка ключей из JSON файла"""
        file_path = self.keys_dir / filename
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_keys(self, filename: str, keys: Dict[str, Any]) -> bool:
        """Сохранение ключей в JSON файл"""
        file_path = self.keys_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2)
            return True
        except Exception:
            return False
    
    def load_script(self, filename: str) -> Optional[str]:
        """Загрузка скрипта из файла"""
        file_path = self.scripts_dir / filename
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    def save_script(self, filename: str, content: str) -> bool:
        """Сохранение скрипта в файл"""
        file_path = self.scripts_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def delete_file(self, filepath: str) -> bool:
        """Удаление файла"""
        file_path = Path(filepath)
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    def get_file_info(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Получение информации о файле"""
        file_path = Path(filepath)
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            'name': file_path.name,
            'path': str(file_path),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'extension': file_path.suffix
        }
