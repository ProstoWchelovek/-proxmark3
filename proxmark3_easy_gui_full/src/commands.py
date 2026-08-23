"""
Proxmark3 Easy GUI - Модуль команд
Полная база данных команд Proxmark3 Iceman/RRG для использования в GUI
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum, auto


# ============================================================================
# ПЕРЕЧИСЛЕНИЯ И ТИПЫ ДАННЫХ
# ============================================================================

class CommandCategory(Enum):
    """Категории команд Proxmark3"""
    HARDWARE = "hardware"
    LF = "lf"
    HF = "hf"
    NFC = "nfc"
    EMV = "emv"
    SMART = "smart"
    PIV = "piv"
    DATA = "data"
    TRACE = "trace"
    SCRIPT = "script"
    MEM = "mem"
    ANALYSE = "analyse"
    DANGEROUS = "dangerous"
    AUTO = "auto"


class CommandRisk(Enum):
    """Уровень риска выполнения команды"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


class CommandType(Enum):
    """Типы команд по способу выполнения"""
    DIRECT = "direct"
    INTERACTIVE = "interactive"
    SCRIPT = "script"
    BATCH = "batch"


@dataclass
class CommandParameter:
    """Параметр команды"""
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""
    choices: List[str] = field(default_factory=list)
    min_value: Optional[int] = None
    max_value: Optional[int] = None


@dataclass
class CommandInfo:
    """Информация о команде Proxmark3"""
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
# ГЛАВНАЯ ВКЛАДКА - АППАРАТНЫЕ КОМАНДЫ
# ============================================================================

register_command(
    "hw_status",
    name="Статус устройства",
    command="hw status",
    category=CommandCategory.HARDWARE,
    description="Проверка статуса подключения и состояния устройства.",
    hint="Показывает текущее состояние Proxmark3",
    info_command="hw status",
    examples=["hw status"]
)

register_command(
    "hw_version",
    name="Версии устройства",
    command="hw version",
    category=CommandCategory.HARDWARE,
    description="Отображение версий Firmware, Bootrom, Hardware.",
    hint="Информация о версиях прошивок и железа",
    info_command="hw version",
    examples=["hw version"]
)

register_command(
    "hw_tune",
    name="Настройка антенн",
    command="hw tune",
    category=CommandCategory.HARDWARE,
    description="Измерение параметров антенн LF и HF.",
    hint="Показывает резонансные частоты и добротность антенн",
    info_command="hw tune",
    examples=["hw tune"]
)

register_command(
    "hw_reset",
    name="Перезагрузка",
    command="hw reset",
    category=CommandCategory.HARDWARE,
    description="Перезагрузка устройства.",
    risk=CommandRisk.WARNING,
    hint="Выполняет мягкую перезагрузку Proxmark3",
    info_command="hw reset",
    examples=["hw reset"]
)

register_command(
    "auto",
    name="Автопоиск карт",
    command="auto",
    category=CommandCategory.AUTO,
    description="Автоматический поиск всех типов карт (LF + HF).",
    hint="Полное сканирование всех частот и протоколов",
    info_command="auto",
    examples=["auto"],
    related_commands=["lf search", "hf search"]
)


# ============================================================================
# LF (Low Frequency) - 125 kHz
# ============================================================================

register_command(
    "lf_search",
    name="Поиск LF",
    command="lf search",
    category=CommandCategory.LF,
    description="Поиск LF карт (125 kHz).",
    hint="Поиск LF карт на антенне",
    info_command="lf search",
    protocols=["EM4100", "EM4x05", "T55xx", "HID", "AWID", "Indala"],
    examples=["lf search", "lf search u"]
)

register_command(
    "lf_read",
    name="Чтение LF",
    command="lf read",
    category=CommandCategory.LF,
    description="Чтение сигнала с LF карты.",
    hint="Чтение LF сигнала",
    info_command="lf read",
    examples=["lf read"]
)

register_command(
    "lf_snoop",
    name="Сниффинг LF",
    command="lf snoop",
    category=CommandCategory.LF,
    description="Перехват LF сигналов.",
    hint="Перехват LF трафика",
    info_command="lf snoop",
    examples=["lf snoop"]
)

register_command(
    "lf_em_read",
    name="Чтение EM4100",
    command="lf em read",
    category=CommandCategory.LF,
    description="Чтение карт EM4100/EM4102.",
    hint="Чтение EM4100 карт",
    info_command="lf em read",
    examples=["lf em read"]
)

register_command(
    "lf_em_sim",
    name="Эмуляция EM4100",
    command="lf em sim",
    category=CommandCategory.LF,
    description="Эмуляция карты EM4100.",
    hint="Эмуляция EM4100 карты",
    parameters=[
        CommandParameter("id", "hex", True, description="ID карты (10 hex символов)")
    ],
    info_command="lf em sim",
    examples=["lf em sim 0123456789"]
)

register_command(
    "lf_em_clone",
    name="Клонирование EM4100",
    command="lf em clone",
    category=CommandCategory.LF,
    description="Запись клона EM4100 на T55xx.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись клона на T55xx",
    parameters=[
        CommandParameter("id", "hex", True, description="ID для записи")
    ],
    info_command="lf em clone",
    examples=["lf em clone 0123456789"]
)

register_command(
    "lf_t55xx_read",
    name="Чтение T55xx",
    command="lf t55xx read",
    category=CommandCategory.LF,
    description="Чтение карт T55xx.",
    hint="Чтение T55xx карт",
    info_command="lf t55xx read",
    examples=["lf t55xx read"]
)

register_command(
    "lf_t55xx_write",
    name="Запись T55xx",
    command="lf t55xx write",
    category=CommandCategory.LF,
    description="Запись данных на T55xx.",
    risk=CommandRisk.DANGEROUS,
    hint="Запись на T55xx",
    parameters=[
        CommandParameter("block", "int", True, description="Номер блока"),
        CommandParameter("data", "hex", True, description="Данные для записи")
    ],
    info_command="lf t55xx write",
    examples=["lf t55xx write 0 12345678"]
)

register_command(
    "lf_hid_read",
    name="Чтение HID",
    command="lf hid read",
    category=CommandCategory.LF,
    description="Чтение карт HID Prox.",
    hint="Чтение HID карт",
    info_command="lf hid read",
    examples=["lf hid read"]
)

register_command(
    "lf_hid_sim",
    name="Эмуляция HID",
    command="lf hid sim",
    category=CommandCategory.LF,
    description="Эмуляция карты HID.",
    hint="Эмуляция HID карты",
    parameters=[
        CommandParameter("id", "hex", True, description="ID карты HID")
    ],
    info_command="lf hid sim",
    examples=["lf hid sim 200A0B0C0D"]
)


# ============================================================================
# HF (High Frequency) - 13.56 MHz
# ============================================================================

register_command(
    "hf_search",
    name="Поиск HF",
    command="hf search",
    category=CommandCategory.HF,
    description="Поиск HF карт (13.56 MHz).",
    hint="Поиск HF карт на антенне",
    info_command="hf search",
    protocols=["ISO14443A", "ISO14443B", "ISO15693", "FeliCa", "NFC"],
    examples=["hf search"]
)

register_command(
    "hf_read",
    name="Чтение HF",
    command="hf read",
    category=CommandCategory.HF,
    description="Чтение данных с HF карты.",
    hint="Чтение HF карты",
    info_command="hf read",
    examples=["hf read"]
)

register_command(
    "hf_list",
    name="Список команд HF",
    command="hf list",
    category=CommandCategory.HF,
    description="Показать список HF команд.",
    hint="Список доступных HF команд",
    info_command="hf list",
    examples=["hf list"]
)

register_command(
    "hf_14a_reader",
    name="Чтение ISO14443A",
    command="hf 14a reader",
    category=CommandCategory.HF,
    description="Чтение карт ISO14443A.",
    hint="Чтение ISO14443A карт",
    info_command="hf 14a reader",
    examples=["hf 14a reader"]
)

register_command(
    "hf_14a_info",
    name="Инфо ISO14443A",
    command="hf 14a info",
    category=CommandCategory.HF,
    description="Получение информации о карте ISO14443A.",
    hint="Информация о карте",
    info_command="hf 14a info",
    examples=["hf 14a info"]
)

register_command(
    "hf_mfu_read",
    name="Чтение Mifare Ultralight",
    command="hf mfu read",
    category=CommandCategory.HF,
    description="Чтение карт Mifare Ultralight.",
    hint="Чтение MF Ultralight",
    info_command="hf mfu read",
    examples=["hf mfu read"]
)

register_command(
    "hf_mf_dump",
    name="Дамп Mifare Classic",
    command="hf mf dump",
    category=CommandCategory.HF,
    description="Полный дамп памяти Mifare Classic.",
    hint="Дамп всех секторов",
    info_command="hf mf dump",
    examples=["hf mf dump"]
)

register_command(
    "hf_mf_nested",
    name="Nested атака Mifare",
    command="hf mf nested",
    category=CommandCategory.HF,
    description="Nested атака для получения ключей Mifare.",
    hint="Nested атака",
    info_command="hf mf nested",
    examples=["hf mf nested 1 0 a ffffffffffff"]
)

register_command(
    "hf_mf_hardnested",
    name="Hard Nested атака",
    command="hf mf hardnested",
    category=CommandCategory.HF,
    description="Hard Nested атака для Mifare Classic.",
    hint="Hard Nested атака",
    info_command="hf mf hardnested",
    examples=["hf mf hardnested 0 a ffffffffffff 1 a"]
)

register_command(
    "hf_mf_sniff",
    name="Сниффинг Mifare",
    command="hf mf sniff",
    category=CommandCategory.HF,
    description="Перехват трафика Mifare.",
    hint="Сниффинг Mifare трафика",
    info_command="hf mf sniff",
    examples=["hf mf sniff"]
)

register_command(
    "hf_14b_reader",
    name="Чтение ISO14443B",
    command="hf 14b reader",
    category=CommandCategory.HF,
    description="Чтение карт ISO14443B.",
    hint="Чтение ISO14443B карт",
    info_command="hf 14b reader",
    examples=["hf 14b reader"]
)

register_command(
    "hf_15_reader",
    name="Чтение ISO15693",
    command="hf 15 reader",
    category=CommandCategory.HF,
    description="Чтение карт ISO15693.",
    hint="Чтение ISO15693 карт",
    info_command="hf 15 reader",
    examples=["hf 15 reader"]
)

register_command(
    "hf_legic_info",
    name="Инфо LEGIC",
    command="hf legic info",
    category=CommandCategory.HF,
    description="Информация о картах LEGIC.",
    hint="LEGIC инфо",
    info_command="hf legic info",
    examples=["hf legic info"]
)

register_command(
    "hf_iclass_info",
    name="Инфо iClass",
    command="hf iclass info",
    category=CommandCategory.HF,
    description="Информация о картах iClass.",
    hint="iClass инфо",
    info_command="hf iclass info",
    examples=["hf iclass info"]
)

register_command(
    "hf_calfm",
    name="Калибровка HF",
    command="hf calfm",
    category=CommandCategory.HF,
    description="Калибровка HF модуляции.",
    hint="Калибровка HF",
    info_command="hf calfm",
    examples=["hf calfm"]
)


# ============================================================================
# DATA - Обработка данных
# ============================================================================

register_command(
    "data_load",
    name="Загрузить данные",
    command="data load",
    category=CommandCategory.DATA,
    description="Загрузка данных из файла.",
    hint="Загрузка из файла",
    parameters=[
        CommandParameter("file", "string", True, description="Имя файла")
    ],
    info_command="data load",
    examples=["data load dump.bin"]
)

register_command(
    "data_save",
    name="Сохранить данные",
    command="data save",
    category=CommandCategory.DATA,
    description="Сохранение данных в файл.",
    hint="Сохранение в файл",
    parameters=[
        CommandParameter("file", "string", True, description="Имя файла")
    ],
    info_command="data save",
    examples=["data save dump.bin"]
)

register_command(
    "data_hex",
    name="Hex просмотр",
    command="data hex",
    category=CommandCategory.DATA,
    description="Просмотр данных в hex формате.",
    hint="Hex view",
    info_command="data hex",
    examples=["data hex"]
)

register_command(
    "data_print",
    name="Печать данных",
    command="data print",
    category=CommandCategory.DATA,
    description="Печать данных в консоль.",
    hint="Печать данных",
    info_command="data print",
    examples=["data print"]
)

register_command(
    "data_demod",
    name="Демодуляция",
    command="data demod",
    category=CommandCategory.DATA,
    description="Демодуляция сигнала.",
    hint="Демодуляция",
    info_command="data demod",
    examples=["data demod"]
)

register_command(
    "data_manch",
    name="Манчестер декод",
    command="data manch",
    category=CommandCategory.DATA,
    description="Декодирование Манчестера.",
    hint="Манчестер",
    info_command="data manch",
    examples=["data manch"]
)


# ============================================================================
# TRACE - Трассировка
# ============================================================================

register_command(
    "trace_list",
    name="Список трассировки",
    command="trace list",
    category=CommandCategory.TRACE,
    description="Показать список трассировки.",
    hint="Список трасс",
    info_command="trace list",
    examples=["trace list"]
)

register_command(
    "trace_load",
    name="Загрузить трассу",
    command="trace load",
    category=CommandCategory.TRACE,
    description="Загрузка трассировки из файла.",
    hint="Загрузка трассы",
    parameters=[
        CommandParameter("file", "string", True, description="Имя файла")
    ],
    info_command="trace load",
    examples=["trace trace.sav"]
)

register_command(
    "trace_save",
    name="Сохранить трассу",
    command="trace save",
    category=CommandCategory.TRACE,
    description="Сохранение трассировки в файл.",
    hint="Сохранение трассы",
    parameters=[
        CommandParameter("file", "string", True, description="Имя файла")
    ],
    info_command="trace save",
    examples=["trace save trace.sav"]
)


# ============================================================================
# MEM - Память устройства
# ============================================================================

register_command(
    "mem_dump",
    name="Дамп памяти",
    command="mem dump",
    category=CommandCategory.MEM,
    description="Дамп памяти устройства.",
    hint="Дамп памяти",
    info_command="mem dump",
    examples=["mem dump"]
)

register_command(
    "mem_restore",
    name="Восстановление памяти",
    command="mem restore",
    category=CommandCategory.MEM,
    description="Восстановление памяти из дампа.",
    risk=CommandRisk.DANGEROUS,
    hint="Восстановление памяти",
    parameters=[
        CommandParameter("file", "string", True, description="Файл дампа")
    ],
    info_command="mem restore",
    examples=["mem restore dump.bin"]
)

register_command(
    "mem_wipe",
    name="Очистка памяти",
    command="mem wipe",
    category=CommandCategory.MEM,
    description="Полная очистка памяти устройства.",
    risk=CommandRisk.DANGEROUS,
    hint="Очистка памяти",
    info_command="mem wipe",
    examples=["mem wipe"]
)

register_command(
    "mem_info",
    name="Инфо о памяти",
    command="mem info",
    category=CommandCategory.MEM,
    description="Информация о памяти устройства.",
    hint="Инфо о памяти",
    info_command="mem info",
    examples=["mem info"]
)


# ============================================================================
# ANALYSE - Анализ сигналов
# ============================================================================

register_command(
    "analyse_plot",
    name="Построить график",
    command="plot",
    category=CommandCategory.ANALYSE,
    description="Построение графика сигнала.",
    hint="График сигнала",
    info_command="plot",
    examples=["plot"]
)

register_command(
    "analyse_spectrum",
    name="Спектральный анализ",
    command="specan",
    category=CommandCategory.ANALYSE,
    description="Спектральный анализ сигнала.",
    hint="Спектр",
    info_command="specan",
    examples=["specan"]
)

register_command(
    "analyse_demod",
    name="Демодуляция анализа",
    command="data demod",
    category=CommandCategory.ANALYSE,
    description="Демодуляция для анализа.",
    hint="Демодуляция",
    info_command="data demod",
    examples=["data demod"]
)


# ============================================================================
# SCRIPT - Lua скрипты
# ============================================================================

register_command(
    "script_run",
    name="Запуск скрипта",
    command="script run",
    category=CommandCategory.SCRIPT,
    description="Запуск Lua скрипта.",
    hint="Запуск скрипта",
    parameters=[
        CommandParameter("name", "string", True, description="Имя скрипта")
    ],
    info_command="script run",
    examples=["script run hf_mf_keys"]
)

register_command(
    "script_load",
    name="Загрузить скрипт",
    command="script load",
    category=CommandCategory.SCRIPT,
    description="Загрузка Lua скрипта.",
    hint="Загрузка скрипта",
    parameters=[
        CommandParameter("file", "string", True, description="Файл скрипта")
    ],
    info_command="script load",
    examples=["script load myscript.lua"]
)

register_command(
    "script_stats",
    name="Статистика скриптов",
    command="script stats",
    category=CommandCategory.SCRIPT,
    description="Статистика использования скриптов.",
    hint="Статистика",
    info_command="script stats",
    examples=["script stats"]
)


# ============================================================================
# Функции-обертки для быстрого доступа
# ============================================================================

# HF функции
def hf_search() -> str: return "hf search"
def hf_list() -> str: return "hf list"
def hf_read() -> str: return "hf read"
def hf_write(block: int, data: str) -> str: return f"hf write {block} {data}"
def hf_clone(uid: str) -> str: return f"hf clone {uid}"
def hf_emulate(uid: str) -> str: return f"hf emulate {uid}"
def hf_sniff() -> str: return "hf sniff"
def hf_info() -> str: return "hf info"

# LF функции
def lf_search() -> str: return "lf search"
def lf_read() -> str: return "lf read"
def lf_write(block: int, data: str) -> str: return f"lf write {block} {data}"
def lf_emulate(uid: str) -> str: return f"lf emulate {uid}"
def lf_sniff() -> str: return "lf sniff"
def lf_info() -> str: return "lf info"

# Data функции
def data_load(file: str) -> str: return f"data load {file}"
def data_save(file: str) -> str: return f"data save {file}"
def data_hex() -> str: return "data hex"
def data_print() -> str: return "data print"

# Trace функции
def trace_list() -> str: return "trace list"
def trace_load(file: str) -> str: return f"trace load {file}"
def trace_save(file: str) -> str: return f"trace save {file}"

# Memory функции
def mem_dump() -> str: return "mem dump"
def mem_restore(file: str) -> str: return f"mem restore {file}"
def mem_wipe() -> str: return "mem wipe"
def mem_info() -> str: return "mem info"

# Analyse функции
def analyse_plot() -> str: return "plot"
def analyse_spectrum() -> str: return "specan"
def analyse_demod() -> str: return "data demod"

# System функции
def sys_version() -> str: return "hw version"
def sys_status() -> str: return "hw status"
def sys_reset() -> str: return "hw reset"
def sys_flash_write(addr: int, data: str) -> str: return f"hw flash write {addr} {data}"
def sys_flash_read(addr: int, length: int) -> str: return f"hw flash read {addr} {length}"


# Экспорт всех команд
HF_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.HF}
LF_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.LF}
DATA_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.DATA}
TRACE_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.TRACE}
MEM_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.MEM}
ANALYSE_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.ANALYSE}
SYS_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category in [CommandCategory.HARDWARE, CommandCategory.AUTO]}
SCRIPT_COMMANDS = {k: v for k, v in COMMANDS_DB.items() if v.category == CommandCategory.SCRIPT}

__all__ = [
    'CommandCategory', 'CommandRisk', 'CommandType',
    'CommandParameter', 'CommandInfo',
    'COMMANDS_DB', 'register_command',
    'HF_COMMANDS', 'LF_COMMANDS', 'DATA_COMMANDS', 
    'TRACE_COMMANDS', 'MEM_COMMANDS', 'ANALYSE_COMMANDS',
    'SYS_COMMANDS', 'SCRIPT_COMMANDS',
    'hf_search', 'hf_list', 'hf_read', 'hf_write', 
    'hf_clone', 'hf_emulate', 'hf_sniff', 'hf_info',
    'lf_search', 'lf_read', 'lf_write', 'lf_emulate', 
    'lf_sniff', 'lf_info',
    'data_load', 'data_save', 'data_hex', 'data_print',
    'trace_list', 'trace_load', 'trace_save',
    'mem_dump', 'mem_restore', 'mem_wipe', 'mem_info',
    'analyse_plot', 'analyse_spectrum', 'analyse_demod',
    'sys_version', 'sys_status', 'sys_reset', 
    'sys_flash_write', 'sys_flash_read',
]
