# 🚀 ProxMaster3 Easy v2.0

**Профессиональное приложение для работы с Proxmark3 Easy на прошивке Iceman**

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 📋 Описание

ProxMaster3 Easy - это полноценное GUI-приложение для Windows, предназначенное для работы с устройством Proxmark3 Easy с прошивкой Iceman. Приложение предоставляет удобный графический интерфейс для всех 857+ команд Proxmark3, встроенный Hex-редактор, Node Editor для создания скриптов, AI-помощника и многое другое.

## ✨ Возможности

### 9 Вкладок Интерфейса:

1. **🏠 ГЛАВНАЯ** - Быстрый доступ к основным функциям
   - Подключение к устройству
   - Статус устройства
   - Быстрые команды (статус, версия, антенна, поиск LF/HF)

2. **🔍 ПОИСК** - Поиск и чтение карт
   - LF протоколы (EM410x, T55xx, HID, Indala, HiTag2, и др.)
   - HF протоколы (ISO14443A/B, Mifare, iClass, LEGIC, FeliCa)

3. **💾 МЕНЕДЖЕР ДАННЫХ** - Работа с дампами
   - Встроенный Hex-редактор
   - Сохранение/загрузка дампов
   - История изменений
   - Экспорт в различные форматы

4. **✏️ ЗАПИСЬ** - Запись на карты
   - T55xx программирование
   - Mifare Classic запись
   - EM410x клонирование

5. **🎭 ЭМУЛЯЦИЯ** - Эмуляция карт
   - LF эмуляция
   - HF эмуляция
   - Mifare симуляция

6. **📡 СНИФИНГ** - Перехват трафика
   - LF снифинг
   - HF снифинг
   - Анализ трафика

7. **📜 СКРИПТЫ** - Автоматизация
   - Lua скрипты
   - Node.js Editor
   - Готовые атаки

8. **🛠️ ИНСТРУМЕНТЫ** - Дополнительные функции
   - Графики сигнала
   - Анализ данных
   - GPIO управление
   - UART тесты

9. **⚙️ НАСТРОЙКИ** - Конфигурация
   - Установка ProxSpace
   - Обновление прошивки
   - AI помощник
   - Тема интерфейса

## 🔧 Технические Характеристики

- **857+ команд** Proxmark3 Iceman firmware
- **JSON конфигурация** команд для легкого расширения
- **Реальная работа** с устройством (не эмуляция!)
- **Hex-редактор** с историей изменений
- **Node Editor** для JavaScript/Node.js скриптов
- **AI-помощник** с поддержкой локальных моделей
- **Автоматическое обновление** прошивки
- **Темная тема** оформления

## 🚀 Установка

### Требования:
- Windows 10/11
- Python 3.8 или выше
- Proxmark3 Easy с прошивкой Iceman (или установите через приложение)
- Драйверы CP210x или CH340 для Proxmark3

### Быстрая установка:

1. **Скачайте репозиторий:**
```bash
git clone https://github.com/yourusername/ProxMaster3_Easy.git
cd ProxMaster3_Easy
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Запустите приложение:**
```bash
python main.py
```

**Или используйте готовый скрипт для Windows:**
```
install.bat
```

### Установка ProxSpace и Iceman:

Если у вас не установлен ProxSpace:

1. Откройте вкладку **НАСТРОЙКИ**
2. Нажмите **"Установить ProxSpace"**
3. Следуйте инструкциям

**Или вручную:**
```bash
python installer/proxspace_installer.py
```

## 📖 Использование

### Подключение к устройству:

1. Подключите Proxmark3 Easy к USB
2. Запустите ProxMaster3 Easy
3. На вкладке **ГЛАВНАЯ** нажмите **"🔄 Обновить"** для поиска портов
4. Выберите найденный порт и нажмите **"🔌 Подключиться"**

### Выполнение команд:

1. Перейдите на нужную вкладку
2. Выберите команду из списка
3. При необходимости введите параметры
4. Нажмите **"Выполнить"**
5. Смотрите результат в логе

### Работа с Hex-редактором:

1. Откройте вкладку **МЕНЕДЖЕР ДАННЫХ**
2. Загрузите дамп или создайте новый
3. Редактируйте данные в hex формате
4. Используйте **Ctrl+Z** для отмены
5. Сохраните изменения

### AI Помощник:

1. Установите LM Studio, Ollama или Cherry Studio
2. Загрузите модель (рекомендуется Llama 3, Mistral, или аналогичная)
3. В настройках ProxMaster укажите URL API
4. Задавайте вопросы по командам, анализу дампов, созданию скриптов

## 📁 Структура Проекта

```
ProxMaster3_Easy/
├── main.py                 # Точка входа
├── proxmaster_main.py      # Основное приложение (для совместимости)
├── commands.json           # 857+ команд в JSON
├── requirements.txt        # Зависимости Python
├── install.bat            # Скрипт установки для Windows
├── README.md              # Документация
├── core/                  # Ядро приложения
│   ├── __init__.py
│   ├── device_manager.py   # Управление устройством
│   ├── command_executor.py # Выполнение команд
│   └── data_manager.py     # Работа с данными
├── gui/                   # Графический интерфейс
│   ├── __init__.py
│   ├── main_window.py      # Главное окно
│   └── tabs/              # Вкладки
│       ├── __init__.py
│       ├── home_tab.py     # Главная
│       └── ...            # Остальные вкладки
├── utils/                 # Утилиты
│   ├── __init__.py
│   ├── logger_setup.py    # Логирование
│   ├── config_manager.py  # Конфигурация
│   └── ai_assistant.py    # AI помощник
├── installer/             # Установщик
│   └── proxspace_installer.py
├── dumps/                 # Дампы карт
├── keys/                  # Ключи доступа
├── scripts/               # Скрипты
├── logs/                  # Логи
└── models/                # AI модели
```

## 🔌 API AI Помощника

Поддерживаемые провайдеры:
- **LM Studio**: `http://localhost:1234/v1`
- **Ollama**: `http://localhost:11434`
- **Cherry Studio**: `http://localhost:8080/v1`

Пример запроса:
```python
from utils.ai_assistant import AIAssistant

ai = AIAssistant(provider='lm_studio')
ai.set_model('llama-3-8b')

answer = ai.ask("Как скопировать карту Mifare Classic?")
print(answer)
```

## 🛠️ Разработка

### Добавление новых команд:

Откройте `commands.json` и добавьте:

```json
{
  "id": "unique_command_id",
  "name": "Название команды",
  "command": "pm3_command <params>",
  "description": "Описание",
  "category": "категория",
  "icon": "🔧",
  "parameters": ["param1"],
  "warning": "Предупреждение если есть"
}
```

### Сборка в EXE:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name="ProxMaster3_Easy" main.py
```

## ⚠️ Предупреждения

- Используйте только на картах, которыми владеете
- Некоторые операции могут повредить карты
- Соблюдайте законодательство вашей страны
- Авторы не несут ответственности за неправильное использование

## 📄 Лицензия

MIT License - см. файл LICENSE

## 🤝 Вклад в проект

Pull requests приветствуются! Пожалуйста:
1. Fork репозиторий
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📞 Контакты

- GitHub: [ваш профиль]
- Telegram: [ваш канал]
- Email: [ваш email]

## 🙏 Благодарности

- [Proxmark3 Iceman Team](https://github.com/RfidResearchGroup/proxmark3)
- [ProxSpace](https://github.com/Gator96100/ProxSpace)
- Всем контрибьюторам open-source проектов

---

**ProxMaster3 Easy v2.0** © 2024. Создано с ❤️ для сообщества RFID исследователей.
