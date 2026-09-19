"""
AI Assistant Module for ProxMaster3 Easy
Поддержка локальных ИИ моделей: LM Studio, Cherry Studio, Ollama
"""

import json
import requests
import threading
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from enum import Enum


class AIProvider(Enum):
    """Провайдеры ИИ"""
    LM_STUDIO = "lm_studio"
    CHERRY_STUDIO = "cherry_studio"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class AIConfig:
    """Конфигурация ИИ помощника"""
    provider: AIProvider = AIProvider.LM_STUDIO
    host: str = "localhost"
    port: int = 1234  # LM Studio default
    model: str = ""
    timeout: int = 60
    max_tokens: int = 2048
    temperature: float = 0.7
    system_prompt: str = ""
    enabled: bool = True
    dev_mode: bool = False  # Режим разработчика с доступом к коду


class AIAssistant:
    """
    Локальный ИИ помощник для ProxMaster3 Easy
    
    Возможности:
    - Помощь в управлении устройством
    - Редактирование данных карт
    - Создание скриптов атак
    - Адаптация приложения под пользователя
    - Создание обновлений программы
    - Режим разработчика с live-editing
    """
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig()
        self.session = requests.Session()
        self.conversation_history: List[Dict[str, str]] = []
        self.is_processing = False
        self.callbacks: List[Callable[[str], None]] = []
        
        # Системные промпты для разных режимов
        self.system_prompts = {
            "general": """Ты ИИ-помощник для приложения ProxMaster3 Easy - профессионального GUI для Proxmark3 Easy с прошивкой Iceman.
            
Твоя задача:
1. Помогать пользователям работать с RFID/NFC картами
2. Объяснять команды Proxmark3 и их параметры
3. Помогать анализировать дампы карт
4. Предлагать безопасные методы работы
5. Отвечать на вопросы о RFID технологиях

Важно:
- Никогда не предлагай опасные операции без предупреждения
- Всегда объясняй последствия действий
- Помогай новичкам разобраться в интерфейсе
- Предлагай лучшие практики безопасности

Формат ответов: четкий, структурированный, на русском языке.""",
            
            "scripting": """Ты эксперт по созданию скриптов для Proxmark3 (Lua) и Node.js для атак на RFID/NFC.

Твоя задача:
1. Создавать рабочие скрипты для автоматизации задач
2. Объяснять логику работы скриптов
3. Оптимизировать существующие скрипты
4. Помогать отлаживать код
5. Предлагать новые методы атак (только в образовательных целях)

Поддерживаемые языки:
- Lua (для Proxmark3)
- JavaScript/Node.js (для внешних скриптов)
- Python (для утилит)

Всегда проверяй безопасность кода и добавляй комментарии.""",
            
            "hex_editor": """Ты эксперт по редактированию hex-дампов RFID/NFC карт.

Твоя задача:
1. Помогать анализировать структуру дампов
2. Объяснять значение байтов в различных форматах карт
3. Предлагать корректные изменения данных
4. Проверять контрольные суммы и CRC
5. Объяснять форматы ключей доступа

Форматы карт:
- Mifare Classic/Ultralight/DESFire
- EM410x, T55xx
- iClass, LEGIC, FeliCa
- И многие другие

Всегда предупреждай о возможных последствиях изменений.""",
            
            "developer": """Ты ИИ-ассистент в режиме РАЗРАБОТЧИКА с полным доступом к коду приложения ProxMaster3 Easy.

Твои возможности:
1. Анализировать исходный код приложения
2. Предлагать улучшения архитектуры
3. Писать новые функции и модули
4. Исправлять баги в реальном времени
5. Создавать обновления программы
6. Адаптировать приложение под новые версии ProxSpace/Iceman
7. Генерировать документацию

Режим разработчика активирован - ты имеешь доступ к:
- Файловой системе проекта
- Модулям GUI (PyQt6)
- Ядру работы с устройством
- Конфигурационным файлам
- Системе обновлений

Пиши чистый, оптимизированный код с комментариями.""",
            
            "updates": """Ты специалист по созданию обновлений для ProxMaster3 Easy.

Твоя задача:
1. Анализировать изменения в ProxSpace и Iceman firmware
2. Предлагать адаптацию приложения под новые функции
3. Создавать патчи и обновления
4. Проверять совместимость версий
5. Генерировать changelog

Источники обновлений:
- GitHub: https://github.com/Gator96100/ProxSpace
- GitHub: https://github.com/RfidResearchGroup/proxmark3

Всегда тестируй обновления перед выпуском."""
        }
        
        self._load_models_list()
    
    def _load_models_list(self):
        """Загрузка списка доступных моделей от провайдера"""
        if not self.config.enabled:
            return
            
        try:
            if self.config.provider == AIProvider.LM_STUDIO:
                url = f"http://{self.config.host}:{self.config.port}/v1/models"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    if models and not self.config.model:
                        self.config.model = models[0]
                        
            elif self.config.provider == AIProvider.OLLAMA:
                url = f"http://{self.config.host}:11434/api/tags"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if models and not self.config.model:
                        self.config.model = models[0]
                        
        except Exception as e:
            print(f"[AI] Не удалось загрузить список моделей: {e}")
    
    def get_available_models(self) -> List[str]:
        """Получить список доступных моделей"""
        models = []
        try:
            if self.config.provider == AIProvider.LM_STUDIO:
                url = f"http://{self.config.host}:{self.config.port}/v1/models"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    
            elif self.config.provider == AIProvider.OLLAMA:
                url = f"http://{self.config.host}:11434/api/tags"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    
            elif self.config.provider == AIProvider.CHERRY_STUDIO:
                # Cherry Studio использует аналогичный API
                url = f"http://{self.config.host}:{self.config.port}/v1/models"
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    
        except Exception as e:
            print(f"[AI] Ошибка получения списка моделей: {e}")
            
        return models
    
    def set_provider(self, provider: AIProvider, host: str = "localhost", port: int = None):
        """Установить провайдера ИИ"""
        self.config.provider = provider
        self.config.host = host
        if port:
            self.config.port = port
            
        # Default ports
        if provider == AIProvider.LM_STUDIO and not port:
            self.config.port = 1234
        elif provider == AIProvider.OLLAMA and not port:
            self.config.port = 11434
        elif provider == AIProvider.CHERRY_STUDIO and not port:
            self.config.port = 1234
            
        self._load_models_list()
    
    def set_model(self, model_name: str):
        """Установить модель"""
        self.config.model = model_name
    
    def enable_dev_mode(self, enabled: bool = True):
        """Включить режим разработчика"""
        self.config.dev_mode = enabled
        if enabled:
            self.set_system_prompt("developer")
            print("[AI] Режим разработчика активирован")
        else:
            self.set_system_prompt("general")
            print("[AI] Режим разработчика деактивирован")
    
    def set_system_prompt(self, mode: str):
        """Установить системный промпт для режима"""
        if mode in self.system_prompts:
            self.config.system_prompt = self.system_prompts[mode]
            # Очистить историю при смене режима
            self.conversation_history = []
    
    def add_callback(self, callback: Callable[[str], None]):
        """Добавить колбэк для получения ответов"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]):
        """Удалить колбэк"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, message: str):
        """Уведомить все колбэки"""
        for callback in self.callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"[AI] Ошибка колбэка: {e}")
    
    def ask(self, question: str, mode: Optional[str] = None, 
            stream: bool = False) -> Optional[str]:
        """
        Задать вопрос ИИ
        
        Args:
            question: Вопрос пользователя
            mode: Режим (general, scripting, hex_editor, developer, updates)
            stream: Потоковый ответ
            
        Returns:
            Ответ ИИ или None при ошибке
        """
        if not self.config.enabled:
            return "ИИ помощник отключен в настройках"
        
        if self.is_processing:
            return "ИИ уже обрабатывает предыдущий запрос"
        
        # Установить режим если указан
        if mode:
            self.set_system_prompt(mode)
        
        self.is_processing = True
        
        try:
            # Подготовить сообщения
            messages = []
            
            # Добавить системный промпт
            if self.config.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.config.system_prompt
                })
            
            # Добавить историю разговора (последние 10 сообщений)
            messages.extend(self.conversation_history[-10:])
            
            # Добавить текущий вопрос
            messages.append({
                "role": "user",
                "content": question
            })
            
            # Сформировать запрос
            if self.config.provider in [AIProvider.LM_STUDIO, AIProvider.CHERRY_STUDIO]:
                url = f"http://{self.config.host}:{self.config.port}/v1/chat/completions"
                payload = {
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": stream
                }
                
            elif self.config.provider == AIProvider.OLLAMA:
                url = f"http://{self.config.host}:{self.config.port}/api/chat"
                payload = {
                    "model": self.config.model,
                    "messages": messages,
                    "stream": stream
                }
            else:
                return "Неизвестный провайдер ИИ"
            
            # Отправить запрос
            if stream:
                return self._stream_request(url, payload)
            else:
                response = self.session.post(
                    url, 
                    json=payload, 
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Извлечь ответ в зависимости от провайдера
                    if self.config.provider == AIProvider.OLLAMA:
                        answer = data.get("message", {}).get("content", "")
                    else:
                        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Сохранить в историю
                    self.conversation_history.append({
                        "role": "user",
                        "content": question
                    })
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": answer
                    })
                    
                    self._notify_callbacks(answer)
                    return answer
                else:
                    error_msg = f"Ошибка ИИ: {response.status_code} - {response.text}"
                    print(f"[AI] {error_msg}")
                    return error_msg
                    
        except requests.exceptions.ConnectionError:
            error_msg = "Не удалось подключиться к ИИ серверу. Проверьте настройки."
            print(f"[AI] {error_msg}")
            return error_msg
            
        except Exception as e:
            error_msg = f"Ошибка ИИ: {str(e)}"
            print(f"[AI] {error_msg}")
            return error_msg
            
        finally:
            self.is_processing = False
    
    def _stream_request(self, url: str, payload: dict) -> Optional[str]:
        """Обработка потокового запроса"""
        full_response = ""
        
        try:
            with self.session.post(url, json=payload, stream=True, timeout=self.config.timeout) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            
                            if self.config.provider == AIProvider.OLLAMA:
                                # Ollama streaming format
                                data = json.loads(line_str)
                                chunk = data.get("message", {}).get("content", "")
                            else:
                                # OpenAI-compatible format (LM Studio, Cherry Studio)
                                if line_str.startswith("data: "):
                                    line_str = line_str[6:]
                                if line_str == "[DONE]":
                                    break
                                data = json.loads(line_str)
                                chunk = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            
                            if chunk:
                                full_response += chunk
                                self._notify_callbacks(chunk)
                    
                    # Сохранить полный ответ в историю
                    if full_response:
                        self.conversation_history.append({
                            "role": "user",
                            "content": payload["messages"][-1]["content"]
                        })
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": full_response
                        })
                    
                    return full_response
                    
        except Exception as e:
            error_msg = f"Ошибка потокового ответа: {str(e)}"
            print(f"[AI] {error_msg}")
            return error_msg
        
        return None
    
    def ask_sync(self, question: str, mode: Optional[str] = None, 
                 callback: Optional[Callable[[str], None]] = None) -> str:
        """Асинхронный запрос с колбэком"""
        def worker():
            result = self.ask(question, mode, stream=True)
            if callback and result:
                callback(result)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return "Запрос отправлен..."
    
    def clear_history(self):
        """Очистить историю разговора"""
        self.conversation_history = []
        print("[AI] История разговора очищена")
    
    def export_conversation(self, filepath: str):
        """Экспортировать историю разговора в файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            print(f"[AI] История экспортирована в {filepath}")
        except Exception as e:
            print(f"[AI] Ошибка экспорта: {e}")
    
    def import_conversation(self, filepath: str):
        """Импортировать историю разговора из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
            print(f"[AI] История импортирована из {filepath}")
        except Exception as e:
            print(f"[AI] Ошибка импорта: {e}")
    
    def test_connection(self) -> bool:
        """Проверить подключение к ИИ серверу"""
        try:
            if self.config.provider == AIProvider.OLLAMA:
                url = f"http://{self.config.host}:11434/api/tags"
            else:
                url = f"http://{self.config.host}:{self.config.port}/v1/models"
            
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            print(f"[AI] Проверка подключения не удалась: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Получить статус ИИ помощника"""
        return {
            "enabled": self.config.enabled,
            "provider": self.config.provider.value,
            "host": self.config.host,
            "port": self.config.port,
            "model": self.config.model,
            "dev_mode": self.config.dev_mode,
            "connected": self.test_connection(),
            "history_length": len(self.conversation_history),
            "is_processing": self.is_processing
        }
    
    def save_config(self, filepath: str):
        """Сохранить конфигурацию в файл"""
        config_data = {
            "provider": self.config.provider.value,
            "host": self.config.host,
            "port": self.config.port,
            "model": self.config.model,
            "timeout": self.config.timeout,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "enabled": self.config.enabled,
            "dev_mode": self.config.dev_mode
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print(f"[AI] Конфигурация сохранена в {filepath}")
        except Exception as e:
            print(f"[AI] Ошибка сохранения конфигурации: {e}")
    
    def load_config(self, filepath: str):
        """Загрузить конфигурацию из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.config.provider = AIProvider(config_data.get("provider", "lm_studio"))
            self.config.host = config_data.get("host", "localhost")
            self.config.port = config_data.get("port", 1234)
            self.config.model = config_data.get("model", "")
            self.config.timeout = config_data.get("timeout", 60)
            self.config.max_tokens = config_data.get("max_tokens", 2048)
            self.config.temperature = config_data.get("temperature", 0.7)
            self.config.enabled = config_data.get("enabled", True)
            self.config.dev_mode = config_data.get("dev_mode", False)
            
            self._load_models_list()
            print(f"[AI] Конфигурация загружена из {filepath}")
            
        except Exception as e:
            print(f"[AI] Ошибка загрузки конфигурации: {e}")


# Ленивая инициализация для предотвращения ошибок при импорте
_ai_instance = None

def get_ai_assistant():
    """Получить экземпляр AIAssistant с ленивой инициализацией"""
    global _ai_instance
    if _ai_instance is None:
        try:
            _ai_instance = AIAssistant()
        except Exception as e:
            print(f"[AI] Ошибка инициализации: {e}")
            return None
    return _ai_instance
