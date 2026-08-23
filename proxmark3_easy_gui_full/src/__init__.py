"""
Proxmark3 Easy GUI - Модуль команд и структур данных
Определяет все команды Proxmark3 Iceman для использования в GUI

Этот файл содержит полную базу данных команд для работы с:
- LF (Low Frequency) 125 kHz
- HF (High Frequency) 13.56 MHz
- NFC протоколами
- EMV картами
- Smart картами
- PIV картами
- Управлением памятью и данными
- Анализу сигналов
- Скриптами автоматизации
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum, auto
import re


# ============================================================================
# ПЕРЕЧИСЛЕНИЯ И ТИПЫ ДАННЫХ
# ============================================================================

class CommandCategory(Enum):
    """Категории команд Proxmark3"""
    HARDWARE = "hardware"           # Аппаратные команды
    LF = "lf"                       # Низкочастотные (125 kHz)
    HF = "hf"                       # Высокочастотные (13.56 MHz)
    NFC = "nfc"                     # NFC протоколы
    EMV = "emv"                     # EMV банковские карты
    SMART = "smart"                 # Смарт-карты ISO 7816
    PIV = "piv"                     # PIV карты
    DATA = "data"                   # Обработка данных
    TRACE = "trace"                 # Трассировка
    SCRIPT = "script"               # Lua скрипты
    MEM = "mem"                     # Память устройства
    ANALYSE = "analyse"             # Анализ сигналов
    DANGEROUS = "dangerous"         # Опасные операции
    AUTO = "auto"                   # Автопоиск


class CommandRisk(Enum):
    """Уровень риска выполнения команды"""
    SAFE = "safe"               # Безопасная команда
    WARNING = "warning"         # Требует внимания
    DANGEROUS = "dangerous"     # Опасная операция (запись, прошивка)


class CommandType(Enum):
    """Типы команд по способу выполнения"""
    DIRECT = "direct"           # Прямое выполнение
    INTERACTIVE = "interactive" # Интерактивный режим
    SCRIPT = "script"           # Lua скрипт
    BATCH = "batch"             # Пакетное выполнение


@dataclass
class CommandParameter:
    """Параметр команды"""
    name: str
    type: str = "string"        # string, int, hex, bool
    required: bool = False
    default: Any = None
    description: str = ""
    choices: List[str] = field(default_factory=list)  # Для enum параметров
    min_value: Optional[int] = None
    max_value: Optional[int] = None


@dataclass
class CommandInfo:
    """
    Полная информация о команде Proxmark3
    
    Attributes:
        id: Уникальный идентификатор команды (ключ в базе)
        name: Отображаемое имя в GUI
        command: Строка команды для выполнения
        category: Категория команды
        description: Подробное описание
        risk: Уровень риска
        hint: Краткая подсказка при наведении
        info_command: Команда для получения подробной справки
        parameters: Список параметров
        protocols: Поддерживаемые протоколы (для LF/HF)
        examples: Примеры использования
        related_commands: Связанные команды
        output_parser: Функция парсинга вывода (опционально)
    """
    id: str
    name: str
    command: str
    category: CommandCategory
    description: str
    risk: CommandRisk = CommandRisk.SAFE
    hint: str = ""
    info_command: str = ""
    parameters: List[CommandParameter] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    related_commands: List[str] = field(default_factory=list)
    output_parser: Optional[Callable] = None


# ============================================================================
# БАЗА ДАННЫХ КОМАНД
# ============================================================================

COMMANDS_DB: Dict[str, CommandInfo] = {}


def register_command(cmd_id: str, **kwargs) -> CommandInfo:
    """Регистрация команды в базе данных"""
    cmd = CommandInfo(id=cmd_id, **kwargs)
    COMMANDS_DB[cmd_id] = cmd
    return cmd


# ============================================================================
# ГЛАВНАЯ ВКЛАДКА - АППАРАТНЫЕ КОМАНДЫ И АВТОПОИСК
# ============================================================================

register_command(
    "hw_status",
    name="Статус устройства",
    command="hw status",
    category=CommandCategory.HARDWARE,
    description="Проверка статуса подключения и состояния устройства. "
                "Показывает текущее состояние Proxmark3, версию прошивки, "
                "статус антенн и подключенных модулей.",
    hint="Показывает текущее состояние Proxmark3",
    info_command="hw status --info",
    examples=["hw status", "hw status verbose"]
)

register_command(
    "hw_version",
    name="Версии устройства",
    command="hw version",
    category=CommandCategory.HARDWARE,
    description="Отображение версий Firmware, Bootrom, Hardware. "
                "Выводит полную информацию о версиях всех компонентов устройства.",
    hint="Информация о версиях прошивок и железа",
    info_command="hw version",
    examples=["hw version", "hw version full"]
)

register_command(
    "hw_tune",
    name="Настройка антенн",
    command="hw tune",
    category=CommandCategory.HARDWARE,
    description="Измерение параметров антенн LF и HF. "
                "Показывает резонансные частоты, добротность и другие параметры.",
    hint="Показывает резонансные частоты и добротность антенн",
    info_command="hw tune",
    examples=["hw tune", "hw tune -a"]
)

register_command(
    "hw_reset",
    name="Перезагрузка",
    command="hw reset",
    category=CommandCategory.HARDWARE,
    description="Перезагрузка устройства. Выполняет мягкую перезагрузку Proxmark3.",
    risk=CommandRisk.WARNING,
    hint="Выполняет мягкую перезагрузку Proxmark3",
    info_command="hw reset",
    examples=["hw reset"]
)

register_command(
    "hw_teardown",
    name="Проверка цепей",
    command="hw teardown",
    category=CommandCategory.HARDWARE,
    description="Тестирование аппаратных цепей устройства. "
                "Диагностика hardware компонентов.",
    hint="Диагностика hardware компонентов",
    info_command="hw teardown",
    examples=["hw teardown"]
)

register_command(
    "hw_decay",
    name="Затухание HF",
    command="hw decay",
    category=CommandCategory.HARDWARE,
    description="Измерение затухания HF антенны. "
                "Проверка качества HF антенны.",
    hint="Проверка качества HF антенны",
    info_command="hw decay",
    examples=["hw decay"]
)

register_command(
    "hw_readmem",
    name="Память ARM",
    command="hw readmem",
    category=CommandCategory.HARDWARE,
    description="Чтение памяти ARM процессора. "
                "Прямой доступ к памяти устройства.",
    hint="Прямой доступ к памяти устройства",
    parameters=[
        CommandParameter("address", "hex", True, description="Адрес начала чтения"),
        CommandParameter("length", "int", False, 256, "Количество байт")
    ],
    info_command="hw readmem",
    examples=["hw readmem 0x00000000 256"]
)

register_command(
    "hw_setmux",
    name="Мультиплексор",
    command="hw setmux",
    category=CommandCategory.HARDWARE,
    description="Настройка мультиплексора антенн. "
                "Выбор активной антенны (0-7).",
    hint="Выбор активной антенны (0-7)",
    parameters=[
        CommandParameter("channel", "int", True, 
                        min_value=0, max_value=7,
                        description="Номер канала антенны")
    ],
    info_command="hw setmux",
    examples=["hw setmux 0", "hw setmux 1"]
)

register_command(
    "hw_lcd",
    name="LCD управление",
    command="hw lcd",
    category=CommandCategory.HARDWARE,
    description="Управление LCD дисплеем (если есть). "
                "Вкл/выкл/настройка LCD.",
    hint="Управление LCD дисплеем",
    parameters=[
        CommandParameter("action", "string", False, "show",
                        choices=["on", "off", "show", "brightness"],
                        description="Действие с LCD")
    ],
    info_command="hw lcd",
    examples=["hw lcd on", "hw lcd off", "hw lcd brightness 50"]
)

register_command(
    "hw_kick",
    name="Антенна вкл/выкл",
    command="hw kick",
    category=CommandCategory.HARDWARE,
    description="Включение/выключение питания антенн. "
                "Управление питанием антенн.",
    hint="Управление питанием антенн",
    parameters=[
        CommandParameter("antenna", "string", False, "all",
                        choices=["lf", "hf", "all", "off"],
                        description="Какие антенны включить")
    ],
    info_command="hw kick",
    examples=["hw kick lf", "hw kick hf", "hw kick off"]
)

register_command(
    "hw_break",
    name="Прервать операцию",
    command="hw break",
    category=CommandCategory.HARDWARE,
    description="Экстренная остановка текущей операции. "
                "Останавливает выполнение любой команды.",
    risk=CommandRisk.WARNING,
    hint="Останавливает выполнение любой команды",
    info_command="hw break",
    examples=["hw break"]
)

register_command(
    "hw_bootloader",
    name="Режим загрузчика",
    command="hw bootloader",
    category=CommandCategory.HARDWARE,
    description="Переход в режим загрузчика для прошивки. "
                "Требуется для обновления прошивки.",
    risk=CommandRisk.DANGEROUS,
    hint="Требуется для обновления прошивки",
    info_command="hw bootloader",
    examples=["hw bootloader"]
)

register_command(
    "auto",
    name="Автопоиск карт",
    command="auto",
    category=CommandCategory.AUTO,
    description="Автоматический поиск всех типов карт (LF + HF). "
                "Полное сканирование всех частот и протоколов.",
    hint="Полное сканирование всех частот и протоколов",
    info_command="auto",
    examples=["auto", "auto -v"],
    related_commands=["lf search", "hf search"]
)


# ============================================================================
# LF (Low Frequency) - 125 kHz - ПОИСК И ЧТЕНИЕ
# ============================================================================

register_command(
    "lf_search",
    name="Поиск LF",
    command="lf search",
    category=CommandCategory.LF,
    description="Поиск LF карт (125 kHz). "
                "Сканирование всех известных LF протоколов.",
    hint="Поиск LF карт на антенне",
    info_command="lf search",
    protocols=["EM4100", "EM4x05", "T55xx", "HID", "AWID", "Indala", 
               "IO", "Keri", "Motorola", "Nedap", "Paradox", "Pyramid", 
               "Securakey", "TI", "Trojan", "Viking"],
    examples=["lf search", "lf search u", "lf search v"]
)

register_command(
    "lf_read",
    name="Чтение LF",
    command="lf read",
    category=CommandCategory.LF,
    description="Чтение сигнала с LF карты. "
                "Запись сырого сигнала в буфер.",
    hint="Чтение LF сигнала",
    info_command="lf read",
    examples=["lf read", "lf read -s"]
)

register_command(
    "lf_config",
    name="Настройка LF",
    command="lf config",
    category=CommandCategory.LF,
    description="Конфигурация параметров чтения LF. "
                "Настройка делителя, децимации, усреднения.",
    hint="Настройка параметров чтения",
    parameters=[
        CommandParameter("divid", "int", False, description="Делитель частоты"),
        CommandParameter("decim", "int", False, description="Децимация"),
        CommandParameter("avg", "int", False, description="Усреднение"),
        CommandParameter("samples", "int", False, description="Количество сэмплов")
    ],
    info_command="lf config",
    examples=["lf config 110592", "lf config 110592 0 0 0"]
)

register_command(
    "lf_cmdread",
    name="Чтение с параметрами",
    command="lf cmdread",
    category=CommandCategory.LF,
    description="Чтение LF с заданными параметрами. "
                "Прямое управление таймингами чтения.",
    hint="Чтение с ручными параметрами",
    parameters=[
        CommandParameter("off_time", "int", True, description="Время выключения"),
        CommandParameter("on_time", "int", True, description="Время включения"),
        CommandParameter("period", "int", True, description="Период"),
        CommandParameter("data", "hex", True, description="Данные для отправки")
    ],
    info_command="lf cmdread",
    examples=["lf cmdread 1 1 1 FF"]
)

register_command(
    "lf_snoop",
    name="Сниффинг LF",
    command="lf snoop",
    category=CommandCategory.LF,
    description="Перехват LF сигналов. "
                "Запись всех проходящих сигналов.",
    hint="Перехват LF трафика",
    info_command="lf snoop",
    examples=["lf snoop", "lf snoop -t 5000"]
)

register_command(
    "lf_sniff",
    name="Сниффинг LF (альт)",
    command="lf sniff",
    category=CommandCategory.LF,
    description="Альтернативный режим перехвата LF. "
                "Расширенные возможности сниффинга.",
    hint="Альтернативный сниффинг",
    info_command="lf sniff",
    examples=["lf sniff"]
)


# ============================================================================
# LF - EM4100 / EM4102
# ============================================================================

register_command(
    "lf_em_410x_reader",
    name="Чтение EM4100",
    command="lf em 410x reader",
    category=CommandCategory.LF,
    description="Чтение карт EM4100/EM4102. "
                "Стандартный протокол идентификации.",
    hint="Чтение EM4100 карт",
    protocols=["EM4100"],
    info_command="lf em 410x reader",
    examples=["lf em 410x reader"]
)

register_command(
    "lf_em_410x_watch",
    name="Мониторинг EM4100",
    command="lf em 410x watch",
    category=CommandCategory.LF,
    description="Непрерывное чтение EM4100. "
                "Мониторинг появления карт.",
    hint="Непрерывный мониторинг",
    info_command="lf em 410x watch",
    examples=["lf em 410x watch"]
)

register_command(
    "lf_em_410x_sim",
    name="Эмуляция EM4100",
    command="lf em 410x sim",
    category=CommandCategory.LF,
    description="Эмуляция карты EM4100. "
                "Симуляция ответа карты с заданным ID.",
    hint="Эмуляция EM4100 карты",
    parameters=[
        CommandParameter("id", "hex", True, description="ID карты (10 hex символов)")
    ],
    info_command="lf em 410x sim",
    examples=["lf em 410x sim 0123456789"]
)

register_command(
    "lf_em_410x_clone",
    name="Клонирование EM4100",
    command="lf em 410x clone",
    category=CommandCategory.LF,
    description="Запись клона EM4100 на T55xx. "
                "Копирование ID на перезаписываемую карту.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись клона на T55xx",
    parameters=[
        CommandParameter("id", "hex", True, description="ID для записи")
    ],
    info_command="lf em 410x clone",
    examples=["lf em 410x clone 0123456789"]
)

register_command(
    "lf_em_410x_brute",
    name="Брутфорс EM4100",
    command="lf em 410x brute",
    category=CommandCategory.LF,
    description="Перебор ID карт EM4100. "
                "Автоматический подбор идентификатора.",
    hint="Перебор ID",
    info_command="lf em 410x brute",
    examples=["lf em 410x brute"]
)


# ============================================================================
# LF - EM4x05
# ============================================================================

register_command(
    "lf_em_4x05_info",
    name="Инфо EM4x05",
    command="lf em 4x05 info",
    category=CommandCategory.LF,
    description="Получение информации о карте EM4x05. "
                "Чтение конфигурации и статуса.",
    hint="Информация о карте",
    info_command="lf em 4x05 info",
    examples=["lf em 4x05 info"]
)

register_command(
    "lf_em_4x05_read",
    name="Чтение EM4x05",
    command="lf em 4x05 read",
    category=CommandCategory.LF,
    description="Чтение данных с EM4x05. "
                "Побайтовое чтение памяти.",
    hint="Чтение данных",
    parameters=[
        CommandParameter("address", "int", True, description="Адрес начала чтения")
    ],
    info_command="lf em 4x05 read",
    examples=["lf em 4x05 read 0"]
)

register_command(
    "lf_em_4x05_dump",
    name="Дамп EM4x05",
    command="lf em 4x05 dump",
    category=CommandCategory.LF,
    description="Полное чтение памяти EM4x05. "
                "Сохранение всего содержимого карты.",
    hint="Полный дамп карты",
    info_command="lf em 4x05 dump",
    examples=["lf em 4x05 dump"]
)

register_command(
    "lf_em_4x05_write",
    name="Запись EM4x05",
    command="lf em 4x05 write",
    category=CommandCategory.LF,
    description="Запись данных на EM4x05. "
                "Изменение содержимого карты.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись данных на карту",
    parameters=[
        CommandParameter("address", "int", True, description="Адрес записи"),
        CommandParameter("data", "hex", True, description="Данные для записи")
    ],
    info_command="lf em 4x05 write",
    examples=["lf em 4x05 write 0 DEADBEEF"]
)

register_command(
    "lf_em_4x05_config",
    name="Конфиг EM4x05",
    command="lf em 4x05 config",
    category=CommandCategory.LF,
    description="Настройка конфигурации EM4x05. "
                "Изменение настроек карты.",
    hint="Настройка конфигурации",
    parameters=[
        CommandParameter("config", "hex", True, description="Новое значение конфига")
    ],
    info_command="lf em 4x05 config",
    examples=["lf em 4x05 config 0x00000000"]
)

register_command(
    "lf_em_4x05_unlock",
    name="Разблокировка EM4x05",
    command="lf em 4x05 unlock",
    category=CommandCategory.LF,
    description="Разблокировка защищенной EM4x05. "
                "Снятие защиты паролем.",
    risk=CommandRisk.WARNING,
    hint="Разблокировка карты",
    parameters=[
        CommandParameter("password", "hex", True, description="Пароль доступа")
    ],
    info_command="lf em 4x05 unlock",
    examples=["lf em 4x05 unlock 12345678"]
)

register_command(
    "lf_em_4x05_chk",
    name="Проверка ключа EM4x05",
    command="lf em 4x05 chk",
    category=CommandCategory.LF,
    description="Проверка пароля EM4x05. "
                "Верификация ключа доступа.",
    hint="Проверка пароля",
    parameters=[
        CommandParameter("password", "hex", True, description="Пароль для проверки")
    ],
    info_command="lf em 4x05 chk",
    examples=["lf em 4x05 chk 12345678"]
)

register_command(
    "lf_em_4x05_brute",
    name="Брутфорс EM4x05",
    command="lf em 4x05 brute",
    category=CommandCategory.LF,
    description="Перебор пароля EM4x05. "
                "Автоматический подбор ключа.",
    hint="Перебор пароля",
    info_command="lf em 4x05 brute",
    examples=["lf em 4x05 brute"]
)


# ============================================================================
# LF - EM4x50
# ============================================================================

register_command(
    "lf_em_4x50_info",
    name="Инфо EM4x50",
    command="lf em 4x50 info",
    category=CommandCategory.LF,
    description="Информация о карте EM4x50. "
                "Чтение технических параметров.",
    hint="Информация о карте",
    info_command="lf em 4x50 info",
    examples=["lf em 4x50 info"]
)

register_command(
    "lf_em_4x50_rdbl",
    name="Чтение блока EM4x50",
    command="lf em 4x50 rdbl",
    category=CommandCategory.LF,
    description="Чтение блока EM4x50. "
                "Поблочное чтение памяти.",
    hint="Чтение блока",
    parameters=[
        CommandParameter("block", "int", True, description="Номер блока")
    ],
    info_command="lf em 4x50 rdbl",
    examples=["lf em 4x50 rdbl 0"]
)

register_command(
    "lf_em_4x50_dump",
    name="Дамп EM4x50",
    command="lf em 4x50 dump",
    category=CommandCategory.LF,
    description="Полный дамп EM4x50. "
                "Сохранение всей памяти карты.",
    hint="Полный дамп",
    info_command="lf em 4x50 dump",
    examples=["lf em 4x50 dump"]
)

register_command(
    "lf_em_4x50_login",
    name="Логин EM4x50",
    command="lf em 4x50 login",
    category=CommandCategory.LF,
    description="Авторизация на EM4x50. "
                "Вход с использованием пароля.",
    hint="Авторизация",
    parameters=[
        CommandParameter("password", "hex", True, description="Пароль")
    ],
    info_command="lf em 4x50 login",
    examples=["lf em 4x50 login 12345678"]
)

register_command(
    "lf_em_4x50_wrbl",
    name="Запись блока EM4x50",
    command="lf em 4x50 wrbl",
    category=CommandCategory.LF,
    description="Запись блока EM4x50. "
                "Изменение содержимого блока.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись блока",
    parameters=[
        CommandParameter("block", "int", True, description="Номер блока"),
        CommandParameter("data", "hex", True, description="Данные")
    ],
    info_command="lf em 4x50 wrbl",
    examples=["lf em 4x50 wrbl 0 DEADBEEF"]
)

register_command(
    "lf_em_4x50_wrpwd",
    name="Запись пароля EM4x50",
    command="lf em 4x50 wrpwd",
    category=CommandCategory.LF,
    description="Изменение пароля EM4x50. "
                "Установка нового пароля доступа.",
    risk=CommandRisk.DANGEROUS,
    hint="Смена пароля",
    parameters=[
        CommandParameter("new_password", "hex", True, description="Новый пароль")
    ],
    info_command="lf em 4x50 wrpwd",
    examples=["lf em 4x50 wrpwd 87654321"]
)

register_command(
    "lf_em_4x50_chk",
    name="Проверка ключа EM4x50",
    command="lf em 4x50 chk",
    category=CommandCategory.LF,
    description="Проверка пароля EM4x50. "
                "Верификация ключа.",
    hint="Проверка пароля",
    parameters=[
        CommandParameter("password", "hex", True, description="Пароль")
    ],
    info_command="lf em 4x50 chk",
    examples=["lf em 4x50 chk 12345678"]
)

register_command(
    "lf_em_4x50_brute",
    name="Брутфорс EM4x50",
    command="lf em 4x50 brute",
    category=CommandCategory.LF,
    description="Перебор пароля EM4x50. "
                "Автоматический подбор.",
    hint="Перебор пароля",
    info_command="lf em 4x50 brute",
    examples=["lf em 4x50 brute"]
)


# ============================================================================
# LF - EM4x70
# ============================================================================

register_command(
    "lf_em_4x70_info",
    name="Инфо EM4x70",
    command="lf em 4x70 info",
    category=CommandCategory.LF,
    description="Информация о карте EM4x70. "
                "Технические параметры и статус.",
    hint="Информация о карте",
    info_command="lf em 4x70 info",
    examples=["lf em 4x70 info"]
)

register_command(
    "lf_em_4x70_auth",
    name="Авторизация EM4x70",
    command="lf em 4x70 auth",
    category=CommandCategory.LF,
    description="Авторизация на EM4x70. "
                "Вход с использованием ключа.",
    hint="Авторизация",
    parameters=[
        CommandParameter("key", "hex", True, description="Ключ авторизации")
    ],
    info_command="lf em 4x70 auth",
    examples=["lf em 4x70 auth AABBCCDD"]
)

register_command(
    "lf_em_4x70_calc",
    name="Расчет ключа EM4x70",
    command="lf em 4x70 calc",
    category=CommandCategory.LF,
    description="Вычисление ключа EM4x70. "
                "Расчет на основе известных данных.",
    hint="Расчет ключа",
    info_command="lf em 4x70 calc",
    examples=["lf em 4x70 calc"]
)

register_command(
    "lf_em_4x70_brute",
    name="Брутфорс EM4x70",
    command="lf em 4x70 brute",
    category=CommandCategory.LF,
    description="Перебор пароля EM4x70. "
                "Автоматический подбор ключа.",
    hint="Перебор пароля",
    info_command="lf em 4x70 brute",
    examples=["lf em 4x70 brute"]
)

register_command(
    "lf_em_4x70_recover",
    name="Восстановление EM4x70",
    command="lf em 4x70 recover",
    category=CommandCategory.LF,
    description="Восстановление доступа EM4x70. "
                "Восстановление утерянных ключей.",
    hint="Восстановление доступа",
    info_command="lf em 4x70 recover",
    examples=["lf em 4x70 recover"]
)

register_command(
    "lf_em_4x70_autorecover",
    name="Авто-восстановление EM4x70",
    command="lf em 4x70 autorecover",
    category=CommandCategory.LF,
    description="Автоматическое восстановление EM4x70. "
                "Полностью автоматизированный процесс.",
    hint="Авто-восстановление",
    info_command="lf em 4x70 autorecover",
    examples=["lf em 4x70 autorecover"]
)


# ============================================================================
# LF - T55xx
# ============================================================================

register_command(
    "lf_t55xx_detect",
    name="Детекция T55xx",
    command="lf t55xx detect",
    category=CommandCategory.LF,
    description="Определение типа карты T55xx. "
                "Автоматическое определение модели.",
    hint="Определение типа карты",
    info_command="lf t55xx detect",
    examples=["lf t55xx detect"]
)

register_command(
    "lf_t55xx_info",
    name="Инфо T55xx",
    command="lf t55xx info",
    category=CommandCategory.LF,
    description="Информация о конфигурации T55xx. "
                "Текущие настройки карты.",
    hint="Информация о конфигурации",
    info_command="lf t55xx info",
    examples=["lf t55xx info"]
)

register_command(
    "lf_t55xx_read",
    name="Чтение T55xx",
    command="lf t55xx read",
    category=CommandCategory.LF,
    description="Чтение данных T55xx. "
                "Поблочное чтение.",
    hint="Чтение данных",
    parameters=[
        CommandParameter("block", "int", False, description="Номер блока")
    ],
    info_command="lf t55xx read",
    examples=["lf t55xx read", "lf t55xx read 0"]
)

register_command(
    "lf_t55xx_dump",
    name="Дамп T55xx",
    command="lf t55xx dump",
    category=CommandCategory.LF,
    description="Полный дамп памяти T55xx. "
                "Сохранение всех блоков.",
    hint="Полный дамп",
    info_command="lf t55xx dump",
    examples=["lf t55xx dump"]
)

register_command(
    "lf_t55xx_write",
    name="Запись T55xx",
    command="lf t55xx write",
    category=CommandCategory.LF,
    description="Запись данных на T55xx. "
                "Изменение содержимого блока.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись блока",
    parameters=[
        CommandParameter("block", "int", True, description="Номер блока"),
        CommandParameter("data", "hex", True, description="Данные")
    ],
    info_command="lf t55xx write",
    examples=["lf t55xx write 0 12345678"]
)

register_command(
    "lf_t55xx_config",
    name="Конфигурация T55xx",
    command="lf t55xx config",
    category=CommandCategory.LF,
    description="Настройка конфигурации T55xx. "
                "Изменение настроек карты.",
    risk=CommandRisk.DANGEROUS,
    hint="Настройка конфигурации",
    parameters=[
        CommandParameter("config", "hex", True, description="Значение конфига")
    ],
    info_command="lf t55xx config",
    examples=["lf t55xx config 00088040"]
)

register_command(
    "lf_t55xx_chk",
    name="Проверка ключа T55xx",
    command="lf t55xx chk",
    category=CommandCategory.LF,
    description="Проверка пароля T55xx. "
                "Верификация ключа.",
    hint="Проверка пароля",
    parameters=[
        CommandParameter("password", "hex", True, description="Пароль")
    ],
    info_command="lf t55xx chk",
    examples=["lf t55xx chk 12345678"]
)

register_command(
    "lf_t55xx_bruteforce",
    name="Брутфорс T55xx",
    command="lf t55xx bruteforce",
    category=CommandCategory.LF,
    description="Перебор пароля T55xx. "
                "Автоматический подбор.",
    hint="Перебор пароля",
    info_command="lf t55xx bruteforce",
    examples=["lf t55xx bruteforce"]
)

register_command(
    "lf_t55xx_protect",
    name="Защита T55xx",
    command="lf t55xx protect",
    category=CommandCategory.LF,
    description="Установка защиты на T55xx. "
                "Блокировка записи.",
    risk=CommandRisk.DANGEROUS,
    hint="Установка защиты",
    info_command="lf t55xx protect",
    examples=["lf t55xx protect"]
)

register_command(
    "lf_t55xx_recoverpw",
    name="Восстановление пароля T55xx",
    command="lf t55xx recoverpw",
    category=CommandCategory.LF,
    description="Восстановление утерянного пароля T55xx. "
                "Атака на защиту.",
    hint="Восстановление пароля",
    info_command="lf t55xx recoverpw",
    examples=["lf t55xx recoverpw"]
)

register_command(
    "lf_t55xx_p1detect",
    name="Детекция Page 1 T55xx",
    command="lf t55xx p1detect",
    category=CommandCategory.LF,
    description="Обнаружение страницы 1 T55xx. "
                "Проверка наличия расширенной памяти.",
    hint="Детекция Page 1",
    info_command="lf t55xx p1detect",
    examples=["lf t55xx p1detect"]
)

register_command(
    "lf_t55xx_resetread",
    name="Сброс и чтение T55xx",
    command="lf t55xx resetread",
    category=CommandCategory.LF,
    description="Сброс и чтение T55xx. "
                "Сброс конфигурации и чтение.",
    hint="Сброс и чтение",
    info_command="lf t55xx resetread",
    examples=["lf t55xx resetread"]
)

register_command(
    "lf_t55xx_special",
    name="Специальный режим T55xx",
    command="lf t55xx special",
    category=CommandCategory.LF,
    description="Специальные операции T55xx. "
                "Нестандартные команды.",
    risk=CommandRisk.WARNING,
    hint="Специальные операции",
    info_command="lf t55xx special",
    examples=["lf t55xx special"]
)

register_command(
    "lf_t55xx_wakeup",
    name="Пробуждение T55xx",
    command="lf t55xx wakeup",
    category=CommandCategory.LF,
    description="Команда пробуждения T55xx. "
                "Активация спящего режима.",
    hint="Пробуждение карты",
    info_command="lf t55xx wakeup",
    examples=["lf t55xx wakeup"]
)

register_command(
    "lf_t55xx_wipe",
    name="Очистка T55xx",
    command="lf t55xx wipe",
    category=CommandCategory.LF,
    description="Полная очистка T55xx. "
                "Сброс всех данных.",
    risk=CommandRisk.DANGEROUS,
    hint="Полная очистка",
    info_command="lf t55xx wipe",
    examples=["lf t55xx wipe"]
)

register_command(
    "lf_t55xx_sim",
    name="Эмуляция T55xx",
    command="lf t55xx sim",
    category=CommandCategory.LF,
    description="Эмуляция карты T55xx. "
                "Симуляция ответа карты.",
    hint="Эмуляция карты",
    parameters=[
        CommandParameter("data", "hex", True, description="Данные для эмуляции")
    ],
    info_command="lf t55xx sim",
    examples=["lf t55xx sim 0123456789ABCDEF"]
)


# ============================================================================
# ФУНКЦИИ ПОИСКА И ДОСТУПА К КОМАНДАМ
# ============================================================================

def get_command(cmd_id: str) -> Optional[CommandInfo]:
    """Получение команды по идентификатору"""
    return COMMANDS_DB.get(cmd_id)


def get_commands_by_category(category: CommandCategory) -> List[CommandInfo]:
    """Получение всех команд категории"""
    return [cmd for cmd in COMMANDS_DB.values() if cmd.category == category]


def search_commands(query: str) -> List[CommandInfo]:
    """Поиск команд по запросу"""
    query_lower = query.lower()
    results = []
    
    for cmd in COMMANDS_DB.values():
        if (query_lower in cmd.id.lower() or
            query_lower in cmd.name.lower() or
            query_lower in cmd.command.lower() or
            query_lower in cmd.description.lower()):
            results.append(cmd)
    
    return results


def get_command_categories() -> List[CommandCategory]:
    """Получение списка всех категорий"""
    return list(CommandCategory)


def get_protocols_for_category(category: CommandCategory) -> List[str]:
    """Получение всех протоколов для категории"""
    protocols = set()
    for cmd in COMMANDS_DB.values():
        if cmd.category == category:
            protocols.update(cmd.protocols)
    return sorted(list(protocols))


# Экспорт публичного API
__all__ = [
    'CommandCategory',
    'CommandRisk',
    'CommandType',
    'CommandParameter',
    'CommandInfo',
    'COMMANDS_DB',
    'get_command',
    'get_commands_by_category',
    'search_commands',
    'get_command_categories',
    'get_protocols_for_category',
    'register_command'
]
