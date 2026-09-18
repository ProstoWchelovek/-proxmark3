@echo off
chcp 65001 >nul
title ProxMaster Ultimate - Запуск

echo ╔═══════════════════════════════════════════════════════════╗
echo ║           ProxMaster Ultimate v1.0.0                      ║
echo ║     Полноценное GUI для управления Proxmark3              ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ошибка: Python не найден!
    echo Установите Python 3.8+ с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

REM Создание виртуального окружения (если нет)
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo 🔧 Активация окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo 📥 Проверка зависимостей...
pip install pyserial --quiet

REM Запуск приложения
echo.
echo 🚀 Запуск ProxMaster Ultimate...
echo.
python main_app.py

if errorlevel 1 (
    echo.
    echo ❌ Произошла ошибка при запуске!
    echo.
    pause
)
