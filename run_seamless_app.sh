#!/bin/bash
# Запуск Proxmark3 Seamless Application

echo "🔷 Proxmark3 Iceman Seamless Application"
echo "========================================"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3."
    exit 1
fi

# Проверка Tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Tkinter не установлен."
    echo "Установите командой:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  Fedora: sudo dnf install python3-tkinter"
    echo "  Arch: sudo pacman -S tk"
    exit 1
fi

# Проверка pyserial
python3 -c "import serial" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ PySerial не установлен. Установка..."
    pip3 install pyserial --user
fi

echo "✅ Все зависимости найдены"
echo "🚀 Запуск приложения..."
echo ""

# Запуск приложения
cd "$(dirname "$0")"
python3 proxmark3_seamless_app.py
