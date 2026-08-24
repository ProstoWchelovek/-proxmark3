#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для извлечения ценных файлов Proxmark3 Iceman из merged_part_*.txt
"""

import os
import re
import glob
from pathlib import Path

# Паттерны для поиска ценных файлов
VALUABLE_PATTERNS = [
    # Критичные C-файлы клиента для GUI
    r'client/src/cmdhf.*\.c',
    r'client/src/cmdlf.*\.c',
    r'client/src/pm3\.c',
    r'client/src/cmdmain\.c',
    r'client/src/comms\.c',
    r'client/src/cmdparser\.c',
    r'client/src/cliparser\.c',
    
    # Документация
    r'doc/commands\.md',
    r'doc/commands\.json',
    r'doc/mfc_notes\.md',
    r'doc/desfire\.md',
    r'doc/unofficial_desfire_bible\.md',
    r'doc/emv_notes\.md',
    r'doc/iclass.*\.md',
    r'doc/mfu.*\.md',
    r'doc/T5577_Guide\.md',
    r'doc/magic_cards_notes\.md',
    r'doc/trace_notes\.md',
    r'doc/cliparser\.md',
    r'README\.md',
    r'CHANGELOG\.md',
    
    # Lua библиотеки
    r'client/lualibs/.*\.lua',
    
    # Lua скрипты
    r'client/luascripts/.*\.lua',
    
    # Python скрипты
    r'client/pyscripts/.*\.py',
    
    # Словари ключей
    r'client/dictionaries/.*\.dic',
    
    # JSON ресурсы
    r'client/resources/.*\.json',
    r'client/resources/calypso/.*\.json',
    r'client/resources/felica/.*\.json',
    
    # Заголовочные файлы (API)
    r'include/.*\.h',
    r'client/include/.*\.h',
    
    # Прошивка (armsrc)
    r'armsrc/.*\.c',
    r'armsrc/.*\.h',
    
    # FPGA код
    r'fpga/.*\.v',
    r'fpga/.*\.sv',
    
    # Утилиты
    r'tools/.*\.py',
    r'tools/.*\.sh',
    
    # Трейсы (для понимания протоколов)
    r'traces/README\.md',
]

def extract_files():
    """Извлекает ценные файлы из merged_part_*.txt"""
    
    input_dir = Path('/workspace/весьproxspace')
    output_dir = input_dir / 'proxmark3_valuable'
    
    # Создаем выходную папку
    output_dir.mkdir(exist_ok=True)
    
    # Находим все merged_part_*.txt
    merged_files = sorted(glob.glob(str(input_dir / 'merged_part_*.txt')))
    
    if not merged_files:
        print("❌ Файлы merged_part_*.txt не найдены!")
        return
    
    print(f"📂 Найдено {len(merged_files)} файлов для обработки")
    print(f"📁 Выходная папка: {output_dir}")
    
    # Компилируем паттерны
    compiled_patterns = [re.compile(p) for p in VALUABLE_PATTERNS]
    
    # Статистика
    total_files = 0
    extracted_count = 0
    
    # Регулярка для извлечения пути файла из содержимого
    # Формат: pm3/proxmark3/client/src/cmdhf.c или client/src/cmdhf.c
    file_path_pattern = re.compile(r'^((?:pm3/)?(?:proxmark3/)?)(.+)$', re.MULTILINE)
    
    current_file = None
    current_content = []
    in_file = False
    
    for merged_file in merged_files:
        print(f"🔄 Обработка {os.path.basename(merged_file)}...")
        
        with open(merged_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.rstrip('\n\r')
                
                # Проверяем, начинается ли новый файл
                # Формат: ===== НАЧАЛО ФАЙЛА: path/to/file.c =====
                file_marker = re.match(r'^=====\s*НАЧАЛО\s+ФАЙЛА:\s*(.+?)\s*=====', line)
                
                if file_marker:
                    # Сохраняем предыдущий файл если был
                    if in_file and current_file and should_extract(current_file, compiled_patterns):
                        save_file(output_dir, current_file, current_content)
                        extracted_count += 1
                    
                    # Начинаем новый файл
                    current_file = file_marker.group(1).strip()
                    current_content = []
                    in_file = True
                    total_files += 1
                
                elif in_file:
                    # Проверяем конец файла (следующий НАЧАЛО ФАЙЛА означает конец текущего)
                    if re.match(r'^=====\s*НАЧАЛО\s+ФАЙЛА:', line):
                        # Это уже обработано выше, пропускаем
                        pass
                    elif line.startswith('=====') and 'КОНЕЦ' in line:
                        # Явный конец файла
                        if current_file and should_extract(current_file, compiled_patterns):
                            save_file(output_dir, current_file, current_content)
                            extracted_count += 1
                        in_file = False
                        current_file = None
                        current_content = []
                    else:
                        current_content.append(line)
    
    # Сохраняем последний файл если остался
    if in_file and current_file and should_extract(current_file, compiled_patterns):
        save_file(output_dir, current_file, current_content)
        extracted_count += 1
    
    print("\n" + "="*60)
    print(f"✅ Готово!")
    print(f"📊 Всего файлов в архивах: {total_files}")
    print(f"💎 Извлечено ценных файлов: {extracted_count}")
    print(f"📁 Результат в: {output_dir}")
    print("="*60)

def should_extract(file_path, compiled_patterns):
    """Проверяет, соответствует ли путь файла паттернам ценных файлов"""
    # Нормализуем путь
    file_path = file_path.replace('\\', '/')
    
    for pattern in compiled_patterns:
        if pattern.search(file_path):
            return True
    return False

def save_file(output_dir, file_path, content):
    """Сохраняет файл в выходную директорию"""
    # Нормализуем путь
    file_path = file_path.replace('\\', '/')
    
    # Убираем префиксы pm3/proxmark3/ если есть
    for prefix in ['pm3/proxmark3/', 'proxmark3/', 'pm3/']:
        if file_path.startswith(prefix):
            file_path = file_path[len(prefix):]
            break
    
    # Создаем полный путь
    full_path = output_dir / file_path
    
    # Создаем директории
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Записываем файл
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
    except Exception as e:
        print(f"⚠️  Ошибка записи {file_path}: {e}")

if __name__ == '__main__':
    print("🚀 Извлечение ценных файлов Proxmark3 Iceman")
    print("="*60)
    extract_files()
