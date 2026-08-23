"""
Proxmark3 Easy GUI - Продолжение базы команд
HF (High Frequency), NFC, EMV, Smart Card, PIV команды
"""

from .commands import CommandInfo, CommandCategory, CommandRisk, COMMANDS_DB


# ============================================================================
# HF (High Frequency) - 13.56 MHz - ISO 14443A
# ============================================================================

COMMANDS_DB.update({
    # HF - Общие команды
    "hf_search": CommandInfo(
        name="Поиск HF",
        command="hf search",
        category=CommandCategory.HF,
        description="Поиск HF карт (13.56 MHz)"
    ),
    "hf_reader": CommandInfo(
        name="Чтение HF",
        command="hf reader",
        category=CommandCategory.HF,
        description="Чтение HF карты"
    ),
    "hf_plot": CommandInfo(
        name="График HF",
        command="hf plot",
        category=CommandCategory.HF,
        description="Построение графика HF сигнала"
    ),
    "hf_tune": CommandInfo(
        name="Настройка HF",
        command="hf tune",
        category=CommandCategory.HF,
        description="Настройка HF антенны"
    ),
    "hf_sniff": CommandInfo(
        name="Сниффинг HF",
        command="hf sniff",
        category=CommandCategory.HF,
        description="Перехват HF трафика"
    ),
    
    # HF - ISO 14443A
    "hf_14a_reader": CommandInfo(
        name="Чтение ISO 14443A",
        command="hf 14a reader",
        category=CommandCategory.HF,
        description="Чтение карт ISO 14443A",
        protocols=["ISO14443A"]
    ),
    "hf_14a_info": CommandInfo(
        name="Инфо ISO 14443A",
        command="hf 14a info",
        category=CommandCategory.HF,
        description="Получение информации о карте ISO 14443A"
    ),
    "hf_14a_cuids": CommandInfo(
        name="CUIDs ISO 14443A",
        command="hf 14a cuids",
        category=CommandCategory.HF,
        description="Сбор CUIDs для атак"
    ),
    "hf_14a_raw": CommandInfo(
        name="RAW команды ISO 14443A",
        command="hf 14a raw",
        category=CommandCategory.HF,
        description="Отправка RAW команд ISO 14443A",
        parameters=["<data>"]
    ),
    "hf_14a_apdu": CommandInfo(
        name="APDU ISO 14443A",
        command="hf 14a apdu",
        category=CommandCategory.HF,
        description="Отправка APDU команд"
    ),
    "hf_14a_apdufind": CommandInfo(
        name="Поиск APDU ISO 14443A",
        command="hf 14a apdufind",
        category=CommandCategory.HF,
        description="Поиск APDU команд в трейсе"
    ),
    "hf_14a_ndefread": CommandInfo(
        name="Чтение NDEF ISO 14443A",
        command="hf 14a ndefread",
        category=CommandCategory.HF,
        description="Чтение NDEF сообщений"
    ),
    "hf_14a_sim": CommandInfo(
        name="Эмуляция ISO 14443A",
        command="hf 14a sim",
        category=CommandCategory.HF,
        description="Эмуляция карты ISO 14443A"
    ),
    "hf_14a_simaid": CommandInfo(
        name="Эмуляция AID ISO 14443A",
        command="hf 14a simaid",
        category=CommandCategory.HF,
        description="Эмуляция с указанием AID"
    ),
    "hf_14a_config": CommandInfo(
        name="Конфигурация ISO 14443A",
        command="hf 14a config",
        category=CommandCategory.HF,
        description="Настройка параметров ISO 14443A"
    ),
    "hf_14a_chaining": CommandInfo(
        name="Chaining ISO 14443A",
        command="hf 14a chaining",
        category=CommandCategory.HF,
        description="Управление цепочками команд"
    ),
    "hf_14a_antifuzz": CommandInfo(
        name="Anti-fuzz ISO 14443A",
        command="hf 14a antifuzz",
        category=CommandCategory.HF,
        description="Защита от fuzzing атак"
    ),
    
    # HF - Mifare Classic
    "hf_mf_info": CommandInfo(
        name="Инфо Mifare Classic",
        command="hf mf info",
        category=CommandCategory.HF,
        description="Получение информации о Mifare Classic",
        protocols=["Mifare Classic"]
    ),
    "hf_mf_dump": CommandInfo(
        name="Дамп Mifare Classic",
        command="hf mf dump",
        category=CommandCategory.HF,
        description="Полный дамп памяти Mifare Classic"
    ),
    "hf_mf_restore": CommandInfo(
        name="Восстановление Mifare Classic",
        command="hf mf restore",
        category=CommandCategory.HF,
        description="Восстановление ключей из сохраненного дампа"
    ),
    "hf_mf_rdbl": CommandInfo(
        name="Чтение блока Mifare",
        command="hf mf rdbl",
        category=CommandCategory.HF,
        description="Чтение блока Mifare Classic",
        parameters=["<block>", "<key A/B>", "<key>"]
    ),
    "hf_mf_rdsc": CommandInfo(
        name="Чтение сектора Mifare",
        command="hf mf rdsc",
        category=CommandCategory.HF,
        description="Чтение сектора Mifare Classic",
        parameters=["<sector>", "<key A/B>", "<key>"]
    ),
    "hf_mf_acl": CommandInfo(
        name="ACL Mifare Classic",
        command="hf mf acl",
        category=CommandCategory.HF,
        description="Отображение Access Control List"
    ),
    "hf_mf_mad": CommandInfo(
        name="MAD Mifare Classic",
        command="hf mf mad",
        category=CommandCategory.HF,
        description="Mifare Application Directory"
    ),
    "hf_mf_madread": CommandInfo(
        name="Чтение MAD Mifare",
        command="hf mf madread",
        category=CommandCategory.HF,
        description="Чтение записей MAD"
    ),
    "hf_mf_madwrite": CommandInfo(
        name="Запись MAD Mifare",
        command="hf mf madwrite",
        category=CommandCategory.HF,
        description="Запись записей MAD",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_madverify": CommandInfo(
        name="Проверка MAD Mifare",
        command="hf mf madverify",
        category=CommandCategory.HF,
        description="Верификация записей MAD"
    ),
    "hf_mf_isen": CommandInfo(
        name="Проверка SEN Mifare",
        command="hf mf isen",
        category=CommandCategory.HF,
        description="Проверка наличия SEN (Smart Error)"
    ),
    "hf_mf_personalize": CommandInfo(
        name="Персонализация Mifare",
        command="hf mf personalize",
        category=CommandCategory.HF,
        description="Персонализация карты Mifare",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_setmod": CommandInfo(
        name="Установка режима Mifare",
        command="hf mf setmod",
        category=CommandCategory.HF,
        description="Установка режима работы Mifare"
    ),
    "hf_mf_value": CommandInfo(
        name="Value блок Mifare",
        command="hf mf value",
        category=CommandCategory.HF,
        description="Операции с value блоками",
        parameters=["<block>", "<cmd>", "<value>"]
    ),
    "hf_mf_view": CommandInfo(
        name="Просмотр Mifare Classic",
        command="hf mf view",
        category=CommandCategory.HF,
        description="Просмотр содержимого Mifare Classic"
    ),
    "hf_mf_wipe": CommandInfo(
        name="Очистка Mifare Classic",
        command="hf mf wipe",
        category=CommandCategory.HF,
        description="Полная очистка Mifare Classic",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_ndefread": CommandInfo(
        name="Чтение NDEF Mifare",
        command="hf mf ndefread",
        category=CommandCategory.HF,
        description="Чтение NDEF из Mifare Classic"
    ),
    "hf_mf_ndefformat": CommandInfo(
        name="Форматирование NDEF Mifare",
        command="hf mf ndefformat",
        category=CommandCategory.HF,
        description="Форматирование под NDEF",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_encodehid": CommandInfo(
        name="Кодирование HID Mifare",
        command="hf mf encodehid",
        category=CommandCategory.HF,
        description="Кодирование данных HID"
    ),
    "hf_mf_auth4": CommandInfo(
        name="Auth4 Mifare",
        command="hf mf auth4",
        category=CommandCategory.HF,
        description="Аутентификация по протоколу 4"
    ),
    "hf_mf_keygen": CommandInfo(
        name="Генерация ключей Mifare",
        command="hf mf keygen",
        category=CommandCategory.HF,
        description="Генерация ключей Mifare"
    ),
    "hf_mf_decrypt": CommandInfo(
        name="Дешифровка Mifare",
        command="hf mf decrypt",
        category=CommandCategory.HF,
        description="Дешифровка данных Mifare"
    ),
    "hf_mf_supercard": CommandInfo(
        name="SuperCard Mifare",
        command="hf mf supercard",
        category=CommandCategory.HF,
        description="Создание SuperCard клона"
    ),
    "hf_mf_fchk": CommandInfo(
        name="Быстрая проверка ключей",
        command="hf mf fchk",
        category=CommandCategory.HF,
        description="Быстрая проверка ключей Mifare"
    ),
    
    # HF - Mifare Classic Атаки
    "hf_mf_nested": CommandInfo(
        name="Nested атака Mifare",
        command="hf mf nested",
        category=CommandCategory.HF,
        description="Nested атака на Mifare Classic",
        risk=CommandRisk.WARNING
    ),
    "hf_mf_hardnested": CommandInfo(
        name="HardNested атака Mifare",
        command="hf mf hardnested",
        category=CommandCategory.HF,
        description="HardNested атака на Mifare Classic",
        risk=CommandRisk.WARNING
    ),
    "hf_mf_staticnested": CommandInfo(
        name="StaticNested атака Mifare",
        command="hf mf staticnested",
        category=CommandCategory.HF,
        description="StaticNested атака на Mifare Classic",
        risk=CommandRisk.WARNING
    ),
    "hf_mf_darkside": CommandInfo(
        name="DarkSide атака Mifare",
        command="hf mf darkside",
        category=CommandCategory.HF,
        description="DarkSide атака на Mifare Classic",
        risk=CommandRisk.WARNING
    ),
    "hf_mf_autopwn": CommandInfo(
        name="AutoPwn Mifare",
        command="hf mf autopwn",
        category=CommandCategory.HF,
        description="Автоматический взлом Mifare Classic",
        risk=CommandRisk.WARNING
    ),
    "hf_mf_chk": CommandInfo(
        name="Проверка ключей Mifare",
        command="hf mf chk",
        category=CommandCategory.HF,
        description="Проверка ключей Mifare Classic по словарям"
    ),
    
    # HF - Mifare Classic Запись
    "hf_mf_wrbl": CommandInfo(
        name="Запись блока Mifare",
        command="hf mf wrbl",
        category=CommandCategory.HF,
        description="Запись блока Mifare Classic",
        risk=CommandRisk.DANGEROUS,
        parameters=["<block>", "<key A/B>", "<key>", "<data>"]
    ),
    "hf_mf_cload": CommandInfo(
        name="Загрузка клона Mifare",
        command="hf mf cload",
        category=CommandCategory.HF,
        description="Загрузка дампа для клонирования"
    ),
    "hf_mf_csetblk": CommandInfo(
        name="Запись блока клону Mifare",
        command="hf mf csetblk",
        category=CommandCategory.HF,
        description="Запись блока на клон Mifare",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_csetuid": CommandInfo(
        name="Запись UID клону Mifare",
        command="hf mf csetuid",
        category=CommandCategory.HF,
        description="Запись UID на клон Mifare",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_cwipe": CommandInfo(
        name="Очистка клона Mifare",
        command="hf mf cwipe",
        category=CommandCategory.HF,
        description="Полная очистка клона Mifare",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_csave": CommandInfo(
        name="Сохранение клона Mifare",
        command="hf mf csave",
        category=CommandCategory.HF,
        description="Сохранение дампа клона Mifare"
    ),
    
    # HF - Mifare Classic Gen3/Gen4
    "hf_mf_gen3uid": CommandInfo(
        name="Запись UID Gen3",
        command="hf mf gen3uid",
        category=CommandCategory.HF,
        description="Запись UID на Gen3 карту",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gen3blk": CommandInfo(
        name="Запись блока Gen3",
        command="hf mf gen3blk",
        category=CommandCategory.HF,
        description="Запись блока на Gen3 карту",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gen3freeze": CommandInfo(
        name="Блокировка Gen3",
        command="hf mf gen3freeze",
        category=CommandCategory.HF,
        description="Блокировка изменений на Gen3",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gload": CommandInfo(
        name="Загрузка Gen4",
        command="hf mf gload",
        category=CommandCategory.HF,
        description="Загрузка дампа на Gen4 карту"
    ),
    "hf_mf_gsetblk": CommandInfo(
        name="Запись блока Gen4",
        command="hf mf gsetblk",
        category=CommandCategory.HF,
        description="Запись блока на Gen4 карту",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gchpwd": CommandInfo(
        name="Смена пароля Gen4",
        command="hf mf gchpwd",
        category=CommandCategory.HF,
        description="Изменение пароля Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmsetcfg": CommandInfo(
        name="Настройка конфигурации Gen4",
        command="hf mf gdmsetcfg",
        category=CommandCategory.HF,
        description="Настройка конфигурации Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmsetblk": CommandInfo(
        name="Запись блока DAM Gen4",
        command="hf mf gdmsetblk",
        category=CommandCategory.HF,
        description="Запись блока DAM на Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmsethidblk": CommandInfo(
        name="Запись HID блока Gen4",
        command="hf mf gdmsethidblk",
        category=CommandCategory.HF,
        description="Запись HID блока на Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmsetuid": CommandInfo(
        name="Запись UID DAM Gen4",
        command="hf mf gdmsetuid",
        category=CommandCategory.HF,
        description="Запись UID на DAM Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmwipe": CommandInfo(
        name="Очистка DAM Gen4",
        command="hf mf gdmwipe",
        category=CommandCategory.HF,
        description="Полная очистка DAM Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    "hf_mf_gdmsetsig": CommandInfo(
        name="Запись подписи Gen4",
        command="hf mf gdmsetsig",
        category=CommandCategory.HF,
        description="Запись цифровой подписи на Gen4",
        risk=CommandRisk.DANGEROUS
    ),
    
    # HF - Mifare Classic Эмуляция
    "hf_mf_sim": CommandInfo(
        name="Эмуляция Mifare Classic",
        command="hf mf sim",
        category=CommandCategory.HF,
        description="Эмуляция карты Mifare Classic"
    ),
    "hf_mf_eload": CommandInfo(
        name="Загрузка эмуляции Mifare",
        command="hf mf eload",
        category=CommandCategory.HF,
        description="Загрузка дампа для эмуляции"
    ),
    "hf_mf_esave": CommandInfo(
        name="Сохранение эмуляции Mifare",
        command="hf mf esave",
        category=CommandCategory.HF,
        description="Сохранение дампа эмулятора"
    ),
    "hf_mf_eview": CommandInfo(
        name="Просмотр эмуляции Mifare",
        command="hf mf eview",
        category=CommandCategory.HF,
        description="Просмотр содержимого эмулятора"
    ),
    "hf_mf_esetblk": CommandInfo(
        name="Запись блока эмулятора Mifare",
        command="hf mf esetblk",
        category=CommandCategory.HF,
        description="Запись блока в эмулятор"
    ),
    "hf_mf_egetblk": CommandInfo(
        name="Чтение блока эмулятора Mifare",
        command="hf mf egetblk",
        category=CommandCategory.HF,
        description="Чтение блока из эмулятора"
    ),
    "hf_mf_egetsc": CommandInfo(
        name="Чтение сектора эмулятора Mifare",
        command="hf mf egetsc",
        category=CommandCategory.HF,
        description="Чтение сектора из эмулятора"
    ),
    "hf_mf_ekeyprn": CommandInfo(
        name="Печать ключей эмулятора Mifare",
        command="hf mf ekeyprn",
        category=CommandCategory.HF,
        description="Вывод ключей эмулятора"
    ),
    "hf_mf_ecfill": CommandInfo(
        name="Заполнение эмулятора Mifare",
        command="hf mf ecfill",
        category=CommandCategory.HF,
        description="Заполнение эмулятора данными"
    ),
    "hf_mf_eclr": CommandInfo(
        name="Очистка эмулятора Mifare",
        command="hf mf eclr",
        category=CommandCategory.HF,
        description="Очистка эмулятора"
    ),
})

# Продолжение следует...
