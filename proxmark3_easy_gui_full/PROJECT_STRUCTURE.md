# Proxmark3 Easy GUI - Структура Проекта

## 📁 Файловая Структура

```
proxmark3_easy_gui_full/
├── proxmark3_easy_gui.py      # Главный файл приложения (1854 строки)
├── src/
│   ├── __init__.py            # Экспорт команд из commands.py
│   └── commands.py            # База данных всех команд Proxmark3 (794 строки)
├── dumps/                     # Папка для дампов памяти карт
├── keys/                      # Папка для файлов ключей (.key)
├── scripts/                   # Папка для Lua скриптов
├── logs/                      # Папка для логов работы
├── resources/                 # Ресурсы (иконки, изображения)
├── installers/                # Установщик ProxSpace
├── requirements.txt           # Python зависимости
├── run_app.bat               # Скрипт запуска для Windows
├── README.md                 # Основная документация
└── PROJECT_STRUCTURE.md      # Этот файл
```

## 🔧 Модульная Архитектура

### 1. `src/commands.py` - Ядро Систем Команд
- **49 команд** Proxmark3 Iceman
- Категории: HARDWARE, LF, HF, DATA, TRACE, MEM, ANALYSE, SCRIPT
- Уровни риска: SAFE, WARNING, DANGEROUS
- Параметры команд с типизацией
- Примеры использования для каждой команды

**Структура команды:**
```python
@dataclass
class CommandInfo:
    id: str                    # Уникальный ID
    name: str                  # Отображаемое имя
    command: str               # Строка команды
    category: CommandCategory  # Категория
    description: str           # Описание
    risk: CommandRisk          # Уровень риска
    hint: str                  # Подсказка
    info_command: str          # Команда справки
    parameters: List[CommandParameter]
    protocols: List[str]       # Протоколы (LF/HF)
    examples: List[str]        # Примеры
```

### 2. `proxmark3_easy_gui.py` - Графический Интерфейс
**9 Вкладок:**
1. **ГЛАВНАЯ** - Статус устройства, версии, подключение
2. **ПОИСК И ЧТЕНИЕ** - LF/HF поиск, чтение, визуализация
3. **ПАМЯТЬ И КЛЮЧИ** - Hex редактор, управление ключами
4. **ЗАПИСЬ** - Мастер записи карт (T5577, Magic UID)
5. **СНИФФИГ** - Перехват трафика, таблица пакетов
6. **ЭМУЛЯЦИЯ** - Эмуляция карт по дампу/UID
7. **ИНСТРУМЕНТЫ** - Графики, спектр, демодуляция
8. **СКРИПТЫ** - Lua скрипты + Node Editor
9. **СИСТЕМА** - Установка ProxSpace, прошивка, настройки

**Ключевые Классы:**
- `Proxmark3EasyGUI` - Главное окно
- `ProxmarkClient` - Работа с процессом Proxmark3
- `LogViewer` - Цветной вывод логов
- `SignalPlotter` - Графики сигналов
- `HexEditor` - Редактор дампов
- `NodeScriptEditor` - Визуальный редактор скриптов
- `ProxSpaceInstaller` - Мастер установки

## 🚀 Запуск Приложения

### На Windows:
```batch
# Вариант 1: Через BAT файл
run_app.bat

# Вариант 2: Вручную
pip install -r requirements.txt
python proxmark3_easy_gui.py
```

### Зависимости (`requirements.txt`):
```
customtkinter>=5.2.0
matplotlib>=3.7.0
numpy>=1.24.0
pyserial>=3.5
Pillow>=9.0.0
```

## 🔌 Подключение к Proxmark3

1. **Первый запуск:**
   - Приложение проверяет наличие ProxSpace
   - Если не найден → запускается Мастер установки
   - Автоматическая загрузка с GitHub RRG/Iceman

2. **Подключение:**
   - COM-порт определяется автоматически
   - Кнопка "Connect" в главной вкладке
   - Индикация статуса в реальном времени

## 📊 Возможности GUI

### Умные Команды
- **!** - Простая подсказка при наведении
- **!!** - Подробная справка по клику
- Группировка по категориям
- Выпадающие списки для специфичных команд

### Безопасность
- Модальные подтверждения для опасных операций
- Уровни риска: SAFE → WARNING → DANGEROUS
- Блокировка случайных нажатий

### Визуализация
- Цветные логи: `[+]` зеленый, `[-]` красный, `[=]` синий
- Прогресс-бары для длительных операций
- Графики сигналов (Matplotlib)
- Спектральный анализ

### Hex Редактор
- Просмотр дампов в hex/grid формате
- Редактирование байтов
- Drag & Drop файлов (.eml, .bin)
- Сохранение изменений

### Node Editor (Скрипты)
- Визуальное создание скриптов
- Ноды: Чтение → Обработка → Запись
- Экспорт в Lua
- Библиотека готовых нод

## 🛠 Расширение Функционала

### Добавление Новой Команды
В файле `src/commands.py`:

```python
register_command(
    "my_new_command",
    name="Моя Команда",
    command="hf mycmd",
    category=CommandCategory.HF,
    description="Описание команды",
    hint="Подсказка",
    risk=CommandRisk.SAFE,
    parameters=[
        CommandParameter("param1", "int", True, description="Параметр 1")
    ],
    examples=["hf mycmd 123"]
)
```

### Добавление Вкладки
В классе `Proxmark3EasyGUI`:
1. Создать метод `create_<tabname>_tab()`
2. Добавить вызов в `create_tabs()`
3. Реализовать логику работы

## 📝 Конфигурация

Файл конфигурации: `~/.proxmark3_easy_gui/config.json`

```json
{
    "proxspace_path": "C:/Proxmark3/ProxSpace/pm3",
    "client_path": "C:/Proxmark3/ProxSpace/pm3/client/proxmark3.exe",
    "com_port": "COM3",
    "theme": "Dark",
    "language": "ru",
    "auto_connect": false,
    "log_level": "INFO"
}
```

## 🎯 Roadmap

- [ ] Полная поддержка всех протоколов LF/HF
- [ ] Готовые шаблоны Node скриптов
- [ ] Автообновление GUI
- [ ] Мультиязычность (RU/EN/CN)
- [ ] Плагины для расширения
- [ ] Онлайн база дампов карт

## 🤝 Вклад в Проект

1. Fork репозитория
2. Создание ветки (`git checkout -b feature/NewFeature`)
3. Коммит изменений (`git commit -m 'Add NewFeature'`)
4. Push в ветку (`git push origin feature/NewFeature`)
5. Открыть Pull Request

## 📄 Лицензия

MIT License - свободное использование и модификация

## 👥 Авторы

- Proxmark3 Community
- RRG/Iceman проект
- Вдохновлено Chameleon Ultra GUI

---

**Версия:** 2.0.0  
**Дата:** 2024  
**Совместимость:** Windows 10/11, Proxmark3 Easy/RDV4/Iceman
