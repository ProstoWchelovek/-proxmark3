#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для извлечения ценных файлов Proxmark3 Iceman из merged_part_*.txt
"""
import os
import re
from pathlib import Path
from collections import defaultdict

# 🛠 ИСПРАВЛЕНИЕ: Определяем папку, где лежит сам скрипт
SCRIPT_DIR = Path(__file__).parent.resolve()

# Ищем файлы и сохраняем результат в папку со скриптом
MERGED_DIR = SCRIPT_DIR
OUTPUT_DIR = SCRIPT_DIR / "proxmark3_valuable"

# Список ценных путей (нормализованные пути для поиска)
VALUABLE_PATTERNS = [
    # Клиентские команды HF/LF (КРИТИЧНО)
    r"client/src/cmdhf.*\.c",
    r"client/src/cmdlf.*\.c",
    r"client/src/cmdhf\.c",
    r"client/src/cmdlf\.c",
    # Основные файлы клиента
    r"client/src/pm3\.c",
    r"client/src/cmdmain\.c",
    r"client/src/cmdparser\.c",
    r"client/src/comms\.c",
    r"client/src/ui\.c",
    r"client/src/graph\.c",
    r"client/src/preferences\.c",
    # Заголовочные файлы
    r"client/include/.*\.h",
    r"include/.*\.h",
    # Документация
    r"doc/commands\.md",
    r"doc/commands\.json",
    r"doc/mfc_notes\.md",
    r"doc/desfire\.md",
    r"doc/iclass_.*\.md",
    r"doc/README\.md",
    r"doc/CHANGELOG\.md",
    r"doc/cheatsheet\.md",
    r"doc/cliparser\.md",
    r"doc/T5577_Guide\.md",
    r"doc/magic_cards_notes\.md",
    r"doc/emv_notes\.md",
    r"doc/standalone/.*",
    # Lua скрипты и библиотеки
    r"client/lualibs/.*\.lua",
    r"client/luascripts/.*\.lua",
    # Python скрипты
    r"client/pyscripts/.*\.py",
    # Словари ключей
    r"client/dictionaries/.*\.dic",
    # Ресурсы JSON
    r"client/resources/.*\.json",
    # Исходники прошивки (armsrc)
    r"armsrc/.*\.c",
    # FPGA код
    r"fpga/.*\.v",
    # Конфигурации сборки
    r"client/CMakeLists\.txt",
    r"client/Makefile",
    # Утилиты
    r"tools/pm3_tests\.sh",
    r"tools/pm3_online_check\.py",
    r"tools/findbits\.py",
]

def compile_patterns():
    """Компилируем regex паттерны для быстрого поиска"""
    return [re.compile(p, re.IGNORECASE) for p in VALUABLE_PATTERNS]

def normalize_path(path):
    """Нормализуем путь для сравнения"""
    path = re.sub(r"^(pm3/|proxmark3/)", "", path, flags=re.IGNORECASE)
    path = path.strip().strip('"').strip("'").strip()
    return path.replace("\\", "/").lower()

def is_valuable_file(filepath, patterns):
    """Проверяем, является ли файл ценным"""
    normalized = normalize_path(filepath)
    return any(pattern.search(normalized) for pattern in patterns)

def extract_files_from_merged(merged_file, patterns, output_dir):
    """Извлекает ценные файлы из merged_part_*.txt"""
    print(f"📄 Обработка {merged_file.name}...")
    current_file = None
    current_content = []
    extracted_count = 0
    
    # Универсальный паттерн для поиска начала файла
    file_start_pattern = re.compile(
        r"^(?:File:\s*|===\s*FILE:\s*|=====\s*НАЧАЛО\s+ФАЙЛА:\s*)(.+?)(?:\s*===*)?$", 
        re.IGNORECASE
    )
    
    try:
        with open(merged_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                file_match = file_start_pattern.match(line.strip())
                if file_match:
                    if current_file and is_valuable_file(current_file, patterns):
                        save_extracted_file(current_file, current_content, output_dir)
                        extracted_count += 1
                    
                    current_file = file_match.group(1).strip()
                    current_content = []
                elif current_file is not None:
                    current_content.append(line)
            
            if current_file and is_valuable_file(current_file, patterns):
                save_extracted_file(current_file, current_content, output_dir)
                extracted_count += 1
                
    except Exception as e:
        print(f"   ⚠️ Ошибка чтения {merged_file.name}: {e}")
        
    return extracted_count

def save_extracted_file(filepath, content, output_dir):
    """Сохраняет извлечённый файл"""
    clean_path = re.sub(r"^(pm3/|proxmark3/)", "", filepath, flags=re.IGNORECASE)
    clean_path = clean_path.strip().strip('"').strip("'").strip().replace("\\", "/")
    
    dest_path = output_dir / clean_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.writelines(content)
    except Exception as e:
        print(f"   ⚠️ Ошибка записи {dest_path}: {e}")

def main():
    print("🚀 Извлечение ценных файлов Proxmark3 Iceman")
    print("=" * 60)
    print(f"📂 Папка скрипта: {SCRIPT_DIR}")
    
    patterns = compile_patterns()
    print(f"✅ Загружено {len(patterns)} паттернов для поиска")
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"📁 Выходная папка: {OUTPUT_DIR}")
    
    # Ищем файлы в папке, где лежит скрипт
    merged_files = sorted(MERGED_DIR.glob("merged_part_*.txt"))
    if not merged_files:
        print(f"❌ Файлы merged_part_*.txt не найдены в папке {MERGED_DIR}!")
        print("💡 Убедитесь, что скрипт и файлы merged_part_*.txt лежат в одной папке.")
        return
        
    print(f"📂 Найдено {len(merged_files)} файлов для обработки")
    
    total_extracted = 0
    for i, merged_file in enumerate(merged_files, 1):
        print(f"\n[{i}/{len(merged_files)}]")
        count = extract_files_from_merged(merged_file, patterns, OUTPUT_DIR)
        total_extracted += count
        print(f"   ✅ Извлечено файлов: {count}")
        
    print("\n" + "=" * 60)
    print(f"🎉 ГОТОВО! Извлечено {total_extracted} ценных файлов")
    print(f"📁 Результат в: {OUTPUT_DIR}")
    
    # Статистика по типам файлов
    stats = defaultdict(int)
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            ext = Path(f).suffix.lower() or "(без расширения)"
            stats[ext] += 1
            
    print("\n📊 Структура извлечённых файлов:")
    for ext, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {ext:15} : {count} файлов")

if __name__ == "__main__":
    main()