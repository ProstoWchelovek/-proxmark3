#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Command Executor
Модуль для выполнения команд Proxmark3 через JSON конфигурацию
"""

import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from .device_manager import DeviceManager

logger = logging.getLogger(__name__)

class CommandExecutor:
    """Выполнение команд Proxmark3 на основе JSON конфигурации"""
    
    def __init__(self, device_manager: DeviceManager, config_path: Optional[str] = None):
        self.device = device_manager
        self.commands_config: Dict = {}
        self.flat_commands: List[Dict] = []  # Плоский список всех команд
        self.config_path = config_path or 'commands.json'
        self.load_commands()
        
    def load_commands(self, config_path: Optional[str] = None) -> bool:
        """Загрузить конфигурацию команд из JSON файла"""
        path = config_path or self.config_path
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.commands_config = json.load(f)
            
            # Разворачиваем структуру tabs/categories/commands в плоский список
            self.flat_commands = []
            tabs = self.commands_config.get('tabs', {})
            for tab_name, tab_data in tabs.items():
                # Прямые команды вкладки
                if 'commands' in tab_data:
                    for cmd in tab_data['commands']:
                        cmd['tab'] = tab_name
                        self.flat_commands.append(cmd)
                
                # Команды по категориям
                if 'categories' in tab_data:
                    for cat_name, cat_data in tab_data['categories'].items():
                        if 'commands' in cat_data:
                            for cmd in cat_data['commands']:
                                cmd['tab'] = tab_name
                                cmd['category'] = cat_name
                                self.flat_commands.append(cmd)
            
            logger.info(f"Загружено {len(self.flat_commands)} команд из {path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Файл конфигурации не найден: {path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return False
    
    def get_command_by_id(self, command_id: str) -> Optional[Dict]:
        """Получить команду по ID"""
        for cmd in self.flat_commands:
            if cmd.get('id') == command_id:
                return cmd
        return None
    
    def get_commands_by_category(self, category: str) -> List[Dict]:
        """Получить все команды категории"""
        return [
            cmd for cmd in self.flat_commands
            if cmd.get('category') == category
        ]
    
    def get_commands_by_tab(self, tab_name: str) -> List[Dict]:
        """Получить все команды вкладки"""
        return [
            cmd for cmd in self.flat_commands
            if cmd.get('tab') == tab_name
        ]
    
    def get_all_categories(self) -> List[str]:
        """Получить список всех категорий"""
        categories = set()
        for cmd in self.flat_commands:
            if 'category' in cmd:
                categories.add(cmd['category'])
        return sorted(list(categories))
    
    def get_all_tabs(self) -> List[str]:
        """Получить список всех вкладок"""
        return list(self.commands_config.get('tabs', {}).keys())
    
    def execute_command(self, command_id: str, parameters: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Выполнить команду по ID с параметрами
        
        Args:
            command_id: ID команды из конфигурации
            parameters: Параметры для подстановки в команду
            
        Returns:
            Tuple[bool, str]: (успех, результат)
        """
        cmd_config = self.get_command_by_id(command_id)
        
        if not cmd_config:
            error_msg = f"Команда с ID '{command_id}' не найдена"
            logger.error(error_msg)
            return False, error_msg
        
        # Проверка предупреждений
        if cmd_config.get('warning'):
            logger.warning(f"Предупреждение для команды {command_id}: {cmd_config['warning']}")
        
        # Формирование команды с параметрами
        command_template = cmd_config.get('command', '')
        
        if parameters:
            try:
                command = command_template.format(**parameters)
            except KeyError as e:
                error_msg = f"Отсутствует требуемый параметр: {e}"
                logger.error(error_msg)
                return False, error_msg
        else:
            command = command_template
        
        logger.info(f"Выполнение команды: {command}")
        
        # Отправка команды устройству
        if not self.device.is_connected:
            return False, "Устройство не подключено"
        
        success, response = self.device.send_command(command)
        
        if success:
            logger.info(f"Команда выполнена успешно: {command_id}")
        else:
            logger.error(f"Ошибка выполнения команды {command_id}: {response}")
        
        return success, response
    
    def execute_raw_command(self, command: str) -> Tuple[bool, str]:
        """
        Выполнить произвольную команду
        
        Args:
            command: Текст команды для выполнения
            
        Returns:
            Tuple[bool, str]: (успех, результат)
        """
        logger.info(f"Выполнение произвольной команды: {command}")
        
        if not self.device.is_connected:
            return False, "Устройство не подключено"
        
        return self.device.send_command(command)
    
    def search_commands(self, query: str) -> List[Dict]:
        """
        Поиск команд по названию или описанию
        
        Args:
            query: Строка поиска
            
        Returns:
            Список найденных команд
        """
        query_lower = query.lower()
        results = []
        
        for cmd in self.flat_commands:
            name = cmd.get('name', '').lower()
            description = cmd.get('description', '').lower()
            cmd_str = cmd.get('command', '').lower()
            
            if (query_lower in name or 
                query_lower in description or 
                query_lower in cmd_str):
                results.append(cmd)
        
        logger.info(f"Поиск '{query}': найдено {len(results)} команд")
        return results
    
    def get_command_help(self, command_id: str) -> str:
        """Получить справку по команде"""
        cmd = self.get_command_by_id(command_id)
        
        if not cmd:
            return f"Команда '{command_id}' не найдена"
        
        help_text = f"""
Команда: {cmd.get('name', 'N/A')}
ID: {cmd.get('id', 'N/A')}
Синтаксис: {cmd.get('command', 'N/A')}
Описание: {cmd.get('description', 'N/A')}
Категория: {cmd.get('category', 'N/A')}
Иконка: {cmd.get('icon', 'N/A')}
"""
        
        if cmd.get('warning'):
            help_text += f"\n⚠️ ПРЕДУПРЕЖДЕНИЕ: {cmd['warning']}\n"
        
        if cmd.get('parameters'):
            help_text += f"\nПараметры: {', '.join(cmd['parameters'])}\n"
        
        return help_text.strip()
