"""
Proxmark3 Easy GUI - Модуль базы данных команд
Содержит структуру команд, описания, параметры и флаги для интерфейса.
"""

COMMANDS_DB = {
    "dashboard": {
        "connect": {"label": "Подключить", "icon": "!", "desc": "Подключение к устройству", "dangerous": False},
        "disconnect": {"label": "Отключить", "icon": "!", "desc": "Отключение от устройства", "dangerous": False},
        "restart": {"label": "Перезагрузка", "icon": "!!", "desc": "Перезагрузка устройства Proxmark3", "dangerous": False, "cmd": "hw restart"},
        "status": {"label": "Статус", "icon": "!!", "desc": "Получение полной информации об устройстве", "dangerous": False, "cmd": "hw status"}
    },
    "search_read": {
        "auto_detect": {"label": "Auto-Detect (Полный поиск)", "icon": "!!", "desc": "Автоматический поиск карт LF и HF", "dangerous": False, "cmd": "search"},
        "lf_group": {
            "label": "LF (125 kHz)",
            "items": {
                "search": {"label": "Поиск LF", "icon": "!!", "desc": "Поиск известных LF тегов", "dangerous": False, "cmd": "lf search"},
                "read": {"label": "Чтение LF", "icon": "!", "desc": "Считывание сигнала LF антенны", "dangerous": False, "cmd": "lf read"},
                "em410x": {"label": "EM410x Decode", "icon": "!", "desc": "Декодирование EM410x из буфера", "dangerous": False, "cmd": "lf em 410xread"},
                "hid": {"label": "HID Decode", "icon": "!", "desc": "Декодирование HID Prox из буфера", "dangerous": False, "cmd": "lf hid fskdemod"}
            }
        },
        "hf_group": {
            "label": "HF (13.56 MHz)",
            "items": {
                "search": {"label": "Поиск HF", "icon": "!!", "desc": "Поиск известных HF тегов", "dangerous": False, "cmd": "hf search"},
                "reader": {"label": "Чтение HF", "icon": "!", "desc": "Активация поля и чтение UID", "dangerous": False, "cmd": "hf reader"},
                "list": {"label": "Список пакетов", "icon": "!", "desc": "Показать список последних пакетов", "dangerous": False, "cmd": "hf list"},
                "mf_autopwn": {"label": "Mifare Autopwn", "icon": "!!", "desc": "Автоматическая атака на Mifare Classic", "dangerous": True, "cmd": "hf mf autopwn"}
            }
        }
    },
    "memory_keys": {
        "load_dump": {"label": "Загрузить дамп", "icon": "!", "desc": "Загрузка файла .eml или .bin в слот", "dangerous": False},
        "save_dump": {"label": "Сохранить дамп", "icon": "!", "desc": "Сохранение содержимого слота в файл", "dangerous": False},
        "edit_hex": {"label": "Hex Редактор", "icon": "!", "desc": "Редактирование памяти в шестнадцатеричном виде", "dangerous": False},
        "keys_manage": {"label": "Управление ключами", "icon": "!", "desc": "Загрузка/сохранение файлов ключей", "dangerous": False},
        "mf_keys_add": {"label": "Добавить ключи", "icon": "!", "desc": "Добавить найденные ключи в таблицу", "dangerous": False, "cmd": "hf mf fkey"},
        "mf_keys_clear": {"label": "Очистить ключи", "icon": "!!", "desc": "Очистить таблицу ключей", "dangerous": True, "cmd": "hf mf clrkey"}
    },
    "write_clone": {
        "t5577_write": {"label": "Запись T5577", "icon": "!!", "desc": "Запись дампа на карту T5577", "dangerous": True, "cmd": "lf t55xx write"},
        "magic_write": {"label": "Запись Magic Card", "icon": "!!", "desc": "Запись на китайскую карту (Magic UID)", "dangerous": True, "cmd": "hf mf wrbl"},
        "clone_emu": {"label": "Клонировать в эмуляцию", "icon": "!", "desc": "Загрузить дамп в слот эмуляции", "dangerous": False},
        "restore": {"label": "Восстановление оригинала", "icon": "!!", "desc": "Попытка восстановить оригинальную карту", "dangerous": True}
    },
    "sniffing": {
        "lf_sniff": {"label": "Сниффинг LF", "icon": "!", "desc": "Перехват сигналов LF", "dangerous": False, "cmd": "lf sniff"},
        "hf_sniff": {"label": "Сниффинг HF", "icon": "!", "desc": "Перехват трафика HF (ISO14443a)", "dangerous": False, "cmd": "hf sniff"},
        "stop": {"label": "Стоп", "icon": "!", "desc": "Остановка сниффинга", "dangerous": False, "cmd": "trace stop"},
        "list": {"label": "Список трафика", "icon": "!", "desc": "Отобразить перехваченный трафик", "dangerous": False, "cmd": "trace list"},
        "save": {"label": "Сохранить дамп", "icon": "!", "desc": "Сохранить трафик в файл", "dangerous": False, "cmd": "trace save"}
    },
    "emulation": {
        "lf_sim": {"label": "Эмуляция LF", "icon": "!", "desc": "Эмуляция LF тега", "dangerous": False, "cmd": "lf sim"},
        "hf_sim": {"label": "Эмуляция HF", "icon": "!", "desc": "Эмуляция HF карты", "dangerous": False, "cmd": "hf sim"},
        "uid_change": {"label": "Сменить UID", "icon": "!", "desc": "Изменить UID для эмуляции", "dangerous": False},
        "stop": {"label": "Стоп эмуляции", "icon": "!", "desc": "Остановить эмуляцию", "dangerous": False, "cmd": "hw cancel"}
    },
    "tools_plotter": {
        "plot_show": {"label": "Показать график", "icon": "!", "desc": "Отобразить текущий сигнал", "dangerous": False, "cmd": "plot"},
        "demod_ask": {"label": "Демодуляция ASK", "icon": "!", "desc": "Демодуляция ASK сигнала", "dangerous": False, "cmd": "data askdemod"},
        "demod_fsk": {"label": "Демодуляция FSK", "icon": "!", "desc": "Демодуляция FSK сигнала", "dangerous": False, "cmd": "data fskdemod"},
        "demod_psk": {"label": "Демодуляция PSK", "icon": "!", "desc": "Демодуляция PSK сигнала", "dangerous": False, "cmd": "data pskdemod"},
        "spectrogram": {"label": "Спектрограмма", "icon": "!", "desc": "Построить спектрограмму сигнала", "dangerous": False, "cmd": "data spectr"}
    },
    "scripts": {
        "run_script": {"label": "Запустить скрипт", "icon": "!", "desc": "Выполнить выбранный Lua скрипт", "dangerous": False},
        "list_scripts": {"label": "Список скриптов", "icon": "!", "desc": "Обновить список доступных скриптов", "dangerous": False, "cmd": "script list"},
        "console": {"label": "Консоль аргументов", "icon": "!", "desc": "Ввод аргументов для скрипта", "dangerous": False}
    },
    "system": {
        "fw_update": {"label": "Обновить прошивку", "icon": "!!", "desc": "Обновление Full Image и Bootrom", "dangerous": True, "cmd": "hw flash"},
        "bootrom_update": {"label": "Обновить Bootrom", "icon": "!!", "desc": "Обновление только загрузчика", "dangerous": True, "cmd": "hw bootrom"},
        "settings": {"label": "Настройки", "icon": "!", "desc": "Настройки приложения и путей", "dangerous": False},
        "check_updates": {"label": "Проверить обновления", "icon": "!", "desc": "Проверка обновлений GUI и ProxSpace", "dangerous": False},
        "install_proxspace": {"label": "Установить ProxSpace", "icon": "!!", "desc": "Запустить мастер установки ProxSpace", "dangerous": False}
    }
}

# Группировка для выпадающих списков
DROPDOWN_GROUPS = {
    "HF Cards": ["14443a", "14443b", "15693", "felica", "legic", "iso15693", "emv", "smartcard", "piv", "mifare"],
    "LF Tags": ["em410x", "hid", "indala", "awid", "keriopass", "pac", "viking", "joop", "fido"],
    "Attack Tools": ["nonce", "darkside", "nested", "hardnested", "chk", "fkey"]
}

def get_command_info(cmd_key, category):
    """Получает информацию о команде по ключу"""
    if category in COMMANDS_DB:
        cat_data = COMMANDS_DB[category]
        if cmd_key in cat_data:
            return cat_data[cmd_key]
        # Поиск во вложенных группах
        for key, val in cat_data.items():
            if isinstance(val, dict) and "items" in val:
                if cmd_key in val["items"]:
                    return val["items"][cmd_key]
    return None
