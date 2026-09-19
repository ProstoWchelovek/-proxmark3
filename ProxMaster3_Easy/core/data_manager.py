#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Data Manager
Модуль для управления данными: дампы, ключи, hex-редактор
"""

import json
import logging
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class DataManager:
    """Управление данными: сохранение, загрузка, редактирование"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.dumps_dir = self.base_dir / 'dumps'
        self.keys_dir = self.base_dir / 'keys'
        self.scripts_dir = self.base_dir / 'scripts'
        self.logs_dir = self.base_dir / 'logs'
        
        # Создание директорий
        self._ensure_directories()
        
        # Текущие данные в памяти
        self.current_dump: Optional[bytes] = None
        self.current_keys: Dict = {}
        self.edit_history: List[bytes] = []  # Для отмены изменений
        
    def _ensure_directories(self):
        """Создать необходимые директории"""
        for directory in [self.dumps_dir, self.keys_dir, self.scripts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Директория проверена: {directory}")
    
    # === Работа с дампами ===
    
    def save_dump(self, data: bytes, filename: Optional[str] = None, 
                  card_type: str = "unknown", description: str = "") -> Tuple[bool, str]:
        """
        Сохранить дамп карты
        
        Args:
            data: Байты дампа
            filename: Имя файла (генерируется если не указано)
            card_type: Тип карты
            description: Описание
            
        Returns:
            Tuple[bool, str]: (успех, путь к файлу или ошибка)
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dump_{timestamp}_{card_type}.bin"
            
            filepath = self.dumps_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(data)
            
            # Сохранение метаданных
            metadata = {
                'filename': filename,
                'card_type': card_type,
                'description': description,
                'size': len(data),
                'created_at': datetime.now().isoformat(),
                'hex_preview': data[:32].hex()
            }
            
            meta_filepath = filepath.with_suffix('.json')
            with open(meta_filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Дамп сохранен: {filepath} ({len(data)} байт)")
            return True, str(filepath)
            
        except Exception as e:
            error_msg = f"Ошибка сохранения дампа: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def load_dump(self, filename: str) -> Tuple[bool, bytes, str]:
        """
        Загрузить дамп из файла
        
        Args:
            filename: Имя файла или путь
            
        Returns:
            Tuple[bool, bytes, str]: (успех, данные, сообщение)
        """
        try:
            filepath = Path(filename)
            
            if not filepath.is_absolute():
                filepath = self.dumps_dir / filename
            
            if not filepath.exists():
                return False, b"", f"Файл не найден: {filepath}"
            
            with open(filepath, 'rb') as f:
                data = f.read()
            
            self.current_dump = data
            self.edit_history = [data]  # Сброс истории
            
            logger.info(f"Дамп загружен: {filepath} ({len(data)} байт)")
            return True, data, str(filepath)
            
        except Exception as e:
            error_msg = f"Ошибка загрузки дампа: {str(e)}"
            logger.error(error_msg)
            return False, b"", error_msg
    
    def list_dumps(self) -> List[Dict]:
        """Получить список всех сохраненных дампов"""
        dumps = []
        
        for filepath in self.dumps_dir.glob('*.bin'):
            meta_filepath = filepath.with_suffix('.json')
            
            dump_info = {
                'filename': filepath.name,
                'path': str(filepath),
                'size': filepath.stat().st_size,
                'modified': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            }
            
            if meta_filepath.exists():
                try:
                    with open(meta_filepath, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    dump_info.update(metadata)
                except:
                    pass
            
            dumps.append(dump_info)
        
        # Сортировка по дате изменения (новые первые)
        dumps.sort(key=lambda x: x.get('modified', ''), reverse=True)
        
        return dumps
    
    def delete_dump(self, filename: str) -> Tuple[bool, str]:
        """Удалить дамп"""
        try:
            filepath = self.dumps_dir / filename
            meta_filepath = filepath.with_suffix('.json')
            
            if filepath.exists():
                filepath.unlink()
            
            if meta_filepath.exists():
                meta_filepath.unlink()
            
            logger.info(f"Дамп удален: {filename}")
            return True, f"Удалено: {filename}"
            
        except Exception as e:
            error_msg = f"Ошибка удаления: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    # === Hex операции ===
    
    def bytes_to_hex(self, data: bytes) -> str:
        """Преобразовать байты в hex строку"""
        return data.hex().upper()
    
    def hex_to_bytes(self, hex_string: str) -> Tuple[bool, bytes, str]:
        """
        Преобразовать hex строку в байты
        
        Args:
            hex_string: Hex строка (с пробелами или без)
            
        Returns:
            Tuple[bool, bytes, str]: (успех, данные, сообщение)
        """
        try:
            # Удаление пробелов и разделителей
            clean_hex = hex_string.replace(' ', '').replace(':', '').replace('-', '')
            
            # Проверка на корректность
            if len(clean_hex) % 2 != 0:
                return False, b"", "Нечетное количество hex символов"
            
            data = bytes.fromhex(clean_hex)
            return True, data, "Успешно"
            
        except ValueError as e:
            return False, b"", f"Некорректный hex формат: {str(e)}"
    
    def edit_hex(self, offset: int, new_values: bytes) -> Tuple[bool, str]:
        """
        Редактировать дамп по смещению
        
        Args:
            offset: Смещение в байтах
            new_values: Новые байты
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        if self.current_dump is None:
            return False, "Нет загруженного дампа"
        
        if offset < 0 or offset >= len(self.current_dump):
            return False, f"Некорректное смещение: {offset}"
        
        if offset + len(new_values) > len(self.current_dump):
            return False, "Новые данные выходят за границы дампа"
        
        # Сохранение в историю для отмены
        self.edit_history.append(self.current_dump[:])
        
        # Ограничение истории последними 10 изменениями
        if len(self.edit_history) > 10:
            self.edit_history.pop(0)
        
        # Создание изменяемой копии
        dump_list = bytearray(self.current_dump)
        
        # Замена байтов
        for i, byte in enumerate(new_values):
            dump_list[offset + i] = byte
        
        self.current_dump = bytes(dump_list)
        
        logger.info(f"Hex редактор: изменено {len(new_values)} байт по смещению {offset}")
        return True, f"Изменено {len(new_values)} байт"
    
    def undo_edit(self) -> Tuple[bool, str]:
        """Отменить последнее изменение"""
        if len(self.edit_history) <= 1:
            return False, "Нечего отменять"
        
        # Удаляем текущее состояние
        self.edit_history.pop()
        
        # Восстанавливаем предыдущее
        if self.edit_history:
            self.current_dump = self.edit_history[-1]
            logger.info("Отмена последнего изменения")
            return True, "Изменение отменено"
        
        return False, "История пуста"
    
    def get_hex_view(self, start: int = 0, length: int = 256) -> str:
        """
        Получить hex представление данных
        
        Args:
            start: Начальное смещение
            length: Количество байт для отображения
            
        Returns:
            Форматированная hex строка
        """
        if self.current_dump is None:
            return ""
        
        end = min(start + length, len(self.current_dump))
        data = self.current_dump[start:end]
        
        result = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            
            # Hex часть
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            hex_part = hex_part.ljust(48)  # Выравнивание
            
            # ASCII часть
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            
            # Смещение
            offset_str = f'{start + i:08X}'
            
            result.append(f"{offset_str}  {hex_part}  |{ascii_part}|")
        
        return '\n'.join(result)
    
    # === Работа с ключами ===
    
    def save_keys(self, keys: Dict, filename: str) -> Tuple[bool, str]:
        """Сохранить ключи в файл"""
        try:
            filepath = self.keys_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(keys, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Ключи сохранены: {filepath}")
            return True, str(filepath)
            
        except Exception as e:
            error_msg = f"Ошибка сохранения ключей: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def load_keys(self, filename: str) -> Tuple[bool, Dict, str]:
        """Загрузить ключи из файла"""
        try:
            filepath = self.keys_dir / filename
            
            if not filepath.exists():
                return False, {}, f"Файл не найден: {filename}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                keys = json.load(f)
            
            logger.info(f"Ключи загружены: {filepath}")
            return True, keys, str(filepath)
            
        except Exception as e:
            error_msg = f"Ошибка загрузки ключей: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def list_keys(self) -> List[Dict]:
        """Получить список файлов с ключами"""
        keys_files = []
        
        for filepath in self.keys_dir.glob('*.json'):
            keys_files.append({
                'filename': filepath.name,
                'path': str(filepath),
                'size': filepath.stat().st_size,
                'modified': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            })
        
        return keys_files
    
    # === Экспорт/Импорт ===
    
    def export_to_file(self, data: bytes, filepath: str, format: str = 'bin') -> Tuple[bool, str]:
        """Экспорт данных в файл различных форматов"""
        try:
            path = Path(filepath)
            
            if format == 'bin':
                with open(path, 'wb') as f:
                    f.write(data)
            elif format == 'hex':
                with open(path, 'w') as f:
                    f.write(data.hex())
            elif format == 'json':
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({'data': data.hex()}, f, indent=2)
            else:
                return False, f"Неподдерживаемый формат: {format}"
            
            logger.info(f"Экспорт выполнен: {filepath}")
            return True, str(filepath)
            
        except Exception as e:
            error_msg = f"Ошибка экспорта: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_statistics(self) -> Dict:
        """Получить статистику по данным"""
        return {
            'dumps_count': len(list(self.dumps_dir.glob('*.bin'))),
            'keys_count': len(list(self.keys_dir.glob('*.json'))),
            'scripts_count': len(list(self.scripts_dir.glob('*'))),
            'current_dump_size': len(self.current_dump) if self.current_dump else 0,
            'edit_history_size': len(self.edit_history)
        }
