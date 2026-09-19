#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Менеджер конфигурации
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Управление конфигурацией приложения"""
    
    DEFAULT_CONFIG = {
        'app': {
            'version': '2.0.0',
            'name': 'ProxMaster3 Easy',
            'language': 'ru'
        },
        'device': {
            'default_port': None,
            'baudrate': 115200,
            'auto_connect': False
        },
        'paths': {
            'dumps': 'dumps',
            'keys': 'keys',
            'scripts': 'scripts',
            'logs': 'logs',
            'models': 'models'
        },
        'ui': {
            'theme': 'dark',
            'font_size': 12,
            'log_max_lines': 1000
        },
        'ai': {
            'enabled': True,
            'provider': 'lm_studio',  # lm_studio, ollama, cherry_studio
            'model': None,
            'api_url': 'http://localhost:1234/v1'
        },
        'updates': {
            'auto_check': True,
            'check_interval_days': 7
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path('config.json')
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> bool:
        """Загрузить конфигурацию из файла"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Объединение с конфигурацией по умолчанию
                self._merge_config(loaded_config)
                logger.info(f"Конфигурация загружена: {self.config_path}")
                return True
            else:
                logger.info("Файл конфигурации не найден, используется конфигурация по умолчанию")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return False
    
    def save_config(self) -> bool:
        """Сохранить конфигурацию в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Конфигурация сохранена: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def _merge_config(self, loaded: Dict) -> None:
        """Объединить загруженную конфигурацию с default"""
        for key, value in loaded.items():
            if key in self.config and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение конфигурации"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """Установить значение конфигурации"""
        keys = key.split('.')
        config = self.config
        
        try:
            for k in keys[:-1]:
                config = config[k]
            config[keys[-1]] = value
            return True
        except (KeyError, TypeError):
            logger.error(f"Неверный ключ конфигурации: {key}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Сбросить конфигурацию к значениям по умолчанию"""
        self.config = self.DEFAULT_CONFIG.copy()
        logger.info("Конфигурация сброшена к значениям по умолчанию")
