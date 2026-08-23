"""
Proxmark3 Easy GUI - Модуль команд и структур данных
Определяет все команды Proxmark3 Iceman для использования в GUI
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class CommandCategory(Enum):
    """Категории команд"""
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


class CommandRisk(Enum):
    """Уровень риска команды"""
    SAFE = "safe"           # Обычная команда
    WARNING = "warning"     # Требует внимания
    DANGEROUS = "dangerous" # Опасная операция (запись, прошивка)


@dataclass
class CommandInfo:
    """Информация о команде"""
    name: str                          # Отображаемое имя
    command: str                       # Команда для выполнения
    category: CommandCategory          # Категория
    description: str                   # Описание
    risk: CommandRisk = CommandRisk.SAFE  # Уровень риска
    hint: str = ""                     # Подсказка при наведении
    info_command: str = ""             # Команда для получения подробной информации
    parameters: List[str] = field(default_factory=list)  # Параметры
    protocols: List[str] = field(default_factory=list)   # Протоколы (для LF/HF)


# ============================================================================
# БАЗА ДАННЫХ КОМАНД
# ============================================================================

COMMANDS_DB: Dict[str, CommandInfo] = {
    # =========================================================================
    # ГЛАВНАЯ - АППАРАТНЫЕ КОМАНДЫ
    # =========================================================================
    "hw_status": CommandInfo(
        name="Статус устройства",
        command="hw status",
        category=CommandCategory.HARDWARE,
        description="Проверка статуса подключения и состояния устройства",
        hint="Показывает текущее состояние Proxmark3"
    ),
    "hw_version": CommandInfo(
        name="Версии устройства",
        command="hw version",
        category=CommandCategory.HARDWARE,
        description="Отображение версий Firmware, Bootrom, Hardware",
        hint="Информация о версиях прошивок и железа"
    ),
    "hw_tune": CommandInfo(
        name="Настройка антенн",
        command="hw tune",
        category=CommandCategory.HARDWARE,
        description="Измерение параметров антенн LF и HF",
        hint="Показывает резонансные частоты и добротность антенн"
    ),
    "hw_reset": CommandInfo(
        name="Перезагрузка",
        command="hw reset",
        category=CommandCategory.HARDWARE,
        description="Перезагрузка устройства",
        risk=CommandRisk.WARNING,
        hint="Выполняет мягкую перезагрузку Proxmark3"
    ),
    "hw_teardown": CommandInfo(
        name="Проверка цепей",
        command="hw teardown",
        category=CommandCategory.HARDWARE,
        description="Тестирование аппаратных цепей устройства",
        hint="Диагностика hardware компонентов"
    ),
    "hw_decay": CommandInfo(
        name="Затухание HF",
        command="hw decay",
        category=CommandCategory.HARDWARE,
        description="Измерение затухания HF антенны",
        hint="Проверка качества HF антенны"
    ),
    "hw_readmem": CommandInfo(
        name="Память ARM",
        command="hw readmem",
        category=CommandCategory.HARDWARE,
        description="Чтение памяти ARM процессора",
        hint="Прямой доступ к памяти устройства"
    ),
    "hw_setmux": CommandInfo(
        name="Мультиплексор",
        command="hw setmux",
        category=CommandCategory.HARDWARE,
        description="Настройка мультиплексора антенн",
        parameters=["<0-7>"],
        hint="Выбор активной антенны (0-7)"
    ),
    "hw_lcd": CommandInfo(
        name="LCD управление",
        command="hw lcd",
        category=CommandCategory.HARDWARE,
        description="Управление LCD дисплеем (если есть)",
        hint="Вкл/выкл/настройка LCD"
    ),
    "hw_kick": CommandInfo(
        name="Антенна вкл/выкл",
        command="hw kick",
        category=CommandCategory.HARDWARE,
        description="Включение/выключение питания антенн",
        hint="Управление питанием антенн"
    ),
    "hw_break": CommandInfo(
        name="Прервать операцию",
        command="hw break",
        category=CommandCategory.HARDWARE,
        description="Экстренная остановка текущей операции",
        risk=CommandRisk.WARNING,
        hint="Останавливает выполнение любой команды"
    ),
    "hw_bootloader": CommandInfo(
        name="Режим загрузчика",
        command="hw bootloader",
        category=CommandCategory.HARDWARE,
        description="Переход в режим загрузчика для прошивки",
        risk=CommandRisk.DANGEROUS,
        hint="Требуется для обновления прошивки"
    ),
    
    # =========================================================================
    # АВТОПОИСК И ОБЩИЕ КОМАНДЫ
    # =========================================================================
    "auto": CommandInfo(
        name="Автопоиск карт",
        command="auto",
        category=CommandCategory.HARDWARE,
        description="Автоматический поиск всех типов карт (LF + HF)",
        hint="Полное сканирование всех частот и протоколов"
    ),
    
    # =========================================================================
    # LF (Low Frequency) - 125 kHz
    # =========================================================================
    "lf_search": CommandInfo(
        name="Поиск LF",
        command="lf search",
        category=CommandCategory.LF,
        description="Поиск LF карт (125 kHz)",
        protocols=["EM4100", "EM4x05", "T55xx", "HID", "AWID", "Indala", "IO", "Keri", "Motorola", "Nedap", "Paradox", "Pyramid", "Securakey", "TI", "Trovan", "Viking"]
    ),
    "lf_read": CommandInfo(
        name="Чтение LF",
        command="lf read",
        category=CommandCategory.LF,
        description="Чтение сигнала с LF карты"
    ),
    "lf_config": CommandInfo(
        name="Настройка LF",
        command="lf config",
        category=CommandCategory.LF,
        description="Конфигурация параметров чтения LF",
        parameters=["<divid>", "<decim>", "<avg>", "<samples>"]
    ),
    "lf_cmdread": CommandInfo(
        name="Чтение с параметрами",
        command="lf cmdread",
        category=CommandCategory.LF,
        description="Чтение LF с заданными параметрами",
        parameters=["<off_time>", "<on_time>", "<period>", "<data>"]
    ),
    "lf_snoop": CommandInfo(
        name="Сниффинг LF",
        command="lf snoop",
        category=CommandCategory.LF,
        description="Перехват LF сигналов"
    ),
    "lf_sniff": CommandInfo(
        name="Сниффинг LF (альт)",
        command="lf sniff",
        category=CommandCategory.LF,
        description="Альтернативный режим перехвата LF"
    ),
    
    # LF - EM4100
    "lf_em_410x_reader": CommandInfo(
        name="Чтение EM4100",
        command="lf em 410x reader",
        category=CommandCategory.LF,
        description="Чтение карт EM4100/EM4102",
        protocols=["EM4100"]
    ),
    "lf_em_410x_watch": CommandInfo(
        name="Мониторинг EM4100",
        command="lf em 410x watch",
        category=CommandCategory.LF,
        description="Непрерывное чтение EM4100"
    ),
    "lf_em_410x_sim": CommandInfo(
        name="Эмуляция EM4100",
        command="lf em 410x sim",
        category=CommandCategory.LF,
        description="Эмуляция карты EM4100"
    ),
    "lf_em_410x_clone": CommandInfo(
        name="Клонирование EM4100",
        command="lf em 410x clone",
        category=CommandCategory.LF,
        description="Запись клона EM4100 на T55xx",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_em_410x_brute": CommandInfo(
        name="Брутфорс EM4100",
        command="lf em 410x brute",
        category=CommandCategory.LF,
        description="Перебор ID карт EM4100"
    ),
    
    # LF - EM4x05
    "lf_em_4x05_info": CommandInfo(
        name="Инфо EM4x05",
        command="lf em 4x05 info",
        category=CommandCategory.LF,
        description="Получение информации о карте EM4x05"
    ),
    "lf_em_4x05_read": CommandInfo(
        name="Чтение EM4x05",
        command="lf em 4x05 read",
        category=CommandCategory.LF,
        description="Чтение данных с EM4x05"
    ),
    "lf_em_4x05_dump": CommandInfo(
        name="Дамп EM4x05",
        command="lf em 4x05 dump",
        category=CommandCategory.LF,
        description="Полное чтение памяти EM4x05"
    ),
    "lf_em_4x05_write": CommandInfo(
        name="Запись EM4x05",
        command="lf em 4x05 write",
        category=CommandCategory.LF,
        description="Запись данных на EM4x05",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_em_4x05_config": CommandInfo(
        name="Конфиг EM4x05",
        command="lf em 4x05 config",
        category=CommandCategory.LF,
        description="Настройка конфигурации EM4x05"
    ),
    "lf_em_4x05_unlock": CommandInfo(
        name="Разблокировка EM4x05",
        command="lf em 4x05 unlock",
        category=CommandCategory.LF,
        description="Разблокировка защищенной EM4x05",
        risk=CommandRisk.WARNING
    ),
    "lf_em_4x05_chk": CommandInfo(
        name="Проверка ключа EM4x05",
        command="lf em 4x05 chk",
        category=CommandCategory.LF,
        description="Проверка пароля EM4x05"
    ),
    "lf_em_4x05_brute": CommandInfo(
        name="Брутфорс EM4x05",
        command="lf em 4x05 brute",
        category=CommandCategory.LF,
        description="Перебор пароля EM4x05"
    ),
    
    # LF - EM4x50
    "lf_em_4x50_info": CommandInfo(
        name="Инфо EM4x50",
        command="lf em 4x50 info",
        category=CommandCategory.LF,
        description="Информация о карте EM4x50"
    ),
    "lf_em_4x50_rdbl": CommandInfo(
        name="Чтение блока EM4x50",
        command="lf em 4x50 rdbl",
        category=CommandCategory.LF,
        description="Чтение блока EM4x50",
        parameters=["<block>"]
    ),
    "lf_em_4x50_dump": CommandInfo(
        name="Дамп EM4x50",
        command="lf em 4x50 dump",
        category=CommandCategory.LF,
        description="Полный дамп EM4x50"
    ),
    "lf_em_4x50_login": CommandInfo(
        name="Логин EM4x50",
        command="lf em 4x50 login",
        category=CommandCategory.LF,
        description="Авторизация на EM4x50"
    ),
    "lf_em_4x50_wrbl": CommandInfo(
        name="Запись блока EM4x50",
        command="lf em 4x50 wrbl",
        category=CommandCategory.LF,
        description="Запись блока EM4x50",
        risk=CommandRisk.DANGEROUS,
        parameters=["<block>", "<data>"]
    ),
    "lf_em_4x50_wrpwd": CommandInfo(
        name="Запись пароля EM4x50",
        command="lf em 4x50 wrpwd",
        category=CommandCategory.LF,
        description="Изменение пароля EM4x50",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_em_4x50_chk": CommandInfo(
        name="Проверка ключа EM4x50",
        command="lf em 4x50 chk",
        category=CommandCategory.LF,
        description="Проверка пароля EM4x50"
    ),
    "lf_em_4x50_brute": CommandInfo(
        name="Брутфорс EM4x50",
        command="lf em 4x50 brute",
        category=CommandCategory.LF,
        description="Перебор пароля EM4x50"
    ),
    
    # LF - EM4x70
    "lf_em_4x70_info": CommandInfo(
        name="Инфо EM4x70",
        command="lf em 4x70 info",
        category=CommandCategory.LF,
        description="Информация о карте EM4x70"
    ),
    "lf_em_4x70_auth": CommandInfo(
        name="Авторизация EM4x70",
        command="lf em 4x70 auth",
        category=CommandCategory.LF,
        description="Авторизация на EM4x70"
    ),
    "lf_em_4x70_calc": CommandInfo(
        name="Расчет ключа EM4x70",
        command="lf em 4x70 calc",
        category=CommandCategory.LF,
        description="Вычисление ключа EM4x70"
    ),
    "lf_em_4x70_brute": CommandInfo(
        name="Брутфорс EM4x70",
        command="lf em 4x70 brute",
        category=CommandCategory.LF,
        description="Перебор пароля EM4x70"
    ),
    "lf_em_4x70_recover": CommandInfo(
        name="Восстановление EM4x70",
        command="lf em 4x70 recover",
        category=CommandCategory.LF,
        description="Восстановление доступа EM4x70"
    ),
    "lf_em_4x70_autorecover": CommandInfo(
        name="Авто-восстановление EM4x70",
        command="lf em 4x70 autorecover",
        category=CommandCategory.LF,
        description="Автоматическое восстановление EM4x70"
    ),
    
    # LF - T55xx
    "lf_t55xx_detect": CommandInfo(
        name="Детекция T55xx",
        command="lf t55xx detect",
        category=CommandCategory.LF,
        description="Определение типа карты T55xx"
    ),
    "lf_t55xx_info": CommandInfo(
        name="Инфо T55xx",
        command="lf t55xx info",
        category=CommandCategory.LF,
        description="Информация о конфигурации T55xx"
    ),
    "lf_t55xx_read": CommandInfo(
        name="Чтение T55xx",
        command="lf t55xx read",
        category=CommandCategory.LF,
        description="Чтение данных T55xx"
    ),
    "lf_t55xx_dump": CommandInfo(
        name="Дамп T55xx",
        command="lf t55xx dump",
        category=CommandCategory.LF,
        description="Полный дамп памяти T55xx"
    ),
    "lf_t55xx_write": CommandInfo(
        name="Запись T55xx",
        command="lf t55xx write",
        category=CommandCategory.LF,
        description="Запись данных на T55xx",
        risk=CommandRisk.DANGEROUS,
        parameters=["<block>", "<data>"]
    ),
    "lf_t55xx_config": CommandInfo(
        name="Конфигурация T55xx",
        command="lf t55xx config",
        category=CommandCategory.LF,
        description="Настройка конфигурации T55xx",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_t55xx_chk": CommandInfo(
        name="Проверка ключа T55xx",
        command="lf t55xx chk",
        category=CommandCategory.LF,
        description="Проверка пароля T55xx"
    ),
    "lf_t55xx_bruteforce": CommandInfo(
        name="Брутфорс T55xx",
        command="lf t55xx bruteforce",
        category=CommandCategory.LF,
        description="Перебор пароля T55xx"
    ),
    "lf_t55xx_protect": CommandInfo(
        name="Защита T55xx",
        command="lf t55xx protect",
        category=CommandCategory.LF,
        description="Установка защиты на T55xx",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_t55xx_recoverpw": CommandInfo(
        name="Восстановление пароля T55xx",
        command="lf t55xx recoverpw",
        category=CommandCategory.LF,
        description="Восстановление утерянного пароля"
    ),
    "lf_t55xx_p1detect": CommandInfo(
        name="Детекция Page 1 T55xx",
        command="lf t55xx p1detect",
        category=CommandCategory.LF,
        description="Обнаружение страницы 1 T55xx"
    ),
    "lf_t55xx_resetread": CommandInfo(
        name="Сброс и чтение T55xx",
        command="lf t55xx resetread",
        category=CommandCategory.LF,
        description="Сброс и чтение T55xx"
    ),
    "lf_t55xx_special": CommandInfo(
        name="Специальный режим T55xx",
        command="lf t55xx special",
        category=CommandCategory.LF,
        description="Специальные операции T55xx",
        risk=CommandRisk.WARNING
    ),
    "lf_t55xx_wakeup": CommandInfo(
        name="Пробуждение T55xx",
        command="lf t55xx wakeup",
        category=CommandCategory.LF,
        description="Команда пробуждения T55xx"
    ),
    "lf_t55xx_wipe": CommandInfo(
        name="Очистка T55xx",
        command="lf t55xx wipe",
        category=CommandCategory.LF,
        description="Полная очистка T55xx",
        risk=CommandRisk.DANGEROUS
    ),
    "lf_t55xx_sim": CommandInfo(
        name="Эмуляция T55xx",
        command="lf t55xx sim",
        category=CommandCategory.LF,
        description="Эмуляция карты T55xx"
    ),
}


def get_command(name: str) -> Optional[CommandInfo]:
    """Получить информацию о команде по имени"""
    return COMMANDS_DB.get(name)


def get_commands_by_category(category: CommandCategory) -> List[CommandInfo]:
    """Получить все команды категории"""
    return [cmd for cmd in COMMANDS_DB.values() if cmd.category == category]


def get_commands_by_protocol(protocol: str) -> List[CommandInfo]:
    """Получить команды для конкретного протокола"""
    return [cmd for cmd in COMMANDS_DB.values() if protocol in cmd.protocols]


def search_commands(query: str) -> List[CommandInfo]:
    """Поиск команд по запросу"""
    query_lower = query.lower()
    results = []
    for cmd in COMMANDS_DB.values():
        if (query_lower in cmd.name.lower() or 
            query_lower in cmd.command.lower() or 
            query_lower in cmd.description.lower()):
            results.append(cmd)
    return results


# Продолжение базы команд будет добавлено в следующих файлах...
