#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - AI Ассистент
Интеграция с локальными AI моделями (LM Studio, Ollama, Cherry Studio)
"""

import json
import logging
import requests
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class AIAssistant:
    """AI помощник для работы с Proxmark3"""
    
    def __init__(self, provider: str = 'lm_studio', api_url: str = 'http://localhost:1234/v1'):
        self.provider = provider
        self.api_url = api_url
        self.model = None
        self.is_available = False
        
        # Проверка доступности AI
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """Проверить доступность AI сервиса"""
        try:
            if self.provider == 'ollama':
                response = requests.get(f"{self.api_url}/tags", timeout=3)
                self.is_available = response.status_code == 200
            else:  # lm_studio, cherry_studio
                response = requests.get(f"{self.api_url}/models", timeout=3)
                self.is_available = response.status_code == 200
                
            if self.is_available:
                logger.info(f"AI сервис доступен: {self.provider} ({self.api_url})")
            else:
                logger.warning(f"AI сервис недоступен: {self.provider}")
                
            return self.is_available
            
        except Exception as e:
            logger.warning(f"AI сервис недоступен: {e}")
            self.is_available = False
            return False
    
    def list_models(self) -> List[str]:
        """Получить список доступных моделей"""
        if not self.is_available:
            return []
        
        try:
            if self.provider == 'ollama':
                response = requests.get(f"{self.api_url}/tags", timeout=5)
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            else:
                response = requests.get(f"{self.api_url}/models", timeout=5)
                data = response.json()
                return [model['id'] for model in data.get('data', [])]
                
        except Exception as e:
            logger.error(f"Ошибка получения списка моделей: {e}")
            return []
    
    def set_model(self, model_name: str) -> bool:
        """Установить модель для использования"""
        models = self.list_models()
        
        if model_name in models:
            self.model = model_name
            logger.info(f"AI модель установлена: {model_name}")
            return True
        else:
            logger.warning(f"Модель не найдена: {model_name}")
            return False
    
    def ask(self, question: str, context: Optional[str] = None) -> Optional[str]:
        """
        Задать вопрос AI ассистенту
        
        Args:
            question: Вопрос пользователя
            context: Дополнительный контекст
            
        Returns:
            Ответ AI или None при ошибке
        """
        if not self.is_available:
            logger.warning("AI сервис недоступен")
            return None
        
        if not self.model:
            logger.warning("AI модель не выбрана")
            return "⚠️ Модель AI не выбрана. Выберите модель в настройках."
        
        # Формирование промпта для Proxmark3
        system_prompt = """Ты - экспертный помощник по работе с Proxmark3 Easy и прошивкой Iceman.
Твоя задача - помогать пользователям с:
- Выбором правильных команд для Proxmark3
- Анализом дампов карт доступа
- Созданием скриптов для атак
- Объяснением протоколов RFID/NFC (LF/HF)
- Решением проблем с подключением и работой устройства

Важно:
- Используй только реальные команды Proxmark3 Iceman firmware
- Предупреждай об опасных операциях
- Объясняй сложные концепции простым языком
- Предлагай пошаговые инструкции

Команды Proxmark3 имеют формат:
- lf <команда> - для низкочастотных операций (125 kHz)
- hf <команда> - для высокочастотных операций (13.56 MHz)
- hw <команда> - аппаратные команды
- data <команда> - работа с данными
- script <команда> - выполнение скриптов"""

        if context:
            system_prompt += f"\n\nКонтекст текущей операции:\n{context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
                "stream": False
            }
            
            endpoint = f"{self.api_url}/chat/completions"
            
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            logger.info(f"AI ответ получен ({len(answer)} символов)")
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка AI запроса: {e}")
            return f"⚠️ Ошибка AI сервиса: {str(e)}"
    
    def explain_command(self, command: str) -> Optional[str]:
        """Объяснить команду Proxmark3"""
        question = f"Объясни подробно команду Proxmark3: {command}. Что она делает, какие параметры принимает, когда используется?"
        return self.ask(question)
    
    def suggest_attack(self, card_type: str, known_data: str = "") -> Optional[str]:
        """Предложить атаку для типа карты"""
        context = f"Тип карты: {card_type}\nИзвестные данные: {known_data}"
        question = f"Какие команды Proxmark3 использовать для анализа и клонирования карты типа {card_type}? Пошаговая инструкция."
        return self.ask(question, context)
    
    def analyze_dump(self, dump_hex: str) -> Optional[str]:
        """Проанализировать дамп карты"""
        context = f"Hex дамп карты:\n{dump_hex[:500]}"  # Ограничиваем размер
        question = "Проанализируй этот дамп карты. Какой это тип карты? Какие данные содержатся? Есть ли ключи доступа?"
        return self.ask(question, context)
    
    def generate_script(self, task: str) -> Optional[str]:
        """Сгенерировать Lua скрипт для задачи"""
        question = f"Создай Lua скрипт для Proxmark3 Iceman для следующей задачи: {task}. Код должен быть рабочим и с комментариями."
        return self.ask(question)
    
    def help_with_error(self, error_message: str, command: str = "") -> Optional[str]:
        """Помочь с ошибкой"""
        context = f"Команда: {command}\nОшибка: {error_message}"
        question = f"Произошла ошибка при работе с Proxmark3. Как её исправить? Дай подробное решение."
        return self.ask(question, context)
