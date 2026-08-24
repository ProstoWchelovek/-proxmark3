#!/usr/bin/env python3
"""
Скрипт для извлечения ценных файлов Proxmark3 Iceman из merged_part_*.txt
Извлекает: исходный код, документацию, скрипты, словари, конфиги
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Пути
MERGED_DIR = Path("весьproxspace")
OUTPUT_DIR = Path("proxmark3_valuable")

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
    # Удаляем префиксы pm3/, proxmark3/
    path = re.sub(r"^(pm3/|proxmark3/)", "", path, flags=re.IGNORECASE)
    # Нормализуем разделители
    path = path.replace("\\", "/")
    return path.lower()

def is_valuable_file(filepath, patterns):
    """Проверяем, является ли файл ценным"""
    normalized = normalize_path(filepath)
    for pattern in patterns:
        if pattern.search(normalized):
            return True
    return False

def extract_files_from_merged(merged_file, patterns, output_dir):
    """Извлекает ценные файлы из merged_part_*.txt"""
    print(f"📄 Обработка {merged_file.name}...")
    
    current_file = None
    current_content = []
    extracted_count = 0
    
    try:
        with open(merged_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Ищем начало файла: "File: path/to/file.ext" или "=== FILE: path ==="
                file_match = re.match(r"^(?:File:\s*|===\s*FILE:\s*)(.+)$", line.strip(), re.IGNORECASE)
                
                if file_match:
                    # Сохраняем предыдущий файл если он ценный
                    if current_file and is_valuable_file(current_file, patterns):
                        save_extracted_file(current_file, current_content, output_dir)
                        extracted_count += 1
                    
                    # Начинаем новый файл
                    current_file = file_match.group(1).strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)
        
        # Сохраняем последний файл
        if current_file and is_valuable_file(current_file, patterns):
            save_extracted_file(current_file, current_content, output_dir)
            extracted_count += 1
            
    except Exception as e:
        print(f"   ⚠️ Ошибка чтения {merged_file.name}: {e}")
    
    return extracted_count

def save_extracted_file(filepath, content, output_dir):
    """Сохраняет извлечённый файл"""
    normalized = normalize_path(filepath)
    
    # Создаём полную структуру папок
    dest_path = output_dir / normalized
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.writelines(content)
    except Exception as e:
        print(f"   ⚠️ Ошибка записи {dest_path}: {e}")

def main():
    print("🚀 Извлечение ценных файлов Proxmark3 Iceman")
    print("=" * 60)
    
    # Компилируем паттерны
    patterns = compile_patterns()
    print(f"✅ Загружено {len(patterns)} паттернов для поиска")
    
    # Создаём выходную директорию
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"📁 Выходная папка: {OUTPUT_DIR.absolute()}")
    
    # Находим все merged_part_*.txt
    merged_files = sorted(MERGED_DIR.glob("merged_part_*.txt"))
    print(f"📂 Найдено {len(merged_files)} файлов для обработки")
    
    if not merged_files:
        print("❌ Файлы merged_part_*.txt не найдены!")
        return
    
    total_extracted = 0
    
    # Обрабатываем каждый файл
    for i, merged_file in enumerate(merged_files, 1):
        print(f"\n[{i}/{len(merged_files)}]")
        count = extract_files_from_merged(merged_file, patterns, OUTPUT_DIR)
        total_extracted += count
        print(f"   ✅ Извлечено файлов: {count}")
    
    print("\n" + "=" * 60)
    print(f"🎉 ГОТОВО! Извлечено {total_extracted} ценных файлов")
    print(f"📁 Результат в: {OUTPUT_DIR.absolute()}")
    print("\n📊 Структура извлечённых файлов:")
    
    # Показываем статистику
    stats = defaultdict(int)
    for root, dirs, files in os.walk(OUTPUT_DIR):
        rel_path = Path(root).relative_to(OUTPUT_DIR)
        for f in files:
            ext = Path(f).suffix or "(no ext)"
            stats[ext] += 1
    
    for ext, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {ext}: {count} файлов")

if __name__ == "__main__":
    main()
